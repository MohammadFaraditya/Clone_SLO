from datetime import datetime
from flask import Blueprint, jsonify, request
import jwt, os
from functools import wraps
from db import get_db_connection, release_db_connection
from psycopg2.extras import RealDictCursor, execute_values

config_bp = Blueprint('config', __name__, url_prefix='/config')
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

# GET DATA CONFIG
@config_bp.route('/data', methods=['GET'])
@token_required
def get_config():
    try:
        offset = int((request.args.get('offset', 0)))
    except Exception:
        offset = 0
    try:
        limit = int(request.args.get('limit', 50))
    except Exception:
        limit = 50

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute(""" 
        SELECT c.branch, b.nama_branch, c.id_salesman, c.id_customer, c.id_product, c.qty1, c.qty2, c.qty3, c.price, c.grossamount, c.discount1, c.discount2,
        c.discount3, c.discount4, c.discount5, c.discount6, c.discount7, c.discount8, c.total_discount, c.flag_bonus, c.dpp, c.tax, c.nett, c.order_no, c.order_date,
        c.invoice_no, c.invoice_date, c.invoice_type, c.sfa_order_no, c.sfa_order_date, c.kodebranch, c.file_extension, c.separator_file, c.first_row, c.createdate, c.createby,
        c.updatedate, c.updateby
        FROM config c
        INNER JOIN branch b ON c.branch = b.kodebranch
        ORDER BY c.branch
        LIMIT %s OFFSET %s
        """, (limit, offset))
    data = cursor.fetchall()

    cursor.execute("SELECT COUNT(1) AS TOTAL FROM config")
    total_row = cursor.fetchone()
    total_count = total_row['total'] if total_row else 0

    cursor.close()
    release_db_connection(conn)

    return jsonify({
        "data": data,
        "offset": offset,
        "limit": limit,
        "total": total_count
    }), 200


# INSERT PRICEGROUP
@config_bp.route('/insert', methods=['POST'])
@token_required
def insert_config():
    data = request.get_json()
    if not data or not isinstance(data, list):
        return jsonify({"error": "Data tidak valid"}), 400

    rows_input = []
    branches = []

    for row in data:
        branch = str(row.get("branch", "")).strip()

        rows_input.append({
            "branch": branch,
            "kodebranch": row.get("kodebranch"),
            "id_salesman": row.get("id_salesman"),
            "id_customer": row.get("id_customer"),
            "id_product": row.get("id_product"),
            "qty1": row.get("qty1"),
            "qty2": row.get("qty2"),
            "qty3": row.get("qty3"),
            "price": row.get("price"),
            "grossamount": row.get("grossamount"),
            "discount1": row.get("discount1"),
            "discount2": row.get("discount2"),
            "discount3": row.get("discount3"),
            "discount4": row.get("discount4"),
            "discount5": row.get("discount5"),
            "discount6": row.get("discount6"),
            "discount7": row.get("discount7"),
            "discount8": row.get("discount8"),
            "total_discount": row.get("total_discount"),
            "dpp": row.get("dpp"),
            "tax": row.get("tax"),
            "nett": row.get("nett"),
            "order_no": row.get("order_no"),
            "order_date": row.get("order_date"),
            "invoice_no": row.get("invoice_no"),
            "invoice_date": row.get("invoice_date"),
            "invoice_type": row.get("invoice_type"),
            "sfa_order_no": row.get("sfa_order_no"),
            "sfa_order_date": row.get("sfa_order_date"),
            "file_extension": row.get("file_extension"),
            "separator_file": row.get("separator_file"),
            "first_row": row.get("first_row"),
            "flag_bonus": row.get("flag_bonus"),
            "createdate": row.get("createdate") or datetime.now(),
            "createby": row.get("createby") or "SYSTEM"
        })

        branches.append(branch)

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # CEK DUPLIKAT (branch di config)
    cur.execute(
        """
        SELECT branch
        FROM config
        WHERE branch = ANY(%s)
        """,
        (branches,)
    )
    existing_branches = {r["branch"] for r in cur.fetchall()}

    # VALIDASI BRANCH TERDAFTAR
    cur.execute(
        """
        SELECT kodebranch
        FROM branch
        WHERE kodebranch = ANY(%s)
        """,
        (branches,)
    )
    valid_branches = {r["kodebranch"] for r in cur.fetchall()}

    rows_to_insert = []
    skipped_duplicate = []
    skipped_invalid_branch = []

    for r in rows_input:
        # DUPLIKAT
        if r["branch"] in existing_branches:
            skipped_duplicate.append(r["branch"])
            continue

        # TIDAK TERDAFTAR DI BRANCH
        if r["branch"] not in valid_branches:
            skipped_invalid_branch.append(r["branch"])
            continue

        rows_to_insert.append((
            r["branch"],
            r["kodebranch"],
            r["id_salesman"],
            r["id_customer"],
            r["id_product"],
            r["qty1"],
            r["qty2"],
            r["qty3"],
            r["price"],
            r["grossamount"],
            r["discount1"],
            r["discount2"],
            r["discount3"],
            r["discount4"],
            r["discount5"],
            r["discount6"],
            r["discount7"],
            r["discount8"],
            r["total_discount"],
            r["dpp"],
            r["tax"],
            r["nett"],
            r["order_no"],
            r["order_date"],
            r["invoice_no"],
            r["invoice_date"],
            r["invoice_type"],
            r["sfa_order_no"],
            r["sfa_order_date"],
            r["file_extension"],
            r["separator_file"],
            r["first_row"],
            r["flag_bonus"],
            r["createdate"],
            r["createby"]
        ))

    inserted_count = 0
    if rows_to_insert:
        insert_sql = """
            INSERT INTO config
            (
                branch, kodebranch, id_salesman, id_customer, id_product,
                qty1, qty2, qty3, price, grossamount,
                discount1, discount2, discount3, discount4, discount5,
                discount6, discount7, discount8, total_discount,
                dpp, tax, nett,
                order_no, order_date, invoice_no, invoice_date, invoice_type,
                sfa_order_no, sfa_order_date,
                file_extension, separator_file, first_row, flag_bonus,
                createdate, createby
            )
            VALUES %s
        """
        execute_values(cur, insert_sql, rows_to_insert, page_size=500)
        inserted_count = len(rows_to_insert)

    conn.commit()
    cur.close()
    release_db_connection(conn)

    return jsonify({
        "message": f"{inserted_count} record berhasil ditambahkan",
        "inserted": inserted_count,
        "skipped_duplicate": list(set(skipped_duplicate)),
        "skipped_invalid_branch": list(set(skipped_invalid_branch))
    }), 200


# UPDATE CONFIG
@config_bp.route('/update/<id>', methods=['PUT'])
@token_required
def update_config(id):
    payload = request.get_json(silent=True)
    if not payload:
        return jsonify({"error": "Request body harus JSON"}), 400

    updateby = payload.get("updateby") or "SYSTEM"

    def to_int(v):
        try:
            return int(v) if v not in ("", None) else None
        except:
            return None

    # INTEGER FIELDS
    kodebranch     = to_int(payload.get("kodebranch"))
    id_salesman    = to_int(payload.get("id_salesman"))
    id_customer    = to_int(payload.get("id_customer"))
    id_product     = to_int(payload.get("id_product"))
    qty1           = to_int(payload.get("qty1"))
    qty2           = to_int(payload.get("qty2"))
    qty3           = to_int(payload.get("qty3"))
    price          = to_int(payload.get("price"))
    grossamount    = to_int(payload.get("grossamount"))
    discount1      = to_int(payload.get("discount1"))
    discount2      = to_int(payload.get("discount2"))
    discount3      = to_int(payload.get("discount3"))
    discount4      = to_int(payload.get("discount4"))
    discount5      = to_int(payload.get("discount5"))
    discount6      = to_int(payload.get("discount6"))
    discount7      = to_int(payload.get("discount7"))
    discount8      = to_int(payload.get("discount8"))
    total_discount = to_int(payload.get("total_discount"))
    dpp            = to_int(payload.get("dpp"))
    tax            = to_int(payload.get("tax"))
    nett           = to_int(payload.get("nett"))
    order_no       = to_int(payload.get("order_no"))
    order_date     = to_int(payload.get("order_date"))
    invoice_no     = to_int(payload.get("invoice_no"))
    invoice_date   = to_int(payload.get("invoice_date"))
    invoice_type   = to_int(payload.get("invoice_type"))
    sfa_order_no   = to_int(payload.get("sfa_order_no"))
    sfa_order_date = to_int(payload.get("sfa_order_date"))
    first_row      = to_int(payload.get("first_row"))
    flag_bonus     = to_int(payload.get("flag_bonus"))

    # STRING FIELDS
    file_extension = payload.get("file_extension")
    separator_file = payload.get("separator_file")

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            UPDATE config
            SET
                kodebranch=%s,
                id_salesman=%s,
                id_customer=%s,
                id_product=%s,
                qty1=%s,
                qty2=%s,
                qty3=%s,
                price=%s,
                grossamount=%s,
                discount1=%s,
                discount2=%s,
                discount3=%s,
                discount4=%s,
                discount5=%s,
                discount6=%s,
                discount7=%s,
                discount8=%s,
                total_discount=%s,
                dpp=%s,
                tax=%s,
                nett=%s,
                order_no=%s,
                order_date=%s,
                invoice_no=%s,
                invoice_date=%s,
                invoice_type=%s,
                sfa_order_no=%s,
                sfa_order_date=%s,
                file_extension=%s,
                separator_file=%s,
                first_row=%s,
                flag_bonus=%s,
                updatedate=%s,
                updateby=%s
            WHERE branch=%s
        """, (
            kodebranch,
            id_salesman,
            id_customer,
            id_product,
            qty1,
            qty2,
            qty3,
            price,
            grossamount,
            discount1,
            discount2,
            discount3,
            discount4,
            discount5,
            discount6,
            discount7,
            discount8,
            total_discount,
            dpp,
            tax,
            nett,
            order_no,
            order_date,
            invoice_no,
            invoice_date,
            invoice_type,
            sfa_order_no,
            sfa_order_date,
            file_extension,
            separator_file,
            first_row,
            flag_bonus,
            datetime.now(),
            updateby,
            id   
        ))

        if cursor.rowcount == 0:
            conn.rollback()
            return jsonify({"error": "Data tidak ditemukan"}), 404

        conn.commit()

    except Exception as e:
        conn.rollback()
        print("UPDATE CONFIG ERROR:", e)
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        release_db_connection(conn)

    return jsonify({"message": "Config berhasil diupdate"}), 200




# DELETE CONFIG
@config_bp.route('/delete', methods=['DELETE'])
@token_required
def delete_areas_route():
    payload = request.json
    branch = payload.get("ids", [])

    if not branch or not isinstance(branch, list):
        return jsonify({"error": "Harus mengirim list Branch"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        format_strings = ",".join(["%s"] * len(branch))
        cursor.execute(f"DELETE FROM config WHERE branch IN ({format_strings})", tuple(branch))
        conn.commit()
    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()
        return jsonify({"error": str(e)}), 500

    cursor.close()
    conn.close()
    release_db_connection(conn)
    return jsonify({"message": f"{len(branch)} area berhasil dihapus"}), 200