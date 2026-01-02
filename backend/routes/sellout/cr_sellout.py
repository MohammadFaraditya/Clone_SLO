from datetime import datetime
from flask import Blueprint, jsonify, request
import jwt, os, uuid
import pandas as pd
from functools import wraps
from db import get_db_connection, release_db_connection
from psycopg2.extras import RealDictCursor
from process.sellout_temp import (
    load_file,
    process_sellout,
    insert_sellout,
    get_date_range,
    delete_sellout_by_range
)

sellout_bp = Blueprint('sellout', __name__, url_prefix='/sellout')
SECRET_KEY = os.getenv('SECRET_KEY', "dev_secret")

# ================= TOKEN =================
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({"error": "Token tidak ditemukan"}), 401
        try:
            jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        except Exception:
            return jsonify({"error": "Token tidak valid atau kedaluwarsa"}), 401
        return f(*args, **kwargs)
    return decorated


# ================= CONFIG =================
def get_branch_config(branch_code, conn):
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM config
        WHERE branch=%s
        ORDER BY id DESC
        LIMIT 1
    """, (branch_code,))
    row = cur.fetchone()
    if not row:
        cur.close()
        return None
    columns = [desc[0] for desc in cur.description]
    config = dict(zip(columns, row))
    cur.close()
    return config


# =====================================================
# ================= GET DATA SELLOUT ==================
# =====================================================
@sellout_bp.route('/data', methods=['GET'])
@token_required
def get_sellout():
    try:
        offset = int(request.args.get('offset', 0))
    except Exception:
        offset = 0

    try:
        limit = int(request.args.get('limit', 50))
    except Exception:
        limit = 50

    kodebranch = request.args.get('kodebranch')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')

    if not kodebranch:
        return jsonify({"error": "kodebranch wajib diisi"}), 400
    if not date_from or not date_to:
        return jsonify({"error": "date_from dan date_to wajib diisi"}), 400

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cursor.execute("""
            SELECT
                region_code, region_name,
                entity_code, entity_name,
                branch_code, branch_name,
                area_code, area_name,
                salesman_code, salesman_name,
                custcode_prc, custcode_dist, custname, custaddress,
                custcity, sub_channel, type_outlet,
                order_no, order_date,
                invoice_no, invoice_type, invoice_date,
                product_brand, product_group1, product_group2, product_group3,
                pcode, pcode_name,
                qty1, qty2, qty3, qty4, qty5,
                flag_bonus,
                grossamount,
                discount1, discount2, discount3, discount4,
                discount5, discount6, discount7, discount8,
                total_discount, dpp, tax, nett,
                category, vtkp, npd,
                createdate, createby, updatedate, updateby
            FROM sellout
            WHERE branch_code=%s
              AND invoice_date BETWEEN %s AND %s
            ORDER BY invoice_date
            LIMIT %s OFFSET %s
        """, (kodebranch, date_from, date_to, limit, offset))

        data = cursor.fetchall()

        cursor.execute("""
            SELECT COUNT(1) AS total
            FROM sellout
            WHERE branch_code=%s
              AND invoice_date BETWEEN %s AND %s
        """, (kodebranch, date_from, date_to))

        total = cursor.fetchone()["total"]

        return jsonify({
            "data": data,
            "offset": offset,
            "limit": limit,
            "total": total
        }), 200

    finally:
        cursor.close()
        release_db_connection(conn)


# =====================================================
# ================= UPLOAD SELLOUT ====================
# =====================================================
@sellout_bp.route('/upload', methods=['POST'])
@token_required
def upload_sellout():
    conn = None
    try:
        branch = request.form.get('branch')
        file = request.files.get('file')
        username = request.form.get('username', 'system')

        if not branch:
            return jsonify({"error": "Branch wajib dipilih"}), 400
        if not file:
            return jsonify({"error": "File tidak ditemukan"}), 400

        conn = get_db_connection()
        config = get_branch_config(branch, conn)

        if not config:
            return jsonify({"error": f"Config untuk branch {branch} belum ada"}), 400

        ext = os.path.splitext(file.filename)[1].replace('.', '').lower()
        if ext != config['file_extension']:
            return jsonify({"error": "Format file tidak sesuai config"}), 400

        # ===== GENERATE BATCH ID =====
        upload_batch_id = str(uuid.uuid4())

        df = load_file(file, config)
        rows = process_sellout(df, config, username, upload_batch_id)

        if not rows:
            return jsonify({"error": "Tidak ada data valid"}), 400

        start_date, end_date = get_date_range(rows)
        if not start_date or not end_date:
            return jsonify({"error": "Invoice date tidak ditemukan"}), 400

        delete_sellout_by_range(conn, branch, start_date, end_date)

        insert_sellout(conn, rows)
        conn.commit()

        # ===== INSERT QUEUE =====
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO sellout_process_queue (
                upload_batch_id,
                status,
                created_at
            )
            VALUES (%s, 'PENDING', NOW())
        """, (upload_batch_id,))
        conn.commit()
        cur.close()

        return jsonify({
            "message": "Upload sellout berhasil",
            "total_row": len(rows),
            "upload_batch_id": upload_batch_id
        })

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"error": str(e)}), 500

    finally:
        if conn:
            release_db_connection(conn)
