def process_sellout_to_final(conn, upload_batch_id, batch_size=1000):
    cur = conn.cursor()

    while True:
        # AMBIL SET ID YANG FIX
        cur.execute("""
            SELECT st.id
            FROM sellout_temp st
            JOIN mapping_branch mb
                ON st.kodebranch = mb.branch_dist
            JOIN mapping_salesman ms
                ON st.id_salesman = ms.id_salesman_dist
            JOIN mapping_customer mc
                ON st.id_customer = mc.custno_dist
            JOIN mapping_product mp
                ON st.id_product = mp.pcode_dist
            WHERE st.upload_batch_id = %s
              AND st.flag_move = 'N'
            ORDER BY st.id
            LIMIT %s
            FOR UPDATE SKIP LOCKED
        """, (upload_batch_id, batch_size))

        batch_ids = [r[0] for r in cur.fetchall()]
        if not batch_ids:
            break

        # INSERT KE SELLOUT
        cur.execute("""
            INSERT INTO sellout (
                region_code,
                region_name,
                entity_code,
                entity_name,
                branch_code,
                branch_name,
                area_code,
                area_name,
                salesman_code,
                salesman_name,
                custcode_prc,
                custcode_dist,
                custname,
                custaddress,
                custcity,
                sub_channel,
                type_outlet,
                order_no,
                order_date,
                invoice_no,
                invoice_type,
                invoice_date,
                product_brand,
                product_group1,
                product_group2,
                product_group3,
                pcode,
                pcode_name,
                qty1,
                qty2,
                qty3,
                flag_bonus,
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
                category,
                vtkp,
                npd,
                createdate,
                createby
            )
            SELECT
                r.koderegion,
                r.keterangan,
                e.id_entity,
                e.keterangan,
                b.kodebranch,
                b.nama_branch,
                a.id_area,
                a.description,
                ms.id_salesman,
                ms.nama_salesman,
                mc.custno,
                mc.custno_dist,
                mc.custname_prc,
                cp.custadd,
                cp.city,
                cp.type,
                cp.type,
                st.order_no,
                st.order_date,
                st.invoice_no,
                st.invoice_type,
                st.invoice_date,
                pg.brand,
                pg.product_group_1,
                pg.product_group_2,
                pg.product_group_3,
                mp.pcode_prc,
                mp.pcode_prc_name,
                st.qty1,
                st.qty2,
                st.qty3,
                st.flag_bonus,
                st.grossamount,
                st.discount1,
                st.discount2,
                st.discount3,
                st.discount4,
                st.discount5,
                st.discount6,
                st.discount7,
                st.discount8,
                st.total_discount,
                st.dpp,
                st.tax,
                st.nett,
                pg.category_item,
                pg.vtkp,
                pg.npd,
                NOW(),
                st.createby
            FROM sellout_temp st
            JOIN mapping_branch mb ON st.kodebranch = mb.branch_dist
            JOIN branch b ON mb.kodebranch = b.kodebranch
            JOIN area a ON b.id_area = a.id_area
            JOIN entity e ON b.entity = e.id_entity
            JOIN region r ON e.koderegion = r.koderegion
            JOIN mapping_salesman ms ON st.id_salesman = ms.id_salesman_dist
            JOIN mapping_customer mc ON st.id_customer = mc.custno_dist
            JOIN customer_prc cp ON mc.custno = cp.custno
            JOIN mapping_product mp ON st.id_product = mp.pcode_dist
            JOIN product_group pg ON mp.pcode_prc = pg.pcode
            WHERE st.id = ANY(%s)
        """, (batch_ids,))

        # FLAG SUKSES (ID YANG SAMA)
        cur.execute("""
            UPDATE sellout_temp
            SET flag_move = 'Y'
            WHERE id = ANY(%s)
        """, (batch_ids,))

        conn.commit()

    # FAILED MAPPING
    cur.execute("""
        INSERT INTO mapping_error (
            upload_batch_id,
            kodebranch,
            id_salesman,
            id_customer,
            id_product,
            invoice_no,
            invoice_date,
            price,
            qty3,
            grossamount,
            status,
            modified_date
        )
        SELECT 
            st.upload_batch_id,
            st.kodebranch,
            st.id_salesman,
            st.id_customer,
            st.id_product,
            st.invoice_no,
            st.invoice_date,
            st.price,
            st.qty3,
            st.grossamount,
            CASE 
                WHEN mb.id IS NULL THEN 'BRANCH_NOT_MAPPED'
                WHEN ms.id IS NULL THEN 'SALESMAN_NOT_MAPPED'
                WHEN mc.id IS NULL THEN 'CUSTOMER_NOT_MAPPED'
                WHEN mp.id IS NULL THEN 'PRODUCT_NOT_MAPPED'
                -- PENYEBAB 21 DATA HILANG:
                WHEN cp.id IS NULL THEN 'CUSTOMER_NOT_FOUND_IN_MASTER_PRC'
                WHEN pg.id IS NULL THEN 'PRODUCT_NOT_FOUND_IN_PRODUCT_GROUP'
                WHEN b.kodebranch IS NULL THEN 'BRANCH_CODE_NOT_FOUND_IN_MASTER'
                ELSE 'UNKNOWN_REASON_CHECK_MASTER_DATA'
            END,
            NOW()
        FROM sellout_temp st
        LEFT JOIN mapping_branch mb ON st.kodebranch = mb.branch_dist
        LEFT JOIN branch b ON mb.kodebranch = b.kodebranch
        LEFT JOIN mapping_salesman ms ON st.id_salesman = ms.id_salesman_dist
        LEFT JOIN mapping_customer mc ON st.id_customer = mc.custno_dist
        LEFT JOIN customer_prc cp ON mc.custno = cp.custno
        LEFT JOIN mapping_product mp ON st.id_product = mp.pcode_dist
        LEFT JOIN product_group pg ON mp.pcode_prc = pg.pcode
        WHERE st.upload_batch_id = %s 
          AND st.flag_move = 'N'
    """, (upload_batch_id,))

    # 5. Flag sisa (error) sebagai selesai
    cur.execute("""
        UPDATE sellout_temp 
        SET flag_move = 'Y' 
        WHERE upload_batch_id = %s AND flag_move = 'N'
    """, (upload_batch_id,))

    # FLAG ERROR SEBAGAI SELESAI
    cur.execute("""
        UPDATE sellout_temp
        SET flag_move = 'Y'
        WHERE upload_batch_id = %s
          AND flag_move = 'N'
    """, (upload_batch_id,))

    conn.commit()
    cur.close()
