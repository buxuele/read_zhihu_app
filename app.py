import os
import json
import re
import csv
import threading  
import random
import subprocess
import sys
from datetime import datetime, date
from flask import Flask, render_template, abort, url_for, request, jsonify  
# from parsers import auto_parse_data  

from utils.parsers_questions import auto_parse_data  
import webbrowser

app = Flask(__name__)

GOOD_VOTEUP_THRESHOLD = 1000  # 筛选阈值，可配置
high_quality_pool = []  # 高质量内容池
recommended_ids = set()  # 已推荐内容ID集合

how_good = GOOD_VOTEUP_THRESHOLD  # 保持向后兼容
processed_data = {}  # 保留原有数据结构（暂时）

# 收藏相关
favorites_data = set()  # 收藏的内容URL集合
FAVORITES_FILE = 'favorites.json'  # 收藏文件名
file_lock = threading.Lock()  # 文件锁，防止并发写入时数据损坏

RECOMMENDED_FILE = 'recommended_ids.json'  # 已推荐内容ID文件

# 当前数据源目录
CURRENT_DATA_DIR = 'data/1.6_new'

# 爬虫状态
crawler_status = {
    'is_running': False,
    'message': '',
    'progress': 0,
    'total': 0
}

def load_recommended_ids():
    """从 recommended_ids.json 加载已推荐的内容ID到内存中"""
    global recommended_ids
    recommended_ids.clear()
    if not os.path.exists(RECOMMENDED_FILE):
        print(f"已推荐文件 '{RECOMMENDED_FILE}' 不存在，从头开始推荐")
        return
    
    try:
        with open(RECOMMENDED_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                recommended_ids.update(data)
                print(f"已加载 {len(recommended_ids)} 个已推荐内容ID")
            else:
                print(f"警告: {RECOMMENDED_FILE} 格式不正确，应该是数组格式")
    except Exception as e:
        print(f"警告: 读取已推荐文件 '{RECOMMENDED_FILE}' 时发生错误: {e}")

def save_recommended_ids():
    """将已推荐的内容ID保存到 recommended_ids.json"""
    global recommended_ids
    try:
        with open(RECOMMENDED_FILE, 'w', encoding='utf-8') as f:
            json.dump(list(recommended_ids), f, ensure_ascii=False, indent=2)
        print(f"已保存 {len(recommended_ids)} 个已推荐内容ID到 {RECOMMENDED_FILE}")
    except Exception as e:
        print(f"严重错误: 保存已推荐文件 '{RECOMMENDED_FILE}' 失败: {e}")

def load_favorites():
    """从 favorites.json 加载收藏到内存中"""
    global favorites_data
    favorites_data.clear()
    if not os.path.exists(FAVORITES_FILE):
        print(f"收藏文件 '{FAVORITES_FILE}' 不存在，从头开始")
        return
    
    try:
        with open(FAVORITES_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                favorites_data.update(data)
                print(f"已加载 {len(favorites_data)} 个收藏内容")
            else:
                print(f"警告: {FAVORITES_FILE} 格式不正确，应该是数组格式")
    except Exception as e:
        print(f"警告: 读取收藏文件 '{FAVORITES_FILE}' 时发生错误: {e}")

def save_favorites():
    """将收藏保存到 favorites.json"""
    global favorites_data
    try:
        with open(FAVORITES_FILE, 'w', encoding='utf-8') as f:
            json.dump(list(favorites_data), f, ensure_ascii=False, indent=2)
        print(f"已保存 {len(favorites_data)} 个收藏到 {FAVORITES_FILE}")
    except Exception as e:
        print(f"严重错误: 保存收藏文件 '{FAVORITES_FILE}' 失败: {e}")

def get_available_data_dirs():
    """获取data目录下所有可用的数据文件夹"""
    data_base = 'data'
    if not os.path.exists(data_base):
        return []
    
    dirs = []
    for item in os.listdir(data_base):
        item_path = os.path.join(data_base, item)
        if os.path.isdir(item_path):
            # 检查是否包含json文件
            json_files = [f for f in os.listdir(item_path) if f.endswith('.json')]
            if json_files:
                dirs.append(item)
    return sorted(dirs)

def check_today_data():
    """检查今天是否已有数据"""
    today = date.today().isoformat()
    today_folder = os.path.join('playwright_zhihu', today)
    
    if os.path.exists(today_folder):
        json_files = [f for f in os.listdir(today_folder) if f.endswith('.json')]
        return len(json_files) > 0
    return False

def run_crawler_background():
    """后台运行爬虫"""
    global crawler_status
    
    crawler_status['is_running'] = True
    crawler_status['message'] = '正在启动爬虫...'
    crawler_status['progress'] = 0
    crawler_status['total'] = 20
    
    try:
        # 切换到爬虫目录
        crawler_dir = 'playwright_zhihu'
        crawler_script = 'a2_get_api_data.py'
        
        # 检查cookies是否存在
        cookies_path = os.path.join(crawler_dir, 'cookies.json')
        if not os.path.exists(cookies_path):
            crawler_status['message'] = '错误：未找到cookies.json，请先运行 a1_login.py 登录'
            crawler_status['is_running'] = False
            return
        
        crawler_status['message'] = '正在爬取数据，请倒一杯水，耐心等待...'
        
        # 运行爬虫脚本
        process = subprocess.Popen(
            [sys.executable, crawler_script],
            cwd=crawler_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8'
        )
        
        # 等待完成
        stdout, stderr = process.communicate()
        
        if process.returncode == 0:
            crawler_status['message'] = '爬取完成！正在加载新数据...'
            crawler_status['progress'] = 20
            
            # 将今天的数据移动到data目录
            today = date.today().isoformat()
            source_folder = os.path.join('playwright_zhihu', today)
            
            if os.path.exists(source_folder):
                # 创建目标文件夹
                target_folder = os.path.join('data', today)
                os.makedirs(target_folder, exist_ok=True)
                
                # 复制文件
                import shutil
                for filename in os.listdir(source_folder):
                    if filename.endswith('.json'):
                        shutil.copy2(
                            os.path.join(source_folder, filename),
                            os.path.join(target_folder, filename)
                        )
                
                # 重新加载数据
                global CURRENT_DATA_DIR
                CURRENT_DATA_DIR = target_folder
                load_and_process_data(CURRENT_DATA_DIR)
                
                crawler_status['message'] = f'成功！今日数据已加载到 {today}'
            else:
                crawler_status['message'] = '警告：爬取完成但未找到数据文件'
        else:
            crawler_status['message'] = f'爬取失败：{stderr[:200]}'
            
    except Exception as e:
        crawler_status['message'] = f'错误：{str(e)}'
    finally:
        crawler_status['is_running'] = False





def generate_unique_id(item):
    """为内容项生成唯一ID"""
    if item['type'] == 'article':
        return item['url']  # 文章用URL作为ID
    elif item['type'] == 'answer':
        # 回答尝试从URL提取question_id和answer_id
        url = item['url']
        if 'question/' in url and 'answer/' in url:
            parts = url.split('/')
            question_idx = parts.index('question') + 1 if 'question' in parts else -1
            answer_idx = parts.index('answer') + 1 if 'answer' in parts else -1
            if question_idx > 0 and answer_idx > 0:
                return f"{parts[question_idx]}-{parts[answer_idx]}"
        return item['url']  # 备用方案
    return item['url']  # 默认用URL

def load_and_process_data(data_dir, threshold=None):
    """
    加载并处理指定目录下的所有JSON文件，直接填充高质量内容池
    
    Args:
        data_dir (str): 存放JSON文件的数据目录路径。
        threshold (int): 点赞数阈值，如果为None则使用全局GOOD_VOTEUP_THRESHOLD
    """
    global high_quality_pool, recommended_ids, processed_data, GOOD_VOTEUP_THRESHOLD
    
    if threshold is not None:
        GOOD_VOTEUP_THRESHOLD = threshold
    
    high_quality_pool.clear()
    processed_data.clear()  # 保持兼容性
    
    if not os.path.isdir(data_dir):
        print(f"警告: 数据目录 '{data_dir}' 不存在或不是一个目录。")
        return

    total_items = 0
    high_quality_count = 0
    
    for filename in os.listdir(data_dir):
        if filename.endswith('.json'):
            filepath = os.path.join(data_dir, filename)
            
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 解析文件中的内容
            items_in_file = auto_parse_data(data)
            
            if items_in_file:
                # 保持兼容性，存储到processed_data
                items_in_file.sort(key=lambda x: x.get('created', 0), reverse=True)
                processed_data[filename] = items_in_file
                
                # 筛选高质量内容到内容池
                for item in items_in_file:
                    total_items += 1
                    upvotes = item.get('upvotes', 0)
                    
                    if upvotes >= GOOD_VOTEUP_THRESHOLD:
                        # 生成唯一ID
                        unique_id = generate_unique_id(item)
                        
                        # 添加到高质量内容池
                        item_copy = item.copy()
                        item_copy['unique_id'] = unique_id
                        high_quality_pool.append(item_copy)
                        high_quality_count += 1
    
    print(f"数据加载完成！")
    print(f"  总内容数: {total_items}")
    print(f"  高质量内容数: {high_quality_count} (>= {GOOD_VOTEUP_THRESHOLD} 赞)")
    print(f"  处理文件数: {len(processed_data)}")
    
    # 按赞数降序排序内容池，以便分页显示时优质内容在前
    if high_quality_pool:
        print("正在按赞数排序内容池...")
        high_quality_pool.sort(key=lambda x: x.get('upvotes', 0), reverse=True)
        print(f"内容池已排序，共 {len(high_quality_pool)} 项内容，按赞数从高到低排列")
    
    print("http://127.0.0.1:5065")
    print()
    

def get_page_data(page=1, per_page=10):
    """
    获取分页数据
    
    Args:
        page (int): 页码，从1开始
        per_page (int): 每页显示数量
    
    Returns:
        dict: 包含分页数据的字典
    """
    global high_quality_pool
    
    total_items = len(high_quality_pool)
    total_pages = (total_items + per_page - 1) // per_page  # 向上取整
    
    # 确保页码在有效范围内
    if page < 1:
        page = 1
    elif page > total_pages and total_pages > 0:
        page = total_pages
    
    # 计算起始和结束索引
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    
    # 获取当前页的内容
    current_page_items = high_quality_pool[start_idx:end_idx]
    
    print(f"  分页查询: 第{page}页，共{total_pages}页，本页{len(current_page_items)}篇")
    
    return {
        'items': current_page_items,
        'current_page': page,
        'total_pages': total_pages,
        'total_items': total_items,
        'per_page': per_page,
        'has_prev': page > 1,
        'has_next': page < total_pages,
        'prev_page': page - 1 if page > 1 else None,
        'next_page': page + 1 if page < total_pages else None
    }
 
@app.context_processor
def inject_now():
    return {'now': datetime.utcnow()} 

@app.template_filter('timestamp_to_datetime_str')
def timestamp_to_datetime_str_filter(s):
    if isinstance(s, (int, float)):
        try:
            if 0 <= s <= 8 * (10**9):
                 return datetime.fromtimestamp(s).strftime('%Y-%m-%d %H:%M:%S')
            else:
                return "时间戳解析范围错误"
        except (ValueError, OSError): 
            return "无效时间戳"
    return str(s)

@app.template_filter('shorten_filename')
def shorten_filename_filter(filename, max_len=30):
    if len(filename) <= max_len:
        return filename
    match_prefix_date = re.match(r'^(\d+[_|-]\d{4}-\d{2}-\d{2})', filename)
    if match_prefix_date:
        prefix = match_prefix_date.group(1)
        if len(prefix) < max_len - 3:
             return f"{prefix}..."
        else:
            return f"{prefix[:max_len-3]}..."
    return f"{filename[:max_len-3]}..."

# --- Flask 路由（部分修改，部分新增） ---
@app.route('/')
@app.route('/page/<int:page>')
def index(page=1):
    """
    主页路由，支持分页
    
    Args:
        page (int): 页码，默认为1
    """
    print(f"用户访问第{page}页...")
    
    # 获取每页显示数量参数，默认为20
    per_page = request.args.get('per_page', 20, type=int)
    # 限制per_page只能是10或20
    if per_page not in [10, 20]:
        per_page = 20
    
    # 获取分页数据
    page_data = get_page_data(page, per_page=per_page)
    items = page_data['items']
    
    print(f"分页结果: 第{page_data['current_page']}页，共{page_data['total_pages']}页，本页{len(items)}篇内容")
    
    # 为内容注入收藏状态
    items_with_favorites = []
    for item in items:
        is_favorited = item['url'] in favorites_data
        item_copy = item.copy()
        item_copy['is_favorited'] = is_favorited
        items_with_favorites.append(item_copy)
        print(f"  显示: {item['title'][:40]}... (赞: {item['upvotes']}, 收藏: {is_favorited})")
    
    # 获取可用的数据目录
    available_dirs = get_available_data_dirs()
    
    return render_template('index.html', 
                         recommendations=items_with_favorites,
                         pagination=page_data,
                         total_pool_size=len(high_quality_pool),
                         current_threshold=GOOD_VOTEUP_THRESHOLD,
                         current_data_dir=CURRENT_DATA_DIR,
                         available_dirs=available_dirs)

@app.route('/api/toggle_favorite', methods=['POST'])
def toggle_favorite():
    """切换收藏状态"""
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({'status': 'error', 'message': '请求数据不完整'}), 400
    
    try:
        url = data['url']
        
        if url in favorites_data:
            # 取消收藏
            favorites_data.remove(url)
            is_favorited = False
            message = '已取消收藏'
        else:
            # 添加收藏
            favorites_data.add(url)
            is_favorited = True
            message = '已收藏'
        
        # 保存到文件
        save_favorites()
        
        return jsonify({
            'status': 'success', 
            'message': message,
            'is_favorited': is_favorited
        })
    except Exception as e:
        print(f"API 错误: {e}")
        return jsonify({'status': 'error', 'message': '服务器内部错误'}), 500

@app.route('/api/update_settings', methods=['POST'])
def update_settings():
    """更新设置（数据源和阈值）"""
    global CURRENT_DATA_DIR
    
    data = request.get_json()
    if not data:
        return jsonify({'status': 'error', 'message': '请求数据不完整'}), 400
    
    try:
        data_dir = data.get('data_dir')
        threshold = data.get('threshold')
        
        if data_dir:
            full_path = os.path.join('data', data_dir)
            if not os.path.isdir(full_path):
                return jsonify({'status': 'error', 'message': '数据目录不存在'}), 400
            CURRENT_DATA_DIR = full_path
        
        if threshold is not None:
            threshold = int(threshold)
            if threshold < 0:
                return jsonify({'status': 'error', 'message': '阈值必须大于等于0'}), 400
        
        # 重新加载数据
        load_and_process_data(CURRENT_DATA_DIR, threshold)
        
        return jsonify({
            'status': 'success',
            'message': '设置已更新',
            'total_items': len(high_quality_pool)
        })
    except Exception as e:
        print(f"API 错误: {e}")
        return jsonify({'status': 'error', 'message': f'服务器内部错误: {str(e)}'}), 500

@app.route('/favorites')
def view_favorites():
    """查看收藏列表"""
    # 从高质量内容池中筛选出收藏的内容
    favorited_items = [item for item in high_quality_pool if item['url'] in favorites_data]
    
    # 按赞数排序
    favorited_items.sort(key=lambda x: x.get('upvotes', 0), reverse=True)
    
    # 添加收藏状态标记
    for item in favorited_items:
        item['is_favorited'] = True
    
    return render_template('favorites.html',
                         favorites=favorited_items,
                         total_favorites=len(favorited_items))

@app.route('/api/start_crawler', methods=['POST'])
def start_crawler():
    """启动爬虫"""
    global crawler_status
    
    if crawler_status['is_running']:
        return jsonify({'status': 'error', 'message': '爬虫正在运行中'})
    
    # 在后台线程运行爬虫
    thread = threading.Thread(target=run_crawler_background)
    thread.daemon = True
    thread.start()
    
    return jsonify({'status': 'success', 'message': '爬虫已启动'})

@app.route('/api/crawler_status')
def get_crawler_status():
    """获取爬虫状态"""
    return jsonify(crawler_status)


if __name__ == '__main__':
    print("="*60)
    print("知乎阅读App 启动中...")
    print("="*60)
    
    # 检查今天是否已有数据
    has_today_data = check_today_data()
    today = date.today().isoformat()
    
    if has_today_data:
        print(f"[OK] 检测到今日数据 ({today})")
        CURRENT_DATA_DIR = os.path.join('data', today)
        
        # 如果data目录下没有今天的文件夹，从playwright_zhihu复制
        if not os.path.exists(CURRENT_DATA_DIR):
            print(f"正在复制今日数据到 {CURRENT_DATA_DIR}...")
            import shutil
            source = os.path.join('playwright_zhihu', today)
            os.makedirs(CURRENT_DATA_DIR, exist_ok=True)
            for filename in os.listdir(source):
                if filename.endswith('.json'):
                    shutil.copy2(
                        os.path.join(source, filename),
                        os.path.join(CURRENT_DATA_DIR, filename)
                    )
            print("[OK] 数据复制完成")
    else:
        print(f"[WARN] 未检测到今日数据 ({today})")
        print("提示：访问应用后可以点击'爬取今日数据'按钮获取最新内容")
        print("或者手动运行: cd playwright_zhihu && python a2_get_api_data.py")
        CURRENT_DATA_DIR = 'data/1.6_new'  # 使用默认数据
    
    print(f"\n当前数据源: {CURRENT_DATA_DIR}")
    
    load_and_process_data(CURRENT_DATA_DIR) 
    load_favorites()
    load_recommended_ids()
    
    print("\n" + "="*60)
    print("应用已启动: http://127.0.0.1:5065")
    print("="*60 + "\n")
    
    app.run(host='0.0.0.0', port=5065, debug=True)
 
