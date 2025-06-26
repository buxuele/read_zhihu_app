# 文件: app.py

import os
import json
import re
import csv
import threading # 导入线程模块，用于文件锁
from datetime import datetime
from flask import Flask, render_template, abort, url_for, request, jsonify # 导入 jsonify
from parsers import auto_parse_data # <<< 新增此行


app = Flask(__name__)

# --- 新增部分：用于处理评分数据 ---
processed_data = {}
scores_data = {} # 全局字典，用于在内存中存储评分 {url: score}
SCORES_FILE = 'scores.csv' # 评分文件名
file_lock = threading.Lock() # 文件锁，防止并发写入时数据损坏

def load_scores():
    """从 scores.csv 加载评分到内存中"""
    global scores_data
    scores_data.clear()
    if not os.path.exists(SCORES_FILE):
        return # 如果文件不存在，则不执行任何操作
    
    with file_lock: # 加锁读取
        try:
            with open(SCORES_FILE, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if 'url' in row and 'score' in row:
                        try:
                            # 确保存储的是整数
                            scores_data[row['url']] = int(row['score'])
                        except (ValueError, TypeError):
                            # 如果分数不是有效数字，跳过此行
                            print(f"警告: 在 {SCORES_FILE} 中发现无效的分数，行: {row}")
        except Exception as e:
            print(f"警告: 读取评分文件 '{SCORES_FILE}' 时发生错误: {e}")

def save_score(url, title, score):
    """安全地保存或更新一条评分到 scores.csv"""
    with file_lock: # 在写入操作期间锁定文件
        # 1. 更新内存中的字典
        scores_data[url] = int(score)

        # 2. 更新 CSV 文件
        fieldnames = ['url', 'title', 'score']
        file_exists = os.path.exists(SCORES_FILE)
        
        # 读取现有数据
        all_scores = []
        if file_exists:
            with open(SCORES_FILE, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                all_scores = list(reader)

        # 检查 URL 是否已存在，并更新或追加
        url_found = False
        for item in all_scores:
            if item.get('url') == url:
                item['score'] = score
                # 如果标题也想更新，可以取消下面这行注释
                # item['title'] = title 
                url_found = True
                break
        
        if not url_found:
            all_scores.append({'url': url, 'title': title, 'score': score})

        # 将所有数据写回文件
        try:
            with open(SCORES_FILE, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(all_scores)
        except Exception as e:
            print(f"严重错误: 写入评分文件 '{SCORES_FILE}' 失败: {e}")





def load_and_process_data(data_dir):  # <<< 修改点 1: 增加 data_dir 参数
    """
    加载并处理指定目录下的所有JSON文件
    
    Args:
        data_dir (str): 存放JSON文件的数据目录路径。
    """
    global processed_data
    processed_data.clear() 

    # data_dir = 'total_json_data'  # <<< 修改点 2: 删除这一行硬编码的路径

    if not os.path.isdir(data_dir):
        print(f"警告: 数据目录 '{data_dir}' 不存在或不是一个目录。")
        return

    for filename in os.listdir(data_dir):
        if filename.endswith('.json'):
            filepath = os.path.join(data_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # --- 调用自动解析函数 (这部分保持不变) ---
                items_in_file = auto_parse_data(data)
                # ------------------------------------

                if items_in_file:
                    items_in_file.sort(key=lambda x: x.get('created', 0), reverse=True)
                    processed_data[filename] = items_in_file

            except json.JSONDecodeError:
                print(f"警告: 解析 JSON 文件 '{filepath}' 失败，跳过。")
            except Exception as e:
                print(f"警告: 处理文件 '{filepath}' 时发生未知错误: {e}，跳过。")
    
    if processed_data:
        print(f"成功处理 {len(processed_data)} 个JSON文件。")
    else:
        print(f"没有加载或处理任何JSON文件。请检查 '{data_dir}' 目录和 JSON 文件内容。")






# --- Flask 模板过滤器和上下文处理器（保持不变） ---
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
def index():
    filenames = list(processed_data.keys()) 
    active_file = request.args.get('active_file')
    def sort_key(filename):
        match = re.match(r'^(\d+)', filename) 
        if match:
            return int(match.group(1)) 
        return (float('inf'), filename) 
    sorted_filenames = sorted(filenames, key=sort_key)
    return render_template('index.html', filenames=sorted_filenames, active_file=active_file)

@app.route('/file/<path:filename>')
def show_articles_from_file(filename):
    articles_raw = processed_data.get(filename) 
    if articles_raw is None: 
        abort(404) 

    # --- 修改部分：为每篇文章注入评分 ---
    articles_with_scores = []
    for article in articles_raw:
        # 从内存中的 scores_data 获取分数，如果找不到，默认为 0
        score = scores_data.get(article['url'], 0)
        article_copy = article.copy() # 创建副本以避免修改原始数据
        article_copy['score'] = score
        articles_with_scores.append(article_copy)

    total_items = len(articles_with_scores)
    # 传递带有评分的文章列表到模板
    return render_template('file_articles.html', filename=filename, articles=articles_with_scores, total_items=total_items)

# --- 新增部分：保存评分的 API 端点 ---
@app.route('/api/rate_article', methods=['POST'])
def rate_article():
    data = request.get_json()
    if not data or 'url' not in data or 'title' not in data or 'score' not in data:
        return jsonify({'status': 'error', 'message': '请求数据不完整'}), 400
    
    try:
        url = data['url']
        title = data['title']
        score = int(data['score'])
        if not (0 <= score <= 10):
            return jsonify({'status': 'error', 'message': '分数必须在0-10之间'}), 400

        # 调用保存函数
        save_score(url, title, score)

        return jsonify({'status': 'success', 'message': '评分已保存'})
    except (ValueError, TypeError):
        return jsonify({'status': 'error', 'message': '分数必须是整数'}), 400
    except Exception as e:
        print(f"API 错误: {e}")
        return jsonify({'status': 'error', 'message': '服务器内部错误'}), 500


if __name__ == '__main__':
    data_dir = 'data/mix_data'   
    load_and_process_data(data_dir) 
    load_scores() 
    
    # 知乎阅读app, 端口号是 5082 (使用您之前的端口号)
    app.run(host='0.0.0.0', port=5080, debug=True)

