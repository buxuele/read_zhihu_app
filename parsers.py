# 文件: parsers.py

def _parse_item_legacy(item):
    """解析 'someone.json' (旧版) 格式的单个条目"""
    target = item.get('target')
    if not isinstance(target, dict):
        return None

    item_type = target.get('type')
    title = None
    created_ts = target.get('created_time') or target.get('created')
    item_url = None

    if item_type == 'article':
        title = target.get('title')
        # 旧格式的文章URL通常是完整的，直接使用
        item_url = target.get('url')
        if item_url and 'zhuanlan.zhihu.com' not in item_url:
            # 尝试从API URL中提取ID，构造标准URL
            article_id = target.get('id')
            if article_id:
                item_url = f"https://zhuanlan.zhihu.com/p/{article_id}"

    elif item_type == 'answer':
        question_data = target.get('question')
        if isinstance(question_data, dict):
            title = question_data.get('title')
            question_id = question_data.get('id')
            answer_id = target.get('id')
            if question_id and answer_id:
                item_url = f"https://www.zhihu.com/question/{question_id}/answer/{answer_id}"
        else:
            title = target.get('title') or f"回答 (ID: {target.get('id')})"
            item_url = target.get('url')

    if title and created_ts is not None and item_url:
        return {
            'type': item_type,
            'title': title,
            'created': created_ts,
            'url': item_url
        }
    return None

def _parse_item_api(item):
    """解析 'api.json' (新版) 格式的单个条目"""
    # 新格式中，广告需要被过滤掉
    if item.get('type') != 'feed':
        return None
    
    # 复用旧的解析逻辑，因为 target 结构非常相似
    return _parse_item_legacy(item)


def auto_parse_data(data):
    """
    自动检测JSON格式并调用相应的解析器。
    
    Args:
        data (dict): 从json.load()加载的Python字典。

    Returns:
        list: 解析后的文章/回答列表。
    """
    if not isinstance(data, dict) or 'data' not in data:
        return []

    feed_items = data.get('data')
    if not isinstance(feed_items, list) or not feed_items:
        return []

    # --- 格式检测逻辑 ---
    # 检查第一个条目是否有 'verb' 字段，这是旧格式的典型特征
    if 'verb' in feed_items[0]:
        parser_func = _parse_item_legacy
        # print("检测到旧版格式 (someone.json type)")
    # 否则，我们假设它是新格式 (api.json type)
    else:
        parser_func = _parse_item_api
        # print("检测到新版格式 (api.json type)")

    # --- 开始解析 ---
    parsed_results = []
    for item in feed_items:
        parsed_item = parser_func(item)
        if parsed_item:
            parsed_results.append(parsed_item)
    
    return parsed_results