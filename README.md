# A-Share Quantitative Analysis & Alert System

一个高容错、全自动的 A 股中线量化分析与预警系统。基于 Tushare 数据源，采用多因子共振策略进行��股，并由本地大语言模型（LLM）生成策略简报。

## 📋 项目特性

- ✅ **高可用数据管道** - 指数退避重试机制，支持完全增量更新
- ✅ **多因子评分引擎** - 趋势、资金面、板块情绪三维共振
- ✅ **实时可视化看板** - Streamlit 前端展示选股池和资金流向
- ✅ **AI 研报生成** - 本地 LLM 驱动的自动化策略简报
- ✅ **跨平台支持** - Dev (macOS) / Prod (Ubuntu) 双环境配置

## 🏗 项目架构

### 开发阶段

| Phase | 名称 | 状态 | 描述 |
|-------|------|------|------|
| Phase 1 | 数据管道建设 (Data Pipeline) | ✅ 完成 | Tushare 增量拉取、SQLite 存储、同步日志 |
| Phase 2 | 多因子分析引擎 (Quant Logic) | 🔄 进行中 | EMA/MACD 计算、因子评分、共振判断 |
| Phase 3 | 可视化看板 (Dashboard) | ⏳ 计划中 | Streamlit 前端、实时更新、数据可视化 |
| Phase 4 | LLM 代理与自动化 (AI Agent) | ⏳ 计划中 | 报告生成、调度器、双环境 Docker 配置 |

### 文件结构

```
a-share-quant-system/
├── .env.example              # 环境变量模板
├── .gitignore               # Git 忽略文件
├── requirements.txt         # Python 依赖
├── README.md               # 项目文档
├── docker-compose.yml      # Dev 环境 Docker 配置
├── docker-compose.prod.yml # Prod 环境 Docker 配置
├── src/
│   ├── __init__.py
│   ├── config.py           # 配置管理（Dev/Prod）
│   ├── logger.py           # 日志配置
│   └── data/
│       ├── __init__.py
│       ├── db_schema.py    # SQLite 数据库架构定义
│       ├── tushare_client.py  # Tushare API 客户端（含重试机制）
│       ├── pipeline.py     # 数据管道引擎（增量同步）
│       └── init_db.py      # 数据库初始化脚本
├── data/                   # 数据目录（.gitignore）
└── logs/                   # 日志目录（.gitignore）
```

## 🚀 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/sean202306/a-share-quant-system.git
cd a-share-quant-system
```

### 2. 创建虚拟环境

```bash
python3.11 -m venv venv
source venv/bin/activate  # macOS/Linux
# 或
venv\Scripts\activate  # Windows
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入你的 Tushare Token：

```env
TUSHARE_TOKEN=your_tushare_pro_token_here
ENV=dev
DEBUG=true
```

获取 Tushare Token：https://www.tushare.pro/

### 5. 初始化数据库

```bash
python -m src.data.init_db
```

### 6. 执行数据管道

```bash
python -c "
from src.data.pipeline import DataPipeline

with DataPipeline() as pipeline:
    results = pipeline.full_sync()
    print(results)
"
```

## 🔑 核心模块说明

### 配置管理 (`src/config.py`)

- 支持 Dev (macOS) 和 Prod (Ubuntu) 两套环境配置
- 使用 `python-dotenv` 管理敏感信息
- 跨平台路径处理（基于 `pathlib`）

### Tushare 客户端 (`src/data/tushare_client.py`)

**特性:**
- 🔄 **指数退避重试机制** - 自动处理 API 频率限制
- 🛡️ **异常捕获** - 智能识别速率限制错误并重试
- 📦 **方法封装** - 股票基础、日线行情、资金流向、概念板块等

**使用示例:**

```python
from src.data.tushare_client import TushareClient

client = TushareClient(token="your_token")

# 获取股票列表
stocks = client.get_stocks()

# 获取日线行情
quotes = client.get_daily_quotes(ts_code="000001.SZ", start_date="20230101")

# 获取资金流向
fund_flow = client.get_fund_flow(ts_code="000001.SZ")
```

### 数据库架构 (`src/data/db_schema.py`)

**主要表:**

| 表名 | 描述 | 关键字段 |
|------|------|----------|
| stocks | A股股票列表 | ts_code, name, industry, list_date |
| daily_quotes | OHLCV K线数据 | ts_code, trade_date, close, volume |
| fund_flow | 主力资金流向 | ts_code, trade_date, net_inflow |
| indicators | 技术指标 | ts_code, trade_date, ema20, ema60, macd |
| concept_sectors | 概念板块成分股 | concept_id, ts_code |
| sector_daily_performance | 板块日线表现 | concept_id, trade_date, close_change |
| sync_log | 同步日志 | table_name, last_sync_date, status |

### 数据管道 (`src/data/pipeline.py`)

**增量同步特性:**

- 🔄 `sync_stocks()` - 同步股票列表
- 📊 `sync_daily_quotes()` - 增量同步日线数据（UPSERT）
- 💰 `sync_fund_flow()` - 增量同步资金流向
- 📈 `sync_concepts()` - 同步板块成分及其关系
- ⚙️ `full_sync()` - 一键执行完整同步流程

**使用示例:**

```python
from src.data.pipeline import DataPipeline

with DataPipeline() as pipeline:
    # 执行完整同步
    results = pipeline.full_sync()
    
    # 或单独执行
    pipeline.sync_daily_quotes(days=5)  # 同步最近 5 天
```

## 🐳 Docker 使用

### Dev 环境 (macOS)

```bash
docker-compose up -d
```

### Prod 环境 (Ubuntu with GPU)

```bash
docker-compose -f docker-compose.prod.yml up -d
```

## 📊 多因子评分引擎说明

系统采用百分制 (0-100) 评分，重点捕获"右侧交易"的确定性：

### 因子A: 趋势与动量底座 (40%)

条件：
- K线站上 EMA20
- EMA20 处于上升趋势或刚刚金叉 EMA60
- MACD 处于零轴上方

### 因子B: 资金面深度验证 (40%)

条件：
- 近 5-10 个交易日主力资金/大单净流入累计值为正
- 筹码集中度高
- 加分项：北向资金同期增持

### 因子C: 板块与情绪共振 (20%)

条件：
- 所属概念板块资金净流入排名靠前
- 板块指数处于上升通道
- 享受 Beta 溢价

## 🔄 环境变量配置

| 变量 | 值 | 说明 |
|------|-----|------|
| ENV | dev / prod | 运行环境 |
| DEBUG | true / false | 调试模式 |
| TUSHARE_TOKEN | - | Tushare Pro API Token |
| DB_PATH | data/quant_system.db | 数据库路径 |
| LLM_BASE_URL | http://localhost:8000/v1 | LLM API 地址（Phase 4） |
| MAX_RETRIES | 5 | 最大重试次数 |
| RETRY_BACKOFF_FACTOR | 2 | 重试退避因子 |
REQUEST_TIMEOUT | 30 | 请求超时时间（秒） |
| LOG_LEVEL | INFO | 日志级别 |

## 🧪 测试

运行单元测试：

```bash
pytest tests/ -v
```

生成覆盖率报告：

```bash
pytest tests/ --cov=src --cov-report=html
```

## 📝 工作流程

1. **数据采集** → Tushare API (每日定时)
2. **增量更新** → SQLite (UPSERT 避免重复)
3. **指标计算** → EMA, MACD, 资金流 (实时)
4. **因子评分** → 多维评分引擎 (实时)
5. **可视化展示** → Streamlit Dashboard (实时)
6. **研报生成** → 本地 LLM Agent (定时)

## 🔧 系统要求

### Dev 环境 (macOS)

- Python 3.11+
- macOS 12.7.6
- 6-core Intel Xeon E5
- 3GB 显存 (MD FirePro D500)

### Prod 环境 (Ubuntu)

- Python 3.11+
- Ubuntu 24.04 LTS
- NVIDIA GPU (20GB VRAM)

## 📚 参考资源

- [Tushare Pro 文档](https://www.tushare.pro/)
- [Streamlit 文档](https://docs.streamlit.io/)
- [TA-Lib 文档](https://github.com/mrjbq7/ta-lib)
- [SQLite 文档](https://www.sqlite.org/docs.html)

## 📄 许可证

MIT License - 详见 LICENSE 文件

## 👤 作者

- **GitHub:** [@sean202306](https://github.com/sean202306)

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

**最后更新:** 2026-05-08