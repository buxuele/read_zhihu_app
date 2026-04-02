def _parse_item_legacy(item):
    """解析字典条目"""
    target = item.get('target', item)
    if not isinstance(target, dict):
        return None

    item_type = target.get('type')
    
    # 【业务逻辑 3】反噪音：直接抛弃视频流和商业推广
    if item_type in ['video', 'zvideo', 'commercial', 'commercial_article'] or item.get('type') in ['commercial', 'commercial_article']:
        return None

    title = None
    created_ts = target.get('created_time') or target.get('created')
    item_url = None

    if item_type == 'article':
        title = target.get('title')
        item_url = target.get('url')
        if item_url and 'zhuanlan.zhihu.com' not in item_url:
            article_id = target.get('id')
            if article_id:
                item_url = f"https://zhuanlan.zhihu.com/p/{article_id}"
    elif item_type == 'answer':
        question_data = target.get('question')
        if isinstance(question_data, dict):
            title = question_data.get('title')
            q_id = question_data.get('id')
            a_id = target.get('id')
            if q_id and a_id:
                item_url = f"https://www.zhihu.com/question/{q_id}/answer/{a_id}"
        else:
            title = target.get('title') or f"回答 (ID: {target.get('id')})"
            item_url = target.get('url')

    excerpt = target.get('excerpt', '')
    
    # 【业务逻辑 3】反噪音：严格文字过滤，剔除盐选小说、带货卡片
    text_content = (str(title) + str(excerpt)).lower()
    if '盐选' in text_content or '带货' in text_content or '红包' in text_content or '小说' in text_content:
        return None

    # 【业务逻辑 2】多维度提取指标（赞同数、评论数、收藏数）
    upvotes = target.get('voteup_count', 0)
    comments = target.get('comment_count', 0)
    fav_count = target.get('favlists_count', 0)  # 高优先级的“干货指标”
    
    author_name = "未知作者"
    author_data = target.get('author')
    if isinstance(author_data, dict):
        author_name = author_data.get('name', '未知作者')
    
    if title and created_ts is not None and item_url:
        return {
            'type': item_type,
            'title': title,
            'created': created_ts,
            'url': item_url,
            'upvotes': upvotes,
            'comments': comments,
            'fav_count': fav_count,
            'author': author_name,
            'excerpt': excerpt
        }
    return None

def _parse_item_api(item):
    item_type = item.get('type')
    # 热榜数据一般是 hot_list_feed
    if item_type not in ['feed', 'question_feed_card', 'hot_list_feed']:
        return None
    return _parse_item_legacy(item)


def auto_parse_data(data):
    """自动判断结构并解析，加入反噪音处理"""
    if not isinstance(data, dict):
        return []

    feed_items = data.get('data')
    if not isinstance(feed_items, list) or not feed_items:
        return []

    parser_func = _parse_item_legacy if 'verb' in feed_items[0] else _parse_item_api

    parsed_results = []
    for item in feed_items:
        parsed_item = parser_func(item)
        if parsed_item:
            parsed_results.append(parsed_item)
    
    return parsed_results