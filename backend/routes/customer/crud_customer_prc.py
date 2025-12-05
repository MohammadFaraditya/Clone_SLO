from datetime import datetime
from flask import Blueprint, jsonify, request
import jwt, os
from functools import wraps
from db import get_db_connection, release_db_connection
from psycopg2.extras import RealDictCursor, execute_values

customer_prc_bp = Blueprint('customer_prc',__name__, url_prefix='/customer-prc')
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


# GET DATA CUSTOMER PRC
@customer_prc_bp.route('/data', methods=['GET'])
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

    kodebranch = request.args.get('kodebranch')

    if not kodebranch:
        return jsonify({
            "error": "Harus menggunakan filter kodebranch"
        }), 400

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cursor.execute("""
                SELECT cp.custno, cp.custname, cp.custadd, cp.city, cp.type, cp.gharga, cp.kodebranch, b.nama_branch, cp.createdate, cp.createby, cp.updatedate, cp.updateby
                FROM customer_prc cp
                INNER JOIN branch b ON cp.kodebranch = b.kodebranch
                WHERE cp.kodebranch = %s
                LIMIT %s OFFSET %s
            """, (kodebranch, limit, offset))
        data = cursor.fetchall()

        cursor.execute("""
                SELECT COUNT(1) AS total
                FROM customer_prc 
                WHERE kodebranch = %s
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

#INSERT DATA CUSTOMER PRC
@customer_prc_bp.route('/insert', methods=['POST'])
@token_required
def insert_salesman_master():
    data = request.json
    if not data or not isinstance(data, list):
        return jsonify({"error": "Data tidak valid"}), 400

    rows = []

    for row in data:
        custno = row.get("custno")
        custname = row.get("custname")
        custadd = row.get("custadd")
        city = row.get("city")
        type = row.get("type")
        gharga = row.get("gharga")
        kodebranch = row.get("kodebranch")

        createdate = row.get("createdate") or datetime.now()
        createby = row.get("createby") or "SYSTEM"

        rows.append((custno, custname, custadd, city, type, gharga, kodebranch, createdate, createby))

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # Ambil semua custno
    ids = [r[0] for r in rows]
    kodebranches = [r[6] for r in rows]

    # Cek DUPLIKAT di database
    cur.execute("SELECT custno FROM customer_prc WHERE custno = ANY(%s)", (ids,))
    existing_rows = cur.fetchall()
    existing_ids = {r["custno"] for r in existing_rows}

    # Cek VALID branch
    cur.execute("SELECT kodebranch FROM branch WHERE kodebranch = ANY(%s)", (kodebranches,))
    branch_rows = cur.fetchall()
    valid_branches = {r["kodebranch"] for r in branch_rows}

    # Filter valid rows
    rows_valid = []
    invalid_kodebranch = []

    for r in rows:
        custno, custname, custadd, city, type, gharga, kodebranch, createdate, createby = r

        # Skip duplikat custno
        if custno in existing_ids:
            continue

        # Skip invalid branch
        if kodebranch not in valid_branches:
            invalid_kodebranch.append(kodebranch)
            continue

        rows_valid.append(r)

    # Insert data
    inserted_count = 0
    if rows_valid:
        insert_sql = """
        INSERT INTO customer_prc
        (custno, custname, custadd, city, type, gharga, kodebranch, createdate, createby)
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


