# 面试答辩要点

## AI 为什么是真实且可验证的？

主演示关闭 Demo Provider，由 OpenAI Responses API 生成严格结构化结果。每轮保存模型、Prompt 版本、消息 ID、Token、耗时、请求 ID、验证状态、修复次数、知识引用和评分证据；原始对话与事实来源可逐项对照。

## 为什么不是固定问卷？

模型同时看到 Lead、已持久化 Profile、最近对话和知识库，依据当前缺口选择下一问题。已知字段不会重复询问，拒绝、合同承诺、知识边界和高意向会走不同动作。

## 模型和代码各自负责什么？

模型负责语言理解、事实建议、分项证据、推荐与动作建议。代码负责 Schema 校验、Intent 纠正、状态优先级、权限、事务、幂等、预约占用、重试、调度与审计。模型不能直接决定最终数据库状态。

## 如何控制幻觉和 Prompt 注入？

知识库有稳定引用 ID；Prompt 禁止虚构价格、案例、合同和效果保证；枚举和 JSON Schema 限制动作；价格/合同/保证类请求转人工。固定评测包含知识外问题与 Prompt 注入。

## 无效模型输出怎么办？

先由严格 Schema 与 Pydantic 校验。失败时仅进行一次结构修复；再失败则写失败调用，向客户返回自然降级提示，不改 Profile、评分、Intent 和状态。人工可以从后台接管。

## 预约并发如何证明？

时段是独立 `AvailabilitySlot`，`resource_id + start_time` 唯一。预约用 `UPDATE ... WHERE status=Available` 原子领取；同一 Lead 同一时段返回原预约，不同 Lead 同抢时只有一个更新成功，其余返回 409。测试覆盖该行为。

## Google Calendar 失败会不会产生脏状态？

先原子 Held，再创建 Google Event。创建失败回滚事务、释放 Slot、记录分类失败，Lead 不进入 Meeting；两者都成功后才写 Appointment、Booked 和 Meeting。取消外部事件失败时保留本地 Confirmed，避免内外状态假一致。

## Follow-up 如何避免重复发送？

任务有业务幂等键、状态机、条件领取与 lease。只有人工审批后的 Scheduled 可执行；崩溃后回收过期 lease；Meeting、Closed 或人工接管会取消/跳过任务。Resend 只允许白名单收件人。

## 为什么用 SQLite 和进程内调度器？

面试 Demo 是单实例、低吞吐场景，SQLite Volume 提供最少外部依赖和可重复部署。并发正确性仍依靠数据库条件更新与唯一约束。生产多实例应迁移 PostgreSQL 和独立 Worker，这一点已明确写入边界。

## 安全如何落地？

生产缺少强密码、长 Session Secret 或真实 AI 配置时拒绝启动；管理写请求有 CSRF；Cookie、安全响应头、登录限流、请求上限、同源托管、邮件白名单和统一脱敏均有实现及测试。CI 使用 Gitleaks，公开前扫描完整 Git 历史。

## 你会如何衡量效果？

离线看事实准确率、重复提问、幻觉、动作、状态、转人工与预约建议；线上看模型成功率、修复率、P50/P95、Token、预约转化、Follow-up 成功率和人工接管率。当前固定 9 场景为可重复基线。
