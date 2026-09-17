import os
from datetime import datetime,timedelta,timezone
os.environ.update({"DATABASE_URL":"sqlite:///./test_julu.db","DEMO_MODE":"true","ADMIN_USERNAME":"admin","ADMIN_PASSWORD":"change-me"})
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.ai_service import intent,demo_result
from backend.app.security import redact,redact_email
from backend.app.schemas import AIResult
from backend.app.database import Base,engine
from backend.app.database import SessionLocal
from backend.app.config import settings
from backend.app.integrations import CalendarService,EmailService,IntegrationError
from backend.app.ai_service import run_ai
from backend.app.models import FollowUpTask,EmailDelivery,Lead
from backend.app.scheduler import process_due_once
from pydantic import ValidationError

Base.metadata.drop_all(engine); Base.metadata.create_all(engine)
client=TestClient(app)
payload={"name":"王经理","company":"智造设备有限公司","email":"wang@example.com","industry":"B2B 制造","country":"中国","website":"https://example.com","interested_service":"全球 AI 搜索优化","initial_requirement":"希望进入欧美市场，当前依赖 Google Ads，三个月内启动，有初步预算，我参与决策，希望提升 ChatGPT 和 Google AI 可见度和询盘"}

def create(key="lead-1"):
    r=client.post('/api/public/leads',json=payload,headers={'Idempotency-Key':key}); assert r.status_code in (200,201); return r.json()
def login():
    r=client.post('/api/admin/login',json={'username':'admin','password':'change-me'}); assert r.status_code==200; return r.json()['csrf_token']

def test_score_boundaries_and_intent_correction():
    assert intent(0)=='Low' and intent(39)=='Low' and intent(40)=='Medium' and intent(69)=='Medium' and intent(70)=='High' and intent(100)=='High'
    data={"reply":"x","lead_score":75,"intent":"Low","score_breakdown":{"业务匹配度":20,"痛点明确度":20,"时间紧迫度":15,"预算可行性":10,"决策影响力":10},"score_reason":"x","next_action":"offer_meeting","suggested_status":"Qualified","conversation_summary":"x"}
    assert AIResult.model_validate(data).intent=='High'
def test_create_lead_first_reply_and_idempotency():
    a=create('idem-a'); b=create('idem-a'); assert a['lead']['id']==b['lead']['id']; assert a['first_message']['role']=='assistant'
def test_multiturn_profile_decision_and_duplicate_message():
    d=create('idem-chat'); t=d['lead']['public_token']; body={'content':'目标是欧美市场，主要依靠 Google Ads，三个月启动，预算 20 万，我是决策负责人','client_message_id':'msg-001'}
    a=client.post(f'/api/public/leads/{t}/messages',json=body); b=client.post(f'/api/public/leads/{t}/messages',json=body); assert a.status_code==200 and b.json()['deduplicated'] is True; assert a.json()['lead']['lead_score']>=70
def test_appointment_duplicate_and_conflict():
    a=create('idem-appt-a'); b=create('idem-appt-b'); slot=client.get('/api/public/availability').json()[0]
    body={'start_time':slot['start_time'],'timezone':'Asia/Shanghai','attendee_name':'王经理','attendee_email':'wang@example.com'}
    r1=client.post(f"/api/public/leads/{a['lead']['public_token']}/appointments",json=body); r2=client.post(f"/api/public/leads/{a['lead']['public_token']}/appointments",json=body); r3=client.post(f"/api/public/leads/{b['lead']['public_token']}/appointments",json=body)
    assert r1.status_code==201 and r2.status_code==201 and r1.json()['id']==r2.json()['id'] and r3.status_code==409
def test_admin_auth_and_detail_takeover_blocks_status():
    d=create('idem-admin'); assert client.get('/api/admin/dashboard').status_code==401; csrf=login(); assert client.get('/api/admin/dashboard').status_code==200
    lid=d['lead']['id']; assert client.post(f'/api/admin/leads/{lid}/takeover',json={'reason':'test'},headers={'X-CSRF-Token':csrf}).status_code==200
    t=d['lead']['public_token']; before=client.get(f'/api/admin/leads/{lid}').json()['lead']['status']; client.post(f'/api/public/leads/{t}/messages',json={'content':'欧美市场，三个月启动，预算明确，我是决策人','client_message_id':'takeover-msg'}); after=client.get(f'/api/admin/leads/{lid}').json()['lead']['status']; assert before==after
def test_knowledge_boundary_handoff_and_rejection():
    d=create('idem-bound'); t=d['lead']['public_token']; r=client.post(f'/api/public/leads/{t}/messages',json={'content':'请保证排名并给合同最低价','client_message_id':'price-msg'}).json(); assert r['lead']['next_action']=='handoff_to_human'
    r=client.post(f'/api/public/leads/{t}/messages',json={'content':'我们不需要，请不要联系','client_message_id':'close-msg'}).json(); assert r['lead']['status']=='Closed'

def test_redaction_and_csrf():
    value=redact({'authorization':'Bearer secret','email':'person@example.com','phone':'13812345678'})
    assert value['authorization']=='[REDACTED]' and 'person@example.com' not in value['email'] and '[PHONE_REDACTED]' in value['phone']
    d=create('csrf-lead'); login(); assert client.post(f"/api/admin/leads/{d['lead']['id']}/takeover",json={'reason':'x'},headers={'X-CSRF-Token':'wrong'}).status_code==403

def test_followup_created_and_integration_status():
    create('followup-lead'); csrf=login(); tasks=client.get('/api/admin/follow-ups').json(); assert tasks and tasks[0]['status']=='PendingApproval'
    r=client.post(f"/api/admin/follow-ups/{tasks[0]['id']}/approve",json={},headers={'X-CSRF-Token':csrf}); assert r.status_code==200 and r.json()['status']=='Scheduled'
    status=client.get('/api/admin/integrations/status').json(); assert set(status)=={'openai','google_calendar','resend'}

def test_schema_rejects_invalid_dimension_and_total():
    bad={"reply":"x","lead_score":101,"intent":"High","score_breakdown":{},"score_reason":"x","next_action":"offer_meeting","suggested_status":"Qualified","conversation_summary":"x"}
    try:AIResult.model_validate(bad);assert False
    except ValidationError:pass

def test_email_allowlist_dry_run_and_blocking():
    old=settings.email_test_allowlist
    try:
        settings.email_test_allowlist="allowed@example.com"
        service=EmailService();allowed=service.send("allowed@example.com","主题","正文");blocked=service.send("other@example.com","主题","正文")
        assert allowed["status"]=="DryRun" and blocked["status"]=="Blocked" and blocked["recipient"]!="other@example.com"
    finally:settings.email_test_allowlist=old

def test_calendar_error_classification():
    class Resp:status=429
    class FakeError(Exception):resp=Resp()
    err=CalendarService._error("calendar_create_error",FakeError())
    assert isinstance(err,IntegrationError) and err.retryable and err.code.endswith("rate_limit")

def test_followup_scheduler_executes_and_recovers_lease():
    d=create('scheduler-lead');lead_id=d['lead']['id'];old=settings.email_test_allowlist
    try:
        settings.email_test_allowlist="wang@example.com"
        with SessionLocal() as db:
            task=db.query(FollowUpTask).filter(FollowUpTask.lead_id==lead_id).first();task.status="Scheduled";task.scheduled_at=datetime.now(timezone.utc)-timedelta(minutes=1)
            stuck=FollowUpTask(lead_id=lead_id,idempotency_key="stuck-v1",status="Processing",subject="x",content="x",scheduled_at=datetime.now(timezone.utc)+timedelta(days=1),lease_until=datetime.now(timezone.utc)-timedelta(minutes=1));db.add(stuck);db.commit();task_id=task.id;stuck_id=stuck.id
        process_due_once()
        with SessionLocal() as db:
            assert db.get(FollowUpTask,task_id).status=="Sent" and db.get(FollowUpTask,stuck_id).status=="Scheduled"
            assert db.query(EmailDelivery).filter(EmailDelivery.follow_up_id==task_id).count()==1
    finally:settings.email_test_allowlist=old

def test_admin_can_cancel_appointment_and_release_slot():
    d=create('cancel-appt');slot=client.get('/api/public/availability').json()[0];body={'start_time':slot['start_time'],'timezone':'Asia/Shanghai','attendee_name':'王经理','attendee_email':'wang@example.com'}
    booking=client.post(f"/api/public/leads/{d['lead']['public_token']}/appointments",json=body);assert booking.status_code==201,booking.text;booked=booking.json();csrf=login()
    r=client.patch(f"/api/admin/appointments/{booked['id']}",json={'status':'Cancelled'},headers={'X-CSRF-Token':csrf});assert r.status_code==200 and r.json()['status']=='Cancelled'
    assert any(x['id']==slot['id'] for x in client.get('/api/public/availability').json())

def test_resend_success_and_non_retryable_auth(monkeypatch):
    old=(settings.resend_api_key,settings.resend_from_email,settings.email_test_allowlist)
    class Response:
        def __init__(self,status):self.status_code=status
        def raise_for_status(self):return None
        def json(self):return {'id':'email-123'}
    try:
        settings.resend_api_key='test-key';settings.resend_from_email='demo@example.com';settings.email_test_allowlist='allowed@example.com'
        monkeypatch.setattr('backend.app.integrations.httpx.post',lambda *a,**k:Response(200))
        result=EmailService().send('allowed@example.com','主题','正文');assert result['status']=='Sent' and result['provider_id']=='email-123'
        monkeypatch.setattr('backend.app.integrations.httpx.post',lambda *a,**k:Response(401))
        try:EmailService().send('allowed@example.com','主题','正文');assert False
        except IntegrationError as e:assert e.code=='email_auth' and not e.retryable
    finally:settings.resend_api_key,settings.resend_from_email,settings.email_test_allowlist=old

def test_real_ai_without_key_fails_without_mutating_business_state():
    d=create('real-no-key')
    with SessionLocal() as db:
        lead=db.get(Lead,d['lead']['id']);old=(settings.demo_mode,settings.openai_api_key)
        try:
            settings.demo_mode=False;settings.openai_api_key=''
            execution=run_ai(lead,lead.profile,lead.messages,False);assert execution.result is None and execution.error_type=='missing_api_key'
        finally:settings.demo_mode,settings.openai_api_key=old

def test_admin_operational_endpoints_and_manual_priority():
    d=create('admin-ops');csrf=login();lid=d['lead']['id']
    patched=client.patch(f'/api/admin/leads/{lid}',json={'status':'Nurture'},headers={'X-CSRF-Token':csrf});assert patched.status_code==200 and patched.json()['status']=='Nurture'
    assert client.post(f'/api/admin/leads/{lid}/release',headers={'X-CSRF-Token':csrf}).status_code==200
    for endpoint in ['/api/admin/appointments','/api/admin/follow-ups','/api/admin/activity-logs','/api/admin/ai-invocations','/api/admin/ai-metrics','/api/admin/email-deliveries']:
        assert client.get(endpoint).status_code==200
