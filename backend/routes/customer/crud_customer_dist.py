from datetime import datetime
from flask import Blueprint, jsonify, request
import jwt, os
from functools import wraps
from db import get_db_connection, release_db_connection
from psycopg2.extras import RealDictCursor, execute_values

customer_dist_bp = Blueprint('customer_dist',__name__, url_prefix='/customer-dist')
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

# GET DATA CUSTOMER DIST
@customer_dist_bp.route('/data', methods=['GET'])
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
                SELECT cp.custno_dist, cp.custname, cp.branch_dist, b.nama_branch_dist, cp.createdate, cp.createby, cp.updatedate, cp.updateby
                FROM customer_dist cp
                INNER JOIN branch_dist b ON cp.branch_dist = b.branch_dist
                WHERE cp.branch_dist = %s
                ORDER BY cp.custno_dist
                LIMIT %s OFFSET %s
            """, (kodebranch, limit, offset))
        data = cursor.fetchall()

        cursor.execute("""
                SELECT COUNT(1) AS total
                FROM customer_dist 
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

#INSERT DATA CUSTOMER DIST
@customer_dist_bp.route('/insert', methods=['POST'])
@token_required
def insert_customer_dist():
    data = request.json
    if not data or not isinstance(data, list):
        return jsonify({"error": "Data tidak valid"}), 400

    rows = []

    for row in data:
        custno_dist = str(row.get("custno_dist")).strip()
        custname = row.get("custname")
        branch_dist = str(row.get("branch_dist")).strip()

        createdate = row.get("createdate") or datetime.now()
        createby = row.get("createby") or "SYSTEM"

        rows.append((custno_dist, custname, branch_dist, createdate, createby))

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # Ambil semua custno_dist
    ids = [str(r[0]) for r in rows]
    branch_dist = [str(r[2]) for r in rows]

    # Cek DUPLIKAT di database
    cur.execute("SELECT custno_dist FROM customer_dist WHERE custno_dist = ANY(%s)", (ids,))
    existing_rows = cur.fetchall()
    existing_ids = {r["custno_dist"] for r in existing_rows}

    # Cek VALID branch
    cur.execute("SELECT branch_dist FROM branch_dist WHERE branch_dist = ANY(%s)", (branch_dist,))
    branch_rows = cur.fetchall()
    valid_branches = {r["branch_dist"] for r in branch_rows}

    # Filter valid rows
    rows_valid = []
    invalid_kodebranch = []

    for r in rows:
        custno_dist, custname, branch_dist, createdate, createby = r

        # Skip duplikat custno
        if custno_dist in existing_ids:
            continue

        # Skip invalid branch
        if branch_dist not in valid_branches:
            invalid_kodebranch.append(branch_dist)
            continue

        rows_valid.append(r)

    # Insert data
    inserted_count = 0
    if rows_valid:
        insert_sql = """
        INSERT INTO customer_dist
        (custno_dist, custname, branch_dist, createdate, createby)
        VALUES %s
        """
        execute_values(cur, insert_sql, rows_valid, page_size=500)
        inserted_count = len(rows_valid)

    conn.commit()
    cur.close()
    release_db_connection(conn)

    return jsonify({
        "message": f"{inserted_count} record berhasil ditambahkan",
        "duplicate_ids": list(existing_ids),
        "invalid_kodebranch": invalid_kodebranch,
        "skipped_duplicate": len(existing_ids)
    }), 200


# UPDATE CUSTOMER PRC
@customer_dist_bp.route('/update/<custno_dist>', methods=['PUT'])
@token_required
def update_customer_prc(custno_dist):
    payload = request.json
    custname = payload.get("custname")
    updateby = payload.get("updateby")

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "UPDATE customer_dist SET custname=%s, updatedate=%s, updateby=%s where custno_dist=%s ",
            (custname, datetime.now(), updateby, custno_dist)
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
    return jsonify({"message" : f" Customer Dist {custno_dist} berhasil diupdate"}), 200

# DELETE CUSTOMER DIST
@customer_dist_bp.route('/delete', methods=['DELETE'])
@token_required
def delete_customer_prc_route():
    payload = request.json
    custno_dist = payload.get("ids", [])

    if not custno_dist or not isinstance(custno_dist, list):
        return jsonify({"error": "Harus mengirim list custno dist"}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        format_strings = ",".join(["%s"] * len(custno_dist))
        cursor.execute(f"DELETE FROM customer_dist where custno_dist IN ({format_strings})", tuple(custno_dist))
        conn.commit()
    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()
        return jsonify({"error": str(e)}), 500
    
    cursor.close()
    conn.close()
    release_db_connection(conn)
    return jsonify({"message" : f"{len(custno_dist)} entity berhasil dihapus"}),200