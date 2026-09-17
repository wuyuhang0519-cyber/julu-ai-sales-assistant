import { useEffect, useState } from "react";
import { Routes, Route, Link, useNavigate, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowRight,
  Bot,
  Calendar,
  ChevronDown,
  LogIn,
  MessageSquare,
  ShieldCheck,
  Sparkles,
  Users,
  Mail,
  Activity,
  BrainCircuit,
  Plug,
} from "lucide-react";
const csrf = () =>
  document.cookie
    .split("; ")
    .find((x) => x.startsWith("julu_csrf="))
    ?.split("=")[1] || "";
const api = async (path: string, opts: RequestInit = {}) => {
  const method = opts.method || "GET";
  const r = await fetch(path, {
    credentials: "include",
    ...opts,
    headers: {
      "Content-Type": "application/json",
      ...(method !== "GET" ? { "X-CSRF-Token": csrf() } : {}),
      ...(opts.headers || {}),
    },
  });
  if (!r.ok) {
    const e = await r.json().catch(() => ({ detail: { message: "请求失败" } }));
    throw new Error(e.detail?.message || e.error?.message || "请求失败");
  }
  return r.json();
};
const Badge = ({ v }: { v: string }) => (
  <span className={`pill ${v}`}>{v}</span>
);
function Layout({ children }: { children: any }) {
  return (
    <>
      <header className="nav">
        <div className="shell w-full flex justify-between items-center">
          <Link to="/" className="flex items-center gap-3 text-white">
            <span className="bg-brand rounded-xl p-2 font-black">JL</span>
            <span>
              <b>聚路 AI</b>
              <small className="block text-xs text-blue-200">
                JULU AI SALES COPILOT
              </small>
            </span>
          </Link>
          <nav className="flex gap-5 text-sm">
            <Link to="/">官网</Link>
            <Link to="/admin">管理后台</Link>
          </nav>
        </div>
      </header>
      {children}
    </>
  );
}
function Landing() {
  const nav = useNavigate();
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [demoMode, setDemoMode] = useState<boolean | null>(null);
  useEffect(() => {
    api("/api/health")
      .then((x) => setDemoMode(x.demo_mode))
      .catch(() => undefined);
  }, []);
  const [form, setForm] = useState({
    name: "",
    company: "",
    email: "",
    industry: "B2B 制造",
    country: "中国",
    interested_service: "全球 AI 搜索优化",
    website: "",
    initial_requirement: "",
  });
  const submit = async (e: any) => {
    e.preventDefault();
    setBusy(true);
    setErr("");
    try {
      const d = await api("/api/public/leads", {
        method: "POST",
        headers: { "Idempotency-Key": crypto.randomUUID() },
        body: JSON.stringify(form),
      });
      nav("/chat/" + d.lead.public_token);
    } catch (x: any) {
      setErr(x.message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <Layout>
      <main>
        <section className="bg-[#071a35] text-white py-16">
          <div className="shell grid2 items-center">
            <div>
              <span className="pill bg-blue-500/20 text-blue-200 mb-5">
                <Sparkles size={14} /> {demoMode === false ? "真实 OpenAI 模式" : "离线 Demo 模式"} · 可审计 AI 决策
              </span>
              <h1 className="text-4xl md:text-5xl font-black leading-tight mb-5">
                让每一条官网客资，
                <br />
                <span className="text-blue-400">都有下一步。</span>
              </h1>
              <p className="text-lg text-blue-100 leading-8 max-w-xl">
                AI
                自动接待、动态挖掘需求、评估意向并推进预约。销售团队随时查看判断依据，也可以一键人工接管。
              </p>
              <div className="grid grid-cols-2 gap-3 mt-8 text-sm text-blue-100">
                <span>✓ 结构化线索评分</span>
                <span>✓ 多轮对话记忆</span>
                <span>✓ 动态下一步动作</span>
                <span>✓ 人工优先控制</span>
              </div>
            </div>
            <form onSubmit={submit} className="card p-6 text-ink">
              <h2 className="text-xl font-black mb-1">获取 AI 增长诊断</h2>
              <p className="text-sm text-slate-500 mb-5">
                提交后立即与销售助手沟通
              </p>
              <div className="grid grid-cols-2 gap-3">
                <Field
                  label="姓名*"
                  value={form.name}
                  onChange={(v) => setForm({ ...form, name: v })}
                />
                <Field
                  label="公司*"
                  value={form.company}
                  onChange={(v) => setForm({ ...form, company: v })}
                />
                <Field
                  label="邮箱*"
                  type="email"
                  value={form.email}
                  onChange={(v) => setForm({ ...form, email: v })}
                />
                <Field
                  label="行业*"
                  value={form.industry}
                  onChange={(v) => setForm({ ...form, industry: v })}
                />
                <Field
                  label="国家/地区*"
                  value={form.country}
                  onChange={(v) => setForm({ ...form, country: v })}
                />
                <label>
                  <span className="label">感兴趣服务*</span>
                  <select
                    className="input"
                    value={form.interested_service}
                    onChange={(e) =>
                      setForm({ ...form, interested_service: e.target.value })
                    }
                  >
                    <option>全球 AI 搜索优化</option>
                    <option>国内 AI 搜索优化</option>
                    <option>GEO 官网及落地页建设</option>
                    <option>AI 可见度与排名监测</option>
                    <option>企业 AI 智能体定制</option>
                  </select>
                </label>
              </div>
              <Field
                label="公司官网（可选）"
                value={form.website}
                onChange={(v) => setForm({ ...form, website: v })}
              />
              <label className="block mt-3">
                <span className="label">初步需求（可选）</span>
                <textarea
                  className="input"
                  rows={3}
                  value={form.initial_requirement}
                  onChange={(e) =>
                    setForm({ ...form, initial_requirement: e.target.value })
                  }
                  placeholder="例如：希望三个月内提升 ChatGPT 和 Google AI 可见度"
                />
              </label>
              {err && (
                <p role="alert" className="text-red-600 text-sm mt-2">
                  {err}
                </p>
              )}
              <button disabled={busy} className="btn btn-primary w-full mt-4">
                {busy ? "正在建立专属会话…" : "开始 AI 诊断"}
                <ArrowRight size={17} />
              </button>
            </form>
          </div>
        </section>
        <section className="shell py-14">
          <h2 className="text-2xl font-black text-center mb-8">
            从曝光到成交的 AI 增长能力
          </h2>
          <div className="grid md:grid-cols-5 gap-4">
            {[
              "全球 AI 搜索优化",
              "国内 AI 搜索优化",
              "GEO 官网及落地页",
              "AI 可见度监测",
              "企业智能体定制",
            ].map((x, i) => (
              <div className="card p-5" key={x}>
                <Bot className="text-brand mb-4" />
                <b>{x}</b>
                <p className="text-sm text-slate-500 mt-2">
                  围绕内容、技术与分发构建可持续增长。
                </p>
              </div>
            ))}
          </div>
        </section>
      </main>
    </Layout>
  );
}
function Field({ label, value, onChange, type = "text" }: any) {
  return (
    <label className="block mt-3">
      <span className="label">{label}</span>
      <input
        required={label.includes("*")}
        type={type}
        className="input"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </label>
  );
}
function Chat() {
  const { token } = useParams();
  const [lead, setLead] = useState<any>();
  const [msgs, setMsgs] = useState<any[]>([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [profile, setProfile] = useState<any>({});
  const [show, setShow] = useState(true);
  const [slots, setSlots] = useState<any[]>([]);
  const [booked, setBooked] = useState(false);
  const [demoMode, setDemoMode] = useState(true);
  const load = async () => {
    const [l, m] = await Promise.all([
      api("/api/public/leads/" + token),
      api("/api/public/leads/" + token + "/messages"),
    ]);
    setLead(l.lead);
    setProfile(l.profile);
    setMsgs(m);
    setDemoMode(l.demo_mode);
  };
  useEffect(() => {
    load();
  }, []);
  const send = async (e: any) => {
    e.preventDefault();
    if (!text.trim()) return;
    const value = text;
    setText("");
    setMsgs((x) => [...x, { id: "temp", role: "user", content: value }]);
    setBusy(true);
    try {
      const d = await api(`/api/public/leads/${token}/messages`, {
        method: "POST",
        body: JSON.stringify({
          content: value,
          client_message_id: crypto.randomUUID(),
        }),
      });
      setMsgs((x) => [
        ...x.filter((y) => y.id !== "temp"),
        d.user_message,
        d.assistant_message,
      ]);
      setLead(d.lead);
      const l = await api("/api/public/leads/" + token);
      setProfile(l.profile);
    } finally {
      setBusy(false);
    }
  };
  const getSlots = async () =>
    setSlots(await api("/api/public/availability?timezone_name=Asia/Shanghai"));
  const book = async (s: any) => {
    try {
      await api(`/api/public/leads/${token}/appointments`, {
        method: "POST",
        body: JSON.stringify({
          start_time: s.start_time,
          timezone: "Asia/Shanghai",
          attendee_name: lead.name,
          attendee_email: lead.email,
        }),
      });
      setBooked(true);
      load();
    } catch (e: any) {
      alert(e.message);
    }
  };
  if (!lead)
    return (
      <Layout>
        <p className="shell py-20">正在加载会话…</p>
      </Layout>
    );
  return (
    <Layout>
      <main className="shell py-7">
        <div className="flex flex-wrap justify-between gap-4 items-end mb-5">
          <div>
            <p className="text-sm text-slate-500">客户会话 · {lead.company}</p>
            <h1 className="text-2xl font-black">你好，{lead.name}</h1>
          </div>
          <div className="flex gap-2">
            <Badge v={lead.intent} />
            <span className="pill bg-blue-100 text-blue-800">
              评分 {lead.lead_score}
            </span>
            <span className={`pill ${demoMode ? "bg-amber-100 text-amber-800" : "bg-green-100 text-green-800"}`}>
              {demoMode ? "离线 Demo 模式" : "真实 OpenAI 模式"}
            </span>
          </div>
        </div>
        <div className="grid2">
          <section className="card p-5">
            <div className="chat" aria-live="polite">
              {msgs.map((m, i) => (
                <div className={`bubble ${m.role}`} key={m.id || i}>
                  {m.content}
                  {m.error_code && (
                    <small className="block mt-2 text-red-600">
                      系统已安全降级
                    </small>
                  )}
                </div>
              ))}
              {busy && (
                <div className="bubble assistant text-slate-500">
                  AI 正在分析客户背景与对话记忆…
                </div>
              )}
            </div>
            <form className="flex gap-2 mt-3" onSubmit={send}>
              <input
                className="input"
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder="回答问题，或询问聚路 AI 的服务范围"
              />
              <button className="btn btn-primary" disabled={busy}>
                <MessageSquare size={17} />
                发送
              </button>
            </form>
            <p className="text-xs text-slate-500 mt-3">
              AI 仅回答服务知识范围内问题；价格、合同或承诺将转人工。
            </p>
          </section>
          <aside className="space-y-4">
            <section className="card p-5">
              <button
                className="w-full flex justify-between font-bold"
                onClick={() => setShow(!show)}
              >
                已识别需求摘要 <ChevronDown size={18} />
              </button>
              {show && (
                <div className="mt-4 text-sm space-y-2">
                  {Object.entries(profile)
                    .filter(
                      ([k, v]) =>
                        v && k !== "missing_fields" && k !== "additional_facts",
                    )
                    .map(([k, v]) => (
                      <p key={k}>
                        <b>{k.replaceAll("_", " ")}：</b>
                        {String(v)}
                      </p>
                    ))}
                  <p className="text-slate-500">
                    待补充：
                    {profile.missing_fields?.slice(0, 4).join("、") ||
                      "核心信息已较完整"}
                  </p>
                </div>
              )}
            </section>
            <section className="card p-5">
              <h3 className="font-black mb-2">AI 当前判断</h3>
              <p className="text-sm leading-6">{lead.score_reason}</p>
              <p className="mt-3">
                <b>推荐：</b>
                {lead.recommended_service || "继续诊断"}
              </p>
              <p>
                <b>下一步：</b>
                {lead.next_action}
              </p>
            </section>
            <section className="card p-5">
              <h3 className="font-black">预约 45 分钟需求诊断</h3>
              {booked ? (
                <p className="text-green-700 mt-3 font-bold">
                  ✓ 预约已确认，销售状态已更新为 Meeting
                </p>
              ) : (
                <>
                  <button
                    className="btn btn-secondary w-full mt-3"
                    onClick={getSlots}
                  >
                    <Calendar size={17} />
                    查看可预约时间
                  </button>
                  <div className="space-y-2 mt-3">
                    {slots.slice(0, 4).map((s) => (
                      <button
                        onClick={() => book(s)}
                        className="w-full border rounded-lg p-2 text-sm hover:border-brand"
                        key={s.start_time}
                      >
                        {new Date(s.start_time).toLocaleString("zh-CN")}
                      </button>
                    ))}
                  </div>
                </>
              )}
            </section>
          </aside>
        </div>
      </main>
    </Layout>
  );
}
function Admin() {
  const nav = useNavigate();
  const [auth, setAuth] = useState(false);
  const [dash, setDash] = useState<any>();
  const [leads, setLeads] = useState<any[]>([]);
  const [creds, setCreds] = useState({ username: "", password: "" });
  const [err, setErr] = useState("");
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [intent, setIntent] = useState("");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const load = async (targetPage = page) => {
    try {
      const [d, l] = await Promise.all([
        api("/api/admin/dashboard"),
        api(
          `/api/admin/leads?search=${encodeURIComponent(search)}&status=${status}&intent=${intent}&page=${targetPage}&page_size=20`,
        ),
      ]);
      setDash(d);
      setLeads(l.items);
      setTotal(l.total);
      setPage(targetPage);
      setAuth(true);
    } catch {
      setAuth(false);
    }
  };
  useEffect(() => {
    load();
  }, []);
  const login = async (e: any) => {
    e.preventDefault();
    try {
      await api("/api/admin/login", {
        method: "POST",
        body: JSON.stringify(creds),
      });
      load();
    } catch (x: any) {
      setErr(x.message);
    }
  };
  if (!auth)
    return (
      <Layout>
        <main className="shell py-20 max-w-md">
          <form className="card p-7" onSubmit={login}>
            <LogIn className="text-brand mb-3" />
            <h1 className="text-2xl font-black">管理员登录</h1>
            <p className="text-sm text-slate-500 mb-4">
              测试账号从环境变量读取，页面不会保存密码
            </p>
            <Field
              label="用户名*"
              value={creds.username}
              onChange={(v: string) => setCreds({ ...creds, username: v })}
            />
            <Field
              label="密码*"
              type="password"
              value={creds.password}
              onChange={(v: string) => setCreds({ ...creds, password: v })}
            />
            {err && <p className="text-red-600 mt-2">{err}</p>}
            <button className="btn btn-primary w-full mt-4">登录</button>
          </form>
        </main>
      </Layout>
    );
  return (
    <Layout>
      <main className="shell py-7">
        <AdminNav />
        <div className="flex justify-between items-center mb-6">
          <div>
            <p className="text-sm text-slate-500">销售运营工作台</p>
            <h1 className="text-3xl font-black">客资与 AI 决策</h1>
          </div>
          <span className="pill bg-blue-100 text-blue-800">
            AI 成功率 {dash?.ai_success_rate || 0}%
          </span>
        </div>
        <div className="stats">
          {[
            ["线索总数", dash?.total, Users],
            ["New", dash?.counts?.New, Sparkles],
            ["Qualified", dash?.counts?.Qualified, ShieldCheck],
            ["Meeting", dash?.counts?.Meeting, Calendar],
            ["高意向", dash?.high_intent, Bot],
          ].map(([t, n, I]: any) => (
            <div className="card p-5" key={t}>
              <I className="text-brand" size={22} />
              <p className="text-sm text-slate-500 mt-3">{t}</p>
              <b className="text-3xl">{n || 0}</b>
            </div>
          ))}
        </div>
        <section className="card mt-6 p-5">
          <div className="flex flex-wrap gap-2 mb-4">
            <h2 className="text-xl font-black mr-auto">线索列表</h2>
            <input
              className="input max-w-xs"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="搜索姓名、公司或邮箱"
            />
            <select
              className="input max-w-40"
              value={status}
              onChange={(e) => setStatus(e.target.value)}
            >
              <option value="">全部状态</option>
              {[
                "New",
                "Contacted",
                "Qualified",
                "Meeting",
                "Nurture",
                "Closed",
              ].map((x) => (
                <option key={x}>{x}</option>
              ))}
            </select>
            <select
              className="input max-w-40"
              value={intent}
              onChange={(e) => setIntent(e.target.value)}
            >
              <option value="">全部意向</option>
              {["High", "Medium", "Low"].map((x) => (
                <option key={x}>{x}</option>
              ))}
            </select>
            <button className="btn btn-secondary" onClick={() => load(1)}>
              筛选
            </button>
          </div>
          <div className="tablewrap">
            <table>
              <thead>
                <tr>
                  <th>客户</th>
                  <th>状态</th>
                  <th>评分</th>
                  <th>意向</th>
                  <th>推荐服务</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {leads.map((l) => (
                  <tr key={l.id}>
                    <td>
                      <b>{l.name}</b>
                      <small className="block text-slate-500">
                        {l.company}
                      </small>
                    </td>
                    <td>{l.status}</td>
                    <td>{l.lead_score}</td>
                    <td>
                      <Badge v={l.intent} />
                    </td>
                    <td>{l.recommended_service || "待判断"}</td>
                    <td>
                      <button
                        className="text-brand font-bold"
                        onClick={() => nav("/admin/leads/" + l.id)}
                      >
                        查看详情
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!leads.length && (
              <p className="text-center text-slate-500 py-8">
                没有符合条件的线索
              </p>
            )}
            {total > 0 && (
              <div className="flex items-center justify-end gap-3 pt-4 text-sm">
                <span>
                  第 {page} / {Math.max(1, Math.ceil(total / 20))} 页，共 {total} 条
                </span>
                <button className="btn btn-secondary" disabled={page <= 1} onClick={() => load(page - 1)}>上一页</button>
                <button className="btn btn-secondary" disabled={page * 20 >= total} onClick={() => load(page + 1)}>下一页</button>
              </div>
            )}
          </div>
        </section>
      </main>
    </Layout>
  );
}

function AdminNav() {
  return (
    <nav className="flex flex-wrap gap-2 mb-6 text-sm">
      <Link className="btn btn-secondary" to="/admin">
        线索
      </Link>
      <Link className="btn btn-secondary" to="/admin/appointments">
        预约
      </Link>
      <Link className="btn btn-secondary" to="/admin/followups">
        Follow-up
      </Link>
      <Link className="btn btn-secondary" to="/admin/ai">
        AI 监控
      </Link>
      <Link className="btn btn-secondary" to="/admin/logs">
        日志
      </Link>
      <Link className="btn btn-secondary" to="/admin/integrations">
        集成
      </Link>
    </nav>
  );
}

function DateCell({ value }: { value: any }) {
  return (
    <span className="whitespace-nowrap">
      {value ? new Date(value).toLocaleString("zh-CN") : "—"}
    </span>
  );
}
function AdminData({ kind, title, icon: Icon }: any) {
  const endpoints: any = {
    appointments: "/api/admin/appointments",
    followups: "/api/admin/follow-ups",
    ai: "/api/admin/ai-invocations",
    logs: "/api/admin/activity-logs",
    integrations: "/api/admin/integrations/status",
  };
  const q = useQuery({
    queryKey: ["admin", kind],
    queryFn: () => api(endpoints[kind]),
    retry: false,
  });
  const metrics = useQuery({
    queryKey: ["admin", "ai-metrics"],
    queryFn: () => api("/api/admin/ai-metrics"),
    enabled: kind === "ai",
    retry: false,
  });
  const data: any = q.data;
  const act = async (path: string, method = "POST", body?: any) => {
    await api(path, { method, body: body ? JSON.stringify(body) : undefined });
    await q.refetch();
  };
  if (q.isError)
    return (
      <Layout>
        <main className="shell py-12">
          <p className="card p-6">请先在管理后台登录。</p>
        </main>
      </Layout>
    );
  let content: any = null;
  if (kind === "integrations" && data)
    content = (
      <div className="grid md:grid-cols-3 gap-4 mt-5">
        {Object.entries(data).map(([name, value]: any) => (
          <section className="card p-5" key={name}>
            <h2 className="font-black text-lg">{name}</h2>
            <p
              className={`pill mt-3 ${value.configured ? "bg-green-100 text-green-800" : "bg-amber-100 text-amber-800"}`}
            >
              {value.configured ? "已配置" : "未配置"}
            </p>
            <p className="text-sm mt-4 text-slate-600">
              模式：{value.mode || value.provider || "—"}
            </p>
            <p className="text-sm text-slate-600">
              最后成功：
              {value.last_success
                ? new Date(value.last_success).toLocaleString("zh-CN")
                : "尚无记录"}
            </p>
            {value.allowlist_count !== undefined && (
              <p className="text-sm text-slate-600">
                测试白名单：{value.allowlist_count} 个
              </p>
            )}
          </section>
        ))}
      </div>
    );
  else if (data)
    content = (
      <section className="card p-5 mt-5 tablewrap">
        <table>
          <thead>
            <tr>
              {kind === "appointments" ? (
                <>
                  <th>ID / Lead</th>
                  <th>预约时间</th>
                  <th>本地状态</th>
                  <th>外部同步</th>
                  <th>操作</th>
                </>
              ) : kind === "followups" ? (
                <>
                  <th>ID / Lead</th>
                  <th>主题</th>
                  <th>执行时间</th>
                  <th>状态 / 尝试</th>
                  <th>操作</th>
                </>
              ) : kind === "ai" ? (
                <>
                  <th>时间</th>
                  <th>Lead</th>
                  <th>模型 / Prompt</th>
                  <th>校验</th>
                  <th>耗时 / Token</th>
                  <th>错误</th>
                </>
              ) : (
                <>
                  <th>时间</th>
                  <th>Lead</th>
                  <th>事件</th>
                  <th>内容</th>
                </>
              )}
            </tr>
          </thead>
          <tbody>
            {data.map((x: any) =>
              kind === "appointments" ? (
                <tr key={x.id}>
                  <td>
                    #{x.id}
                    <small className="block">Lead #{x.lead_id}</small>
                  </td>
                  <td>
                    <DateCell value={x.start_time} />
                  </td>
                  <td>
                    <Badge v={x.status} />
                  </td>
                  <td>
                    {x.external_provider} / {x.sync_status}
                    {x.failure_reason && (
                      <small className="block text-red-600">
                        {x.failure_reason}
                      </small>
                    )}
                  </td>
                  <td>
                    {x.status !== "Cancelled" && (
                      <button
                        className="text-red-700 font-bold"
                        onClick={() =>
                          act(`/api/admin/appointments/${x.id}`, "PATCH", {
                            status: "Cancelled",
                          })
                        }
                      >
                        取消预约
                      </button>
                    )}
                  </td>
                </tr>
              ) : kind === "followups" ? (
                <tr key={x.id}>
                  <td>
                    #{x.id}
                    <small className="block">Lead #{x.lead_id}</small>
                  </td>
                  <td>{x.subject}</td>
                  <td>
                    <DateCell value={x.scheduled_at} />
                  </td>
                  <td>
                    <Badge v={x.status} />
                    <small className="block mt-1">
                      {x.attempts}/{x.max_attempts}
                    </small>
                    {x.failure_reason && (
                      <small className="block text-red-600">
                        {x.failure_reason}
                      </small>
                    )}
                  </td>
                  <td className="space-x-3">
                    {["PendingApproval", "Failed"].includes(x.status) && (
                      <button
                        className="text-brand font-bold"
                        onClick={() =>
                          act(
                            `/api/admin/follow-ups/${x.id}/approve`,
                            "POST",
                            {},
                          )
                        }
                      >
                        审批
                      </button>
                    )}
                    {x.status === "Failed" && (
                      <button
                        className="text-brand font-bold"
                        onClick={() =>
                          act(`/api/admin/follow-ups/${x.id}/retry`)
                        }
                      >
                        重试
                      </button>
                    )}
                    {!["Sent", "Cancelled", "Skipped"].includes(x.status) && (
                      <button
                        className="text-red-700 font-bold"
                        onClick={() =>
                          act(`/api/admin/follow-ups/${x.id}/cancel`)
                        }
                      >
                        取消
                      </button>
                    )}
                  </td>
                </tr>
              ) : kind === "ai" ? (
                <tr key={x.id}>
                  <td>
                    <DateCell value={x.created_at} />
                  </td>
                  <td>#{x.lead_id || "—"}</td>
                  <td>
                    {x.model_name}
                    <small className="block">{x.prompt_version}</small>
                  </td>
                  <td>
                    <Badge v={x.validation_status} />
                    <small className="block">修复 {x.repair_attempts} 次</small>
                  </td>
                  <td>
                    {x.latency_ms ?? "—"} ms
                    <small className="block">
                      {(x.input_tokens || 0) + (x.output_tokens || 0)} tokens
                    </small>
                  </td>
                  <td className="text-red-700">{x.error_type || "—"}</td>
                </tr>
              ) : (
                <tr key={x.id}>
                  <td>
                    <DateCell value={x.created_at} />
                  </td>
                  <td>#{x.lead_id || "—"}</td>
                  <td>{x.event_type}</td>
                  <td>{x.message}</td>
                </tr>
              ),
            )}
          </tbody>
        </table>
        {!data.length && (
          <p className="text-center text-slate-500 py-10">暂无数据</p>
        )}
      </section>
    );
  return (
    <Layout>
      <main className="shell py-7">
        <AdminNav />
        <h1 className="text-3xl font-black flex gap-3 items-center">
          <Icon className="text-brand" />
          {title}
        </h1>
        {kind === "ai" && metrics.data && (
          <div className="stats mt-5">
            {[
              ["调用总数", metrics.data.total],
              ["成功率", `${metrics.data.success_rate}%`],
              ["P50 延迟", `${metrics.data.p50_latency_ms ?? "—"} ms`],
              ["P95 延迟", `${metrics.data.p95_latency_ms ?? "—"} ms`],
              ["修复 / 失败", `${metrics.data.repaired} / ${metrics.data.failed}`],
            ].map(([label, value]) => (
              <section className="card p-4" key={label}>
                <p className="text-sm text-slate-500">{label}</p>
                <b className="text-2xl">{value}</b>
              </section>
            ))}
          </div>
        )}
        {q.isLoading ? <p className="py-10">正在加载…</p> : content}
      </main>
    </Layout>
  );
}
function LeadDetail() {
  const { id } = useParams();
  const [d, setD] = useState<any>();
  useEffect(() => {
    api("/api/admin/leads/" + id).then(setD);
  }, []);
  if (!d)
    return (
      <Layout>
        <p className="shell py-20">加载中…</p>
      </Layout>
    );
  const l = d.lead;
  const mutate = async (path: string, method = "POST", body?: any) => {
    await api(path, { method, body: body ? JSON.stringify(body) : undefined });
    location.reload();
  };
  return (
    <Layout>
      <main className="shell py-7">
        <AdminNav />
        <Link className="text-brand" to="/admin">
          ← 返回线索
        </Link>
        <div className="flex flex-wrap justify-between gap-3 mt-4 mb-6">
          <div>
            <h1 className="text-3xl font-black">
              {l.name} · {l.company}
            </h1>
            <p className="text-slate-500">
              {l.email} · {l.industry} · {l.country}
            </p>
          </div>
          <div>
            <Badge v={l.intent} />{" "}
            <span className="pill bg-blue-100 text-blue-800">
              {l.status} · {l.lead_score} 分
            </span>
          </div>
        </div>
        <div className="grid2">
          <div className="space-y-4">
            <section className="card p-5">
              <h2 className="font-black text-lg">AI 判断与证据</h2>
              <p className="mt-2 leading-7">{l.score_reason}</p>
              <p className="mt-3">
                <b>推荐服务：</b>
                {l.recommended_service || "待判断"}
              </p>
              <p>
                <b>下一步动作：</b>
                {l.next_action}
              </p>
              <p>
                <b>会话摘要：</b>
                {l.conversation_summary}
              </p>
              {d.decisions.map((x: any) => (
                <div className="border-t mt-4 pt-3 text-sm" key={x.id}>
                  <b>五维评分 #{x.id}</b>
                  <pre className="whitespace-pre-wrap mt-2">
                    {JSON.stringify(x.score_breakdown, null, 2)}
                  </pre>
                  <p>知识引用：{(x.knowledge_refs || []).join("、") || "—"}</p>
                  <p>提问原因：{x.question_reason || "—"}</p>
                </div>
              ))}
            </section>
            <section className="card p-5">
              <h2 className="font-black text-lg mb-3">完整对话</h2>
              {d.messages.map((m: any) => (
                <div className={`bubble ${m.role}`} key={m.id}>
                  {m.content}
                </div>
              ))}
            </section>
            <section className="card p-5">
              <h2 className="font-black text-lg mb-3">AI 调用</h2>
              {d.invocations.map((x: any) => (
                <p className="text-sm border-b py-2" key={x.id}>
                  <b>{x.model_name}</b> · {x.prompt_version} ·{" "}
                  {x.validation_status} · {x.latency_ms ?? "—"} ms
                  <br />
                  <span className="text-slate-500">
                    请求 {x.request_id} · 修复 {x.repair_attempts} 次 · 错误{" "}
                    {x.error_type || "无"}
                  </span>
                </p>
              ))}
            </section>
          </div>
          <aside className="space-y-4">
            <section className="card p-5">
              <h2 className="font-black">需求信息</h2>
              {Object.entries(d.profile).map(
                ([k, v]) =>
                  v && (
                    <p className="text-sm mt-2" key={k}>
                      <b>{k}：</b>
                      {JSON.stringify(v)}
                    </p>
                  ),
              )}
            </section>
            <section className="card p-5">
              <h2 className="font-black">人工控制</h2>
              <p className="text-sm text-slate-500 mt-2">
                人工接管或手动状态始终优先于 AI 自动推进。
              </p>
              <div className="flex flex-wrap gap-2 mt-3">
                <button
                  className="btn btn-secondary"
                  onClick={() =>
                    mutate(`/api/admin/leads/${id}/takeover`, "POST", {
                      reason: "后台人工接管",
                    })
                  }
                >
                  人工接管
                </button>
                <button
                  className="btn btn-secondary"
                  onClick={() => mutate(`/api/admin/leads/${id}/release`)}
                >
                  释放接管
                </button>
                <select
                  className="input"
                  value={l.status}
                  onChange={(e) =>
                    mutate(`/api/admin/leads/${id}`, "PATCH", {
                      status: e.target.value,
                    })
                  }
                >
                  {[
                    "New",
                    "Contacted",
                    "Qualified",
                    "Meeting",
                    "Nurture",
                    "Closed",
                  ].map((x) => (
                    <option key={x}>{x}</option>
                  ))}
                </select>
              </div>
            </section>
            <section className="card p-5">
              <h2 className="font-black">状态历史</h2>
              {d.status_history.map((x: any) => (
                <p className="text-sm border-b py-2" key={x.id}>
                  <b>
                    {x.from_status || "开始"} → {x.to_status}
                  </b>
                  <br />
                  {x.actor} · {x.reason}
                </p>
              ))}
            </section>
            <section className="card p-5">
              <h2 className="font-black">Follow-up</h2>
              {d.followups.map((x: any) => (
                <p className="text-sm border-b py-2" key={x.id}>
                  <b>{x.status}</b> · <DateCell value={x.scheduled_at} />
                  <br />
                  {x.subject}
                </p>
              ))}
              {!d.followups.length && (
                <p className="text-sm text-slate-500 mt-2">暂无任务</p>
              )}
            </section>
            <section className="card p-5">
              <h2 className="font-black">统一时间线</h2>
              {d.logs.map((x: any) => (
                <p className="text-sm border-b py-2" key={x.id}>
                  <b>{x.event_type}</b>
                  <br />
                  {x.message}
                  <br />
                  <span className="text-slate-400">
                    <DateCell value={x.created_at} />
                  </span>
                </p>
              ))}
            </section>
          </aside>
        </div>
      </main>
    </Layout>
  );
}
export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/chat/:token" element={<Chat />} />
      <Route path="/admin" element={<Admin />} />
      <Route path="/admin/leads/:id" element={<LeadDetail />} />
      <Route
        path="/admin/appointments"
        element={
          <AdminData kind="appointments" title="预约管理" icon={Calendar} />
        }
      />
      <Route
        path="/admin/followups"
        element={
          <AdminData kind="followups" title="Follow-up 任务" icon={Mail} />
        }
      />
      <Route
        path="/admin/ai"
        element={
          <AdminData kind="ai" title="AI 调用监控" icon={BrainCircuit} />
        }
      />
      <Route
        path="/admin/logs"
        element={<AdminData kind="logs" title="活动日志" icon={Activity} />}
      />
      <Route
        path="/admin/integrations"
        element={
          <AdminData kind="integrations" title="外部服务状态" icon={Plug} />
        }
      />
    </Routes>
  );
}
