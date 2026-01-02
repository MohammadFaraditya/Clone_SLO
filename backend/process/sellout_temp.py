from datetime import datetime
import pandas as pd
from psycopg2.extras import execute_values


def load_file(file, config):
    start_row = config['first_row'] - 1

    if config['file_extension'] == 'xlsx':
        return pd.read_excel(file, header=None, skiprows=start_row)

    if config['file_extension'] == 'csv':
        return pd.read_csv(file, header=None, skiprows=start_row,
                           sep=config.get('separator_file') or ',')

    if config['file_extension'] == 'txt':
        return pd.read_csv(file, header=None, skiprows=start_row,
                           sep=config.get('separator_file') or '|')

    raise Exception("Format file tidak didukung")


def get_val(row, idx):
    if not idx:
        return None
    try:
        val = row[idx - 1]
        return None if pd.isna(val) else val
    except Exception:
        return None


def process_sellout(df, config, username, upload_batch_id):
    now = datetime.now()
    data = []

    for _, row in df.iterrows():
        qty3 = get_val(row, config.get('qty3'))
        price = get_val(row, config.get('price'))
        gross = get_val(row, config.get('grossamount'))
        dpp = get_val(row, config.get('dpp'))
        nett = get_val(row, config.get('nett'))

        if not config.get('grossamount'):
            gross = (qty3 or 0) * (price or 0)

        discount8 = get_val(row, config.get('discount8'))
        flag_bonus = 'N'

        if config.get('flag_bonus'):
            if get_val(row, config['flag_bonus']) == 'Y':
                flag_bonus = 'Y'
                discount8 = qty3
                qty3 = 0

        if all(v in [0, None] for v in [price, gross, dpp, nett]):
            flag_bonus = 'Y'
            discount8 = qty3
            qty3 = 0

        data.append({
            "upload_batch_id": upload_batch_id,
            "kodebranch": str(get_val(row, config['kodebranch'])),
            "id_salesman": str(get_val(row, config['id_salesman'])),
            "id_customer": str(get_val(row, config['id_customer'])),
            "id_product": str(get_val(row, config['id_product'])),

            "qty1": get_val(row, config.get('qty1')),
            "qty2": get_val(row, config.get('qty2')),
            "qty3": qty3,

            "price": price or 0,
            "grossamount": gross or 0,

            "discount1": get_val(row, config.get('discount1')),
            "discount2": get_val(row, config.get('discount2')),
            "discount3": get_val(row, config.get('discount3')),
            "discount4": get_val(row, config.get('discount4')),
            "discount5": get_val(row, config.get('discount5')),
            "discount6": get_val(row, config.get('discount6')),
            "discount7": get_val(row, config.get('discount7')),
            "discount8": discount8,

            "total_discount": get_val(row, config.get('total_discount')),
            "dpp": dpp,
            "tax": get_val(row, config.get('tax')),
            "nett": nett,

            "order_no": get_val(row, config.get('order_no')),
            "order_date": get_val(row, config.get('order_date')),
            "invoice_no": get_val(row, config.get('invoice_no')),
            "invoice_date": get_val(row, config.get('invoice_date')),
            "invoice_type": get_val(row, config.get('invoice_type')),

            "flag_bonus": flag_bonus,
            "flag_move": "N",
            "createdate": now,
            "createby": username
        })

    return data


def get_date_range(rows):
    dates = [r['invoice_date'] for r in rows if r.get('invoice_date')]
    if not dates:
        return None, None
    return min(dates), max(dates)


def delete_sellout_by_range(conn, branch, start_date, end_date):
    cur = conn.cursor()
    cur.execute("""
        DELETE FROM sellout_temp
        WHERE kodebranch=%s
          AND invoice_date BETWEEN %s AND %s
    """, (branch, start_date, end_date))
    cur.close()


def insert_sellout(conn, rows):
    cur = conn.cursor()
    columns = rows[0].keys()
    values = [[r[c] for c in columns] for r in rows]

    sql = f"""
        INSERT INTO sellout_temp ({','.join(columns)})
        VALUES %s
    """

    execute_values(cur, sql, values)
    cur.close()
