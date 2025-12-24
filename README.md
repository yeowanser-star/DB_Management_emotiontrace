# BiliMind: AI-Driven Sentiment Analysis System for Bilibili
### ~~BiliMind 是一款基于 DeepSeek 大模型与多线程架构的 B 站评论舆情分析系统。系统通过自动化爬虫获取非结构化评论数据，利用 AI 进行情感极性标注与特征提取，最终通过归一化算法与关系型数据库视图，在 Web 端实现多维度的舆情透视看板。~~ <br>更是哥们的数据库系统管理课程设计

### 🌟 核心特性
高性能并发分析：采用 ThreadPoolExecutor 线程池技术（15路并发），大幅抵消 AI 接口网络延迟，实现评论的秒级批量解析。

语义深度洞察：集成 DeepSeek-V3 接口，支持上下文感知的情感评分（0.0-1.0）及 20 个高频特征标签的自动提取。

工业级数据库设计：基于 MySQL 实现建模，通过自引用外键还原评论嵌套层级，并利用数据库视图（View）实现相关性加权的统计计算。

可视化交互看板：使用 Streamlit 构筑前端，集成 Plotly 动态图表与进度条式明细展示，支持一键物理重置数据库。

### 🏗️ 技术架构
前端: Streamlit (提供实时交互与多维看板)

后端: Python 3.10+ (多线程异步调度)

AI 引擎: DeepSeek API (负责语义理解与特征映射)

数据库: MySQL (支持级联约束与复杂视图计算)

### 🚀 快速开始
#### 1. 克隆项目
```Bash
git clone https://github.com/yeowanser-star/DB_Management_emotiontrace.git
cd DB_Management_emotiontrace
````
#### 2. 环境配置
创建并激活虚拟环境，安装依赖：

```Bash
pip install -r requirements.txt
```
#### 3. 配置隐私信息 (重要)
出于安全原因，自己建.env配置敏感信息

DeepSeek API Key

MySQL 数据库连接凭证

#### 4. 运行系统

```Bash
streamlit run app.py
```
### 📊 数据库结构说明
项目依赖 database_scrpit.sql 进行初始化。

### 🛡️ 安全注意事项
敏感信息: 请勿将包含 SESSDATA 的 B 站 Cookie 或 API Key 硬编码在 app.py 中直接上传。

### 📅 未来路线图 (Roadmap)
[ ] 引入向量数据库 (Milvus) 实现基于语义相似度的评论检索。

[ ] 接入多模态模型，支持视频弹幕与表情包的情感解析。

[ ] 优化训练专门的情感分析模型，deepseek无法做到更复杂的情感分析
