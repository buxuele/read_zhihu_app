import sqlite3
import os
import json
from datetime import date

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_DIR = os.path.join(BASE_DIR, 'data')
DB_PATH = os.path.join(DB_DIR, 'zhihu_data.db')

def get_conn():
    if not os.path.exists(DB_DIR):
        os.makedirs(DB_DIR)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_conn() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS contents (
                unique_id TEXT PRIMARY KEY,
                type TEXT,
                title TEXT,
                url TEXT,
                author TEXT,
                upvotes INTEGER,
                excerpt TEXT,
                created_ts INTEGER,
                fetch_date TEXT,
                is_favorited INTEGER DEFAULT 0
            )
        ''')
        # 兼容升级旧表，加入精细化筛选的评价维度
        try:
            conn.execute("ALTER TABLE contents ADD COLUMN comments INTEGER DEFAULT 0")
            conn.execute("ALTER TABLE contents ADD COLUMN fav_count INTEGER DEFAULT 0")
        except:
            pass
        
        conn.execute('CREATE INDEX IF NOT EXISTS idx_upvotes ON contents(upvotes DESC)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_date ON contents(fetch_date)')

def generate_unique_id(item):
    url = item.get('url', '')
    if item.get('type') == 'article':
        return url
    if 'question/' in url and 'answer/' in url:
        parts = url.split('/')
        q_idx = parts.index('question') + 1 if 'question' in parts else -1
        a_idx = parts.index('answer') + 1 if 'answer' in parts else -1
        if q_idx > 0 and a_idx > 0:
            return f"{parts[q_idx]}-{parts[a_idx]}"
    return url

def upsert_items(items, fetch_date=None):
    if not fetch_date:
        fetch_date = date.today().isoformat()
    count = 0
    with get_conn() as conn:
        for item in items:
            uid = generate_unique_id(item)
            if not uid:
                continue

            cur = conn.execute("SELECT upvotes, comments, fav_count FROM contents WHERE unique_id = ?", (uid,))
            row = cur.fetchone()
            
            upvotes = int(item.get('upvotes', 0) or 0)
            comments = int(item.get('comments', 0) or 0)
            fav_count = int(item.get('fav_count', 0) or 0)

            if row:
                if upvotes > row['upvotes'] or comments > row['comments']:
                    conn.execute("""
                        UPDATE contents SET upvotes = ?, comments = ?, fav_count = ?, fetch_date = ? 
                        WHERE unique_id = ?
                    """, (upvotes, comments, fav_count, fetch_date, uid))
                    count += 1
            else:
                conn.execute("""
                    INSERT INTO contents (unique_id, type, title, url, author, upvotes, comments, fav_count, excerpt, created_ts, fetch_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (uid, item.get('type'), item.get('title'), item.get('url'), item.get('author'), 
                      upvotes, comments, fav_count, item.get('excerpt'), item.get('created', 0), fetch_date))
                count += 1
    return count

def get_available_dates():
    with get_conn() as conn:
        rows = conn.execute("SELECT DISTINCT fetch_date FROM contents ORDER BY fetch_date DESC").fetchall()
        return [row['fetch_date'] for row in rows if row['fetch_date']]

def get_items(page=1, per_page=20, min_upvotes=1000, only_favorites=False, fetch_date=None):
    """【业务逻辑 2】多维度的质量评判：不仅唯点赞论"""
    with get_conn() as conn:
        query = "SELECT * FROM contents WHERE 1=1"
        params = []
        
        if only_favorites:
            query += " AND is_favorited = 1"
        else:
            # 引入多维筛选条件，满足其一即视为“干货”：
            # 1. 常规爆款：高赞数
            # 2. 隐形干货：收藏率极高（大于赞数的1/2）或者绝对收藏过高
            # 3. 无争议纯知识：点赞>300，且没有评论区吵架（点赞是评论的15倍以上，或0评论）
            query += """ AND (
                upvotes >= ? 
                OR fav_count >= ? 
                OR (upvotes >= 300 AND comments > 0 AND (upvotes / CAST(comments AS FLOAT) >= 15))
                OR (upvotes >= 300 AND comments = 0)
            )"""
            params.extend([min_upvotes, min_upvotes // 2])
            
        if fetch_date and fetch_date != '全部':
            query += " AND fetch_date = ?"
            params.append(fetch_date)
            
        # 排序机制迭代：高质量首看收藏量，其次看赞数
        query += " ORDER BY fav_count DESC, upvotes DESC"
        
        count_query = query.replace("SELECT *", "SELECT COUNT(1)")
        total_items = conn.execute(count_query, params).fetchone()[0]
        
        query += " LIMIT ? OFFSET ?"
        params.extend([per_page, (page - 1) * per_page])
        
        rows = conn.execute(query, params).fetchall()
        total_pages = (total_items + per_page - 1) // per_page
        
        return {
            'items': [dict(row) for row in rows],
            'current_page': page,
            'total_pages': total_pages,
            'total_items': total_items,
            'per_page': per_page,
            'has_prev': page > 1,
            'has_next': page < total_pages,
            'prev_page': page - 1 if page > 1 else None,
            'next_page': page + 1 if page < total_pages else None
        }

def toggle_favorite(url):
    with get_conn() as conn:
        cur = conn.execute("SELECT is_favorited FROM contents WHERE url = ?", (url,))
        row = cur.fetchone()
        if not row: return False, False
        new_status = 0 if row['is_favorited'] else 1
        conn.execute("UPDATE contents SET is_favorited = ? WHERE url = ?", (new_status, url))
        return True, bool(new_status)

def migrate_legacy_data():
    init_db()
    with get_conn() as conn:
        if conn.execute("SELECT COUNT(1) FROM contents").fetchone()[0] > 0: return
    try:
        from utils.parsers_questions import auto_parse_data
        import re
        for root, dirs, files in os.walk(DB_DIR):
            for file in files:
                if file.endswith('.json'):
                    try:
                        file_path = os.path.join(root, file)
                        folder_name = os.path.basename(root)
                        
                        # 从文件夹名提取日期，格式如 "2026-01-16"
                        date_match = re.match(r'(\d{4}-\d{2}-\d{2})', folder_name)
                        if date_match:
                            fetch_date = date_match.group(1)
                        else:
                            fetch_date = date.today().isoformat()
                        
                        with open(file_path, 'r', encoding='utf-8') as f:
                            upsert_items(auto_parse_data(json.load(f)), fetch_date=fetch_date)
                    except: pass
        fav_file = os.path.join(BASE_DIR, 'favorites.json')
        if os.path.exists(fav_file):
            with open(fav_file, 'r', encoding='utf-8') as f:
                with get_conn() as conn:
                    for url in json.load(f):
                        conn.execute("UPDATE contents SET is_favorited = 1 WHERE url = ?", (url,))
    except Exception: pass
