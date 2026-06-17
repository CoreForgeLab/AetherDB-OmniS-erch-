# 世界观数据库管理系统

基于 **FastAPI + SQLite** 的世界观（小说设定）数据库管理系统。支持 8 种实体类型管理、关系图谱、标签索引、版本历史、时间线和 LLM 辅助导入。

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

详细配置说明见 [config.yaml](config.yaml)。

## 项目结构

```
├── main.py                          # 后端入口 (FastAPI)
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
├── config.yaml                      # 配置文件示例
└── requirements.txt                 # Python 依赖
```

## API 概览

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| POST | /api/entity | user | 创建实体 |
| GET | /api/entity/{id} | user | 获取实体详情 |
| PUT | /api/entity/{id} | admin | 更新实体 |
| DELETE | /api/entity/{id} | admin | 软删除实体 |
| POST | /api/search | user | 搜索实体 |
| POST | /api/import/preview | admin | LLM 提取预览 |
| POST | /api/import/confirm | admin | 确认导入 |

认证方式：请求头 `X-API-Key: your-key` 或查询参数 `?api_key=your-key`。

## 开放源代码

本项目采用 MIT 许可证。
