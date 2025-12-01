from datetime import datetime
from flask import Blueprint, jsonify, request
import jwt, os
from functools import wraps
from db import get_db_connection, release_db_connection
from psycopg2.extras import RealDictCursor, execute_values

branch_dist_bp = Blueprint('branch_dist', __name__, url_prefix='/branch-dist')
SECRET_KEY = os.getenv('SECRET_KEY', "dev_secret")

# MIDDLEWARE VERIFIKASI TOKEN
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({"error" : "Token tidak ditemukan"}), 401
        try:
            jwt.decode(token, SECRET_KEY, algorithms='HS256')
        except Exception:
            return jsonify({"error" : "Token tidak valid atau kedaluwarsa"}), 401
        return f(*args, **kwargs)
    return decorated

# GET DATA BRANCH DIST
@branch_dist_bp.route('/data', mehods=['GET'])
@token_required
def get_branch_dist():
    try:
        offset = int((request.args.get('offset', 0)))
    except Exception:
        offset = 0
    try:
        limit = int(request.args.get('limit', 50))
    except Exception:
        limit = 50
    
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute("""
        SELECT * FROM branch_dist
        ORDER BY branch_dist
        LIMIT %s OFFSET %s
    """, (limit, offset))

    data = cursor.fetchall()

    cursor.execute("SELECT COUNT(1) AS TOTAL FROM branch_dist")
    total_row = cursor.fetchone()
    total_count = total_row['total'] if total_row else 0

    cursor.close()
    conn.close()
    release_db_connection(conn)

    return jsonify({
        "data" : data,
        "offset" : offset,
        "limit" : limit,
        "total" : total_count
    }), 200

# INSERT DATA ENTITY
@branch_dist_bp.route('/insert', methods=['POST'])
@token_required
def insert_branch_dist():
    data = request.json
    if not data or not isinstance(data, list):
        return jsonify({"error" : "Data tidak valid"}), 400
    
    # BULK INSERT
    rows = []
    ids = []
    for row in data:
        branch_dist = row.get("branch_dist")
        nama_branch_dist = row.get("nama_branch_dist")
        alamat = row.get("alamat")
        createby = row.get("createby")
        createdate = row.get("createdate")

        rows.append((branch_dist, nama_branch_dist, alamat, createdate, createby))
        ids.append(branch_dist)
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # CEK DUPLIKAT
    cur.execute(
        "SELECT branch_dist FROM branch_dist where branch_dist = ANY(%s)",
        (ids, )
    )

    existing_rows = cur.fetchall()
    existing_ids = [row["branch_dist"] for row in existing_rows] if existing_rows else []

    rows_to_insert = [r for r in rows if r[0] not in existing_ids]

    inserted_count = 0
    if rows_to_insert:
        insert_sql = """
        INSERT INTO branch_dist (branch_dist, nama_branch_dist, alamat, createdate, createby)
        VALUES %s
        """
        execute_values(cur, insert_sql, rows_to_insert, page_size=500)
        inserted_count = len(rows_to_insert)

    conn.commit()
    cur.close()
    release_db_connection(conn)

    # PESAN HASIL INSERT
    if existing_ids:
        return jsonify({
            "message" : f"{inserted_count} record berhasil ditambahkan, {len(existing_ids)} recoed ditolak (sudah ada di database)",
            "duplicate_ids" : existing_ids
        }), 200
    else: return jsonify({
        "message" : f"Semua {inserted_count} record berhasil ditambahkan"
    }), 200

# UPDATE BRANCH DIST
@branch_dist_bp.route('/update/<branch_dist>', methods=['PUT'])
@token_required
def update_branch_dist_route(branch_dist):
    payload = request.json
    nama_branch_dist = payload.get("nama_branch_dist")
    alamat = payload.get("alamat")
    updateby = payload.get("updateby")

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE branch_dist SET nama_branch_dist=%s, alamat=%s, updatedate=%s, updateby=%s WHERE branch_dist=%s",
            (nama_branch_dist, alamat, datetime.now(), updateby, branch_dist)
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
    return jsonify({"message" : f"Branch_Dist {branch_dist} berhasil diupdate"}), 200

# DELETE AREA
@branch_dist_bp.route('\delete', methods=['DELETE'])
@token_required
def delete_branch_dist_route():
    payload = request.json
    branch_dist = payload.get("ids", [])

    if not branch_dist or not isinstance(branch_dist, list):
        return jsonify({"error" : "Harus mengirim list branch dist"}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        format_strings = ",".join(["%s"] * len(branch_dist))
        cursor.execute(f"DELETE FROM branch_dist WHERE branch_dist IN ({format_strings})", tuple(branch_dist))
        conn.commit()
    except Exception as e: 
        conn.rollback()
        cursor.close()
        conn.close()
        return jsonify({"error" : str(e)}), 500
    
    cursor.close()
    conn.close()
    release_db_connection(conn)
    return jsonify({"message" : f"{len(branch_dist)} branch dist berhasil dihapus"}), 200