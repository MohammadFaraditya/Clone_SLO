from datetime import datetime
from flask import Blueprint, jsonify, request
import jwt, os
from functools import wraps
from db import get_db_connection, release_db_connection
from psycopg2.extras import RealDictCursor, execute_values

product_dist_bp = Blueprint('product_dist',__name__, url_prefix='/product-dist')
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

# GET DATA PRODUCT DIST
@product_dist_bp.route('/data', methods=['GET'])
@token_required
def get_customer_prc():
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
                SELECT pd.pcode_dist, pd.pcodename, pd.branch_dist, b.nama_branch_dist, pd.createdate, pd.createby, pd.updatedate, pd.updateby
                FROM product_dist pd
                INNER JOIN branch_dist b ON pd.branch_dist = b.branch_dist
                WHERE pd.branch_dist = %s
                ORDER BY pd.pcode_dist
                LIMIT %s OFFSET %s
            """, (kodebranch, limit, offset))
        data = cursor.fetchall()

        cursor.execute("""
                SELECT COUNT(1) AS total
                FROM product_dist 
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
        conn.close()
        release_db_connection(conn)

#INSERT DATA PRODUCT
@product_dist_bp.route('/insert', methods=['POST'])
@token_required
def insert_customer_dist():
    data = request.json
    if not data or not isinstance(data, list):
        return jsonify({"error": "Data tidak valid"}), 400

    rows = []

    for row in data:
        pcode_dist = str(row.get("pcode_dist")).strip()
        pcodename = row.get("pcodename")
        branch_dist = str(row.get("branch_dist")).strip()

        createdate = row.get("createdate") or datetime.now()
        createby = row.get("createby") or "SYSTEM"

        rows.append((pcode_dist, pcodename, branch_dist, createdate, createby))

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # --- CEK DUPLIKAT DI DATABASE
    ids = [r[0] for r in rows]
    cur.execute(
        "SELECT pcode_dist FROM product_dist WHERE pcode_dist = ANY(%s)",
        (ids,)
    )
    existing_rows = cur.fetchall()
    existing_ids = {r["pcode_dist"] for r in existing_rows}

    # --- CEK DUPLIKAT INTERNAL DALAM PAYLOAD
    internal_seen = set()
    internal_duplicates = set()

    for r in rows:
        if r[0] in internal_seen:
            internal_duplicates.add(r[0])
        internal_seen.add(r[0])

    # --- CEK VALID BRANCH
    branch_list = [r[2] for r in rows]
    cur.execute("SELECT branch_dist FROM branch_dist WHERE branch_dist = ANY(%s)", (branch_list,))
    branch_rows = cur.fetchall()
    valid_branches = {r["branch_dist"] for r in branch_rows}

    rows_valid = []
    invalid_kodebranch = []

    for r in rows:
        pcode_dist, pcodename, branch_dist, createdate, createby = r

        # Skip duplikat database
        if pcode_dist in existing_ids:
            continue

        # Skip duplikat internal payload
        if pcode_dist in internal_duplicates:
            continue

        # Skip branch tidak valid
        if branch_dist not in valid_branches:
            invalid_kodebranch.append(branch_dist)
            continue

        rows_valid.append(r)

    inserted_count = 0
    if rows_valid:
        insert_sql = """
        INSERT INTO product_dist
        (pcode_dist, pcodename, branch_dist, createdate, createby)
        VALUES %s
        """
        execute_values(cur, insert_sql, rows_valid, page_size=500)
        inserted_count = len(rows_valid)

    conn.commit()
    cur.close()
    release_db_connection(conn)

    return jsonify({
        "message": f"{inserted_count} record berhasil ditambahkan",
        "duplicate_database": list(existing_ids),
        "duplicate_internal": list(internal_duplicates),
        "invalid_kodebranch": invalid_kodebranch,
    }), 200


# UPDATE PRODUCT DIST
@product_dist_bp.route('/update/<pcode_dist>', methods=['PUT'])
@token_required
def update_customer_prc(pcode_dist):
    payload = request.json
    pcodename = payload.get("pcodename")
    updateby = payload.get("updateby")

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "UPDATE product_dist SET pcodename=%s, updatedate=%s, updateby=%s where pcode_dist=%s ",
            (pcodename, datetime.now(), updateby, pcode_dist)
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
    return jsonify({"message" : f" Customer Dist {pcode_dist} berhasil diupdate"}), 200


# DELETE PRODUCT DIST
@product_dist_bp.route('/delete', methods=['DELETE'])
@token_required
def delete_customer_prc_route():
    payload = request.json
    pcode_dist = payload.get("ids", [])

    if not pcode_dist or not isinstance(pcode_dist, list):
        return jsonify({"error": "Harus mengirim list pcode dist"}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        format_strings = ",".join(["%s"] * len(pcode_dist))
        cursor.execute(f"DELETE FROM product_dist where pcode_dist IN ({format_strings})", tuple(pcode_dist))
        conn.commit()
    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()
        return jsonify({"error": str(e)}), 500
    
    cursor.close()
    conn.close()
    release_db_connection(conn)
    return jsonify({"message" : f"{len(pcode_dist)} entity berhasil dihapus"}),200
