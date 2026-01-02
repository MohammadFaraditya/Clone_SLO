def process_sellout_to_final(conn, upload_batch_id, batch_size=1000):
    cur = conn.cursor()

    while True:
        # ================= INSERT VALID =================
        cur.execute("""
            WITH batch AS (
                SELECT st.id
                FROM sellout_temp st
                JOIN mapping_branch mb ON st.kodebranch = mb.kodebranch_dist
                JOIN mapping_salesman ms ON st.id_salesman = ms.salesman_dist
                JOIN mapping_customer mc ON st.id_customer = mc.customer_dist
                JOIN mapping_product mp ON st.id_product = mp.product_dist
                WHERE st.flag_move='N'
                  AND st.upload_batch_id=%s
                LIMIT %s
            )
            INSERT INTO sellout (
                tanggal,
                branch_code
                -- kolom lain
            )
            SELECT
                st.invoice_date,
                st.kodebranch
                -- kolom lain
            FROM sellout_temp st
            JOIN batch b ON st.id = b.id
        """, (upload_batch_id, batch_size))

        if cur.rowcount == 0:
            break

        # ================= UPDATE FLAG =================
        cur.execute("""
            UPDATE sellout_temp
            SET flag_move='Y'
            WHERE id IN (
                SELECT id
                FROM sellout_temp
                WHERE upload_batch_id=%s
                  AND flag_move='N'
                LIMIT %s
            )
        """, (upload_batch_id, batch_size))

        conn.commit()

    # ================= INSERT ERROR =================
    cur.execute("""
        INSERT INTO mapping_error (sellout_temp_id, error_reason, created_at)
        SELECT st.id, 'MAPPING_FAILED', NOW()
        FROM sellout_temp st
        LEFT JOIN mapping_branch mb ON st.kodebranch = mb.kodebranch_dist
        LEFT JOIN mapping_salesman ms ON st.id_salesman = ms.salesman_dist
        LEFT JOIN mapping_customer mc ON st.id_customer = mc.customer_dist
        LEFT JOIN mapping_product mp ON st.id_product = mp.product_dist
        WHERE st.upload_batch_id=%s
          AND st.flag_move='N'
    """, (upload_batch_id,))

    cur.execute("""
        UPDATE sellout_temp
        SET flag_move='Y'
        WHERE upload_batch_id=%s
          AND flag_move='N'
    """, (upload_batch_id,))

    conn.commit()
    cur.close()
