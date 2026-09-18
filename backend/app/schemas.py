from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl, model_validator

Status=Literal["New","Contacted","Qualified","Meeting","Nurture","Closed"]
Intent=Literal["High","Medium","Low"]
Action=Literal["continue_qualification","recommend_service","share_material","offer_meeting","handoff_to_human","nurture","close"]

class LeadCreate(BaseModel):
    name:str=Field(min_length=2,max_length=100); company:str=Field(min_length=2,max_length=160); email:EmailStr; industry:str; country:str; interested_service:str
    website:str|None=None; phone:str|None=Field(default=None,max_length=40); preferred_language:Literal["auto","zh-CN","en-US","es-ES"]="auto"; initial_requirement:str|None=Field(default=None,max_length=2000)
class MessageCreate(BaseModel): content:str=Field(min_length=1,max_length=4000); client_message_id:str=Field(min_length=4,max_length=100)
class AppointmentCreate(BaseModel): start_time:datetime; timezone:str; attendee_name:str; attendee_email:EmailStr; notes:str|None=None
class LoginCreate(BaseModel): username:str; password:str
class LeadPatch(BaseModel): status:Status|None=None
class TakeoverBody(BaseModel): reason:str="人工跟进"
class AppointmentPatch(BaseModel): status:Literal["Confirmed","Cancelled"]
class FollowUpPatch(BaseModel): scheduled_at:datetime|None=None
class KnowledgeSearch(BaseModel): query:str=Field(min_length=2,max_length=500); top_k:int=Field(default=4,ge=1,le=10)
class QuoteCreate(BaseModel): package_code:Literal["starter","growth","enterprise"]="growth"; discount_percent:int=Field(default=0,ge=0,le=20)
class QuotePatch(BaseModel): status:Literal["Approved","Rejected"]
class ProposalCreate(BaseModel): language:Literal["zh-CN","en-US","es-ES"]="zh-CN"; quote_id:int|None=None
class ChannelSend(BaseModel): channel:Literal["email","whatsapp"]; recipient:str=Field(min_length=3,max_length=220); subject:str=Field(default="JULU AI 后续建议",max_length=200); content:str=Field(min_length=1,max_length=8000)
class CRMSyncCreate(BaseModel): provider:Literal["hubspot","salesforce"]

class ScoreDimension(BaseModel):
    score:int=Field(ge=0)
    max_score:int=Field(gt=0)
    evidence:list[str]=Field(default_factory=list)

    @model_validator(mode="after")
    def within_limit(self):
        if self.score>self.max_score: raise ValueError("score exceeds dimension maximum")
        return self

class AIResult(BaseModel):
    reply:str
    extracted_facts:dict[str, str|bool|None]=Field(default_factory=dict)
    updated_profile:dict[str, str|bool|None]=Field(default_factory=dict)
    missing_fields:list[str]=Field(default_factory=list)
    lead_score:int=Field(ge=0,le=100)
    intent:Intent
    score_breakdown:dict[str,int|ScoreDimension]
    score_reason:str
    recommended_service:str|None=None
    next_action:Action
    suggested_status:Status
    should_offer_meeting:bool=False
    should_handoff:bool=False
    handoff_reason:str|None=None
    conversation_summary:str
    question_reason:str=""
    knowledge_refs:list[str]=Field(default_factory=list)
    fact_sources:dict[str,list[int]]=Field(default_factory=dict)

    @model_validator(mode="after")
    def fix_intent(self):
        limits={"业务匹配度":25,"痛点明确度":25,"时间紧迫度":20,"预算可行性":15,"决策影响力":15}
        normalized={}
        for name,maximum in limits.items():
            value=self.score_breakdown.get(name,0)
            if isinstance(value,int): value=ScoreDimension(score=value,max_score=maximum,evidence=[])
            if value.max_score!=maximum: raise ValueError(f"invalid maximum for {name}")
            normalized[name]=value
        total=sum(x.score for x in normalized.values())
        if total!=self.lead_score: raise ValueError("lead_score must equal score breakdown sum")
        self.score_breakdown=normalized
        expected="High" if self.lead_score>=70 else "Medium" if self.lead_score>=40 else "Low"
        self.intent=expected
        return self

class ORM(BaseModel): model_config=ConfigDict(from_attributes=True)
class MessageOut(ORM): id:int; role:str; content:str; created_at:datetime; error_code:str|None=None
class LeadOut(ORM):
    id:int; public_token:str; name:str; company:str; email:str; industry:str; country:str; website:str|None; interested_service:str; initial_requirement:str|None; source:str; status:str; lead_score:int; intent:str; score_reason:str; recommended_service:str|None; next_action:str; conversation_summary:str; human_takeover:bool; created_at:datetime; updated_at:datetime; last_contacted_at:datetime|None
class LeadCreated(BaseModel): lead:LeadOut; first_message:MessageOut; demo_mode:bool

class FollowUpOut(ORM):
    id:int; lead_id:int; status:str; subject:str; content:str; scheduled_at:datetime; attempts:int; max_attempts:int; failure_reason:str|None=None; created_at:datetime
