from datetime import datetime
from flask import Blueprint, jsonify, request
import jwt, os
from functools import wraps
from db import get_db_connection, release_db_connection
from psycopg2.extras import RealDictCursor, execute_values

region_bp = Blueprint('region', __name__, url_prefix='/region')
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

# GET DATA REGION
@region_bp.route('/data', methods=['GET'])
@token_required
def get_region():
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
        SELECT koderegion, keterangan, pin, createdate, createby, updatedate, updateby
        FROM region
        ORDER BY koderegion
        LIMIT %s OFFSET %s
    """, (limit, offset))
    data = cursor.fetchall()

    cursor.execute("SELECT COUNT(1) AS total FROM region")
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

#INSERT DATA REGION
@region_bp.route('/insert', methods=['POST'])
@token_required
def insert_region():
    data = request.json
    if not data or not isinstance(data, list):
        return jsonify({"error": "Data tidak valid"}), 400

    #bulk insert
    rows = []
    ids = []
    
    for row in data:
        koderegion = row.get("koderegion") or row.get("koderegion") 
        keterangan = row.get("keterangan")
        pin = row.get("pin")
        createby = row.get("createby")
        createdate = row.get("createdate")

        rows.append((koderegion, keterangan, pin, createdate, createby))
        ids.append(koderegion)

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute(
        "SELECT koderegion from region where koderegion = ANY(%s)",
        (ids,)
    )

    existing_rows = cur.fetchall()
    existing_ids = [row["koderegion"] for row in existing_rows] if existing_rows else []

    rows_to_insert = [r for r in rows if r[0] not in existing_ids]

    inserted_count = 0
    if rows_to_insert:
        insert_sql = """
        INSERT INTO region (koderegion, keterangan, pin, createdate, createby)
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


# Update region
@region_bp.route('/update/<koderegion>', methods=['PUT'])
@token_required
def update_area_route(koderegion):
    payload = request.json
    keterangan= payload.get("keterangan")
    pin = payload.get("pin")
    updateby = payload.get("updateby")

    if not keterangan or not updateby or not pin:
        return jsonify({"error": "keterangan, pin dan updateby harus diisi"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE region SET keterangan=%s, pin=%s, updatedate=%s, updateby=%s WHERE koderegion=%s",
            (keterangan,pin, datetime.now(), updateby, koderegion)
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
    return jsonify({"message": f"Region {koderegion} berhasil diupdate"}), 200

# delete region
@region_bp.route('/delete', methods=['DELETE'])
@token_required
def delete_region():
    payload = request.json
    koderegion = payload.get("ids", [])

    if not koderegion or not isinstance(koderegion, list):
        return jsonify({"error": "Harus mengirim list koderegion"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        format_strings = ",".join(["%s"] * len(koderegion))
        cursor.execute(f"DELETE FROM region WHERE koderegion IN ({format_strings})", tuple(koderegion))
        conn.commit()
    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()
        return jsonify({"error": str(e)}), 500

    cursor.close()
    conn.close()
    release_db_connection(conn)
    return jsonify({"message": f"{len(koderegion)} region berhasil dihapus"}), 200

