from datetime import datetime
from flask import Blueprint, jsonify, request
import jwt, os
from functools import wraps
from db import get_db_connection, release_db_connection
from psycopg2.extras import RealDictCursor, execute_values

area_bp = Blueprint('area', __name__, url_prefix='/area')
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

# Get all data area
@area_bp.route('/data', methods=['GET'])
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
        SELECT id_area, description, createdate, createby, updatedate, updateby
        FROM area
        ORDER BY id_area
        LIMIT %s OFFSET %s
    """, (limit, offset))
    data = cursor.fetchall()

    cursor.execute("SELECT COUNT(1) as total FROM area")
    total_row = cursor.fetchone();
    total_count = total_row['total'] if total_row else 0
    conn.close()
    release_db_connection(conn) 

    return jsonify({
        "data": data,
        "offset": offset,
        "limit": limit,
        "total": total_count
    }), 200

# Insert data area
@area_bp.route('/insert', methods=['POST'])
@token_required
def insert_area():
    data = request.json 
    if not data or not isinstance(data, list):
        return jsonify({"error": "Data tidak valid"}), 400
    
    #bulk insert
    rows =[]
    ids = []
    for row in data:
        id_area = row.get("id_area")
        description = row.get("description")
        createby = row.get("createby")
        createdate = row.get("createdate")

        rows.append((id_area, description, createby, createdate))
        ids.append(id_area)

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # cari id duplikat
    cur.execute(
        "SELECT id_area FROM area WHERE id_area = ANY(%s)",
        (ids,)
    )

    existing_rows = cur.fetchall()
    existing_ids = [row["id_area"] for row in existing_rows] if existing_rows else []

    # id data yang tidak duplikat
    rows_to_insert = [r for r in rows if r[0] not in existing_ids]

    inserted_count = 0
    if rows_to_insert:
        insert_sql = """
        INSERT INTO area (id_area, description, createby, createdate)
        VALUES %s
        """    
        execute_values(cur, insert_sql, rows_to_insert, page_size=500)
        inserted_count = len(rows_to_insert)
    
    conn.commit()
    cur.close()
    release_db_connection(conn)

    # 🔹 Buat pesan hasil insert
    if existing_ids:
        return jsonify({
            "message": f"{inserted_count} record berhasil ditambahkan, {len(existing_ids)} record ditolak (sudah ada di database).",
            "duplicate_ids": existing_ids
        }), 200
    else:
        return jsonify({
            "message": f"Semua {inserted_count} record berhasil ditambahkan."
        }), 200

# Update area
@area_bp.route('/update/<id_area>', methods=['PUT'])
@token_required
def update_area_route(id_area):
    payload = request.json
    description = payload.get("description")
    updateby = payload.get("updateby") 

    if not description or not updateby:
        return jsonify({"error": "DESCRIPTION dan UPDATEBY harus diisi"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE area SET description=%s, updatedate=%s, updateby=%s WHERE id_area=%s",
            (description, datetime.now(), updateby, id_area)
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()
        release_db_connection(conn)
        return jsonify({"error": str(e)}), 500

    cursor.close()
    conn.close()
    release_db_connection(conn)
    return jsonify({"message": f"Area {id_area} berhasil diupdate"}), 200

# Delete area
@area_bp.route('/delete', methods=['DELETE'])
@token_required
def delete_areas_route():
    payload = request.json
    id_areas = payload.get("ids", [])

    if not id_areas or not isinstance(id_areas, list):
        return jsonify({"error": "Harus mengirim list ID_AREA"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        format_strings = ",".join(["%s"] * len(id_areas))
        cursor.execute(f"DELETE FROM area WHERE id_area IN ({format_strings})", tuple(id_areas))
        conn.commit()
    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()
        return jsonify({"error": str(e)}), 500

    cursor.close()
    conn.close()
    release_db_connection(conn)
    return jsonify({"message": f"{len(id_areas)} area berhasil dihapus"}), 200
