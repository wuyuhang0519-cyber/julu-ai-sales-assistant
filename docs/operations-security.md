# 运行、安全与故障矩阵

## 安全边界

- 密钥只通过服务端环境变量注入，集成状态接口只返回布尔状态和最后成功时间。
- 管理 Cookie 为 HttpOnly、SameSite=Lax；生产启用 Secure/HSTS。写请求必须同时携带 CSRF Cookie 和 Header。
- 登录失败按来源限流；请求体上限 1 MB；统一设置 CSP、X-Frame-Options、nosniff 和 Referrer-Policy。
- Redactor 处理邮箱、电话、Cookie、Authorization、API Key、Token 和服务账号字段；ActivityLog、AIInvocation 与异常摘要均走脱敏。
- 邮件必须命中 `EMAIL_TEST_ALLOWLIST`，否则保存 `Blocked` 且不访问 Resend。
- Gitleaks 在 CI 扫描仓库；公开前仍需在本机执行 `gitleaks git --log-opts="--all"` 扫描完整历史。

## 故障矩阵

| 场景 | 策略 | 业务状态 |
|---|---|---|
| OpenAI 超时 / 网络 / 5xx | SDK 有限重试，最终安全降级 | 不更新 Profile、分数、Intent、状态 |
| OpenAI 401 | 记录配置错误，不盲重试 | 客户消息保留，转人工 |
| 非法 JSON / 缺字段 / 越界 | 一次结构修复，再失败降级 | 不推进状态 |
| Intent 与总分不一致 | 服务端按区间纠正并审计 | 采用纠正结果 |
| Google 401/403 | 分类为 auth，不更新 Meeting | Slot 回滚释放 |
| Google 409 | 返回冲突 | 原预约和 Lead 不变 |
| Google 429 / 5xx / 网络 | 分类为可重试失败并审计 | Slot 回滚释放 |
| Calendar 取消失败 | 保留本地 Confirmed，标记同步失败 | 不释放 Slot |
| Resend 非白名单 | Blocked，不发请求 | Follow-up Skipped |
| Resend 401/403 | 不重试 | Follow-up Failed |
| Resend 429 / 5xx / 网络 | 指数退避，最多三次 | Scheduled 或 Failed |
| 重复 Lead / 消息 / 预约 | 幂等键与数据库约束 | 返回既有结果 |
| 调度进程崩溃 | lease 过期回收 | 避免永久 Processing |
| 人工接管 / Closed / Meeting | 取消或跳过未执行任务 | 自动推进被阻止 |

## 上线检查

1. `APP_ENV=production`、`DEMO_MODE=false`、`COOKIE_SECURE=true`。
2. 强随机管理员密码和至少 32 位 Session Secret。
3. Railway 单实例，Volume 挂载 `/app/data`，数据库使用绝对路径。
4. OpenAI、Google 服务账号、Resend 使用最小权限测试资源；禁止真实批量触达。
5. 完成一次成功和一次可控失败，并在后台验证 IntegrationEvent、AIInvocation 与 ActivityLog。
6. 扫描代码、镜像、日志和全部 Git 历史，确认无密钥、服务账号 JSON 或客户数据。
7. 备份 SQLite Volume；部署前后记录 Alembic revision。

## 两周演进路线

- 第 1 周：PostgreSQL、独立 Worker、OIDC/RBAC、指标告警、备份恢复、Calendar webhook。
- 第 2 周：版本化评测集、真实模型回归、Prompt A/B、可引用 RAG、OpenTelemetry、数据保留与删除流程。
