# 架构、数据模型与时序

## 组件架构

```mermaid
flowchart TB
  subgraph Browser
    Public[官网 / 对话 / 预约]
    Admin[运营后台]
  end
  subgraph FastAPI
    Auth[Session + CSRF + 限流]
    Workflow[销售工作流与状态优先级]
    Validate[Pydantic / JSON Schema / 修复]
    Scheduler[轮询调度器 / 租约]
    Redactor[统一脱敏]
  end
  Public --> Workflow
  Admin --> Auth --> Workflow
  Workflow --> Validate --> AI[DeepSeek Chat / OpenAI Responses]
  Workflow --> Calendar[Google Calendar]
  Scheduler --> Resend[Resend API]
  Workflow --> SQLite[(SQLite Volume)]
  Scheduler --> SQLite
  Workflow --> Redactor --> SQLite
  Validate --> KB[版本化 Markdown 知识库]
```

## ERD

```mermaid
erDiagram
  LEAD ||--|| LEAD_PROFILE : owns
  LEAD ||--o{ MESSAGE : contains
  LEAD ||--o{ AI_INVOCATION : invokes
  AI_INVOCATION ||--o| AI_DECISION : validates_to
  LEAD ||--o{ LEAD_STATUS_HISTORY : transitions
  LEAD ||--o{ APPOINTMENT : books
  AVAILABILITY_SLOT ||--o| APPOINTMENT : reserved_by
  LEAD ||--o{ FOLLOW_UP_TASK : schedules
  FOLLOW_UP_TASK ||--o{ EMAIL_DELIVERY : delivers
  LEAD ||--o{ ACTIVITY_LOG : audits
  LEAD ||--o{ INTEGRATION_EVENT : triggers
```

## AI 工作流

```mermaid
flowchart LR
  Input[客户输入 + Profile + 最近消息] --> Prompt[版本化 Prompt + 知识库]
  Prompt --> Model[DeepSeek JSON 模式 / OpenAI 严格 JSON Schema]
  Model --> Check{Pydantic 校验}
  Check -->|通过| Guard[证据 / 分数 / Intent / 人工优先]
  Check -->|失败| Repair[一次结构化修复]
  Repair --> Check2{再次校验}
  Check2 -->|通过| Guard
  Check2 -->|失败| Fallback[安全降级，不改 Profile / 分数 / 状态]
  Guard --> Persist[Decision + Invocation + StatusHistory + Log]
```

状态优先级为 `Closed > manual_status > human_takeover > AI suggestion`。模型只提出建议，应用代码拥有状态写权限。

## 预约时序

```mermaid
sequenceDiagram
  participant U as 客户
  participant A as FastAPI
  participant D as SQLite
  participant G as Google Calendar
  U->>A: 查询时段
  A->>G: FreeBusy
  A->>D: 读取 Available Slot
  U->>A: 预约指定时间
  A->>D: 条件 UPDATE Available -> Held
  alt 抢占失败
    A-->>U: 409 conflict
  else 抢占成功
    A->>G: 创建事件
    alt Google 失败
      A->>D: 回滚并记录失败
      A-->>U: 502，不进入 Meeting
    else Google 成功
      A->>D: Appointment + Booked + Meeting + 取消 Follow-up
      A-->>U: 已确认 + 外部事件链接
    end
  end
```

## Follow-up 调度

```mermaid
stateDiagram-v2
  [*] --> PendingApproval
  PendingApproval --> Scheduled: 管理员审批
  Scheduled --> Processing: 原子领取 + lease
  Processing --> Sent: Resend / DryRun 成功
  Processing --> Scheduled: 可重试失败
  Processing --> Failed: 不可重试或达到上限
  Processing --> Skipped: Meeting / Closed / 人工接管
  Processing --> Scheduled: lease 过期回收
  PendingApproval --> Cancelled
  Scheduled --> Cancelled
  Failed --> Scheduled: 人工重试
```

所有时间以 UTC 存储。客户端提交无偏移时间时，服务端按请求中的 IANA 时区解释；返回时间显式携带 UTC 偏移。
