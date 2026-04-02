# TODO: 打造中国版 Hacker News

## 架构改进计划

### 1. Source 抽象层
- 数据库添加 `source` 字段 (zhihu, 36kr, juejin)
- 创建 `ContentSource` 基类
- 重构 parsers 为多平台支持: `parsers/zhihu.py`, `parsers/36kr.py`
- UI 增加平台筛选器

### 2. 统一质量评分系统
- 新增 `quality_score` 字段
- 各平台实现自己的评分算法
  - 知乎: upvotes*1.0 + fav_count*2.0 + (upvotes/comments)*0.5
  - 36kr: views*0.01 + likes*10
- 跨平台统一排序

### 3. 插件化爬虫架构
```
crawlers/
├── base.py
├── zhihu/
├── kr36/
└── juejin/
```
- 配置文件驱动 (sources.yaml)
- 支持定时任务
- 多源并行爬取

### 4. 标签系统
- 创建 tags 表和 content_tags 关联表
- 自动打标 (关键词匹配或 LLM)
- 分类: tech, business, product, design
- UI 增加标签云导航

### 5. RSS 聚合
- 快速接入有 RSS 的平台 (InfoQ, 少数派, V2EX)
- RSSSource 基类
- 降低维护成本

## 实施优先级
1. Source 抽象层 + 数据库改造
2. 统一质量评分
3. 接入 36kr + 掘金
4. 标签系统
5. RSS 聚合扩展

## 参考项目
- daily.dev (100万用户, 1300+源)
- RSSHub (40k stars, 中文 RSS 生成)
- Lobsters (HN 精简版)

## 市场定位
中文技术内容聚合 + 质量筛选 + 本地部署

## 下一步
- 开源到 GitHub
- Docker 一键部署
- Chrome 插件版本
