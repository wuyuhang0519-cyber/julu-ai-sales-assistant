import json,time
from datetime import datetime
from pathlib import Path
import httpx
from .config import settings
from .security import redact_email

class IntegrationError(RuntimeError):
    def __init__(self,code:str,message:str,retryable:bool=False):super().__init__(message);self.code=code;self.retryable=retryable

class CalendarService:
    @property
    def configured(self):
        has_credentials=bool(settings.google_service_account_json) or bool(settings.google_service_account_file and Path(settings.google_service_account_file).is_file())
        return settings.calendar_provider=="google" and bool(settings.google_calendar_id and has_credentials)
    def _service(self):
        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build
        scopes=["https://www.googleapis.com/auth/calendar"]
        if settings.google_service_account_json:
            info=json.loads(settings.google_service_account_json);creds=Credentials.from_service_account_info(info,scopes=scopes)
        else:creds=Credentials.from_service_account_file(settings.google_service_account_file,scopes=scopes)
        return build("calendar","v3",credentials=creds,cache_discovery=False)
    def freebusy(self,start:datetime,end:datetime):
        if not self.configured:return []
        try:
            response=self._service().freebusy().query(body={"timeMin":start.isoformat(),"timeMax":end.isoformat(),"timeZone":"UTC","items":[{"id":settings.google_calendar_id}]}).execute()
            return response.get("calendars",{}).get(settings.google_calendar_id,{}).get("busy",[])
        except Exception as e:raise self._error("calendar_freebusy_error",e) from e
    @staticmethod
    def _error(prefix:str,error:Exception):
        status=getattr(getattr(error,"resp",None),"status",None)
        if status in (401,403):return IntegrationError(f"{prefix}_auth",f"HTTP {status}",False)
        if status==409:return IntegrationError(f"{prefix}_conflict","HTTP 409",False)
        if status==429:return IntegrationError(f"{prefix}_rate_limit","HTTP 429",True)
        if status and status>=500:return IntegrationError(f"{prefix}_server",f"HTTP {status}",True)
        return IntegrationError(prefix,type(error).__name__,True)
    def create(self,start:datetime,end:datetime,name:str,email:str,notes:str|None):
        if not self.configured:return {"provider":"local","event_id":None,"url":None}
        try:
            description=f"{notes or 'JULU AI 官网客资预约'}\n测试联系人：{email}"
            svc=self._service(); body={"summary":f"JULU AI 需求诊断 - {name}","description":description,"start":{"dateTime":start.isoformat(),"timeZone":"UTC"},"end":{"dateTime":end.isoformat(),"timeZone":"UTC"}}
            if settings.google_calendar_invite_attendees:body["attendees"]=[{"email":email}]
            event=svc.events().insert(calendarId=settings.google_calendar_id,body=body,sendUpdates="none").execute()
            return {"provider":"google","event_id":event.get("id"),"url":event.get("htmlLink")}
        except Exception as e: raise self._error("calendar_create_error",e) from e
    def cancel(self,event_id:str|None):
        if not event_id or not self.configured:return
        try:self._service().events().delete(calendarId=settings.google_calendar_id,eventId=event_id,sendUpdates="none").execute()
        except Exception as e: raise self._error("calendar_cancel_error",e) from e

class EmailService:
    @property
    def allowlist(self):return {x.strip().lower() for x in settings.email_test_allowlist.split(",") if x.strip()}
    @property
    def configured(self):return bool(settings.resend_api_key and settings.resend_from_email)
    def send(self,to:str,subject:str,html:str):
        if to.lower() not in self.allowlist:return {"status":"Blocked","provider_id":None,"recipient":redact_email(to)}
        if not self.configured:return {"status":"DryRun","provider_id":None,"recipient":redact_email(to)}
        last=None
        for attempt in range(3):
            try:
                r=httpx.post("https://api.resend.com/emails",headers={"Authorization":f"Bearer {settings.resend_api_key}"},json={"from":settings.resend_from_email,"to":[to],"subject":subject,"html":html},timeout=15)
                if r.status_code in (401,403):raise IntegrationError("email_auth",f"HTTP {r.status_code}",False)
                if r.status_code==429 or r.status_code>=500:raise IntegrationError("email_retryable",f"HTTP {r.status_code}",True)
                r.raise_for_status(); return {"status":"Sent","provider_id":r.json().get("id"),"recipient":redact_email(to)}
            except IntegrationError as e:
                last=e
                if not e.retryable:raise
                if attempt<2:time.sleep(.25*(2**attempt))
            except (httpx.TimeoutException,httpx.NetworkError) as e:
                last=IntegrationError("email_network",type(e).__name__,True)
                if attempt<2:time.sleep(.25*(2**attempt))
        raise last or IntegrationError("email_error","unknown",False)

calendar_service=CalendarService(); email_service=EmailService()
