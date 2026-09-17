# AI Prompt、Schema 与证据链

当前 Prompt 版本：`sales-qualification-v2.0.0`。

## 输入

- Lead：姓名、公司、行业、地区、官网、关注服务、初始需求。
- Profile：十个资格字段及已识别事实。
- 最近 12 条消息：每条包含数据库消息 ID、角色和正文。
- 知识库：`backend/app/knowledge/company.md`，引用 ID 为 `KB-COMPANY-001`、`KB-ROUTING-001`。

系统约束模型不得虚构价格、客户案例、合同、排名和效果保证；每轮最多问两个问题，不重复已知信息；首次接待必须个性化。

## 结构化输出

`AIResult` 包含回复、提取事实、Profile 更新、缺失字段、总分、Intent、五维分项、证据、推荐服务、下一动作、建议状态、预约/转人工标志、摘要、问题原因、知识引用与事实来源消息 ID。

五维上限固定：业务匹配度 25、痛点明确度 25、时间紧迫度 20、预算可行性 15、决策影响力 15。服务端强制总分等于分项和，并按 `<40 Low / 40–69 Medium / >=70 High` 校正 Intent。

## 校验与失败策略

1. Responses API 使用严格 JSON Schema。
2. Pydantic 校验枚举、字段、分数范围、分项上限和总分。
3. 首次失败将原输出截断后交给模型进行一次仅 JSON 的结构修复。
4. 再失败则写入 `AIInvocation(Failed)`，返回安全提示，不修改 Profile、评分或 Lead 状态。
5. 原始模型响应默认不保存；后台只展示白名单摘要、Token、耗时、请求 ID、错误类型和修复次数。

## Demo Provider 边界

Demo Provider 是确定性 Contract Provider，只用于 CI、离线演示和断网备用。它使用结构化场景和证据约束，不代表真实模型推理。面试主演示必须在后台集成页确认 OpenAI 已配置且模式为 `real`。
