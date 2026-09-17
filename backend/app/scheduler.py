import asyncio
from datetime import datetime,timedelta,timezone
from sqlalchemy import select,update
from .config import settings
from .database import SessionLocal
from .models import FollowUpTask,Lead,EmailDelivery,ActivityLog,IntegrationEvent
from .integrations import email_service,IntegrationError
from .security import redact_text

def utcnow():return datetime.now(timezone.utc)

def create_followup(db,lead:Lead):
    if lead.status not in {"Contacted","Qualified","Nurture"} or lead.human_takeover:return None
    key=f"qualification-{lead.id}-v1"
    old=db.scalar(select(FollowUpTask).where(FollowUpTask.lead_id==lead.id,FollowUpTask.idempotency_key==key))
    if old:return old
    task=FollowUpTask(lead_id=lead.id,idempotency_key=key,status="PendingApproval",subject=f"{lead.name}，关于 {lead.interested_service} 的后续建议",content=f"{lead.name}，你好。基于我们之前的沟通，我们整理了与 {lead.interested_service} 相关的下一步建议。如方便，可以回复本邮件或预约一次需求诊断。",scheduled_at=utcnow()+timedelta(seconds=settings.followup_demo_delay_seconds),max_attempts=settings.followup_max_attempts)
    db.add(task);db.add(ActivityLog(lead_id=lead.id,event_type="followup_created",message="已生成待审核 Follow-up",meta={"key":key}));return task

def cancel_open_followups(db,lead_id:int,reason:str):
    tasks=db.scalars(select(FollowUpTask).where(FollowUpTask.lead_id==lead_id,FollowUpTask.status.in_(["Draft","PendingApproval","Scheduled","Failed"]))).all()
    for task in tasks:task.status="Cancelled";task.failure_reason=reason

def process_due_once():
    with SessionLocal() as db:
        now=utcnow()
        expired=db.scalars(select(FollowUpTask).where(FollowUpTask.status=="Processing",FollowUpTask.lease_until<now)).all()
        for task in expired:
            task.status="Scheduled";task.lease_until=None
            db.add(ActivityLog(lead_id=task.lead_id,event_type="followup_lease_recovered",message="已回收过期的 Follow-up 执行租约",meta={"task_id":task.id}))
        db.commit()
        candidates=db.scalars(select(FollowUpTask).where(FollowUpTask.status=="Scheduled",FollowUpTask.scheduled_at<=now).order_by(FollowUpTask.scheduled_at).limit(10)).all()
        for item in candidates:
            claimed=db.execute(update(FollowUpTask).where(FollowUpTask.id==item.id,FollowUpTask.status=="Scheduled").values(status="Processing",lease_until=now+timedelta(minutes=2))).rowcount
            if not claimed:continue
            db.commit(); task=db.get(FollowUpTask,item.id);lead=db.get(Lead,task.lead_id)
            if not lead or lead.human_takeover or lead.status in {"Meeting","Closed"}:
                task.status="Skipped";task.failure_reason="Lead state prevents automation";db.commit();continue
            try:
                result=email_service.send(lead.email,task.subject,task.content.replace("\n","<br>"));task.attempts+=1;task.status="Sent" if result["status"] in {"Sent","DryRun"} else "Skipped"
                db.add(EmailDelivery(lead_id=lead.id,follow_up_id=task.id,recipient_redacted=result["recipient"],provider="resend" if result["status"]=="Sent" else "local",provider_message_id=result["provider_id"],status=result["status"],attempts=task.attempts))
                db.add(IntegrationEvent(provider="resend" if result["status"]=="Sent" else "local_email",operation="send_followup",status="Success",lead_id=lead.id,detail={"delivery_status":result["status"]}))
                db.add(ActivityLog(lead_id=lead.id,event_type="followup_executed",message=f"Follow-up 结果：{result['status']}",meta={"task_id":task.id}))
            except IntegrationError as e:
                task.attempts+=1;task.failure_reason=redact_text(f"{e.code}:{e}");task.status="Scheduled" if e.retryable and task.attempts<task.max_attempts else "Failed";task.scheduled_at=now+timedelta(minutes=2**task.attempts)
                db.add(IntegrationEvent(provider="resend",operation="send_followup",status="Failed",lead_id=lead.id,error_type=e.code,detail={"retryable":e.retryable}))
            task.lease_until=None;db.commit()

async def scheduler_loop():
    while True:
        try:await asyncio.to_thread(process_due_once)
        except Exception:pass
        await asyncio.sleep(max(5,settings.followup_poll_seconds))
