from datetime import datetime
from flask import Blueprint, jsonify, request
import jwt, os
from functools import wraps
from db import get_db_connection, release_db_connection
from psycopg2.extras import RealDictCursor, execute_values

mapping_customer_bp = Blueprint('mapping_customer', __name__, url_prefix='/mapping-customer')
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

# GET DATA MAPPING CUSTOMER
@mapping_customer_bp.route('/data', methods=['GET'])
@token_required
def get_mapping_customer():
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
                SELECT * 
                FROM mapping_customer
                WHERE branch_prc = %s
                LIMIT %s OFFSET %s
            """, (kodebranch, limit, offset))
        data = cursor.fetchall()

        cursor.execute("""
                SELECT COUNT(1) AS total
                FROM mapping_customer
                WHERE branch_prc = %s
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

#INSERT DATA MAPPING CUSTOMER
@mapping_customer_bp.route('/insert', methods=['POST'])
@token_required
def insert_mapping_customer():
    data = request.json
    if not data or not isinstance(data, list):
        return jsonify({"error": "Data tidak valid"}), 400

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # 1. Ambil semua custno & custno_dist dari request untuk batch checking
    custnos_prc = [str(row.get("custno")).strip() for row in data]
    custnos_dist = [str(row.get("custno_dist")).strip() for row in data]

    # 2. CEK DUPLIKAT (LOGIKA BARU)
    # Kita cek apakah custno_dist sudah pernah di-mapping ke MANAPUN sebelumnya
    cur.execute(
        "SELECT custno_dist, custno FROM mapping_customer WHERE custno_dist = ANY(%s)",
        (custnos_dist,)
    )
    existing_rows = cur.fetchall()
    # Buat dictionary untuk mapping yang sudah ada: { 'KODE_DIST': 'KODE_PRC' }
    existing_dist_map = {r["custno_dist"]: r["custno"] for r in existing_rows}

    # 3. Ambil data master (Sama seperti sebelumnya)
    cur.execute("SELECT custno, custname, kodebranch FROM customer_prc WHERE custno = ANY(%s)", (custnos_prc,))
    customer_prc_data = {r["custno"]: r for r in cur.fetchall()}

    cur.execute("SELECT custno_dist, custname, branch_dist FROM customer_dist WHERE custno_dist = ANY(%s)", (custnos_dist,))
    customer_dist_data = {r["custno_dist"]: r for r in cur.fetchall()}

    rows_valid = []
    skipped_duplicate = []
    skipped_prc = []
    skipped_dist = []
    
    # Set internal untuk menangani jika di dalam file upload sendiri ada ID Dist yang ganda
    processed_in_batch = set()

    for row in data:
        custno = str(row.get("custno")).strip()
        custno_dist = str(row.get("custno_dist")).strip()
        kodebranch = row.get("kodebranch")
        branch_dist = row.get("branch_dist")
        createby = row.get("createby") or "SYSTEM"
        createdate = row.get("createdate") or datetime.now()

        # --- VALIDASI 1: CEK DUPLIKAT DI DATABASE ---
        if custno_dist in existing_dist_map:
            # Jika sudah ada mapping, kita catat detailnya untuk info di frontend
            skipped_duplicate.append({
                "custno_dist": custno_dist,
                "already_mapped_to": existing_dist_map[custno_dist],
                "reason": "ID Distributor sudah ter-mapping ke Kode PRC lain"
            })
            continue

        # --- VALIDASI 2: CEK DUPLIKAT DI DALAM FILE UPLOAD ITU SENDIRI ---
        if custno_dist in processed_in_batch:
            skipped_duplicate.append({
                "custno_dist": custno_dist,
                "reason": "ID Distributor muncul dua kali di file upload"
            })
            continue

        # --- VALIDASI 3: CEK MASTER PRC ---
        prc_data = customer_prc_data.get(custno)
        if not prc_data or prc_data["kodebranch"] != kodebranch:
            skipped_prc.append(custno)
            continue
        custname_prc = prc_data["custname"]

        # --- VALIDASI 4: CEK MASTER DIST ---
        dist_data = customer_dist_data.get(custno_dist)
        if not dist_data or dist_data["branch_dist"] != branch_dist:
            skipped_dist.append(custno_dist)
            continue
        custname_dist = dist_data["custname"]

        # Jika lolos semua, tambahkan ke list insert dan tandai sudah diproses
        rows_valid.append((
            custno, custname_prc, custno_dist, custname_dist, 
            createdate, createby, kodebranch, branch_dist
        ))
        processed_in_batch.add(custno_dist)

    # 4. EKSEKUSI INSERT
    inserted_count = 0
    if rows_valid:
        insert_sql = """
            INSERT INTO mapping_customer
            (custno, custname_prc, custno_dist, custname_dist, createdate, createby, branch_prc, branch_dist)
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
@mapping_customer_bp.route('/delete', methods=['DELETE'])
@token_required
def delete_mapping_customer():
    payload = request.json
    cust_pairs = payload.get("ids", [])

    if not cust_pairs or not isinstance(cust_pairs, list):
        return jsonify({"error": "Harus mengirim list pasangan custno & custno_dist"}), 400

    valid_pairs = [
        (p.get("custno"), p.get("custno_dist"))
        for p in cust_pairs
        if p.get("custno") and p.get("custno_dist")
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
            DELETE FROM mapping_customer
            WHERE (custno, custno_dist) IN ({values_sql})
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


