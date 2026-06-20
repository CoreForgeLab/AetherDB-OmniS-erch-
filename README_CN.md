[![中文](https://img.shields.io/badge/lang-中文-red.svg)](README_CN.md) [![English](https://img.shields.io/badge/lang-English-blue.svg)](README.md)

# 世界观数据库管理系统

基于 **FastAPI + SQLite** 的世界观（小说设定）数据库管理系统。支持 8 种实体类型管理、关系图谱、标签索引、版本历史、时间线、语义搜索、LLM 辅助导入、数据备份与日志系统。

---
> **🔒 API 稳定性承诺**
>
> 在 **V1.1.5** 版本之前，本项目承诺**不会引入大面积破坏性变更（Breaking Changes）**。
>
> - ✅ 现有 API 路径、请求/响应格式保持向后兼容
> - ✅ 数据库 Schema 不做破坏性迁移
> - ✅ 配置项与关键参数保持兼容
> - ✅ 新功能以向后兼容的方式添加
>
> 如有必要变更，会在 Release Notes 中明确标注并提供迁移指南。
> *V1.1.5 及之后，破坏性变更将遵循语义化版本规范（SemVer）管理。*

---

## 快速开始

```bash
# 1. 克隆项目
git clone <repo-url> && cd novel-world-db

# 2. 安装依赖
python -m venv venv
source venv/bin/activate  # Linux/Mac
# .\venv\Scripts\Activate.ps1  # Windows
pip install -r requirements.txt

# 3. 启动服务
python main.py

# 4. 打开浏览器
# 网页界面: http://localhost:8000
# API 文档: http://localhost:8000/docs
```

## 配置

复制 `config.yaml` 并按需修改：

```yaml
extractor:
  backend: "openai_compatible"   # 或 "ollama"
  openai_compatible:
    api_base: "https://api.deepseek.com/v1"
    model: "deepseek-chat"
```

API 密钥通过环境变量设置（优先级高于配置文件）：

```bash
export ADMIN_API_KEY="your-admin-key"
export USER_API_KEY="your-user-key"
```

## V1.18.0 新增功能

### 📝 日志系统（services/logger.py）
- 旋转文件日志：`app.log`（应用）、`error.log`（错误）、`access.log`（请求）
- 控制台同步输出，日志级别可配置
- 运行中读取/筛选/统计日志（`/api/logs/*`）

### 💾 数据备份 API（api/backup.py）
- JSON 格式全表导出/导入（entities、relations、timeline_events 等 6 张表）
- 数据库快照（.db 文件拷贝）
- 备份创建、列表浏览、恢复、自动清理
- 自动备份开关（持久化至 config.yaml）

### 🛣️ 路由拆分（routes/web.py）
- Web 页面路由从 `main.py` 独立拆分，代码更清晰

### 🗄️ 数据库迁移（alembic/）
- Alembic 迁移框架集成，支持数据库 Schema 版本管理
- 首个迁移包含完整的表结构

### 🧪 CLI 工具（scripts/）
### 🐍 环境兼容与依赖锁定（requirements.txt）
- 已验证 Python 3.10 ~ 3.13 全部兼容
- 所有依赖版本已精确锁定（pinned exact versions），已知可协同工作
- Starlette TemplateResponse API 兼容性修复（0.27.0 old-sig / 1.3.1+ new-sig）
- OpenAI SDK 改为可选依赖（需要 LLM 抽取时取消注释）
- 新增 httptools（可选的 uvicorn HTTP 解析加速器）
- `scripts/backup.py` — 命令行数据备份

## V1.x 技术路线图

| 版本 | 状态 | 核心功能 |
|------|------|----------|
| v1.0.0Beta | ✅ 已发布 | 初始版本：8 种实体类型、CRUD、关系图谱、标签、时间线 |
| V1.1.5 | ✅ 已发布 | 服务层重构、语义搜索、一致性检查、向量存储、速率限制 |
| V1.19.1 | ✅ 当前 | 日志系统、数据备份 API、路由拆分、Alembic 数据库迁移 |
| v1.1.0 | ✅ 已发布（V1.1.5） | 高级 RAG、sqlite-vec、混合搜索、一致性检查（已在 V1.1.5 中完成） |
| v1.2.0 | 📅 规划 | 多语言架构（entity_translations 表、跨语言搜索） |
| v1.3.0 | 📅 规划 | 缓存（diskcache）、LLMProvider 抽象、D3.js 知识图谱 |
| v2.0+ | 🔮 远期 | FAISS/Qdrant 向量数据库、PostgreSQL、Docker 部署 |

## 项目结构

```
├── main.py                          # 后端入口 (FastAPI)
├── routes/web.py                    # Web 页面路由
├── api/                             # API 路由模块
│   ├── backup.py                    #   数据备份 API
│   ├── search_semantic.py           #   语义搜索
│   ├── rag_context.py               #   RAG 上下文
│   └── consistency_check.py         #   一致性检查
├── services/                        # 服务层
│   ├── logger.py                    #   日志系统
│   ├── db.py                        #   数据库连接池
│   ├── embedding.py                 #   嵌入向量服务
│   ├── vector_store.py              #   向量存储
│   ├── consistency.py               #   一致性检查引擎
│   ├── auth.py                      #   权限认证
│   └── rate_limiter.py              #   速率限制
├── app/dependencies/auth.py         # 权限依赖注入
├── extractors/                      # LLM 实体抽取器
│   ├── base.py                      #   抽象基类
│   ├── openai_compatible.py         #   OpenAI 兼容后端
│   └── ollama.py                    #   Ollama 后端
├── prompts/extract_entities.txt     # 抽取提示词模板
├── templates/                       # Jinja2 前端模板
│   ├── index.html                   #   首页
│   ├── add.html                     #   添加实体
│   ├── search.html                  #   搜索
│   ├── timeline.html                #   时间线
│   ├── admin.html                   #   管理面板
│   └── import.html                  #   LLM 导入
├── static/style.css                 # 全局样式
├── alembic/                         # 数据库迁移
├── scripts/                         # CLI 工具
├── config.yaml                      # 配置文件示例
├── requirements.txt                 # Python 依赖
└── tests/                           # 单元测试
    ├── test_extractors.py           #   抽取器测试（9 用例）
    └── test_crud.py                 #   CRUD 测试（13 用例）
```

## API 概览

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| POST | /api/entity | user | 创建实体 |
| GET | /api/entity/{id} | user | 获取实体详情 |
| PUT | /api/entity/{id} | admin | 更新实体 |
| DELETE | /api/entity/{id} | admin | 软删除实体 |
| POST | /api/search | user | 搜索实体 |
| POST | /api/search/semantic | user | 语义搜索（混合检索） |
| POST | /api/rag/context | user | RAG 上下文检索 |
| POST | /api/consistency/check | admin | 一致性检查 |
| POST | /api/import/preview | admin | LLM 提取预览 |
| POST | /api/import/confirm | admin | 确认导入 |
| POST | /api/backup/create | admin | 创建数据备份 |
| GET | /api/backup/list | user | 备份列表 |
| GET | /api/backup/stats | user | 备份统计 |
| POST | /api/backup/restore/{name} | admin | 恢复备份 |
| POST | /api/backup/cleanup | admin | 清理旧备份 |
| GET | /api/backup/auto-backup | user | 查看自动备份状态 |
| POST | /api/backup/auto-backup | admin | 开关自动备份 |
| GET | /api/logs/{log_type} | user | 读取日志 |
| GET | /api/logs/{log_type}/stats | user | 日志统计 |
| GET | /api/stats | user | 系统统计 |

认证方式：请求头 `X-API-Key: your-key` 或查询参数 `?api_key=your-key`。



## Workspace / Database ID

本项目提前引入了 **Workspace（工作区）** 概念，作为未来多数据库管理的基础设施预留。

配置文件 config.yaml 中对应设置：

```yaml
app:
  workspace_id: "default"   # 当前数据库实例的唯一标识
```

- **用途**：每个数据库实例拥有唯一的 workspace_id，备份元数据中会携带此标识
- **未来路线**：多数据库路由、跨库检索、分布式部署时区分不同实例
- **默认值**："default"（单数据库场景无需修改）
- **备份文件**：backup_metadata.json 中记录 workspace_id 字段
- **当前状态**：仅用于标识和元数据记录，完整多数据库管理功能在后续版本实现

## 运行测试

```bash
python -m unittest discover tests -v
```

覆盖范围：抽取器 JSON 解析边界、输入清洗、CRUD 边界条件（空值、外键约束、软删除、版本历史）。

## 开放源代码

本项目采用 MIT 许可证。