from datetime import datetime
from flask import Blueprint, jsonify, request
import jwt, os
from functools import wraps
from db import get_db_connection, release_db_connection
from psycopg2.extras import RealDictCursor, execute_values

list_bp = Blueprint('list', __name__, url_prefix='/list')
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

# GET ALL REGION + ENTITY + BRANCH 
@list_bp.route('/mapping', methods=['GET'])
@token_required
def get_region_entity_branch_mapping():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute("""
        SELECT 
            r.koderegion,
            r.keterangan AS region_name,
            e.id_entity,
            e.keterangan AS entity_name,
            b.kodebranch,
            b.nama_branch
        FROM region r
        LEFT JOIN entity e ON r.koderegion = e.koderegion
        LEFT JOIN branch b ON e.id_entity = b.entity
        ORDER BY r.koderegion, e.id_entity, b.kodebranch
    """)

    data = cursor.fetchall()

    cursor.close()
    conn.close()
    release_db_connection(conn)

    return jsonify({
        "data": data
    }), 200

