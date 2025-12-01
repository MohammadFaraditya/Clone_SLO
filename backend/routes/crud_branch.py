from datetime import datetime
from flask import Blueprint, jsonify, request
import jwt, os
from functools import wraps
from db import get_db_connection, release_db_connection
from psycopg2.extras import RealDictCursor, execute_values

branch_bp = Blueprint('branch', __name__, url_prefix='/branch')
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

#GET DATA BRANCH
@branch_bp.route('/data', methods=['GET'])
@token_required
def get_branch():
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
        SELECT b.koderegion, r.keterangan as nama_region, b.entity, e.keterangan as nama_entity,
        b.kodebranch, b.nama_branch, b.alamat, b.id_area, b.createdate,
        b.createby, b.updatedate, b.updateby, b.host, b.ftp_user, b.ftp_password
        FROM branch b
        INNER JOIN entity e ON b.entity = e.id_entity
        INNER JOIN region r ON r.koderegion = e.koderegion
        ORDER BY b.kodebranch
        LIMIT %s OFFSET %s
    """, (limit, offset))
    data = cursor.fetchall()

    cursor.execute("SELECT COUNT(1) AS TOTAL FROM branch")
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

#INSERT DATA BRANCH
@branch_bp.route('/insert', methods=['POST'])
@token_required
def insert_branch():
    data = request.json
    if not data or not isinstance(data, list):
        return jsonify({"error": "Data tidak valid"}), 400

    rows = []
    ids = []
    koderegions = []
    kodeentity = []
    id_areas = []

    for row in data:
        kodebranch = row.get("kodebranch")
        nama_branch = row.get("nama_branch")
        koderegion = row.get("koderegion")
        entity = row.get("entity")
        alamat = row.get("alamat")
        id_area = row.get("id_area")
        host = row.get("host")
        ftp_user = row.get("ftp_user")
        ftp_password = row.get("ftp_password")

        createdate = row.get("createdate") or datetime.now()
        createby = row.get("createby") or "SYSTEM"

        rows.append((kodebranch, nama_branch, koderegion, entity, alamat, id_area, host, ftp_user, ftp_password, createdate, createby))

        ids.append(kodebranch)
        koderegions.append(koderegion)
        kodeentity.append(entity)
        id_areas.append(id_area)

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # CEK DUPLIKAT
    cur.execute("SELECT kodebranch FROM branch WHERE kodebranch = ANY(%s)", (ids,))
    existing_rows = cur.fetchall()
    existing_ids = [row["kodebranch"] for row in existing_rows] if existing_rows else []

    # CEK KODEREGION VALID
    cur.execute("SELECT koderegion FROM region WHERE koderegion = ANY(%s)", (koderegions,))
    region_rows = cur.fetchall()
    valid_koderegion = [row["koderegion"] for row in region_rows]

    # CEK ENTITY VALID
    cur.execute("SELECT id_entity FROM entity WHERE id_entity = ANY(%s)", (kodeentity,))
    entity_rows = cur.fetchall()
    valid_entity = [row["id_entity"] for row in entity_rows]

    # CEK AREA VALID
    cur.execute("SELECT id_area FROM area WHERE id_area = ANY(%s)", (id_areas,))
    area_rows = cur.fetchall()
    valid_area = [row["id_area"] for row in area_rows]

    # FILTER VALID ROWS
    rows_valid = [
        r for r in rows
        if r[2] in valid_koderegion and r[3] in valid_entity and (r[5] in valid_area or r[5] is None)
    ]

    # HAPUS YG DUPLIKAT
    rows_to_insert = [r for r in rows_valid if r[0] not in existing_ids]

    inserted_count = 0
    if rows_to_insert:
        insert_sql = """
        INSERT INTO branch (kodebranch, nama_branch, koderegion, entity, alamat, id_area, host, ftp_user, ftp_password, createdate, createby)
        VALUES %s
        """
        execute_values(cur, insert_sql, rows_to_insert, page_size=500)
        inserted_count = len(rows_to_insert)

    conn.commit()
    cur.close()
    release_db_connection(conn)

    return jsonify({
        "message": f"{inserted_count} record berhasil ditambahkan",
        "duplicate_ids": existing_ids,
        "invalid_koderegion": list(set([r[2] for r in rows if r[2] not in valid_koderegion])),
        "invalid_entity": list(set([r[3] for r in rows if r[3] not in valid_entity])),
        "invalid_area": list(set([r[5] for r in rows if r[5] not in valid_area])),
        "skipped_duplicate": len(existing_ids)
    }), 200


# UPDATE DATA BRANCH
@branch_bp.route('/update/<kodebranch>', methods=['PUT'])
@token_required
def update_branch_route(kodebranch):
    payload = request.json
    nama_branch = payload.get("nama_branch")
    alamat = payload.get("alamat")
    host = payload.get("host")
    ftp_user = payload.get("ftp_user")
    ftp_password = payload.get("ftp_password")
    updateby = payload.get("updateby")

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "UPDATE branch SET nama_branch=%s, alamat=%s, host=%s, ftp_user=%s, ftp_password=%s, updatedate=%s, updateby=%s where kodebranch=%s",
            (nama_branch, alamat, host, ftp_user, ftp_password, datetime.now(), updateby, kodebranch)
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
    return jsonify({"message": f"Branch {kodebranch} berhasil diupdate"}), 200

# DELETE BRANCH
@branch_bp.route('delete', methods=['DELETE'])
@token_required
def delete_entity_route():
    payload = request.json
    kodebranch = payload.get("ids", [])

    if not kodebranch or not isinstance(kodebranch, list):
        return jsonify({"error" : "Harus mengirim list kodebranch"}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        format_strings = ",".join(["%s"] * len(kodebranch))
        cursor.execute(f"DELETE FROM branch WHERE kodebranch IN ({format_strings})", tuple(kodebranch))
        conn.commit()
    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()
        return jsonify({"error" : str(e)}), 500
    
    cursor.close()
    conn.close()
    release_db_connection(conn)
    return jsonify({"message" : f"{len(kodebranch)} branch berhasil dihapus"}), 200


    
