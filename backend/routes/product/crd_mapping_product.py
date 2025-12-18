from datetime import datetime
from flask import Blueprint, jsonify, request
import jwt, os
from functools import wraps
from db import get_db_connection, release_db_connection
from psycopg2.extras import RealDictCursor, execute_values

mapping_product_bp = Blueprint('mapping_product',__name__, url_prefix='/mapping-product')
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

# GET DATA MAPPING PRODUCT
@mapping_product_bp.route('/data', methods=['GET'])
@token_required
def get_mapping_product():
    try:
        offset = int(request.args.get('offset', 0))
    except Exception:
        offset = 0

    try:
        limit = int(request.args.get('limit', 50))
    except Exception:
        limit = 50

    kodebranch = request.args.get('branch_dist')

    if not kodebranch:
        return jsonify({
            "error": "Harus menggunakan filter kodebranch"
        }), 400

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cursor.execute("""
                SELECT * FROM mapping_product
                WHERE branch_dist = %s
                LIMIT %s OFFSET %s
            """, (kodebranch, limit, offset))
        data = cursor.fetchall()

        cursor.execute("""
                SELECT COUNT(1) AS total
                FROM mapping_product 
                WHERE branch_dist = %s
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
        release_db_connection(conn)

#INSERT DATA MAPPING PRODUCT
@mapping_product_bp.route('/insert', methods=['POST'])
@token_required
def insert_mapping_customer():
    data = request.json
    if not data or not isinstance(data, list):
        return jsonify({"error": "Data tidak valid"}), 400

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # Ambil semua pcode_prc & pcode_dist dari request
    pcodes_prc = [str(row.get("pcode_prc")).strip() for row in data]
    pcodes_dist = [str(row.get("pcode_dist")).strip() for row in data]

    # CEK DUPLIKAT di mapping_product
    cur.execute(
        "SELECT pcode_prc, pcode_dist FROM mapping_product WHERE pcode_prc = ANY(%s) AND pcode_dist = ANY(%s)",
        (pcodes_prc, pcodes_dist)
    )
    existing_rows = cur.fetchall()
    existing_pairs = {(r["pcode_prc"], r["pcode_dist"]) for r in existing_rows}

    # Ambil data product_prc
    cur.execute(
        "SELECT pcode, pcodename FROM product_prc WHERE pcode = ANY(%s)",
        (pcodes_prc,)
    )
    pcode_prc_data = {r["pcode"]: r for r in cur.fetchall()}

    # Ambil data product_dist
    cur.execute(
        "SELECT pcode_dist, pcodename, branch_dist FROM product_dist WHERE pcode_dist = ANY(%s)",
        (pcodes_dist,)
    )
    pcode_dist_data = {r["pcode_dist"]: r for r in cur.fetchall()}

    rows_valid = []
    skipped_prc = []
    skipped_dist = []
    skipped_duplicate = []

    for row in data:
        pcode_prc = str(row.get("pcode_prc")).strip()
        pcode_dist = str(row.get("pcode_dist")).strip()
        branch_dist = row.get("branch_dist")
        createby = row.get("createby") or "SYSTEM"
        createdate = row.get("createdate") or datetime.now()

        # CEK DUPLIKAT
        if (pcode_prc, pcode_dist) in existing_pairs:
            skipped_duplicate.append((pcode_prc, pcode_dist))
            continue

        # CEK PRODUCT PRC
        prc_data = pcode_prc_data.get(pcode_prc)
        if not prc_data or prc_data["pcode"] != pcode_prc:
            skipped_prc.append(pcode_prc)
            continue
        pcodename_prc = prc_data["pcodename"]

        # CEK CUSTOMER DIST
        dist_data = pcode_dist_data.get(pcode_dist)
        if not dist_data or dist_data["branch_dist"] != branch_dist:
            skipped_dist.append(pcode_dist)
            continue
        pcodename_dist = dist_data["pcodename"]

        # Jika semua valid → tambahkan ke list insert
        rows_valid.append((
            pcode_prc,
            pcodename_prc,
            pcode_dist,
            pcodename_dist,
            createdate,
            createby,
            branch_dist
        ))

    # INSERT DATA
    inserted_count = 0
    if rows_valid:
        insert_sql = """
            INSERT INTO mapping_product
            (pcode_prc, pcode_prc_name, pcode_dist, pcode_dist_name, createdate, createby, branch_dist)
            VALUES %s
        """
        execute_values(cur, insert_sql, rows_valid, page_size=500)
        inserted_count = len(rows_valid)

    conn.commit()
    cur.close()
    release_db_connection(conn)

    return jsonify({
        "message": f"{inserted_count} record berhasil ditambahkan",
        "skipped_duplicate": skipped_duplicate,
        "skipped_invalid_prc": skipped_prc,
        "skipped_invalid_dist": skipped_dist
    }), 200

# DELETE MAPPING CUSTOMER
@mapping_product_bp.route('/delete', methods=['DELETE'])
@token_required
def delete_mapping_product():
    payload = request.json
    pcode_pairs = payload.get("ids", [])

    if not pcode_pairs or not isinstance(pcode_pairs, list):
        return jsonify({"error": "Harus mengirim list pasangan pcode_prc & pcode_dist"}), 400

    valid_pairs = [
        (p.get("pcode_prc"), p.get("pcode_dist"))
        for p in pcode_pairs
        if p.get("pcode_prc") and p.get("pcode_dist")
    ]

    if not valid_pairs:
        return jsonify({"error": "Tidak ada data valid untuk dihapus"}), 400

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        values_sql = ",".join(
            cur.mogrify("(%s, %s)", pair).decode()
            for pair in valid_pairs
        )

        delete_sql = f"""
            DELETE FROM mapping_product
            WHERE (pcode_prc, pcode_dist) IN ({values_sql})
        """

        cur.execute(delete_sql)
        conn.commit()

    except Exception as e:
        conn.rollback()
        cur.close()
        release_db_connection(conn)
        return jsonify({"error": str(e)}), 500

    cur.close()
    release_db_connection(conn)
    return jsonify({"message": f"{len(valid_pairs)} record berhasil dihapus"}), 200