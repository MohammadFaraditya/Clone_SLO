from datetime import datetime
from flask import Blueprint, jsonify, request
import jwt, os
from functools import wraps
from db import get_db_connection, release_db_connection
from psycopg2.extras import RealDictCursor, execute_values

product_prc_bp = Blueprint('product_prc',__name__, url_prefix='/product-prc')
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

# GET DATA PRODUCT PRC
@product_prc_bp.route('/data', methods=['GET'])
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
                SELECT prlin, prlinname, pcode, pcodename, unit1, unit2, unit3,
                convunit2, convunit3, createdate, createby, updatedate, updateby 
                FROM product_prc
                ORDER BY prlin
                LIMIT %s OFFSET %s
            """, (limit, offset))
        data = cursor.fetchall()

        cursor.execute("""
                SELECT COUNT(1) AS total
                FROM product_prc 
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


#INSERT DATA PRODUCT PRC
@product_prc_bp.route('/insert', methods=['POST'])
@token_required
def insert_product_prc():
    data = request.json
    if not data or not isinstance(data, list):
        return jsonify({"error": "Data tidak valid"}), 400

    rows = []
    ids = []

    for row in data:
        prlin = row.get("prlin")
        prlinname = row.get("prlinname")
        pcode = row.get("pcode")
        pcodename = row.get("pcodename")
        unit1 = row.get("unit1")
        unit2 = row.get("unit2")
        unit3 = row.get("unit3")
  
        convunit2 = row.get("convunit2")
        convunit3 = row.get("convunit3")
        createdate = row.get("createdate") or datetime.now()
        createby = row.get("createby") or "SYSTEM"

        rows.append((pcode, pcodename, unit1, unit2, unit3, convunit2, convunit3, createdate, createby, prlin, prlinname))

        ids.append(pcode)  

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # Cek DUPLIKAT di database
    cur.execute("SELECT pcode FROM product_prc WHERE pcode = ANY(%s)", (ids,))
    existing_rows = cur.fetchall()
    existing_ids = [row["pcode"] for row in existing_rows] if existing_rows else []

    rows_to_insert = [r for r in rows if r[0] not in existing_ids]

    

    # Insert data
    inserted_count = 0
    if rows_to_insert:
        insert_sql = """
        INSERT INTO product_prc
        (pcode, pcodename, unit1, unit2, unit3, convunit2, convunit3, createdate, createby, prlin, prlinname)
        VALUES %s
        """
        execute_values(cur, insert_sql, rows_to_insert, page_size=500)
        inserted_count = len(rows_to_insert)

    conn.commit()
    release_db_connection(conn)

    return jsonify({
        "message": f"{inserted_count} record berhasil ditambahkan",
        "duplicate_ids": list(existing_ids),
        "skipped_duplicate": len(existing_ids)
    }), 200

# UPDATE PRODUCT PRC
@product_prc_bp.route('/update/<pcode>', methods=['PUT'])
@token_required
def update_pcode_prc(pcode):
    payload = request.json
    pcodename = payload.get("pcodename")
    unit1 = payload.get("unit1")
    unit2 = payload.get("unit2")
    unit3 = payload.get("unit3")
    convunit2 = payload.get("convunit2")
    convunit3 = payload.get("convunit3")
    prlin = payload.get("prlin")
    prlinname = payload.get("prlinname")
    updateby = payload.get("updateby")

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "UPDATE product_prc SET pcodename=%s, unit1=%s, unit2=%s, unit3=%s, convunit2=%s, convunit3=%s, prlin=%s, prlinname=%s, updatedate=%s, updateby=%s where pcode=%s ",
            (pcodename, unit1, unit2, unit3, convunit2, convunit3, prlin, prlinname, datetime.now(), updateby, pcode)
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        
        release_db_connection(conn)
        return jsonify({"error": str(e)}), 500

    
    release_db_connection(conn)
    return jsonify({"message" : f" Product Prc {pcode} berhasil diupdate"}), 200


# DELETE CUSTOMER PRC
@product_prc_bp.route('/delete', methods=['DELETE'])
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
        cursor.execute(f"DELETE FROM product_prc where pcode IN ({format_strings})", tuple(pcode))
        conn.commit()
    except Exception as e:
        conn.rollback()
        
        return jsonify({"error": str(e)}), 500
    
    release_db_connection(conn)
    return jsonify({"message" : f"{len(pcode)} entity berhasil dihapus"}),200