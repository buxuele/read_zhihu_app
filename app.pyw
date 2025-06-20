import os
import json
import re 
from datetime import datetime 
from flask import Flask, render_template, abort, url_for, request # request 需要导入

app = Flask(__name__)

processed_data = {}

def load_and_process_data():
    global processed_data
    processed_data.clear() 

    data_dir = 'total_json_data' 
    if not os.path.isdir(data_dir):
        print(f"警告: 数据目录 '{data_dir}' 不存在或不是一个目录。")
        return

    for filename in os.listdir(data_dir):
        if filename.endswith('.json'):
            filepath = os.path.join(data_dir, filename)
            items_in_file = [] 
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    feed_items = data.get('data')
                    if not isinstance(feed_items, list):
                        continue

                    for item in feed_items:
                        target = item.get('target')
                        if not isinstance(target, dict):
                            continue
                        
                        item_type = target.get('type')
                        title = None
                        created_ts = target.get('created_time') 
                        if created_ts is None: 
                            created_ts = target.get('created')
                        item_url = None

                        if item_type == 'article':
                            title = target.get('title')
                            item_url = target.get('url')
                        elif item_type == 'answer':
                            question_data = target.get('question')
                            if isinstance(question_data, dict):
                                title = question_data.get('title') 
                                question_id = question_data.get('id')
                                answer_id = target.get('id')
                                if question_id and answer_id:
                                    item_url = f"https://www.zhihu.com/question/{question_id}/answer/{answer_id}"
                            else: 
                                original_answer_title = target.get('title') # 有些回答的 target 可能直接有 title
                                if original_answer_title:
                                    title = original_answer_title
                                else:
                                    title = f"回答 (ID: {target.get('id')})" 
                                item_url = target.get('url') 

                        if title and created_ts is not None and item_url:
                            items_in_file.append({
                                'type': item_type, 
                                'title': title,
                                'created': created_ts,
                                'url': item_url
                            })
                        else:
                            pass 
                
                items_in_file.sort(key=lambda x: x.get('created', 0), reverse=True)
                if items_in_file:
                    processed_data[filename] = items_in_file

            except json.JSONDecodeError:
                print(f"警告: 解析 JSON 文件 '{filepath}' 失败，跳过。")
            except Exception as e:
                print(f"警告: 处理文件 '{filepath}' 时发生未知错误: {e}，跳过。")
    
    if processed_data:
        print(f"成功处理 {len(processed_data)} 个JSON文件。")
    else:
        print("没有加载或处理任何JSON文件。请检查 'data' 目录和 JSON 文件内容。")

@app.context_processor
def inject_now():
    return {'now': datetime.utcnow()} 

@app.template_filter('timestamp_to_datetime_str')
def timestamp_to_datetime_str_filter(s):
    if isinstance(s, (int, float)):
        try:
            if 0 <= s <= 8 * (10**9): # 稍微放宽上限以兼容未来时间戳
                 return datetime.fromtimestamp(s).strftime('%Y-%m-%d %H:%M:%S')
            else:
                return "时间戳解析范围错误" # 更明确的提示
        except (ValueError, OSError): 
            return "无效时间戳" # 更明确的提示
    return str(s)

@app.template_filter('shorten_filename')
def shorten_filename_filter(filename, max_len=30):
    """
    缩短文件名，如果太长则显示部分并加省略号。
    优先保留开头的数字和日期部分。
    """
    if len(filename) <= max_len:
        return filename
    
    # 尝试匹配 "数字_日期" 或 "数字-"
    match_prefix_date = re.match(r'^(\d+[_|-]\d{4}-\d{2}-\d{2})', filename)
    if match_prefix_date:
        prefix = match_prefix_date.group(1)
        if len(prefix) < max_len - 3:
             return f"{prefix}..."
        else: # 如果前缀本身就很长，则截断前缀
            return f"{prefix[:max_len-3]}..."

    # 简单截断
    return f"{filename[:max_len-3]}..."


@app.route('/')
def index():
    filenames = list(processed_data.keys()) 
    # 获取 'active_file' 参数，用于高亮（需求6的简单实现基础）
    active_file = request.args.get('active_file')


    def sort_key(filename):
        match = re.match(r'^(\d+)', filename) 
        if match:
            return int(match.group(1)) 
        return (float('inf'), filename) 

    sorted_filenames = sorted(filenames, key=sort_key)
    return render_template('index.html', filenames=sorted_filenames, active_file=active_file)

@app.route('/file/<path:filename>') # 改为 path 类型转换器以支持包含斜杠等字符的文件名（虽然通常不推荐）
def show_articles_from_file(filename):
    articles = processed_data.get(filename) 
    if articles is None: 
        abort(404) 
    total_items = len(articles)
    return render_template('file_articles.html', filename=filename, articles=articles, total_items=total_items)

if __name__ == '__main__':
    load_and_process_data() 
    # app.run(debug=True)

    # 知乎阅读app, 端口号是 5060
    app.run(host='0.0.0.0', port=5060, debug=True)

