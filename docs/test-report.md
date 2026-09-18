# 测试与验收报告

生成日期：2026-09-19

| 检查项 | 结果 |
|---|---|
| 后端 pytest | 22/22 通过 |
| 后端覆盖率 | 87.62%，门槛 85% |
| AI 固定评测 | 9/9 通过 |
| Ruff | 通过 |
| mypy | 12 个模块无错误 |
| 前端 Vitest | 1/1 通过 |
| TypeScript + Vite 生产构建 | 通过 |
| Playwright 核心 E2E | 1/1 通过 |
| Railway Docker 镜像构建与部署 | 通过 |
| 本机 Docker 重建 | 被 DaoCloud 镜像源 401 阻塞；未停止保底版容器 |
| SQLite 升级 | 0001 → 0002 → 0003 通过 |
| Alembic 新库、旧库、重复升级 | 通过 |
| 桌面浏览器 | 无横向溢出、无控制台错误 |
| 390×844 移动端 | 无横向溢出、无控制台错误 |

## 已覆盖的关键行为

- Lead、消息、预约和 Follow-up 幂等。
- 不同 Lead 抢同一 Slot 返回 409；取消预约释放 Slot。
- SQLite 时区丢失后的显式 UTC 修复与 IANA 时区解释。
- 五维评分上限、总分一致、Intent 服务端纠正。
- 拒绝关闭、价格/合同转人工、人工接管阻止 AI 推进。
- CSRF、认证拒绝、日志脱敏、邮件白名单。
- Follow-up 审批、执行、租约回收、邮件 DryRun/Blocked/成功模拟。
- Calendar/Resend/WhatsApp/CRM 的 DryRun、Blocked、错误分类与真实 Provider 路径。
- HubSpot 只写标准联系人字段，并以 email 幂等 Upsert，避免重复联系人。

## 已完成的真实线上验收

2026-09-18 已在 Railway 公网环境使用虚构客户数据完成 SiliconFlow `deepseek-ai/DeepSeek-V4-Flash` 真实调用；`DEMO_MODE=false`，模型返回通过服务端 Schema 校验并生成 67 分、Medium 意向、Contacted 状态和个性化首次回复。密钥未写入仓库或报告。

同日已完成 Google Calendar 专用测试日历的真实验证：FreeBusy 查询成功、事件创建成功、事件取消成功。首次创建通过 `attendees` 邀请时得到预期的服务账号 403，系统随后改为个人账号安全模式（真实创建事件但不邀请参与者）；Google Workspace 可通过显式开关启用邀请。

Railway 公网健康检查返回 `ok`，数据库迁移为 Alembic，Volume 持久化、管理后台、AI 调用监控与部署后冒烟均已完成。后台保留了 DeepSeek 官方接口连接失败、SiliconFlow 超时和余额不足等可控失败记录，可用于解释安全降级。

2026-09-19 已完成 Resend 真实投递：直接配置验收邮件和经审批的离站 Follow-up 均显示 Delivered；非白名单地址显示 Blocked/Skipped，证明安全边界生效。已完成 HubSpot 最小权限 Service Key 接入，Lead #4 通过邮箱 Upsert 返回 `Synced` 和真实 External ID，并在 HubSpot 联系人页面可检索。

线上只读审计确认：`DEMO_MODE=false`，AI、Google Calendar、Resend、HubSpot 与 RAG 均显示 configured；HubSpot `dry_run=false`；HSTS、CSP、X-Frame-Options、nosniff 和 Referrer-Policy 均存在。

本地补充扫描未发现常见 OpenAI、Resend、HubSpot、GitHub、Google 或私钥特征；最终以 GitHub CI 的 Gitleaks 全历史扫描为准。

## 尚未执行的真实验收

WhatsApp Cloud API 的适配器、白名单、DryRun/Blocked 和审计已经实现，但 Meta 账号申诉尚未通过，无法取得测试号码、Phone Number ID 与临时访问令牌，因此不宣称真实 WhatsApp 发送成功。Salesforce 未配置是主动选择：同一“HubSpot/Salesforce”加分项已经由 HubSpot 路线完成真实验收。
