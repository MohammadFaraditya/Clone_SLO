from datetime import datetime
from flask import Blueprint, jsonify, request
import jwt, os
from functools import wraps
from db import get_db_connection, release_db_connection
from psycopg2.extras import RealDictCursor, execute_values

salesman_team_bp = Blueprint('salesman_team', __name__, url_prefix='/salesman-team')
SECRET_KEY = os.getenv("SECRET_KEY", "dev_secret")

# Middleware: untuk verifikasi token
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({"error": "Token tidak ditemukan"}), 401
        try:
            jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        except Exception:
            return jsonify({"error": "Token tidak valid atau kedaluwarsa"}), 401
        return f(*args, **kwargs)
    return decorated

#GET DATA SALESMAN TEAM
@salesman_team_bp.route('/data', methods=['GET'])
@token_required
def get_area():
    try:
        offset = int(request.args.get('offset', 0))
    except Exception:
        offset = 0
    try:
        limit = int(request.args.get('limit', 50))
    except Exception:
        limit = 50

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor) 

    cursor.execute("""
        SELECT id, description, createdate, createby, updatedate, updateby
        FROM salesman_team
        ORDER BY id
        LIMIT %s OFFSET %s
    """, (limit, offset))
    data = cursor.fetchall()

    cursor.execute("SELECT COUNT(1) AS total FROM salesman_team")
    total_row = cursor.fetchone()
    total_count = total_row['total'] if total_row else 0

    cursor.close()
    conn.close()
    release_db_connection(conn)

    return jsonify({
        "data": data,
        "offset": offset,
        "limit": limit,
        "total": total_count
    }), 200



#INSERT DATA SALESMAN TEAM
@salesman_team_bp.route('/insert', methods=['POST'])
@token_required
def insert_salesman_team():
    data = request.json
    if not data or not isinstance(data, list):
        return jsonify({"error": "Data tidak valid"}), 400
    
    #BULK INSERT
    rows = []
    ids = []

    for row in data:
        id_salesman_team = row.get("id") or row.get("id") 
        description = row.get("description")
        createby = row.get("createby")
        createdate = row.get("createdate")

        rows.append((id_salesman_team, description, createdate, createby))
        ids.append(id_salesman_team)

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute(
        "SELECT id from salesman_team where id = ANY(%s)",
        (ids,)
    )

    existing_rows = cur.fetchall()
    existing_ids = [row["id"] for row in existing_rows] if existing_rows else []

    rows_to_insert = [r for r in rows if r[0] not in existing_ids]

    inserted_count = 0
    if rows_to_insert:
        insert_sql = """
        INSERT INTO salesman_team (id, description, createdate, createby)
        VALUES %s
        """
        
        execute_values(cur, insert_sql, rows_to_insert, page_size=500)
        inserted_count = len(rows_to_insert)

    conn.commit()
    cur.close()
    release_db_connection(conn)

    #pesan hasil insert
    if existing_ids:
        return jsonify({
            "message": f"{inserted_count} record berhasil ditambahkan, {len(existing_ids)} record ditolak (sudah ada di database).",
            "duplicate_ids": existing_ids
        }), 200
    else:
        return jsonify({
            "message": f"Semua {inserted_count} record berhasil ditambahkan."
        }), 200


# Update salesman team
@salesman_team_bp.route('/update/<id>', methods=['PUT'])
@token_required
def update_area_route(id):
    payload = request.json
    description = payload.get("description")
    updateby = payload.get("updateby") 

    if not description or not updateby:
        return jsonify({"error": "DESCRIPTION dan UPDATEBY harus diisi"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE salesman_team SET description=%s, updatedate=%s, updateby=%s WHERE id=%s",
            (description, datetime.now(), updateby, id)
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()
        return jsonify({"error": str(e)}), 500

    cursor.close()
    conn.close()
    release_db_connection(conn)
    return jsonify({"message": f"salesman team {id} berhasil diupdate"}), 200


# delete salesman team
@salesman_team_bp.route('/delete', methods=['DELETE'])
@token_required
def delete_salesman_team():
    payload = request.json
    ID = payload.get("ids", [])

    if not ID or not isinstance(ID, list):
        return jsonify({"error": "Harus mengirim list ID"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        format_strings = ",".join(["%s"] * len(ID))
        cursor.execute(f"DELETE FROM salesman_team WHERE id IN ({format_strings})", tuple(ID))
        conn.commit()
    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()
        return jsonify({"error": str(e)}), 500

    cursor.close()
    conn.close()
    release_db_connection(conn)
    return jsonify({"message": f"{len(ID)} area berhasil dihapus"}), 200

