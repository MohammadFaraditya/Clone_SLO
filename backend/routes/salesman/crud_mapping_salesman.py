from datetime import datetime
from flask import Blueprint, jsonify, request
import jwt, os
from functools import wraps
from db import get_db_connection, release_db_connection
from psycopg2.extras import RealDictCursor, execute_values

mapping_salesman_bp = Blueprint('mapping_salesman', __name__, url_prefix='/mapping-salesman')
SECRET_KEY = os.getenv('SECRET_KEY', "dev_secret")

# Middleware untuk verifikasi token
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({"error" : "Token tidak ditemukan"}), 401
        try:
            jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        except Exception:
            return jsonify({"error" : "Token tidak valid atau kedaluwarsa"}), 401
        return f(*args, **kwargs)
    return decorated  

# GET DATA MAPPING SALESMAN
@mapping_salesman_bp.route('/data', methods=['GET'])
@token_required
def get_mapping_salesman():
    try:
        offset = int(request.args.get('offset', 0))
    except Exception:
        offset = 0

    try:
        limit = int(request.args.get('limit', 50))
    except Exception:
        limit = 50

    kodebranch = request.args.get('kodebranch')

    if not kodebranch:
        return jsonify({
            "error": "Harus menggunakan filter kodebranch"
        }), 400

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:
        
        cursor.execute("""
                SELECT sm.kodebranch, b.nama_branch, sm.id_salesman, sm.nama, ms.id_salesman_dist, ms.nama_salesman_dist, ms.createdate, ms.createby, ms.updatedate, ms.updateby
                FROM mapping_salesman ms 
                INNER JOIN salesman_master sm ON ms.id_salesman = sm.id_salesman
                INNER JOIN branch b ON sm.kodebranch = b.kodebranch
                WHERE sm.kodebranch = %s
                LIMIT %s OFFSET %s
            """, (kodebranch, limit, offset))
        data = cursor.fetchall()

        cursor.execute("""
                SELECT COUNT(1) AS total
                FROM mapping_salesman ms 
                INNER JOIN salesman_master sm ON ms.id_salesman = sm.id_salesman
                WHERE sm.kodebranch = %s
            """, (kodebranch,))
        

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

#INSERT DATA MAPPING SALESMAN
@mapping_salesman_bp.route('/insert', methods=['POST'])
@token_required
def insert_entity():
    data = request.json

    if not data or not isinstance(data, list):
        return jsonify({"error": "Data tidak valid"}), 400

    # Ambil data dari request
    rows = []
    ids = []

    for row in data:
        id_salesman = row.get("id_salesman")
        nama_salesman = row.get("nama_salesman")
        id_salesman_dist = row.get("id_salesman_dist")
        nama_salesman_dist = row.get("nama_salesman_dist")
        createby = row.get("createby")
        createdate = row.get("createdate")

        rows.append((id_salesman, nama_salesman, id_salesman_dist,
                     nama_salesman_dist, createdate, createby))
        ids.append(id_salesman)

    # CEK DUPLIKAT INTERNAL (dalam file Excel)
    seen = set()
    duplicate_internal = []

    for sid in ids:
        if sid in seen:
            duplicate_internal.append(sid)
        else:
            seen.add(sid)

    # Filter rows agar duplikat internal tidak ikut di-insert
    rows_no_internal = [r for r in rows if r[0] not in duplicate_internal]

    # KONEKSI DATABASE
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # CEK DUPLIKAT DI DATABASE
    cur.execute("""
        SELECT id_salesman 
        FROM mapping_salesman 
        WHERE id_salesman = ANY(%s)
    """, (ids,))

    existing_rows = cur.fetchall()
    existing_ids = [row["id_salesman"] for row in existing_rows] if existing_rows else []

    # VALIDASI id_salesman ADA DI TABEL salesman_master
    cur.execute("""
        SELECT id_salesman 
        FROM salesman_master 
        WHERE id_salesman = ANY(%s)
    """, (ids,))

    salesman_rows = cur.fetchall()
    valid_id_salesman = [row["id_salesman"] for row in salesman_rows] if salesman_rows else []

    # FILTER INVALID
    invalid_id_salesman_rows = [r for r in rows_no_internal if r[0] not in valid_id_salesman]

    # hanya yang valid saja
    rows_valid = [r for r in rows_no_internal if r[0] in valid_id_salesman]

    # FILTER DUPLIKAT DATABASE
    rows_to_insert = [r for r in rows_valid if r[0] not in existing_ids]

    # INSERT DATA
    inserted_count = 0

    if rows_to_insert:
        insert_sql = """
            INSERT INTO mapping_salesman
            (id_salesman, nama_salesman, id_salesman_dist, nama_salesman_dist, createdate, createby)
            VALUES %s
        """

        execute_values(cur, insert_sql, rows_to_insert, page_size=500)
        inserted_count = len(rows_to_insert)

    conn.commit()
    cur.close()
    release_db_connection(conn)

    # RESULT API
    return jsonify({
        "message": f"{inserted_count} record berhasil ditambahkan",
        "duplicate_internal": list(set(duplicate_internal)),
        "duplicate_ids_db": existing_ids,
        "invalid_id_salesman": list(set([r[0] for r in invalid_id_salesman_rows])),
        "skipped_duplicate_internal": len(duplicate_internal),
        "skipped_duplicate_db": len(existing_ids),
        "skipped_invalid_id_salesman": len(invalid_id_salesman_rows)
    }), 200

#UPDATE ENTITY
@mapping_salesman_bp.route('/update/<id_salesman>', methods=['PUT'])
@token_required
def update_entity_route(id_salesman):
    payload = request.json
    id_salesman_dist = payload.get("id_salesman_dist")
    nama_salesman_dist = payload.get("nama_salesman_dist")
    updateby = payload.get("updateby")

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "UPDATE mapping_salesman SET id_salesman_dist=%s, nama_salesman_dist=%s, updatedate=%s, updateby=%s where id_salesman=%s ",
            (id_salesman_dist,nama_salesman_dist, datetime.now(), updateby, id_salesman)
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
    return jsonify({"message": f" Entity {id_salesman} berhasil diupdate"}), 200

# DELETE MAPPING SALESMAN
@mapping_salesman_bp.route('/delete', methods=['DELETE'])
@token_required
def delete_entity_route():
    payload = request.json
    id_salesman = payload.get("ids", [])

    if not id_salesman or not isinstance(id_salesman, list):
        return jsonify({"error": "Harus mengirim list id_salesman"}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        format_strings = ",".join(["%s"] * len(id_salesman))
        cursor.execute(f"DELETE FROM mapping_salesman where id_salesman IN ({format_strings})", tuple(id_salesman))
        conn.commit()
    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()
        return jsonify({"error": str(e)}), 500
    
    cursor.close()
    conn.close()
    release_db_connection(conn)
    return jsonify({"message" : f"{len(id_salesman)} entity berhasil dihapus"}),200