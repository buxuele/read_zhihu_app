import sqlite3
import datetime
import os

db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'zhihu_data.db')
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

dates = conn.execute("SELECT DISTINCT fetch_date FROM contents ORDER BY fetch_date DESC").fetchall()

print("当前数据库中各 fetch_date (爬取日期) 下的前3条记录发布时间对比：\n")

for d in dates:
    fetch_date = d['fetch_date']
    print(f"==== 爬取来源文件夹 / fetch_date: {fetch_date} ====")
    # 按照最新的发布时间找几条数据看看
    rows = conn.execute("SELECT title, created_ts FROM contents WHERE fetch_date = ? ORDER BY created_ts DESC LIMIT 3", (fetch_date,)).fetchall()
    
    if not rows:
        print("  (无数据)")
    
    for r in rows:
        ts = r['created_ts']
        published = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S') if ts else '无时间'
        title_sh = (r['title'][:30] + '...') if len(r['title']) > 30 else r['title']
        print(f"  文章发布时间: {published} | 标题: {title_sh}")
    print("")
