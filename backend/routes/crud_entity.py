from datetime import datetime
from flask import Blueprint, jsonify, request
import jwt, os
from functools import wraps
from db import get_db_connection, release_db_connection
from psycopg2.extras import RealDictCursor, execute_values

entity_bp = Blueprint('entity', __name__, url_prefix='/entity')
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

# GET DATA ENTITY
@entity_bp.route('/data', methods=['GET'])
@token_required
def get_entity():
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
        SELECT r.koderegion, r.keterangan as nama_region, e.* 
        FROM entity e
        INNER JOIN region r on e.koderegion = r.koderegion
        ORDER BY e.id_entity
        LIMIT %s OFFSET %s
        """, (limit, offset))
    data = cursor.fetchall()

    cursor.execute("SELECT COUNT(1) AS TOTAL FROM entity")
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

#INSERT DATA ENTITY
@entity_bp.route('/insert', methods=['POST'])
@token_required
def insert_region():
    data = request.json
    if not data or not isinstance(data, list):
        return jsonify({"error": "Data tidak valid"}), 400

    #bulk insert
    rows = []
    ids = []
    koderegions = []

    for row in data:
        id_entity = row.get("id_entity")
        keterangan = row.get("keterangan")
        koderegion = row.get("koderegion")
        createby = row.get("createby")
        createdate = row.get("createdate")

        rows.append((id_entity, keterangan, koderegion, createdate, createby))
        ids.append(id_entity)
        koderegions.append(koderegion)

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # CEK DUPLIKAT ID ENTITY
    cur.execute(
        "select id_entity from entity where id_entity = ANY(%s)",
        (ids,)
    )

    existing_rows = cur.fetchall()
    existing_ids = [row["id_entity"] for row in existing_rows] if existing_rows else []

    #CEK VALIDASI KODEREGION
    cur.execute(
        "select koderegion from region where koderegion = ANY(%s)",
        (koderegions,)
    )

    region_rows = cur.fetchall()
    valid_koderegion = [row["koderegion"] for row in region_rows] if region_rows else []

    # ROW INVALID KODEREGION
    invalid_region_rows = [r for r in rows if r[2] not in valid_koderegion]

    # FILTER OUT INVALID KODEREGION
    rows_valid_region = [r for r in rows if r[2] in valid_koderegion]

    # FILTER OUT DUPLIKAT
    rows_to_insert = [r for r in rows_valid_region if r[0] not in existing_ids]

    inserted_count = 0
    if rows_to_insert:
        insert_sql = """
        INSERT INTO entity (id_entity, keterangan, koderegion, createdate, createby)
        VALUES %s
        """

        execute_values(cur, insert_sql, rows_to_insert, page_size=500)
        inserted_count = len(rows_to_insert)

    conn.commit()
    cur.close()
    release_db_connection(conn)

    # 🔹 Buat pesan hasil insert
    return jsonify({
        "message": f"{inserted_count} record berhasil ditambahkan",
        "duplicate_ids": existing_ids,
        "invalid_koderegion": list(set([r[2] for r in invalid_region_rows])),
        "skipped_duplicate": len(existing_ids),
        "skipped_invalid_region": len(invalid_region_rows)
    }), 200
    

#UPDATE ENTITY
@entity_bp.route('/update/<id_entity>', methods=['PUT'])
@token_required
def update_entity_route(id_entity):
    payload = request.json
    keterangan = payload.get("keterangan")
    updateby = payload.get("updateby")

    if not keterangan or not updateby:
        return jsonify({"error" : "keterangan dan updateby harus diisi"}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "UPDATE entity SET keterangan=%s, updatedate=%s, updateby=%s where id_entity=%s",
            (keterangan, datetime.now(), updateby, id_entity)
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
    return jsonify({"message": f"Area {id_entity} berhasil diupdate"}), 200


#DELETE ENTITY
@entity_bp.route('/delete', methods=['DELETE'])
@token_required
def delete_entity_route():
    payload = request.json
    id_entity = payload.get("ids", [])

    if not id_entity or not isinstance(id_entity, list):
        return jsonify({"error": "Harus mengirim list id_entity"}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        format_strings = ",".join(["%s"] * len(id_entity))
        cursor.execute(f"DELETE FROM entity where id_entity IN ({format_strings})", tuple(id_entity))
        conn.commit()
    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()
        return jsonify({"error": str(e)}), 500
    
    cursor.close()
    conn.close()
    release_db_connection(conn)
    return jsonify({"message" : f"{len(id_entity)} entity berhasil dihapus"}),200