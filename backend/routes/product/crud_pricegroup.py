from datetime import datetime
from flask import Blueprint, jsonify, request
import jwt, os
from functools import wraps
from db import get_db_connection, release_db_connection
from psycopg2.extras import RealDictCursor, execute_values

pricegroup_bp = Blueprint('pricegroup', __name__, url_prefix='/pricegroup')
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

# GET DATA PRICEGROUP
@pricegroup_bp.route('/data', methods=['GET'])
@token_required
def get_pricegroup():
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
        SELECT pricecode, pricename, pcode, pcodename, sellprice1, sellprice2, sellprice3, createdate, createby, updatedate, updateby
        FROM pricegroup
        ORDER BY pcode
        LIMIT %s OFFSET %s
        """, (limit, offset))
    data = cursor.fetchall()

    cursor.execute("SELECT COUNT(1) AS TOTAL FROM pricegroup")
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
@pricegroup_bp.route('/insert', methods=['POST'])
@token_required
def insert_pricegroup():
    data = request.get_json()
    if not data or not isinstance(data, list):
        return jsonify({"error": "Data tidak valid"}), 400

    rows_input = []
    pricecodes = []
    pcodes = []

    for row in data:
        pricecode = str(row.get("pricecode", "")).strip()
        pricename = str(row.get("pricename", "")).strip()
        pcode = str(row.get("pcode", "")).strip()

        sellprice1 = row.get("sellprice1")
        sellprice2 = row.get("sellprice2")
        sellprice3 = row.get("sellprice3")

        createby = row.get("createby") or "SYSTEM"
        createdate = row.get("createdate") or datetime.now()

        rows_input.append({
            "pricecode": pricecode,
            "pricename": pricename,
            "pcode": pcode,
            "sellprice1": sellprice1,
            "sellprice2": sellprice2,
            "sellprice3": sellprice3,
            "createdate": createdate,
            "createby": createby
        })

        pricecodes.append(pricecode)
        pcodes.append(pcode)

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # 1CEK DUPLIKAT (pricecode + pcode)
    cur.execute(
        """
        SELECT pricecode, pcode
        FROM pricegroup
        WHERE pricecode = ANY(%s)
          AND pcode = ANY(%s)
        """,
        (pricecodes, pcodes)
    )

    existing_pairs = {(r["pricecode"], r["pcode"]) for r in cur.fetchall()}


    # VALIDASI PCODE PRC
    cur.execute(
        """
        SELECT pcode, pcodename
        FROM product_prc
        WHERE pcode = ANY(%s)
        """,
        (pcodes,)
    )

    product_map = {r["pcode"]: r["pcodename"] for r in cur.fetchall()}

    # FILTER DATA
    rows_to_insert = []
    skipped_invalid_pcode = []
    skipped_duplicate = []

    for r in rows_input:
        key = (r["pricecode"], r["pcode"])

        # DUPLIKAT
        if key in existing_pairs:
            skipped_duplicate.append(key)
            continue

        # PCODE TIDAK TERDAFTAR
        pcodename = product_map.get(r["pcode"])
        if not pcodename:
            skipped_invalid_pcode.append(r["pcode"])
            continue

        rows_to_insert.append((
            r["pricecode"],
            r["pricename"],
            r["pcode"],
            pcodename,            
            r["sellprice1"],
            r["sellprice2"],
            r["sellprice3"],
            r["createdate"],
            r["createby"]
        ))

    inserted_count = 0
    if rows_to_insert:
        insert_sql = """
            INSERT INTO pricegroup
            (
                pricecode,
                pricename,
                pcode,
                pcodename,
                sellprice1,
                sellprice2,
                sellprice3,
                createdate,
                createby
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
        "skipped_duplicate": skipped_duplicate,
        "skipped_invalid_pcode": list(set(skipped_invalid_pcode))
    }), 200


#UPDATE PRICEGROUP
@pricegroup_bp.route('/update/<pcode>', methods=['PUT'])
@token_required
def update_pricegroup(pcode):
    payload = request.get_json(silent=True)
    if not payload:
        return jsonify({"error": "Request body harus JSON"}), 400

    pricecode = payload.get("pricecode")
    if not pricecode:
        return jsonify({"error": "pricecode wajib"}), 400

    updateby = payload.get("updateby") or "SYSTEM"

    def to_numeric(v):
        try:
            return float(v) if v not in ("", None) else None
        except:
            return None

    sellprice1 = to_numeric(payload.get("sellprice1"))
    sellprice2 = to_numeric(payload.get("sellprice2"))
    sellprice3 = to_numeric(payload.get("sellprice3"))

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            UPDATE pricegroup
            SET sellprice1=%s,
                sellprice2=%s,
                sellprice3=%s,
                updatedate=%s,
                updateby=%s
            WHERE pcode=%s AND pricecode=%s
        """, (
            sellprice1,
            sellprice2,
            sellprice3,
            datetime.now(),
            updateby,
            pcode,
            pricecode
        ))

        if cursor.rowcount == 0:
            conn.rollback()
            return jsonify({"error": "Data tidak ditemukan"}), 404

        conn.commit()

    except Exception as e:
        conn.rollback()
        print("UPDATE ERROR:", e)
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        release_db_connection(conn)

    return jsonify({"message": "Pricegroup berhasil diupdate"}), 200



#DELETE PRICEGROUP
@pricegroup_bp.route("/delete", methods=["DELETE"])
@token_required
def delete_pricegroup():
    payload = request.json
    ids = payload.get("ids", [])

    # Validasi input
    if not ids or not isinstance(ids, list):
        return jsonify({"error": "Harus mengirim list pricecode & pcode"}), 400

    # Ambil pasangan pricecode & pcode
    pairs = []
    for r in ids:
        pricecode = r.get("pricecode")
        pcode = r.get("pcode")
        if not pricecode or not pcode:
            return jsonify({"error": "pricecode dan pcode wajib"}), 400
        pairs.append((pricecode, pcode))

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        deleted_count = 0
        for pricecode, pcode in pairs:
            cur.execute(
                "DELETE FROM pricegroup WHERE pricecode=%s AND pcode=%s",
                (pricecode, pcode)
            )
            deleted_count += cur.rowcount 

        conn.commit()
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        release_db_connection(conn)

    return jsonify({
        "message": f"{deleted_count} pricegroup berhasil dihapus"
    }), 200