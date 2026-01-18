"""
快速测试新功能
"""
import os
import json

def test_data_dirs():
    """测试数据目录扫描"""
    print("=== 测试数据目录扫描 ===")
    data_base = 'data'
    if not os.path.exists(data_base):
        print("❌ data目录不存在")
        return
    
    dirs = []
    for item in os.listdir(data_base):
        item_path = os.path.join(data_base, item)
        if os.path.isdir(item_path):
            json_files = [f for f in os.listdir(item_path) if f.endswith('.json')]
            if json_files:
                dirs.append(item)
                print(f"✓ 找到数据源: {item} ({len(json_files)} 个JSON文件)")
    
    print(f"\n总共找到 {len(dirs)} 个可用数据源")
    return dirs

def test_favorites_file():
    """测试收藏文件"""
    print("\n=== 测试收藏功能 ===")
    favorites_file = 'favorites.json'
    
    if os.path.exists(favorites_file):
        print(f"✓ 收藏文件已存在: {favorites_file}")
        with open(favorites_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"  当前收藏数: {len(data)}")
    else:
        print(f"ℹ 收藏文件不存在，将在首次收藏时创建")
        # 创建空收藏文件
        with open(favorites_file, 'w', encoding='utf-8') as f:
            json.dump([], f)
        print(f"✓ 已创建空收藏文件")

def test_templates():
    """测试模板文件"""
    print("\n=== 测试模板文件 ===")
    templates = ['templates/base.html', 'templates/index.html', 'templates/favorites.html']
    
    for template in templates:
        if os.path.exists(template):
            print(f"✓ {template}")
        else:
            print(f"❌ {template} 不存在")

def test_app_import():
    """测试应用导入"""
    print("\n=== 测试应用导入 ===")
    try:
        import app
        print("✓ app.py 导入成功")
        
        # 检查关键函数
        functions = ['load_favorites', 'save_favorites', 'get_available_data_dirs', 
                    'toggle_favorite', 'update_settings', 'view_favorites']
        for func in functions:
            if hasattr(app, func):
                print(f"  ✓ 函数 {func} 存在")
            else:
                print(f"  ❌ 函数 {func} 不存在")
                
    except Exception as e:
        print(f"❌ 导入失败: {e}")

if __name__ == '__main__':
    print("知乎阅读App - 功能测试\n")
    
    test_data_dirs()
    test_favorites_file()
    test_templates()
    test_app_import()
    
    print("\n" + "="*50)
    print("测试完成！如果所有项都显示 ✓，说明功能正常")
    print("现在可以运行: python app.py")
    print("="*50)
