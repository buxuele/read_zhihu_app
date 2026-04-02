import os
import json
import threading
import subprocess
import sys
from datetime import datetime
from flask import Flask, render_template, request, jsonify

# 引入我们新建的数据库操作模块
from utils import database

app = Flask(__name__)

# 全局变量简化，剔除臃肿的长数组和字典
GOOD_VOTEUP_THRESHOLD = 1000
CURRENT_DATA_DIR = "全部"

# 爬虫状态
crawler_status = {
    'is_running': False,
    'message': '',
    'progress': 0,
    'total': 0
}

def run_crawler_background():
    global crawler_status
    crawler_status.update({'is_running': True, 'message': '正在启动爬虫...', 'progress': 0, 'total': 20})
    
    try:
        crawler_dir = 'playwright_zhihu'
        crawler_script = 'a2_get_api_data.py'
        today = datetime.now().strftime('%Y-%m-%d')
        output_dir = os.path.join(crawler_dir, today)
        
        cookie_path = os.path.join(crawler_dir, 'cookies.json')
        if not os.path.exists(cookie_path):
            crawler_status['message'] = '错误：未找到 cookies.json，请先运行 a1_login.py 登录'
            crawler_status['is_running'] = False
            return
        
        crawler_status['message'] = '后台爬取中...'
        
        process = subprocess.Popen(
            [sys.executable, crawler_script],
            cwd=crawler_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            error_msg = stderr.strip() if stderr.strip() else stdout.strip()
            crawler_status['message'] = f'爬虫执行失败 (退出码 {process.returncode})：{error_msg[:200]}'
            crawler_status['is_running'] = False
            return
        
        if not os.path.isdir(output_dir):
            crawler_status['message'] = f'爬虫运行完成，但未找到输出目录: {output_dir}'
            crawler_status['is_running'] = False
            return
        
        from utils.parsers_questions import auto_parse_data
        added_count = 0
        json_files = [f for f in os.listdir(output_dir) if f.endswith('.json')]
        
        if not json_files:
            crawler_status['message'] = '爬虫运行完成，但未生成任何 JSON 文件，可能 Cookie 已过期'
            crawler_status['is_running'] = False
            return
        
        for fname in json_files:
            fpath = os.path.join(output_dir, fname)
            with open(fpath, 'r', encoding='utf-8') as f:
                raw = json.load(f)
            items = auto_parse_data(raw)
            if items:
                added_count += database.upsert_items(items, fetch_date=today)
        
        if added_count == 0:
            crawler_status['message'] = f'爬取了 {len(json_files)} 个文件，但没有解析到有效内容，可能数据格式变化'
        else:
            crawler_status['message'] = f'爬取完成！解析入库 {added_count} 篇文章'
            crawler_status['progress'] = 20
            
    except FileNotFoundError as e:
        crawler_status['message'] = f'文件错误：{str(e)}'
    except json.JSONDecodeError as e:
        crawler_status['message'] = f'JSON 解析失败：{str(e)}'
    except Exception as e:
        crawler_status['message'] = f'未知错误：{str(e)}'
    finally:
        crawler_status['is_running'] = False


@app.context_processor
def inject_now():
    return {'now': datetime.utcnow()} 

@app.template_filter('timestamp_to_datetime_str')
def timestamp_to_datetime_str_filter(s):
    if isinstance(s, (int, float)):
        if 0 <= s <= 8 * (10**9):
            return datetime.fromtimestamp(s).strftime('%Y-%m-%d %H:%M:%S')
    return "无效时间"

@app.template_filter('shorten_filename')
def shorten_filename_filter(filename, max_len=30):
    return f"{filename[:max_len-3]}..." if len(filename) > max_len else filename


@app.route('/')
@app.route('/page/<int:page>')
def index(page=1):
    """主页路由（极简核心库直读）"""
    global CURRENT_DATA_DIR
    per_page = request.args.get('per_page', 20, type=int)
    # 支持通过URL直接切换目录（兼容旧版或前端跳转）
    req_date = request.args.get('data_dir')
    if req_date:
        CURRENT_DATA_DIR = req_date
    if per_page not in [10, 20]:
        per_page = 20
        
    dates = database.get_available_dates()
    available_dirs = ['全部'] + dates
    
    # 直接查询数据库获取分页，免去旧版占用海量内存的问题
    page_data = database.get_items(page=page, per_page=per_page, min_upvotes=GOOD_VOTEUP_THRESHOLD, fetch_date=CURRENT_DATA_DIR)
    
    return render_template('index.html', 
                         recommendations=page_data['items'],
                         pagination=page_data,
                         total_pool_size=page_data['total_items'],
                         current_threshold=GOOD_VOTEUP_THRESHOLD,
                         current_data_dir=CURRENT_DATA_DIR,
                         available_dirs=available_dirs)

@app.route('/api/toggle_favorite', methods=['POST'])
def toggle_favorite():
    """切换收藏状态"""
    data_rcv = request.get_json()
    if not data_rcv or 'url' not in data_rcv:
        return jsonify({'status': 'error', 'message': '请求数据不完整'}), 400
    
    success, is_favorited = database.toggle_favorite(data_rcv['url'])
    if success:
        return jsonify({'status': 'success', 'message': '操作成功', 'is_favorited': is_favorited})
    return jsonify({'status': 'error', 'message': 'URL 不存在于数据库中'}), 404

@app.route('/api/update_settings', methods=['POST'])
def update_settings():
    """更新设置"""
    global GOOD_VOTEUP_THRESHOLD, CURRENT_DATA_DIR
    data_rcv = request.get_json()
    if data_rcv:
        if 'threshold' in data_rcv:
            thresh = int(data_rcv['threshold'])
            if thresh >= 0:
                GOOD_VOTEUP_THRESHOLD = thresh
        if 'data_dir' in data_rcv:
            CURRENT_DATA_DIR = data_rcv['data_dir']
        
        # 获取最新的总数
        total = database.get_items(page=1, per_page=1, min_upvotes=GOOD_VOTEUP_THRESHOLD, fetch_date=CURRENT_DATA_DIR)['total_items']
        return jsonify({'status': 'success', 'message': '设置已更新', 'total_items': total})
    return jsonify({'status': 'error', 'message': '参数错误'}), 400

@app.route('/favorites')
def view_favorites():
    """查看收藏列表（通过 SQL 一次性取回过滤数据）"""
    # 让数据库帮我们查所有的 `is_favorited = 1`
    fav_data = database.get_items(page=1, per_page=1000, min_upvotes=0, only_favorites=True)
    return render_template('favorites.html',
                         favorites=fav_data['items'],
                         total_favorites=fav_data['total_items'])

@app.route('/api/start_crawler', methods=['POST'])
def start_crawler():
    if crawler_status['is_running']:
        return jsonify({'status': 'error', 'message': '爬虫正在运行中'})
    thread = threading.Thread(target=run_crawler_background)
    thread.daemon = True
    thread.start()
    return jsonify({'status': 'success', 'message': '爬虫已启动'})

@app.route('/api/crawler_status')
def get_crawler_status():
    return jsonify(crawler_status)


if __name__ == '__main__':
    # 初始化数据库 & 平滑迁移
    database.migrate_legacy_data()
    
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not app.debug:
        print("启动成功 -> 访问 http://127.0.0.1:5065")
    
    app.run(host='0.0.0.0', port=5065, debug=True)
