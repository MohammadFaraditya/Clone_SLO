import os
import psycopg2
from psycopg2.pool import ThreadedConnectionPool
from dotenv import load_dotenv

load_dotenv()

MIN_CONN = 1
MAX_CONN = 20

pool = ThreadedConnectionPool(
    MIN_CONN,
    MAX_CONN,
    host= os.getenv("DB_HOST"),
    user= os.getenv("DB_USER"),
    password = os.getenv("DB_PASS"),
    database = os.getenv("DB_NAME"),
    port = os.getenv("DB_PORT")
)

def get_db_connection():
    conn = pool.getconn()
    return conn

def release_db_connection(conn):
    pool.putconn(conn)
