# 知乎高质量内容推荐系统

一个基于 Flask 和 Playwright 的知乎内容筛选与阅读工具，自动采集知乎推荐流数据，按点赞数筛选高质量内容，提供友好的 Web 阅读界面。

## 功能特点

- 🤖 **自动化采集** - 使用 Playwright 自动爬取知乎推荐流数据
- 🎯 **智能筛选** - 根据点赞数阈值（默认 1000+）过滤高质量内容
- 📱 **友好界面** - 响应式 Web 界面，支持分页浏览
- ⭐ **收藏管理** - 一键收藏喜欢的文章和回答
- 📊 **数据管理** - 支持多数据源切换，按日期组织数据
- 🔄 **实时更新** - 支持一键爬取今日最新推荐内容

## 技术栈

- **后端**: Flask
- **爬虫**: Playwright (Chromium)
- **前端**: Bootstrap 5 + 原生 JavaScript
- **数据存储**: JSON 文件

## 项目结构

```
.
├── app.py                      # Flask 主应用
├── app.pyw                     # Windows 无窗口启动
├── playwright_zhihu/           # 爬虫模块
│   ├── a1_login.py            # 登录脚本（保存 cookies）
│   ├── a2_get_api_data.py     # 数据采集脚本
│   └── cookies.json           # 登录凭证（需自行生成）
├── data/                       # 数据存储目录
│   ├── 2026-01-16/            # 按日期组织的数据文件夹
│   ├── 2026-01-17/
│   └── ...
├── templates/                  # HTML 模板
│   ├── base.html
│   ├── index.html             # 主页
│   └── favorites.html         # 收藏页
├── static/                     # 静态资源
│   └── style.css
├── utils/                      # 工具函数
│   └── parsers_questions.py   # JSON 数据解析器
├── favorites.json              # 收藏数据
├── recommended_ids.json        # 已推荐内容 ID
└── requirements.txt            # Python 依赖
```

## 安装与使用

### 1. 环境准备

```bash
# 克隆项目
git clone <your-repo-url>
cd <project-folder>

# 创建虚拟环境（推荐）
python -m venv read_venv
read_venv\Scripts\activate  # Windows
# source read_venv/bin/activate  # Linux/Mac

# 安装依赖
pip install -r requirements.txt

# 安装 Playwright 浏览器
playwright install chromium
```

### 2. 获取知乎登录凭证

首次使用需要获取知乎的 cookies：

```bash
cd playwright_zhihu
python a1_login.py
```

脚本会打开浏览器窗口，手动登录知乎后，cookies 会自动保存到 `cookies.json`。

### 3. 采集数据

```bash
# 在 playwright_zhihu 目录下
python a2_get_api_data.py
```

脚本会：
- 自动打开知乎首页
- 模拟滚动页面 20 次
- 拦截并保存推荐流 API 数据
- 数据保存在 `playwright_zhihu/YYYY-MM-DD/` 目录

### 4. 启动 Web 应用

```bash
# 返回项目根目录
cd ..
python app.py
```

访问 `http://127.0.0.1:5065` 即可使用。

或者使用批处理文件快速启动：
```bash
# Windows
run_read_zhihu_app.bat
```

## 使用说明

### 主界面功能

- **分页浏览** - 支持每页显示 10 或 20 条内容
- **全部打开** - 一键在新标签页打开当前页所有链接
- **收藏按钮** - 点击收藏喜欢的内容
- **数据源切换** - 在设置中切换不同日期的数据
- **阈值调整** - 自定义点赞数筛选阈值

### 爬取今日数据

在 Web 界面点击"爬取今日数据"按钮，系统会：
1. 检查是否已有今日数据
2. 后台运行爬虫脚本
3. 自动加载新数据到应用

### 收藏管理

- 点击"我的收藏"查看所有收藏内容
- 收藏数据保存在 `favorites.json`
- 支持取消收藏

## 数据格式

每个 JSON 文件包含知乎推荐流数据，解析后的格式：

```json
{
  "type": "article",           // 类型：article 或 answer
  "title": "文章标题",
  "author": "作者名",
  "upvotes": 1234,             // 点赞数
  "created": 1234567890,       // 发布时间戳
  "url": "https://...",        // 内容链接
  "excerpt": "内容摘要..."
}
```

## 配置说明

### 修改筛选阈值

在 `app.py` 中修改：

```python
GOOD_VOTEUP_THRESHOLD = 1000  # 默认 1000 赞
```

### 修改爬取次数

在 `playwright_zhihu/a2_get_api_data.py` 中修改：

```python
for i in range(20):  # 默认滚动 20 次
```

### 修改端口

在 `app.py` 最后一行修改：

```python
app.run(host='0.0.0.0', port=5065, debug=True)
```

## 已知问题

1. **Unicode 解码错误** - 爬虫运行时可能出现编码错误，不影响数据采集
2. **Cookies 过期** - 需要定期重新运行 `a1_login.py` 更新登录状态

## 待实现功能

- [ ] 自动定时爬取
- [ ] 内容自动推送（邮件/通知）
- [ ] 数据统计分析
- [ ] 关键词过滤
- [ ] 导出功能（CSV/Excel）

## 依赖项

主要依赖：
- Flask - Web 框架
- Playwright - 浏览器自动化
- python-dotenv - 环境变量管理
- google-generativeai - AI 功能（可选）

完整依赖见 `requirements.txt`

## 注意事项

⚠️ **免责声明**：本项目仅供学习交流使用，请遵守知乎的使用条款和 robots.txt 规则，不要过度爬取造成服务器压力。

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

## 联系方式

如有问题或建议，请提交 Issue。
