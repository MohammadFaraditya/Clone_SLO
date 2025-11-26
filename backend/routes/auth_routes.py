from flask import Blueprint, request, jsonify
from db import get_db_connection, release_db_connection
import bcrypt, jwt, datetime, os
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor

load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY", "dev_secret")

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT * FROM users WHERE id_user = %s", (username,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    release_db_connection(conn)

    if user and bcrypt.checkpw(password.encode('utf-8'), user["password"].encode('utf-8')):
        token = jwt.encode({
            "id_user": user["id_user"],
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=4)
        }, SECRET_KEY, algorithm="HS256")

        return jsonify({
            "message": "Login berhasil",
            "user": {
                "id_user": user["id_user"],
                "nama": user["nama"],
                "jabatan": user["jabatan"]
            },
            "token": token
        }), 200
    else:
        return jsonify({"error": "ID User atau password salah"}), 401
