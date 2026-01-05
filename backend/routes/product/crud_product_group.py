from datetime import datetime
from flask import Blueprint, jsonify, request
import jwt, os, uuid
from functools import wraps
from db import get_db_connection, release_db_connection
from psycopg2.extras import RealDictCursor, execute_values

product_group_bp = Blueprint('product_group',__name__, url_prefix='/product-group')
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

# GET DATA PRODUCT GROUP
@product_group_bp.route('/data', methods=['GET'])
@token_required
def get_product_prc():
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

    try:
        cursor.execute("""
                SELECT pg.group_code, pg.brand, pg.pcode, pp.pcodename, pg.product_group_1, pg.product_group_2, pg.product_group_3, pg.category_item,
                pg.vtkp, pg.npd, pg.createdate, pg.createby, pg.updatedate, pg.updateby 
                FROM product_group pg
                INNER JOIN product_prc pp ON pg.pcode = pp.pcode
                ORDER BY pg.pcode
                LIMIT %s OFFSET %s
            """, (limit, offset))
        data = cursor.fetchall()

        cursor.execute("""
                SELECT COUNT(1) AS total
                FROM product_group
            """,)
        

        total_row = cursor.fetchone()
        total_count = total_row["total"] if total_row else 0

        return jsonify({
            "data": data,
            "offset": offset,
            "limit": limit,
            "total": total_count
        }), 200
    
    finally:
        release_db_connection(conn)


#INSERT DATA PRODUCT GROUP
@product_group_bp.route('/insert', methods=['POST'])
@token_required
def insert_product_prc():
    data = request.json
    if not data or not isinstance(data, list):
        return jsonify({"error": "Data tidak valid"}), 400

    rows = []
    pcodes = []
    seen_in_batch = set() # Tambahan: Untuk melacak pcode unik dalam satu file upload
    duplicate_in_file = [] # Untuk mencatat jika ada pcode ganda di file yang sama

    for row in data:
        pcode = str(row.get("pcode")).strip() if row.get("pcode") else None
        
        if not pcode:
            continue

        # Proteksi 1: Cek apakah pcode muncul dua kali di dalam FILE yang sama
        if pcode in seen_in_batch:
            duplicate_in_file.append(pcode)
            continue
            
        group_code = row.get("group_code")
        brand = row.get("brand")
        product_group_1 = row.get("product_group_1")
        product_group_2 = row.get("product_group_2")
        product_group_3 = row.get("product_group_3")
        category_item = row.get("category_item")
        vtkp = row.get("vtkp")
        npd = row.get("npd")
        createdate = row.get("createdate") or datetime.now()
        createby = row.get("createby") or "SYSTEM"

        rows.append((group_code, brand, pcode, product_group_1, product_group_2, product_group_3, category_item, vtkp, npd, createdate, createby))
        pcodes.append(pcode)
        seen_in_batch.add(pcode)

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # Proteksi 2: Cek apakah pcode sudah ada di DATABASE
    cur.execute("SELECT pcode FROM product_group WHERE pcode = ANY(%s)", (pcodes,))
    existing_group = {row["pcode"] for row in cur.fetchall()}

    # Proteksi 3: Pastikan pcode terdaftar di MASTER PRC
    cur.execute("SELECT pcode FROM product_prc WHERE pcode = ANY(%s)", (pcodes,))
    valid_prc = {row["pcode"] for row in cur.fetchall()}

    # Filter akhir sebelum insert
    rows_to_insert = [
        r for r in rows
        if r[2] not in existing_group and r[2] in valid_prc
    ]

    inserted_count = len(rows_to_insert)
    duplicate_pcode_db = list(existing_group)
    invalid_pcode_master = list(set(pcodes) - valid_prc)

    if rows_to_insert:
        insert_sql = """
        INSERT INTO product_group
        (group_code, brand, pcode, product_group_1, product_group_2, product_group_3, category_item, vtkp, npd, createdate, createby)
        VALUES %s
        """
        execute_values(cur, insert_sql, rows_to_insert, page_size=500)

    conn.commit()
    cur.close()
    release_db_connection(conn)

    return jsonify({
        "message": f"{inserted_count} record berhasil ditambahkan",
        "inserted": inserted_count,
        "duplicate_in_database": duplicate_pcode_db,
        "duplicate_in_this_file": list(set(duplicate_in_file)),
        "not_registered_in_product_prc": invalid_pcode_master
    }), 200



# UPDATE PRODUCT GROUP
@product_group_bp.route('/update/<pcode>', methods=['PUT'])
@token_required
def update_pcode_prc(pcode):
    payload = request.json
    product_group_1 = payload.get("product_group_1")
    product_group_2 = payload.get("product_group_2")
    product_group_3 = payload.get("product_group_3")
    category_item = payload.get("category_item")
    vtkp = payload.get("vtkp")
    npd = payload.get("npd")
    updateby = payload.get("updateby") or "SYSTEM"

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            UPDATE product_group 
            SET product_group_1=%s,
                product_group_2=%s,
                product_group_3=%s,
                category_item=%s,
                vtkp=%s,
                npd=%s,
                updatedate=%s,
                updateby=%s
            WHERE pcode=%s
            """,
            (product_group_1, product_group_2, product_group_3, category_item, vtkp, npd, datetime.now(), updateby, pcode)
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        release_db_connection(conn)
        return jsonify({"error": str(e)}), 500

    release_db_connection(conn)
    return jsonify({"message": f"Product Group pada {pcode} berhasil diupdate"}), 200

# DELETE CUSTOMER PRC
@product_group_bp.route('/delete', methods=['DELETE'])
@token_required
def delete_product_prc_route():
    payload = request.json
    pcode = payload.get("ids", [])

    if not pcode or not isinstance(pcode, list):
        return jsonify({"error": "Harus mengirim list pcode"}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        format_strings = ",".join(["%s"] * len(pcode))
        cursor.execute(f"DELETE FROM product_group where pcode IN ({format_strings})", tuple(pcode))
        conn.commit()
    except Exception as e:
        conn.rollback()
        
        return jsonify({"error": str(e)}), 500
    
    release_db_connection(conn)
    return jsonify({"message" : f"{len(pcode)}  berhasil dihapus"}),200