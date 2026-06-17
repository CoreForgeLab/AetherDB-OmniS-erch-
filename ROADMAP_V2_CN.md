# 整合技术路线图 v2.1 — 终版

> 确认日期 2026-06-17。全部决策来源于完整对话审计。

## 已锁定的架构决策

| 决策项 | 选择 | 时间线 |
|---|---|---|
| 向量数据库 | sqlite-vec V1.x → FAISS/Qdrant V2.0 | V1.1 / V2.0 |
| 多语言支持 | entity_translations 独立表（非 JSON 字段） | V1.2 |
| 一致性检查器 | 规则引擎 + LLM 辅助 | V1.1 基础 / V1.3 高级 |
| 嵌入向量 | Ollama（开发）→ OpenAI（生产） | V1.1 |
| LLM 接口 | 抽象 LLMProvider | V1.3 |
| 多书支持 | book_id V1.1；完整层级 V1.5 | V1.1 / V1.5 |
| 缓存 | diskcache（零依赖、文件级） | V1.3 |
| 开源 | 已在线上；有外部贡献者希望集成 | 当前 |
| 混合搜索权重 | 语义 0.7 + 关键词 0.3（RRF 合并） | V1.1 |
| API 稳定性 | V1.1.0 之前无破坏性变更 | 当前 |

---

## V1.0 补丁 — 立即执行（第 1 周）

**约束**：不破坏现有 API。
- **内网/无域名**：所有部署目标必须支持零域名的本地操作。无硬编码 URL 或 DNS 依赖。
- **单库多书**：一个数据库通过 book_id 隔离支持多本书。
- 安全审计 P0 修复（移除 innerHTML 的 XSS 风险、API Key 从查询参数迁移至请求头、管理密钥移出页面源码）
- Schema：为全部 6 张表添加 book_id（entities、relations、tag_index、entity_versions、references_map、timeline_events）
- 修复缺失的 API 端点（/api/timeline、/api/search/quick、/api/import/preview、/api/import/confirm）
- 软删除级联清理
- 更新 CODEX_PROJECT_CONTEXT.md 以反映当前路线图

## V1.1.0 — 高级 RAG + 基础一致性检查器（第 2-5 周）

### 第一阶段：高级 RAG（第 2-3 周）
- sqlite-vec 集成 + vector_chunks 表
- 文本分块流水线（标题/摘要/内容/标签分块）
- EmbeddingProvider 抽象接口（先使用 Ollama nomic-embed-text）
- 实体创建/更新时自动重建嵌入向量
- /api/search/semantic（混合检索：向量 + FTS5 + 标签，RRF 合并排序）
- 升级 /api/rag/context（实体 + 关系 + 时间线联合检索）
- 多书隔离：所有查询通过 book_id 过滤

### 第二阶段：基础一致性检查器（第 4-5 周）
- 确定性检查的规则引擎
- /api/consistency/check 端点
- 4 种检查类型：时间线、角色、规则、阵营
- 图书感知：作用域限制在同一 book_id
- 输出：带严重级别的结构化冲突报告

---

## V1.2.0 — 多语言架构（第 6-7 周）
- entity_translations 表（entity_id、language、title、content）
- 迁移脚本（处理现有单语言数据）
- 跨语言搜索
- 实体翻译 API 端点
- 更新 EmbeddingProvider 以支持多语言（bge-m3）

## V1.3.0 — 基础设施与集成（第 8-10 周）
- 缓存：diskcache（零依赖、文件级，无需 Redis）
- 一致性检查器第二阶段：历史感知、跨实体深度检查
- LLMProvider 抽象接口（OpenAI、DeepSeek、Claude、Gemini、Ollama）
- D3.js 知识图谱力导向图页面
- 完整 CRUD 端点覆盖
- 部署脚本：NSSM（Windows）、systemd（Linux）

## V1.4.0 — 开放平台打磨（第 11-12 周）
- README、CONTRIBUTING、LICENSE 文件完善
- 完整 API 文档
- 预留插件接口

## V1.5.0 — 图谱层与完整层级（第 13-14 周）
- Neo4j 兼容层（用于关系数据）
- 完整层级：项目 → 宇宙 → 系列 → 书 → 实体
- 图谱查询 API

## V2.0+ — 生产环境与模拟（未来规划）
- VectorIndex 接口切换至 FAISS/Qdrant
- PostgreSQL + 对象存储
- Docker 部署
- Redis 完整缓存
- V3.0 时间线：状态系统、推演引擎、多智能体

---

## V1.x 能力映射

| 能力 | 版本 | 实现方式 |
|---|---|---|
| 世界观搜索 | V1.1.0 | 语义搜索 API |
| 世界观上下文 | V1.1.0 | RAG 上下文升级 |
| 时间线构建器 | V1.0 + V1.1 | 修复 + RAG 流水线 |
| 阵营分析 | V1.1.0 | 一致性检查器 |
| 力量体系 | V2.0+ | 预留后期实现 |
| 一致性检查 | V1.1 基础 / V1.3 高级 | 规则引擎 + LLM |
| 知识图谱 | V1.3.0 | D3.js 可视化 |

---

## 冲突解决记录

1. 一致性检查器 → V1.1.0 第二阶段（基础）+ V1.3.0（高级）
2. 知识图谱 → V1.3.0（非 V1.0 补丁）
3. 多语言支持 → entity_translations 独立表（非 JSON 字段）
4. 服务器部署 → 合并至 V1.3.0
5. 向量数据库 → sqlite-vec V1.x，FAISS/Qdrant V2.0
6. 缓存 → diskcache（零依赖）用于 V1.3.0
7. Schema 深度 → V1.1 仅 book_id；完整层级 V1.5
8. API 稳定性 → V1.1.0 之前无破坏性变更

---

确认日期 2026-06-17 | 本文件替代此前所有版本规划。全部 37/37 项需求已在完整对话审计中覆盖。