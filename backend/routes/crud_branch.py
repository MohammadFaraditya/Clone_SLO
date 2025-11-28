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
        INNER JOIN region r ON r.koderegion = r.koderegion
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
    
    #BULK INSERT
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
        createdate = row.get("createdate")
        createby = row.get("createby")

        rows.append((kodebranch,nama_branch,koderegion,entity,alamat,id_area,createdate,createby))
        ids.append(kodebranch)
        koderegions.append(koderegion)
        kodeentity.append(entity)
        id_areas.append(id_area)

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    #CEK DUPLIKAT BRANCH
    cur.execute(
        "SELECT kodebranch from branch where kodebranch = ANY(%s)",
        (ids, )
    )

    existing_rows = cur.fetchall()
    existing_ids = [row["koderegion"] for row in existing_rows] if existing_rows else []

    #CEK VALIDASI KODEREGION
    cur.execute(
        "SELECT koderegion from region where koderegion = ANY(%s)",
        (koderegions, )
    )

    region_rows = cur.fetchall()
    valid_koderegion = [row["koderegion"] for row in region_rows] if region_rows else []

    #CEK VALIDASI ENTITY
    cur.execute(
        "SELECT id_entity from entity where entity = ANY(%s)",
        (kodeentity, )
    )

    entity_rows = cur.fetchall()
    valid_entity = [row["id_entity"] for row in entity_rows] if entity_rows else []

    #CEK VALIDASI AREA
    cur.execute(
        "SELECT id_area from area where area = ANY(%s)",
        (id_areas, )
    )

    area_rows = cur.fetchall()
    valid_area = [row['id_area'] for row in area_rows] if area_rows else []

    invalid_region_rows = [r for r in rows if r[2] not in valid_koderegion]
    invalid_entity_rows = [r for r in rows if r[3] not in valid_entity]
    invalid_area_rows = [r for r in rows if r[5] not in valid_area]

    valid_region_rows = [r for r in rows if r[2] in valid_koderegion]
    valid_entity_rows = [r for r in rows if r[3] in valid_entity]
    valid_area_rows = [r for r in rows if r[5] in valid_area]

    #INSERT VALID DATA
    rows_valid = [r for r in rows if r[2] in valid_region_rows and r[3] in valid_entity_rows and r[5] in valid_area_rows]
    rows_to_insert = [r for r in rows_valid if r[0] not in existing_ids]

    inserted_count = 0
    if rows_to_insert:
        insert_sql = """
        INSERT INTO branch (kodebranch, nama_branch, koderegion, entity, alamat, id_area, createdate, createby)
        VALUES %s
        """

        execute_values(cur, insert_sql, rows_to_insert, page_size=500)
        inserted_count = len(rows_to_insert)

    conn.commit()
    cur.close()
    release_db_connection(conn)

    return jsonify({
        "message" : f"{inserted_count} record berhasil ditambahkan",
        "duplicate_ids" : existing_ids,
        "invalid_koderegion" : list(set([r[2] for r in invalid_region_rows])),
        "invalid_entity" : list(set([r[3] for r in invalid_entity_rows])),
        "invalid_area" : list(set([r[5] for r in invalid_area_rows])),
        "skipped_invalid_region" : len(invalid_region_rows),
        "skipped_invalid_entity" : len(invalid_entity_rows),
        "skipped_invalid_area" : len(invalid_area_rows),
        "skipped_duplicate" : len(existing_ids)
    }), 200



    
