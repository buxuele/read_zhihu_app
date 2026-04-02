import os
import sqlite3
import json
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from utils.database import get_conn, generate_unique_id
from utils.parsers_questions import auto_parse_data

DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')

def fix_db_dates():
    count_updated = 0
    with get_conn() as conn:
        for root, dirs, files in os.walk(DB_DIR):
            folder_name = os.path.basename(root)
            # 校验文件夹名字是否像日期，比如 "2026-01-16"
            if len(folder_name) == 10 and folder_name.startswith('202'):
                fetch_date = folder_name
                for file in files:
                    if file.endswith('.json'):
                        try:
                            with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                                items = auto_parse_data(json.load(f))
                                for item in items:
                                    uid = generate_unique_id(item)
                                    if uid:
                                        # 如果因为今天是3月25日被迁移设为了3月25日，我们将其改回原本文件夹记录的数据获取日期
                                        cur = conn.execute("UPDATE contents SET fetch_date = ? WHERE unique_id = ? AND fetch_date = '2026-03-25'", (fetch_date, uid))
                                        count_updated += cur.rowcount
                        except Exception as e:
                            pass
        print(f"Fixed {count_updated} records to their original folder dates.")

if __name__ == '__main__':
    fix_db_dates()
