from datetime import datetime
from flask import Blueprint, jsonify, request
import jwt, os, uuid
import pandas as pd
from functools import wraps
from db import get_db_connection, release_db_connection
from psycopg2.extras import RealDictCursor

mapping_error_bp = Blueprint('mapping_error', __name__, url_prefix='/mapping-error')
SECRET_KEY = os.getenv('SECRET_KEY', "dev_secret")

# TOKEN 
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

#  GET DATA MAPPING ERROR
@mapping_error_bp.route('/data', methods=['GET'])
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
                kodebranch, id_salesman, id_customer, order_no, order_date, sfa_order_no, sfa_order_date, invoice_no, invoice_date,
                id_product, price, qty1, qty2, qty3, grossamount, status, modified_date, upload_batch_id
            FROM mapping_error
            WHERE kodebranch=%s
              AND invoice_date BETWEEN %s AND %s
            ORDER BY invoice_date
            LIMIT %s OFFSET %s
        """, (kodebranch, date_from, date_to, limit, offset))

        data = cursor.fetchall()

        cursor.execute("""
            SELECT COUNT(1) AS total
            FROM mapping_error
            WHERE kodebranch=%s
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