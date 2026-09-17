# 测试与验收报告

生成日期：2026-09-18

| 检查项 | 结果 |
|---|---|
| 后端 pytest | 16/16 通过 |
| 后端覆盖率 | 87.79%，门槛 85% |
| AI 固定评测 | 9/9 通过 |
| Ruff | 通过 |
| mypy | 10 个模块无错误 |
| 前端 Vitest | 1/1 通过 |
| TypeScript + Vite 生产构建 | 通过 |
| Playwright 核心 E2E | 1/1 通过 |
| Docker 镜像构建 | 通过 |
| 旧 SQLite Volume 升级 | 0001 → 0002 通过 |
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
- Calendar/Resend 错误分类及真实 Provider 无密钥安全失败。

## 尚需带凭证执行的验收

当前环境未提供 OpenAI、Google Calendar、Resend、GitHub 或 Railway 凭证，因此以下项目不能在本机诚实宣称完成：

- 真实 OpenAI 成功调用、真实结构修复和一次可控失败记录。
- 专用 Google Calendar 的 FreeBusy、创建与取消事件。
- Resend 向本人白名单邮箱真实投递及 Provider Message ID。
- GitHub 私有仓库、Actions 绿灯、公开前全历史 Gitleaks。
- Railway 公网 URL 与部署后冒烟。

配置凭证后按照 `README.md` 的“真实主演示配置”和“Railway 部署”逐项执行，后台 Integration Events 可作为验证证据。
