from datetime import datetime
from flask import Blueprint, jsonify, request
import jwt, os
from functools import wraps
from db import get_db_connection, release_db_connection
from psycopg2.extras import RealDictCursor, execute_values

salesman_master_bp = Blueprint('salesman_master',__name__, url_prefix='/salesman-master')
SECRET_KEY = os.getenv('SECRET_KEY', 'dev_secret')

#MIDDLEWARE TOKEN
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({"error" : "Token tidak ditemukan"}), 401
        try:
            jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        except Exception:
            return jsonify({"error" : "Token tidak valid atau kadaluwarsa"}), 401
        return f(*args, **kwargs)
    return decorated

# GET DATA SALESMAN MASTER
@salesman_master_bp.route('/data', methods=['GET'])
@token_required
def get_salesman_master():
    try:
        offset = int(request.args.get('offset', 0))
    except Exception:
        offset = 0

    try:
        limit = int(request.args.get('limit', 50))
    except Exception:
        limit = 50

    kodebranch = request.args.get('kodebranch')
    salesman_team = request.args.get('salesman_team')

    # kodebranch wajib
    if not kodebranch:
        return jsonify({
            "error": "Harus menggunakan filter kodebranch"
        }), 400

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # CASE 1: Hanya kodebranch
        if not salesman_team:
            cursor.execute("""
                SELECT *
                FROM salesman_master
                WHERE kodebranch = %s
                LIMIT %s OFFSET %s
            """, (kodebranch, limit, offset))
            data = cursor.fetchall()

            cursor.execute("""
                SELECT COUNT(1) AS total
                FROM salesman_master
                WHERE kodebranch = %s
            """, (kodebranch,))
        
        # CASE 2: Kodebranch + salesman_team
        else:
            cursor.execute("""
                SELECT *
                FROM salesman_master
                WHERE kodebranch = %s AND salesman_team = %s
                LIMIT %s OFFSET %s
            """, (kodebranch, salesman_team, limit, offset))
            data = cursor.fetchall()

            cursor.execute("""
                SELECT COUNT(1) AS total
                FROM salesman_master
                WHERE kodebranch = %s AND salesman_team = %s
            """, (kodebranch, salesman_team))

        total_row = cursor.fetchone()
        total_count = total_row["total"] if total_row else 0

        return jsonify({
            "data": data,
            "offset": offset,
            "limit": limit,
            "total": total_count
        }), 200
    
    finally:
        cursor.close()
        conn.close()
        release_db_connection(conn)

# INSERT DATA SALESMAN MASTER
@salesman_master_bp.route('/insert', methods=['POST'])
@token_required
def insert_salesman_master():
    data = request.json
    if not data or not isinstance(data, list):
        return jsonify({"error": "Data tidak valid"}), 400

    rows = []
    ids = []
    id_teams = []
    kodebranches = []

    for row in data:
        id_salesman = row.get("id_salesman")
        nama = row.get("nama")
        id_team = row.get("id_team")
        kodebranch = row.get("kodebranch")

        createdate = row.get("createdate") or datetime.now()
        createby = row.get("createby") or "SYSTEM"

        rows.append((id_salesman, nama, id_team, None, kodebranch, None, createdate, createby))
        ids.append(id_salesman)
        id_teams.append(id_team)
        kodebranches.append(kodebranch)

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # CEK DUPLIKAT id_salesman
    cur.execute("SELECT id_salesman FROM salesman_master WHERE id_salesman = ANY(%s)", (ids,))
    existing_rows = cur.fetchall()
    existing_ids = [r["id_salesman"] for r in existing_rows] if existing_rows else []

    # CEK id_team VALID
    cur.execute("SELECT id, description FROM salesman_team WHERE id = ANY(%s)", (id_teams,))
    team_rows = cur.fetchall()
    valid_teams = {r["id"]: r["description"] for r in team_rows}

    # CEK kodebranch VALID
    cur.execute("SELECT kodebranch, nama_branch FROM branch WHERE kodebranch = ANY(%s)", (kodebranches,))
    branch_rows = cur.fetchall()
    valid_branches = {r["kodebranch"]: r["nama_branch"] for r in branch_rows}

    # FILTER VALID ROWS DAN ISI salesman_team & nama_branch
    rows_valid = []
    for r in rows:
        id_salesman, nama, id_team, _, kodebranch, _, createdate, createby = r
        if id_salesman in existing_ids:
            continue
        if id_team not in valid_teams or kodebranch not in valid_branches:
            continue
        salesman_team_desc = valid_teams[id_team]
        nama_branch_val = valid_branches[kodebranch]
        rows_valid.append((id_salesman, nama, id_team, salesman_team_desc, kodebranch, nama_branch_val, createdate, createby))

    # INSERT DATA
    inserted_count = 0
    if rows_valid:
        insert_sql = """
        INSERT INTO salesman_master 
        (id_salesman, nama, id_team, salesman_team, kodebranch, nama_branch, createdate, createby)
        VALUES %s
        """
        execute_values(cur, insert_sql, rows_valid, page_size=500)
        inserted_count = len(rows_valid)

    conn.commit()
    cur.close()
    release_db_connection(conn)

    # INFO INVALIDS
    invalid_teams = list(set([r[2] for r in rows if r[2] not in valid_teams]))
    invalid_branches = list(set([r[4] for r in rows if r[4] not in valid_branches]))

    return jsonify({
        "message": f"{inserted_count} record berhasil ditambahkan",
        "duplicate_ids": existing_ids,
        "invalid_id_team": invalid_teams,
        "invalid_kodebranch": invalid_branches,
        "skipped_duplicate": len(existing_ids)
    }), 200

# UPDATE SALESMAN MASTER
@salesman_master_bp.route('/update/<id_salesman>', methods=['PUT'])
@token_required
def update_branch_route(id_salesman):
    payload = request.json
    nama = payload.get("nama")
    updateby = payload.get("updateby")

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "UPDATE salesman_master SET nama=%s, updatedate=%s, updateby=%s where id_salesman=%s",
            (nama, datetime.now(), updateby, id_salesman)
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()
        release_db_connection(conn)
        return jsonify({"error" : str(e)}), 500

    cursor.close()
    conn.close()
    release_db_connection(conn)
    return jsonify({"message": f"ID Salesman {id_salesman} berhasil diupdate"}), 200

# DELETE SALESMAN MASTER
@salesman_master_bp.route('delete', methods=['DELETE'])
@token_required
def delete_entity_route():
    payload = request.json
    id_salesman = payload.get("ids", [])

    if not id_salesman or not isinstance(id_salesman, list):
        return jsonify({"error" : "Harus mengirim list id salesman"}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        format_strings = ",".join(["%s"] * len(id_salesman))
        cursor.execute(f"DELETE FROM salesman_master WHERE id_salesman IN ({format_strings})", tuple(id_salesman))
        conn.commit()
    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()
        release_db_connection(conn)
        return jsonify({"error" : str(e)}), 500
    
    cursor.close()
    conn.close()
    release_db_connection(conn)
    return jsonify({"message" : f"{len(id_salesman)} salesman berhasil dihapus"}), 200



