# 全加分功能版说明

本文件对应分支 feature/all-bonus-features。该分支位于独立 Git worktree，不是当前 Railway 稳定版。除非明确合并到 main 并重新部署，否则不会改变现有公网 Demo。

## 完成矩阵

| 能力 | 实现状态 | 验收边界 |
|---|---|---|
| 销售人员接管 | 完成 | 后台接管/释放；接管后 AI 不再自动推进 |
| 长期客户记忆 | 完成 | 对话、Profile、事实、状态、报价、Proposal 和同步记录持久化 |
| 定时 Follow-up | 完成 | 人工审批、定时调度、租约回收、幂等、重试、取消和审计 |
| 邮件渠道 | 已完成并真实验收 | Resend 白名单测试邮件返回 Delivered；密钥只存 Railway Secret |
| RAG 企业知识库 | 完成 | Markdown 分块、本地哈希向量、余弦 Top-K 检索、Prompt 注入、引用追踪；检索 API 仅管理员可用 |
| WhatsApp | 代码完成，真实验收待 Meta | Cloud API、测试白名单、DryRun/Blocked 和审计已实现；账号申诉通过后补充测试号码、Phone Number ID 和令牌 |
| 语音对话 | 完成 | 浏览器 Web Speech API 语音输入和回复朗读；Chrome/Edge 支持最佳 |
| 多语言 | 完成 | 自动识别并支持中文、英语、西班牙语回复和 Proposal |
| 自动报价 | 完成 | 三档演示价格目录、折扣上限、有效期、草案/审批；明确非正式报价 |
| 自动 Proposal | 完成 | 基于已确认客户事实、RAG 引用和报价草案生成中/英/西方案 |
| HubSpot 同步 | 已完成并真实验收 | 最小权限 Service Key；按邮箱 Upsert，已在 HubSpot 生成真实联系人和 External ID |
| Salesforce 同步 | 可选替代适配器完成 | 本次选择 HubSpot 路线，因此 Salesforce 保持未配置，不影响“HubSpot/Salesforce”验收 |

“代码完成”不等于第三方平台已真实连通。没有真实密钥时系统返回 DryRun 或 Blocked，不会伪造 Message ID 或 CRM External ID。当前唯一尚未完成真实外部验收的加分能力是 WhatsApp。

## 后台操作

进入某条线索详情的“加分能力工作台”：

1. 生成报价草案。
2. 生成 Proposal 并预览。
3. 发送测试邮件或 WhatsApp。
4. 同步 HubSpot 或 Salesforce。
5. 在“集成”页查看各 Provider 是否配置、最近成功时间和 RAG 分块数。

## 新增环境变量

    FOLLOWUP_CHANNELS=email,whatsapp
    WHATSAPP_ACCESS_TOKEN=
    WHATSAPP_PHONE_NUMBER_ID=
    WHATSAPP_API_VERSION=v21.0
    WHATSAPP_TEST_ALLOWLIST=8613800000000
    HUBSPOT_ACCESS_TOKEN=
    SALESFORCE_INSTANCE_URL=
    SALESFORCE_ACCESS_TOKEN=
    CRM_DRY_RUN=true
    QUOTE_CURRENCY=CNY
    QUOTE_VALID_DAYS=14
    RAG_TOP_K=4
    RAG_MIN_SCORE=0.04

安全默认值：

- 邮件和 WhatsApp 只有命中 allowlist 才会访问第三方 API。
- CRM 默认 `CRM_DRY_RUN=true`；仅在独立加分版完成 HubSpot 验收后设置为 false。
- 报价与 Proposal 默认都是 Draft。
- 企业知识检索接口需要管理员登录。
- 日志只保存脱敏收件人，不保存第三方密钥。

## 本地运行

隔离版 Docker 端口使用 8001，避免与稳定版的 8000 冲突：

    docker compose up --build

访问 http://localhost:8001。

## 已执行验收

- 后端测试：22 项通过。
- 覆盖率：87.62%，高于 85% 门禁。
- AI 固定评测：9/9 通过。
- Ruff：通过。
- mypy：通过。
- 前端 Vitest：通过。
- 前端生产构建：通过。
- Playwright 隔离端口 8001 核心 E2E：1/1 通过。
- Alembic 0001 → 0002 → 0003：全新升级和重复升级通过。
- Railway Docker 构建与部署：通过。Windows 本机 Docker 重建被用户级 DaoCloud 镜像源 401 阻塞，未停止正在运行的保底版容器；干净 GitHub CI 的独立 Docker 构建已通过。
- GitHub CI 综合任务（含 Gitleaks、Playwright、迁移与完整测试）：通过。
- Resend 直接邮件与定时 Follow-up：Delivered。
- HubSpot 联系人 Upsert：Synced。
