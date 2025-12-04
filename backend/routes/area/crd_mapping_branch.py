from datetime import datetime
from flask import Blueprint, jsonify, request
import jwt, os
from functools import wraps
from db import get_db_connection, release_db_connection
from psycopg2.extras import RealDictCursor, execute_values

mapping_branch_bp = Blueprint('mapping_branch', __name__, url_prefix='/mapping-branch')
SECRET_KEY = os.getenv('SECRET_KEY', 'dev_secret')

# MIDDLEWARE TOKEN
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({"error" : "Token tidak ditemukan"}), 401
        try:
            jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        except Exception:
            return jsonify({"error": "Token tidak valid atau kadaluarsa"}), 401
        return f(*args, **kwargs)
    return decorated

# GET DATA MAPPING BRANCH
@mapping_branch_bp.route('/data', methods=['GET'])
@token_required
def get_mapping_branch():
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
        SELECT * FROM mapping_branch
        ORDER BY kodebranch
        LIMIT %s OFFSET %s
    """, (limit, offset))

    data = cursor.fetchall()

    cursor.execute("SELECT COUNT(1) AS TOTAL FROM mapping_branch")
    total_row = cursor.fetchone()
    total_count = total_row['total'] if total_row else 0

    cursor.close()
    conn.close()
    release_db_connection(conn)

    return jsonify({
        "data": data,
        "offset": offset,
        "limit" : limit,
        "total" : total_count
    }), 200


# INSERT DATA MAPPING
@mapping_branch_bp.route('/insert', methods=['POST'])
@token_required
def insert_mapping_branch():
    data = request.json

    if not data or not isinstance(data, list):
        return jsonify({"error": "Data tidak valid, harus list"}), 400

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    kodebranches = [row.get("kodebranch") for row in data if row.get("kodebranch")]
    branchdists = [row.get("branch_dist") for row in data if row.get("branch_dist")]

    # CEK DATA BRANCH
    cur.execute("""
        SELECT kodebranch, nama_branch 
        FROM branch 
        WHERE kodebranch = ANY(%s::varchar[])
    """, (kodebranches,))
    branch_rows = cur.fetchall()
    branch_map = {r["kodebranch"]: r["nama_branch"] for r in branch_rows}

    # CEK DATA BRANCH_DIST
    cur.execute("""
        SELECT branch_dist, nama_branch_dist
        FROM branch_dist
        WHERE branch_dist = ANY(%s::varchar[])
    """, (branchdists,))
    branchdist_rows = cur.fetchall()
    branchdist_map = {r["branch_dist"]: r["nama_branch_dist"] for r in branchdist_rows}

    # CEK DUPLIKAT DI mapping_branch 
    cur.execute("""
        SELECT kodebranch FROM mapping_branch
        WHERE kodebranch = ANY(%s::varchar[])
    """, (kodebranches,))
    mapping_existing = cur.fetchall()
    existing_kodebranches = [x["kodebranch"] for x in mapping_existing]

    rows_to_insert = []
    invalid_branch = []
    invalid_branchdist = []
    skipped_duplicate = []

    for row in data:
        kodebranch = row.get("kodebranch")
        branchdist = row.get("branch_dist")

        if kodebranch not in branch_map:
            invalid_branch.append(kodebranch)
            continue

        if branchdist not in branchdist_map:
            invalid_branchdist.append(branchdist)
            continue

        if kodebranch in existing_kodebranches:
            skipped_duplicate.append(kodebranch)
            continue

        nama_branch = branch_map[kodebranch]
        nama_branch_dist = branchdist_map[branchdist]

        createdate = datetime.now()
        createby = row.get("createby") or "SYSTEM"

        rows_to_insert.append(
            (kodebranch, nama_branch, branchdist, nama_branch_dist, createdate, createby)
        )

    inserted_count = 0
    if rows_to_insert:
        insert_sql = """
            INSERT INTO mapping_branch
            (kodebranch, nama_branch, branch_dist, nama_branch_dist, createdate, createby)
            VALUES %s
        """
        execute_values(cur, insert_sql, rows_to_insert)
        inserted_count = len(rows_to_insert)

    conn.commit()
    cur.close()
    release_db_connection(conn)

    return jsonify({
        "message": f"{inserted_count} data berhasil diinsert",
        "invalid_kodebranch": list(set(invalid_branch)),
        "invalid_branchdist": list(set(invalid_branchdist)),
        "skipped_duplicate": list(set(skipped_duplicate))
    }), 200

# DELETE MAPPING BRANCH
@mapping_branch_bp.route('delete', methods=['DELETE'])
@token_required
def delete_mapping_branch_route():
    payload = request.json
    kodebranch = payload.get("ids", [])

    if not kodebranch or not isinstance(kodebranch, list):
        return jsonify({"error" "Harus mengitim list kodebranch"}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        format_strings = ",".join(["%s"] * len(kodebranch))
        cursor.execute(f"DELETE FROM mapping_branch WHERE kodebranch IN ({format_strings})", tuple(kodebranch))
        conn.commit()
    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()
        release_db_connection(conn)
    
    cursor.close()
    conn.close()
    release_db_connection(conn)
    return jsonify({"message" : f"{len(kodebranch)} mapping berhasil dihapus"}), 200




