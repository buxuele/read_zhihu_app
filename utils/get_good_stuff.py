#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文章提取脚本
从data/all文件夹中的JSON文件提取高质量文章（赞数>=2000），
过滤特殊字符后保存为txt文件到good_stuff文件夹
"""

import os
import json
import re
from parsers import auto_parse_data

def clean_text(text):
    """
    清理文本，过滤掉特殊字符和HTML标签
    """
    if not text:
        return ""
    
    # 移除HTML标签
    text = re.sub(r'<[^>]+>', '', text)
    
    # 解码HTML实体
    html_entities = {
        '&lt;': '<',
        '&gt;': '>',
        '&amp;': '&',
        '&quot;': '"',
        '&#34;': '"',
        '&#39;': "'",
        '&nbsp;': ' ',
        '\\u003c': '<',
        '\\u003e': '>',
        '\\u0026': '&',
        '\\u003d': '=',
        '\\u0022': '"',
        '\\u0027': "'",
        '\\n': '\n',
        '\\r': '\r',
        '\\t': '\t'
    }
    
    for entity, char in html_entities.items():
        text = text.replace(entity, char)
    
    # 移除多余的空白字符
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    # 移除可能导致文件名问题的字符
    return text

def safe_filename(title, max_length=100):
    """
    生成安全的文件名
    """
    # 移除或替换不安全的字符
    unsafe_chars = r'[<>:"/\\|?*\x00-\x1f]'
    safe_title = re.sub(unsafe_chars, '_', title)
    
    # 限制长度
    if len(safe_title) > max_length:
        safe_title = safe_title[:max_length]
    
    return safe_title.strip()

def extract_articles():
    """
    主函数：提取文章并保存
    """
    data_dir = 'data/all'
    output_dir = 'good_stuff'
    threshold = 2000  # 赞数阈值
    
    # 创建输出目录
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"创建输出目录: {output_dir}")
    
    if not os.path.isdir(data_dir):
        print(f"错误: 数据目录 '{data_dir}' 不存在")
        return
    
    total_files = 0
    total_items = 0
    extracted_count = 0
    
    print(f"开始处理 {data_dir} 目录下的JSON文件...")
    print(f"筛选标准: 赞数 >= {threshold}")
    print("-" * 50)
    
    # 遍历所有JSON文件
    for filename in os.listdir(data_dir):
        if not filename.endswith('.json'):
            continue
            
        filepath = os.path.join(data_dir, filename)
        total_files += 1
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 使用parsers.py中的解析函数
            items = auto_parse_data(data)
            total_items += len(items)
            
            # 筛选高质量内容
            for item in items:
                upvotes = item.get('upvotes', 0)
                if upvotes >= threshold:
                    title = item.get('title', '无标题')
                    content = item.get('content', '')  # 如果有content字段
                    url = item.get('url', '')
                    item_type = item.get('type', 'unknown')
                    
                    # 如果没有content，尝试从原始数据中提取
                    if not content:
                        # 重新读取原始数据尝试提取content
                        try:
                            for raw_item in data.get('data', []):
                                target = raw_item.get('target', {})
                                if target.get('url') == url or str(target.get('id')) in url:
                                    content = target.get('content', target.get('excerpt', ''))
                                    break
                        except:
                            content = item.get('excerpt', '')
                    
                    # 清理文本
                    clean_title = clean_text(title)
                    clean_content = clean_text(content)
                    
                    # 生成文件名
                    safe_title = safe_filename(clean_title)
                    filename_base = f"{extracted_count+1:03d}_{item_type}_{upvotes}赞_{safe_title}"
                    txt_filename = f"{filename_base}.txt"
                    txt_filepath = os.path.join(output_dir, txt_filename)
                    
                    # 写入文件
                    try:
                        with open(txt_filepath, 'w', encoding='utf-8') as f:
                            f.write(f"标题: {clean_title}\n")
                            f.write(f"类型: {item_type}\n")
                            f.write(f"赞数: {upvotes}\n")
                            f.write(f"链接: {url}\n")
                            f.write(f"创建时间: {item.get('created', 'N/A')}\n")
                            f.write("-" * 50 + "\n\n")
                            f.write(clean_content)
                        
                        extracted_count += 1
                        print(f"[{extracted_count:03d}] 已保存: {clean_title[:50]}... ({upvotes}赞)")
                        
                    except Exception as e:
                        print(f"保存文件失败: {txt_filename}, 错误: {e}")
                        
        except Exception as e:
            print(f"处理文件 {filename} 时出错: {e}")
            continue
    
    print("-" * 50)
    print(f"处理完成!")
    print(f"总文件数: {total_files}")
    print(f"总内容数: {total_items}")
    print(f"提取的高质量文章数: {extracted_count}")
    print(f"输出目录: {output_dir}")

if __name__ == "__main__":
    extract_articles()