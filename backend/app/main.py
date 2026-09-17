import asyncio,os,secrets
from contextlib import asynccontextmanager
from datetime import datetime,timedelta,timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from fastapi import FastAPI,Depends,HTTPException,Header,Request,Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse,JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select,func,or_,update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from itsdangerous import URLSafeTimedSerializer
from .config import settings
from .database import get_db
from .models import Lead,LeadProfile,Message,AIDecision,Appointment,ActivityLog,AvailabilitySlot,AIInvocation,LeadStatusHistory,FollowUpTask,EmailDelivery,IntegrationEvent
from .schemas import *
from .ai_service import run_ai,PROMPT_VERSION
from .security import redact,redact_text,csrf_token,require_csrf,login_limiter
from .integrations import calendar_service,email_service,IntegrationError
from .scheduler import scheduler_loop,create_followup,cancel_open_followups

settings.validate_runtime();serializer=URLSafeTimedSerializer(settings.session_secret,salt="admin")

@asynccontextmanager
async def lifespan(app:FastAPI):
    task=asyncio.create_task(scheduler_loop()) if settings.followup_scheduler_enabled else None
    yield
    if task:task.cancel()

app=FastAPI(title="JULU AI 销售助手",version="2.0.0",lifespan=lifespan)

@app.middleware("http")
async def security_headers(request:Request,call_next):
    if int(request.headers.get("content-length","0") or 0)>1_000_000:return JSONResponse(status_code=413,content={"error":{"code":"payload_too_large","message":"请求内容过大"}})
    response=await call_next(request);response.headers.update({"X-Content-Type-Options":"nosniff","X-Frame-Options":"DENY","Referrer-Policy":"strict-origin-when-cross-origin","Content-Security-Policy":"default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'; img-src 'self' data:; connect-src 'self'"})
    if settings.is_production:response.headers["Strict-Transport-Security"]="max-age=31536000; includeSubDomains"
    return response

@app.exception_handler(RequestValidationError)
async def validation_error(request,exc):return JSONResponse(status_code=422,content={"error":{"code":"validation_error","message":"请求字段校验失败","details":redact(exc.errors())}})
@app.exception_handler(IntegrityError)
async def integrity_error(request,exc):return JSONResponse(status_code=409,content={"error":{"code":"conflict","message":"记录已存在或资源冲突"}})

def log(db,lead_id,typ,message,meta=None):db.add(ActivityLog(lead_id=lead_id,event_type=typ,message=redact_text(message) or "",meta=redact(meta or {})))
def rows(items):return [{p.key:getattr(x,p.key) for p in x.__mapper__.column_attrs} for x in items]
def lead_by_token(db,token):
    lead=db.scalar(select(Lead).where(Lead.public_token==token))
    if not lead:raise HTTPException(404,detail={"code":"not_found","message":"线索不存在"})
    return lead
def get_or_404(db,model,pk):
    obj=db.get(model,pk)
    if not obj:raise HTTPException(404,detail={"code":"not_found","message":"记录不存在"})
    return obj
def admin(request:Request):
    token=request.cookies.get("julu_admin")
    try:
        if not token or serializer.loads(token,max_age=43200)!=settings.admin_username:raise ValueError()
    except Exception:raise HTTPException(401,detail={"code":"unauthorized","message":"请先登录"})
def profile_dict(p):return {k:getattr(p,k) for k in ["target_market","current_acquisition","current_seo_geo","target_platforms","target_result","pain_points","budget_range","timeline","decision_role","has_website","additional_facts","missing_fields"]}
def utc_aware(value:datetime):return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
def request_utc(value:datetime,timezone_name:str):
    try:zone=ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:raise HTTPException(422,detail={"code":"invalid_timezone","message":"请使用有效的 IANA 时区"})
    return (value if value.tzinfo else value.replace(tzinfo=zone)).astimezone(timezone.utc)
def transition(db,lead,to_status,actor,reason):
    if lead.status==to_status:return
    old=lead.status;lead.status=to_status;db.add(LeadStatusHistory(lead_id=lead.id,from_status=old,to_status=to_status,actor=actor,reason=reason));log(db,lead.id,"status_changed",f"状态从 {old} 更新为 {to_status}",{"actor":actor})

def apply_ai(db,lead,execution):
    inv=AIInvocation(lead_id=lead.id,request_id=execution.request_id,provider=execution.provider,model_name=execution.model,prompt_version=PROMPT_VERSION,input_message_ids=[m.id for m in lead.messages if m.id],knowledge_refs=execution.result.knowledge_refs if execution.result else [],validation_status=execution.validation_status,repair_attempts=execution.repair_attempts,latency_ms=execution.latency_ms,input_tokens=execution.input_tokens,output_tokens=execution.output_tokens,error_type=execution.error_type,response_summary=execution.response_summary or {})
    db.add(inv);db.flush()
    if execution.provider!="demo":db.add(IntegrationEvent(provider=execution.provider,operation="sales_reasoning",status="Success" if execution.result else "Failed",lead_id=lead.id,latency_ms=execution.latency_ms,error_type=execution.error_type,detail={"validation_status":execution.validation_status,"prompt_version":PROMPT_VERSION}))
    if not execution.result:return inv
    result=execution.result;p=lead.profile
    for k,v in result.updated_profile.items():
        if hasattr(p,k) and v not in (None,""):setattr(p,k,v)
        elif v not in (None,""):p.additional_facts={**(p.additional_facts or {}),k:v}
    p.missing_fields=result.missing_fields;old_intent=lead.intent;lead.lead_score=result.lead_score;lead.intent=result.intent;lead.score_reason=result.score_reason;lead.recommended_service=result.recommended_service;lead.next_action=result.next_action;lead.conversation_summary=result.conversation_summary;lead.last_contacted_at=datetime.now(timezone.utc)
    if old_intent!=result.intent:log(db,lead.id,"intent_changed",f"意向从 {old_intent} 更新为 {result.intent}")
    if not lead.human_takeover and not lead.manual_status and lead.status!="Closed" and result.suggested_status in {"Contacted","Qualified","Nurture","Closed"}:transition(db,lead,result.suggested_status,"AI",result.score_reason)
    db.add(AIDecision(lead_id=lead.id,invocation_id=inv.id,lead_score=result.lead_score,intent=result.intent,score_breakdown={k:v.model_dump() for k,v in result.score_breakdown.items()},score_reason=result.score_reason,recommended_service=result.recommended_service,next_action=result.next_action,suggested_status=result.suggested_status,should_offer_meeting=result.should_offer_meeting,should_handoff=result.should_handoff,handoff_reason=result.handoff_reason,raw_response_redacted="" if not settings.store_raw_ai_response else redact_text(result.model_dump_json()),knowledge_refs=result.knowledge_refs,question_reason=result.question_reason))
    if result.suggested_status=="Closed":cancel_open_followups(db,lead.id,"Lead closed")
    else:create_followup(db,lead)
    return inv

@app.get("/api/health")
def health():return {"status":"ok","demo_mode":settings.demo_mode,"version":"2.0.0","migrations":"alembic"}

@app.post("/api/public/leads",response_model=LeadCreated,status_code=201)
def create_lead(data:LeadCreate,db:Session=Depends(get_db),idempotency_key:str|None=Header(default=None,alias="Idempotency-Key")):
    if idempotency_key:
        old=db.scalar(select(Lead).where(Lead.idempotency_key==idempotency_key))
        if old:log(db,old.id,"duplicate_request","重复线索请求被幂等拦截");db.commit();return LeadCreated(lead=LeadOut.model_validate(old),first_message=MessageOut.model_validate(old.messages[0]),demo_mode=settings.demo_mode)
    lead=Lead(public_token=secrets.token_urlsafe(32),idempotency_key=idempotency_key,**data.model_dump());lead.profile=LeadProfile(has_website=bool(data.website),missing_fields=[]);db.add(lead);db.flush();db.add(LeadStatusHistory(lead_id=lead.id,from_status=None,to_status="New",actor="system",reason="官网表单创建"));log(db,lead.id,"lead_created","官网表单创建线索")
    execution=run_ai(lead,lead.profile,[],True);inv=apply_ai(db,lead,execution)
    if execution.result:msg=Message(lead_id=lead.id,role="assistant",content=execution.result.reply,model_name=execution.model,model_latency_ms=execution.latency_ms);log(db,lead.id,"ai_first_reply","AI 已生成首次接待",{"invocation_id":inv.id})
    else:msg=Message(lead_id=lead.id,role="assistant",content="抱歉，当前智能助手暂时无法完成判断。你的信息已安全保存，顾问可以继续跟进。",error_code=execution.error_type);log(db,lead.id,"ai_error","首次模型调用失败",{"error_type":execution.error_type})
    db.add(msg);db.commit();db.refresh(lead);db.refresh(msg);return LeadCreated(lead=LeadOut.model_validate(lead),first_message=MessageOut.model_validate(msg),demo_mode=settings.demo_mode)

@app.get("/api/public/leads/{token}")
def public_lead(token:str,db:Session=Depends(get_db)):
    l=lead_by_token(db,token);return {"lead":LeadOut.model_validate(l),"profile":profile_dict(l.profile),"demo_mode":settings.demo_mode}
@app.get("/api/public/leads/{token}/messages")
def messages(token:str,db:Session=Depends(get_db)):return [MessageOut.model_validate(x) for x in lead_by_token(db,token).messages]
@app.post("/api/public/leads/{token}/messages")
def send_message(token:str,data:MessageCreate,db:Session=Depends(get_db)):
    lead=lead_by_token(db,token);old=db.scalar(select(Message).where(Message.lead_id==lead.id,Message.client_message_id==data.client_message_id))
    if old:
        ai=db.scalar(select(Message).where(Message.lead_id==lead.id,Message.id>old.id,Message.role=="assistant").order_by(Message.id).limit(1));return {"user_message":MessageOut.model_validate(old),"assistant_message":MessageOut.model_validate(ai) if ai else None,"deduplicated":True,"lead":LeadOut.model_validate(lead)}
    user=Message(lead_id=lead.id,role="user",content=data.content,client_message_id=data.client_message_id);db.add(user);db.flush()
    if lead.human_takeover:ai=Message(lead_id=lead.id,role="assistant",content="当前会话已由人工顾问接管，我们会尽快回复。",model_name="handoff")
    else:
        execution=run_ai(lead,lead.profile,list(lead.messages)+[user],False);inv=apply_ai(db,lead,execution)
        if execution.result:ai=Message(lead_id=lead.id,role="assistant",content=execution.result.reply,model_name=execution.model,model_latency_ms=execution.latency_ms);log(db,lead.id,"ai_decision","AI 完成本轮判断",{"invocation_id":inv.id,"score":execution.result.lead_score,"action":execution.result.next_action})
        else:ai=Message(lead_id=lead.id,role="assistant",content="抱歉，智能判断暂时不可用。消息已经保存，请稍后重试或转人工顾问。",error_code=execution.error_type);log(db,lead.id,"ai_error","模型调用失败并安全降级",{"error_type":execution.error_type})
    db.add(ai);db.commit();db.refresh(user);db.refresh(ai);return {"user_message":MessageOut.model_validate(user),"assistant_message":MessageOut.model_validate(ai),"deduplicated":False,"lead":LeadOut.model_validate(lead)}

def ensure_slots(db):
    base=datetime.now(timezone.utc).replace(minute=0,second=0,microsecond=0)+timedelta(days=1)
    for d in range(7):
        for h in [2,6,8]:
            start=base+timedelta(days=d,hours=h)
            if not db.scalar(select(AvailabilitySlot).where(AvailabilitySlot.resource_id=="julu-sales",AvailabilitySlot.start_time==start)):db.add(AvailabilitySlot(resource_id="julu-sales",start_time=start,end_time=start+timedelta(minutes=45)))
    db.commit()
@app.get("/api/public/availability")
def availability(timezone_name:str="Asia/Shanghai",db:Session=Depends(get_db)):
    ensure_slots(db);items=list(db.scalars(select(AvailabilitySlot).where(AvailabilitySlot.status=="Available",AvailabilitySlot.start_time>datetime.now(timezone.utc)).order_by(AvailabilitySlot.start_time).limit(20)))
    if items and calendar_service.configured:
        try:
            busy=calendar_service.freebusy(utc_aware(items[0].start_time),utc_aware(items[-1].end_time))
            def overlaps(slot):
                return any(utc_aware(slot.start_time)<datetime.fromisoformat(x["end"].replace("Z","+00:00")) and utc_aware(slot.end_time)>datetime.fromisoformat(x["start"].replace("Z","+00:00")) for x in busy)
            items=[x for x in items if not overlaps(x)]
        except IntegrationError as e:
            db.add(IntegrationEvent(provider="google_calendar",operation="freebusy",status="Failed",error_type=e.code,detail={"retryable":e.retryable}));db.commit()
    return [{"id":s.id,"start_time":utc_aware(s.start_time),"end_time":utc_aware(s.end_time),"timezone":timezone_name} for s in items]
@app.post("/api/public/leads/{token}/appointments",status_code=201)
def book(token:str,data:AppointmentCreate,db:Session=Depends(get_db)):
    lead=lead_by_token(db,token);start=request_utc(data.start_time,data.timezone);old=db.scalar(select(Appointment).where(Appointment.lead_id==lead.id,Appointment.start_time==start))
    if old:return old
    slot=db.scalar(select(AvailabilitySlot).where(AvailabilitySlot.resource_id=="julu-sales",AvailabilitySlot.start_time==start))
    if not slot:slot=AvailabilitySlot(resource_id="julu-sales",start_time=start,end_time=start+timedelta(minutes=45));db.add(slot);db.flush()
    claimed=db.execute(update(AvailabilitySlot).where(AvailabilitySlot.id==slot.id,AvailabilitySlot.status=="Available").values(status="Held",held_by_lead_id=lead.id)).rowcount
    if not claimed:db.rollback();raise HTTPException(409,detail={"code":"slot_conflict","message":"该时间已被预约，请重新选择"})
    try:external=calendar_service.create(start,start+timedelta(minutes=45),data.attendee_name,str(data.attendee_email),data.notes)
    except IntegrationError as e:
        lead_id=lead.id;db.rollback();log(db,lead_id,"calendar_error","外部日历创建失败",{"error_type":e.code});db.add(IntegrationEvent(provider="google_calendar",operation="create_event",status="Failed",lead_id=lead_id,error_type=e.code,detail={"retryable":e.retryable}));db.commit();raise HTTPException(502,detail={"code":e.code,"message":"日历同步失败，请稍后重试"})
    appt=Appointment(lead_id=lead.id,slot_id=slot.id,start_time=start,end_time=start+timedelta(minutes=45),timezone=data.timezone,attendee_name=data.attendee_name,attendee_email=str(data.attendee_email),notes=data.notes,status="Confirmed",external_provider=external["provider"],external_event_id=external["event_id"],external_url=external["url"],sync_status="Synced" if external["provider"]=="google" else "LocalOnly",last_synced_at=datetime.now(timezone.utc));db.add(appt);slot.status="Booked";transition(db,lead,"Meeting","system","预约成功");cancel_open_followups(db,lead.id,"Appointment confirmed");log(db,lead.id,"appointment_confirmed","客户已确认预约",{"start_time":start.isoformat(),"provider":external["provider"]});db.add(IntegrationEvent(provider="google_calendar" if external["provider"]=="google" else "local_calendar",operation="create_event",status="Success",lead_id=lead.id,detail={"synced":external["provider"]=="google"}));db.commit();db.refresh(appt);return appt

@app.post("/api/admin/login")
def login(data:LoginCreate,response:Response,request:Request):
    key=request.client.host if request.client else "unknown";login_limiter.check(key)
    if not secrets.compare_digest(data.username,settings.admin_username) or not secrets.compare_digest(data.password,settings.admin_password):login_limiter.fail(key);raise HTTPException(401,detail={"code":"bad_credentials","message":"账号或密码错误"})
    login_limiter.clear(key);csrf=csrf_token();response.set_cookie("julu_admin",serializer.dumps(data.username),httponly=True,secure=settings.cookie_secure,samesite="lax",max_age=43200);response.set_cookie("julu_csrf",csrf,httponly=False,secure=settings.cookie_secure,samesite="lax",max_age=43200);return {"ok":True,"csrf_token":csrf}
@app.post("/api/admin/logout",dependencies=[Depends(admin),Depends(require_csrf)])
def logout(response:Response):response.delete_cookie("julu_admin");response.delete_cookie("julu_csrf");return {"ok":True}

@app.get("/api/admin/dashboard",dependencies=[Depends(admin)])
def dashboard(db:Session=Depends(get_db)):
    counts={s:db.scalar(select(func.count()).select_from(Lead).where(Lead.status==s)) for s in ["New","Contacted","Qualified","Meeting","Nurture","Closed"]};inv_total=db.scalar(select(func.count()).select_from(AIInvocation)) or 0;inv_failed=db.scalar(select(func.count()).select_from(AIInvocation).where(AIInvocation.validation_status=="Failed")) or 0
    return {"total":db.scalar(select(func.count()).select_from(Lead)),"counts":counts,"high_intent":db.scalar(select(func.count()).select_from(Lead).where(Lead.intent=="High")),"ai_success_rate":round((inv_total-inv_failed)*100/inv_total,1) if inv_total else 0,"recent_leads":[LeadOut.model_validate(x) for x in db.scalars(select(Lead).order_by(Lead.created_at.desc()).limit(5))],"recent_decisions":rows(db.scalars(select(AIDecision).order_by(AIDecision.created_at.desc()).limit(5))),"recent_appointments":rows(db.scalars(select(Appointment).order_by(Appointment.created_at.desc()).limit(5)))}
@app.get("/api/admin/leads",dependencies=[Depends(admin)])
def admin_leads(status:str|None=None,intent:str|None=None,search:str|None=None,page:int=1,page_size:int=20,sort:str="updated_desc",db:Session=Depends(get_db)):
    q=select(Lead)
    if status:q=q.where(Lead.status==status)
    if intent:q=q.where(Lead.intent==intent)
    if search:q=q.where(or_(Lead.name.contains(search),Lead.company.contains(search),Lead.email.contains(search)))
    total=db.scalar(select(func.count()).select_from(q.subquery()));order=Lead.updated_at.asc() if sort=="updated_asc" else Lead.updated_at.desc();return {"items":[LeadOut.model_validate(x) for x in db.scalars(q.order_by(order).offset((page-1)*page_size).limit(page_size))],"total":total,"page":page,"page_size":page_size}
@app.get("/api/admin/leads/{lead_id}",dependencies=[Depends(admin)])
def admin_lead(lead_id:int,db:Session=Depends(get_db)):
    l=get_or_404(db,Lead,lead_id);return {"lead":LeadOut.model_validate(l),"profile":profile_dict(l.profile),"messages":[MessageOut.model_validate(x) for x in l.messages],"decisions":rows(db.scalars(select(AIDecision).where(AIDecision.lead_id==l.id).order_by(AIDecision.created_at.desc()))),"invocations":rows(db.scalars(select(AIInvocation).where(AIInvocation.lead_id==l.id).order_by(AIInvocation.created_at.desc()))),"status_history":rows(db.scalars(select(LeadStatusHistory).where(LeadStatusHistory.lead_id==l.id).order_by(LeadStatusHistory.created_at.desc()))),"appointments":rows(db.scalars(select(Appointment).where(Appointment.lead_id==l.id))),"followups":rows(db.scalars(select(FollowUpTask).where(FollowUpTask.lead_id==l.id))),"logs":rows(db.scalars(select(ActivityLog).where(ActivityLog.lead_id==l.id).order_by(ActivityLog.created_at.desc())))}
@app.patch("/api/admin/leads/{lead_id}",dependencies=[Depends(admin),Depends(require_csrf)])
def patch_lead(lead_id:int,data:LeadPatch,db:Session=Depends(get_db)):
    l=get_or_404(db,Lead,lead_id)
    if data.status:l.manual_status=True;transition(db,l,data.status,"admin","管理员手动修改状态");cancel_open_followups(db,l.id,"Manual terminal state") if data.status in {"Meeting","Closed"} else None
    db.commit();return LeadOut.model_validate(l)
@app.post("/api/admin/leads/{lead_id}/takeover",dependencies=[Depends(admin),Depends(require_csrf)])
def takeover(lead_id:int,data:TakeoverBody,db:Session=Depends(get_db)):
    l=get_or_404(db,Lead,lead_id);l.human_takeover=True;cancel_open_followups(db,l.id,"Human takeover");log(db,l.id,"human_takeover",data.reason);db.commit();return {"ok":True}
@app.post("/api/admin/leads/{lead_id}/release",dependencies=[Depends(admin),Depends(require_csrf)])
def release(lead_id:int,db:Session=Depends(get_db)):
    l=get_or_404(db,Lead,lead_id);l.human_takeover=False;create_followup(db,l);log(db,l.id,"human_release","已释放人工接管");db.commit();return {"ok":True}
@app.get("/api/admin/appointments",dependencies=[Depends(admin)])
def appointments(status:str|None=None,db:Session=Depends(get_db)):
    q=select(Appointment)
    if status:q=q.where(Appointment.status==status)
    return rows(db.scalars(q.order_by(Appointment.start_time)))
@app.patch("/api/admin/appointments/{appointment_id}",dependencies=[Depends(admin),Depends(require_csrf)])
def patch_appointment(appointment_id:int,data:AppointmentPatch,db:Session=Depends(get_db)):
    a=get_or_404(db,Appointment,appointment_id)
    if data.status=="Cancelled" and a.status!="Cancelled":
        try:calendar_service.cancel(a.external_event_id)
        except IntegrationError as e:
            a.sync_status="Failed";a.failure_reason=e.code;db.add(IntegrationEvent(provider="google_calendar",operation="cancel_event",status="Failed",lead_id=a.lead_id,error_type=e.code,detail={"retryable":e.retryable}));db.commit();raise HTTPException(502,detail={"code":e.code,"message":"日历取消失败，本地预约未取消"})
        a.status="Cancelled";a.sync_status="Cancelled";slot=db.get(AvailabilitySlot,a.slot_id) if a.slot_id else None
    else:slot=None;a.status=data.status
    if slot:slot.status="Available";slot.held_by_lead_id=None
    log(db,a.lead_id,"appointment_updated",f"预约状态更新为 {data.status}");db.commit();return rows([a])[0]
@app.get("/api/admin/follow-ups",dependencies=[Depends(admin)])
def followups(status:str|None=None,db:Session=Depends(get_db)):
    q=select(FollowUpTask)
    if status:q=q.where(FollowUpTask.status==status)
    return rows(db.scalars(q.order_by(FollowUpTask.scheduled_at.desc())))
@app.post("/api/admin/follow-ups/{task_id}/approve",dependencies=[Depends(admin),Depends(require_csrf)])
def approve_followup(task_id:int,data:FollowUpPatch,db:Session=Depends(get_db)):
    task=get_or_404(db,FollowUpTask,task_id)
    if task.status not in {"PendingApproval","Failed"}:raise HTTPException(409,detail={"code":"invalid_state","message":"当前任务不可审批"})
    task.status="Scheduled";task.approved_at=datetime.now(timezone.utc);task.scheduled_at=data.scheduled_at or task.scheduled_at;log(db,task.lead_id,"followup_approved","Follow-up 已审批",{"task_id":task.id});db.commit();return rows([task])[0]
@app.post("/api/admin/follow-ups/{task_id}/cancel",dependencies=[Depends(admin),Depends(require_csrf)])
def cancel_followup(task_id:int,db:Session=Depends(get_db)):
    task=get_or_404(db,FollowUpTask,task_id);task.status="Cancelled";log(db,task.lead_id,"followup_cancelled","Follow-up 已取消",{"task_id":task.id});db.commit();return rows([task])[0]
@app.post("/api/admin/follow-ups/{task_id}/retry",dependencies=[Depends(admin),Depends(require_csrf)])
def retry_followup(task_id:int,db:Session=Depends(get_db)):
    task=get_or_404(db,FollowUpTask,task_id);task.status="Scheduled";task.scheduled_at=datetime.now(timezone.utc);task.failure_reason=None;db.commit();return rows([task])[0]
@app.get("/api/admin/activity-logs",dependencies=[Depends(admin)])
def logs(event_type:str|None=None,db:Session=Depends(get_db)):
    q=select(ActivityLog)
    if event_type:q=q.where(ActivityLog.event_type==event_type)
    return rows(db.scalars(q.order_by(ActivityLog.created_at.desc()).limit(300)))
@app.get("/api/admin/ai-invocations",dependencies=[Depends(admin)])
def invocations(status:str|None=None,db:Session=Depends(get_db)):
    q=select(AIInvocation)
    if status:q=q.where(AIInvocation.validation_status==status)
    return rows(db.scalars(q.order_by(AIInvocation.created_at.desc()).limit(300)))
@app.get("/api/admin/ai-metrics",dependencies=[Depends(admin)])
def ai_metrics(db:Session=Depends(get_db)):
    items=list(db.scalars(select(AIInvocation).order_by(AIInvocation.created_at.desc()).limit(1000)))
    latencies=sorted(x.latency_ms for x in items if x.latency_ms is not None)
    def percentile(p:float):
        if not latencies:return None
        return latencies[min(len(latencies)-1,max(0,int((len(latencies)-1)*p+0.5)))]
    errors:dict[str,int]={}
    for item in items:
        if item.error_type:errors[item.error_type]=errors.get(item.error_type,0)+1
    success=sum(x.validation_status in {"Valid","Repaired"} for x in items)
    return {"total":len(items),"success_rate":round(success*100/len(items),1) if items else 0,"p50_latency_ms":percentile(.5),"p95_latency_ms":percentile(.95),"repaired":sum(x.validation_status=="Repaired" for x in items),"failed":sum(x.validation_status=="Failed" for x in items),"total_tokens":sum((x.input_tokens or 0)+(x.output_tokens or 0) for x in items),"error_distribution":errors}
@app.get("/api/admin/email-deliveries",dependencies=[Depends(admin)])
def deliveries(db:Session=Depends(get_db)):return rows(db.scalars(select(EmailDelivery).order_by(EmailDelivery.created_at.desc()).limit(300)))
@app.get("/api/admin/integrations/status",dependencies=[Depends(admin)])
def integration_status(db:Session=Depends(get_db)):
    def last(provider):
        x=db.scalar(select(IntegrationEvent).where(IntegrationEvent.provider==provider,IntegrationEvent.status=="Success").order_by(IntegrationEvent.created_at.desc()).limit(1));return x.created_at if x else None
    ai_provider=settings.ai_provider.lower();return {"ai":{"configured":bool(settings.selected_ai_key),"provider":ai_provider,"mode":"demo" if settings.demo_mode else "real","last_success":last(ai_provider)},"google_calendar":{"configured":calendar_service.configured,"provider":settings.calendar_provider,"last_success":last("google_calendar")},"resend":{"configured":email_service.configured,"allowlist_count":len(email_service.allowlist),"last_success":last("resend")}}

frontend="frontend/dist"
if os.path.isdir(frontend):
    app.mount("/assets",StaticFiles(directory=f"{frontend}/assets"),name="assets")
    @app.get("/{path:path}",include_in_schema=False)
    def spa(path:str):
        target=os.path.join(frontend,path);return FileResponse(target if path and os.path.isfile(target) else f"{frontend}/index.html")
