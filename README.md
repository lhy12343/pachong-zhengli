# 🕷️ Python 爬虫学习与实战项目

[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Last Update](https://img.shields.io/badge/Last%20Update-2025--01-orange.svg)](https://github.com/lhy12343/pachong-zhengli)

> 从基础到实战的Python爬虫完整学习路径，包含多种技术栈和真实项目案例

---

## 📚 项目概览

本仓库是一个完整的Python爬虫学习项目，涵盖从入门到高级实战的所有内容。通过循序渐进的方式，帮助开发者掌握网络爬虫的核心技术和最佳实践。

### 🎯 核心特性
- ✅ **系统性学习路径**：从基础HTTP请求到复杂的分布式爬虫
- ✅ **真实项目案例**：小红书、抖音、知乎等主流平台爬虫
- ✅ **多种技术栈**：requests、Selenium、Scrapy框架全覆盖
- ✅ **企业级实践**：反爬对抗、数据存储、监控告警
- ✅ **开箱即用**：完整配置文件和依赖管理

---

## 📁 项目结构

```
pachong/
├── 01_第一章_爬虫入门/           # HTTP基础、requests入门
├── 02_第二章_数据解析/           # 正则表达式、BeautifulSoup、lxml
├── 03_进阶/                     # Cookie处理、代理、反爬对抗
├── 04_多线程/                   # 并发编程、异步爬虫、性能优化
├── 05_selenium入门/             # 浏览器自动化、动态网页处理
├── 06_scrapy框架/               # Scrapy分布式爬虫框架
│   ├── 1_scrapy基础/
│   └── zhihu/                   # 知乎用户数据爬虫项目
├── 抖音小红书/                   # 社交媒体平台爬虫
│   ├── 小红书爬取/
│   └── 抖音搜索关键词批量视频抓取下载/
├── 全国建筑市场监督公共服务平台/  # 政府网站数据采集
├── 实战训练/                     # 综合实战项目
└── requirements.txt             # 项目依赖
```

---

## 🚀 快速开始

### 环境要求
- Python 3.12+
- Google Chrome 浏览器
- Git

### 安装步骤

1. **克隆项目**
```bash
git clone https://github.com/lhy12343/pachong-zhengli.git
cd pachong-zhengli
```

2. **创建虚拟环境**
```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate
```

3. **安装依赖**
```bash
pip install -r requirements.txt
```

4. **运行第一个爬虫**
```bash
python 01_第一章_爬虫入门/01_第一个爬虫的开发.py
```

---

## 💡 学习路径推荐

### 🌱 初级阶段（1-2周）
1. **HTTP基础** → `01_第一章_爬虫入门/`
2. **数据解析** → `02_第二章_数据解析/`
3. **基础实践** → 完成豆瓣电影TOP250项目

### 🌿 中级阶段（2-3周）
1. **进阶技术** → `03_进阶/`（登录、代理、反爬）
2. **并发编程** → `04_多线程/`
3. **浏览器自动化** → `05_selenium入门/`

### 🌳 高级阶段（3-4周）
1. **Scrapy框架** → `06_scrapy框架/`
2. **真实项目** → 知乎用户爬虫、小红书内容爬虫
3. **企业实战** → `实战训练/`

---

## 📖 重点项目介绍

### 🔥 知乎用户爬虫（Scrapy框架）
```bash
cd 06_scrapy框架/zhihu
python run_spider.py
```
- **技术栈**：Scrapy + 动态用户代理 + 智能文件命名
- **功能**：批量采集用户详情数据，支持自定义数量和关键词
- **特色**：智能文件命名（预期数量vs实际数量对比）

### 🎨 小红书内容爬虫
```bash
cd 抖音小红书/小红书爬取
python 小红书爬取关键词笔记.py
```
- **技术栈**：Selenium + CDP抓包 + 并发下载
- **功能**：关键词搜索、笔记详情、图片视频下载
- **特色**：会话持久化、智能登录检测、多媒体下载

### 📊 综合数据采集项目
- **政府网站数据**：`全国建筑市场监督公共服务平台/`
- **PDF文档处理**：`实战训练/`
- **多平台整合**：抖音+小红书联合采集

---

## ⚙️ 配置说明

### Chrome配置
项目使用Chrome浏览器进行自动化操作，需要：
- 安装最新版Chrome
- chromedriver会自动管理（Selenium Manager）
- 用户数据持久化到`chrome_user_data/`目录

### 代理配置
```python
# 示例：使用代理
proxies = {
    'http': 'http://proxy-server:port',
    'https': 'https://proxy-server:port'
}
```

### 反爬策略
- 随机User-Agent
- 智能延时控制
- Cookie池管理
- 请求头伪装

---

## 🔧 故障排除

### 常见问题

**Q: selenium.common.exceptions.WebDriverException**
```bash
# 解决方案：更新Chrome或设置PATH
pip install --upgrade selenium
```

**Q: 403/406错误**
```bash
# 解决方案：检查请求头和Cookie
# 使用CDP抓包获取真实请求参数
```

**Q: 并发下载失败**
```python
# 降低并发数和请求频率
max_workers = 5  # 默认10
rate_limit = 30  # 默认50/秒
```

### 性能优化
- 使用异步请求（aiohttp）
- 启用HTTP连接池
- 合理设置超时时间
- 实现智能重试机制

---

## 📊 技术栈

| 技术 | 用途 | 项目中的应用 |
|------|------|-------------|
| **requests** | HTTP客户端 | 基础数据获取 |
| **Selenium** | 浏览器自动化 | 动态网页、JS渲染 |
| **Scrapy** | 爬虫框架 | 分布式、高并发爬虫 |
| **BeautifulSoup** | HTML解析 | 结构化数据提取 |
| **asyncio** | 异步编程 | 高性能并发请求 |
| **pandas** | 数据处理 | 数据清洗和分析 |

---

## 🤝 贡献指南

### 如何贡献
1. Fork本项目
2. 创建功能分支：`git checkout -b feature/amazing-feature`
3. 提交更改：`git commit -m 'Add some amazing feature'`
4. 推送分支：`git push origin feature/amazing-feature`
5. 提交Pull Request

### 代码规范
- 遵循PEP 8代码风格
- 添加必要的注释和文档
- 包含测试用例
- 更新README文档

---

## ⚖️ 免责声明

> ⚠️ **重要提醒**：本项目仅供学习和研究使用

### 使用原则
- ✅ **学习研究**：用于技术学习和学术研究
- ✅ **遵守法律**：严格遵守当地法律法规
- ✅ **尊重robots.txt**：遵循网站爬虫协议
- ❌ **商业用途**：不得用于商业盈利活动
- ❌ **恶意爬取**：不得进行大规模恶意爬取
- ❌ **侵犯隐私**：不得获取用户隐私信息

### 法律责任
使用本项目代码所产生的一切法律责任由使用者自行承担，项目作者不承担任何责任。

---

## ⭐ Star History

如果这个项目对你有帮助，请给个Star⭐支持一下！

[![Star History Chart](https://api.star-history.com/svg?repos=lhy12343/pachong-zhengli&type=Date)](https://star-history.com/#lhy12343/pachong-zhengli&Date)

---

<div align="center">
  <h3>🎯 让爬虫学习更简单！</h3>
  <p>从零基础到企业级应用，一站式Python爬虫学习平台</p>

  **[⭐ Star](https://github.com/lhy12343/pachong-zhengli)** • **[🍴 Fork](https://github.com/lhy12343/pachong-zhengli/fork)** • **[📖 文档](https://github.com/lhy12343/pachong-zhengli/wiki)** • **[💬 讨论](https://github.com/lhy12343/pachong-zhengli/discussions)**
</div>