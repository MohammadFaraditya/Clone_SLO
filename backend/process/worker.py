import time
from db import get_db_connection, release_db_connection
from process.sellout_service import process_sellout_to_final

def sellout_worker():
    while True:
        conn = get_db_connection()
        cur = conn.cursor()

        try:
            cur.execute("""
                SELECT id, upload_batch_id
                FROM sellout_process_queue
                WHERE status = 'PENDING'
                ORDER BY created_at
                LIMIT 1
                FOR UPDATE SKIP LOCKED
            """)

            job = cur.fetchone()
            if not job:
                conn.commit()
                time.sleep(2)
                continue

            job_id, batch_id = job

            cur.execute("""
                UPDATE sellout_process_queue
                SET status = 'PROCESSING',
                    started_at = NOW()
                WHERE id = %s
            """, (job_id,))
            conn.commit()

            process_sellout_to_final(conn, batch_id)

            cur.execute("""
                UPDATE sellout_process_queue
                SET status = 'DONE',
                    finished_at = NOW()
                WHERE id = %s
            """, (job_id,))
            conn.commit()

        except Exception as e:
            conn.rollback()
            cur.execute("""
                UPDATE sellout_process_queue
                SET status = 'FAILED'
                WHERE id = %s
            """, (job_id,))
            conn.commit()
            print("❌ Worker error:", e)

        finally:
            cur.close()
            release_db_connection(conn)
