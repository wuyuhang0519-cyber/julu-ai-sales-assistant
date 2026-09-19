from datetime import datetime, timezone
from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, Text, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base

def now(): return datetime.now(timezone.utc)

class Lead(Base):
    __tablename__="leads"
    id: Mapped[int]=mapped_column(primary_key=True)
    public_token: Mapped[str]=mapped_column(String(64), unique=True, index=True)
    idempotency_key: Mapped[str|None]=mapped_column(String(100), unique=True, nullable=True)
    name: Mapped[str]=mapped_column(String(100)); company: Mapped[str]=mapped_column(String(160)); email: Mapped[str]=mapped_column(String(200))
    industry: Mapped[str]=mapped_column(String(120)); country: Mapped[str]=mapped_column(String(120)); website: Mapped[str|None]=mapped_column(String(300), nullable=True)
    interested_service: Mapped[str]=mapped_column(String(160)); initial_requirement: Mapped[str|None]=mapped_column(Text, nullable=True)
    source: Mapped[str]=mapped_column(String(30), default="website"); status: Mapped[str]=mapped_column(String(30), default="New")
    lead_score: Mapped[int]=mapped_column(Integer, default=0); intent: Mapped[str]=mapped_column(String(20), default="Low")
    score_reason: Mapped[str]=mapped_column(Text, default="信息不足，等待进一步沟通")
    recommended_service: Mapped[str|None]=mapped_column(String(160), nullable=True); next_action: Mapped[str]=mapped_column(String(40), default="continue_qualification")
    conversation_summary: Mapped[str]=mapped_column(Text, default=""); human_takeover: Mapped[bool]=mapped_column(Boolean, default=False)
    manual_status: Mapped[bool]=mapped_column(Boolean, default=False)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now); updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    last_contacted_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True), nullable=True)
    profile=relationship("LeadProfile", back_populates="lead", uselist=False, cascade="all, delete-orphan")
    messages=relationship("Message", back_populates="lead", cascade="all, delete-orphan", order_by="Message.created_at")

class LeadProfile(Base):
    __tablename__="lead_profiles"
    id: Mapped[int]=mapped_column(primary_key=True); lead_id: Mapped[int]=mapped_column(ForeignKey("leads.id"), unique=True)
    target_market: Mapped[str|None]=mapped_column(Text, nullable=True); current_acquisition: Mapped[str|None]=mapped_column(Text, nullable=True)
    current_seo_geo: Mapped[str|None]=mapped_column(Text, nullable=True); target_platforms: Mapped[str|None]=mapped_column(Text, nullable=True)
    target_result: Mapped[str|None]=mapped_column(Text, nullable=True); pain_points: Mapped[str|None]=mapped_column(Text, nullable=True)
    budget_range: Mapped[str|None]=mapped_column(Text, nullable=True); timeline: Mapped[str|None]=mapped_column(Text, nullable=True)
    decision_role: Mapped[str|None]=mapped_column(Text, nullable=True); has_website: Mapped[bool|None]=mapped_column(Boolean, nullable=True)
    additional_facts: Mapped[dict]=mapped_column(JSON, default=dict); missing_fields: Mapped[list]=mapped_column(JSON, default=list)
    updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now, onupdate=now); lead=relationship("Lead", back_populates="profile")

class Message(Base):
    __tablename__="messages"; __table_args__=(UniqueConstraint("lead_id","client_message_id"),)
    id: Mapped[int]=mapped_column(primary_key=True); lead_id: Mapped[int]=mapped_column(ForeignKey("leads.id")); role: Mapped[str]=mapped_column(String(20)); content: Mapped[str]=mapped_column(Text)
    client_message_id: Mapped[str|None]=mapped_column(String(100), nullable=True); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)
    model_name: Mapped[str|None]=mapped_column(String(100), nullable=True); model_latency_ms: Mapped[int|None]=mapped_column(Integer, nullable=True); error_code: Mapped[str|None]=mapped_column(String(80), nullable=True)
    lead=relationship("Lead", back_populates="messages")

class AIDecision(Base):
    __tablename__="ai_decisions"
    id: Mapped[int]=mapped_column(primary_key=True); lead_id: Mapped[int]=mapped_column(ForeignKey("leads.id")); lead_score: Mapped[int]=mapped_column(Integer)
    intent: Mapped[str]=mapped_column(String(20)); score_breakdown: Mapped[dict]=mapped_column(JSON); score_reason: Mapped[str]=mapped_column(Text)
    recommended_service: Mapped[str|None]=mapped_column(String(160), nullable=True); next_action: Mapped[str]=mapped_column(String(40)); suggested_status: Mapped[str]=mapped_column(String(30))
    should_offer_meeting: Mapped[bool]=mapped_column(Boolean); should_handoff: Mapped[bool]=mapped_column(Boolean); handoff_reason: Mapped[str|None]=mapped_column(Text, nullable=True)
    raw_response_redacted: Mapped[str]=mapped_column(Text, default=""); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)
    invocation_id: Mapped[int|None]=mapped_column(ForeignKey("ai_invocations.id"), nullable=True)
    knowledge_refs: Mapped[list]=mapped_column(JSON, default=list)
    question_reason: Mapped[str|None]=mapped_column(Text, nullable=True)

class Appointment(Base):
    __tablename__="appointments"; __table_args__=(UniqueConstraint("lead_id","start_time"),)
    id: Mapped[int]=mapped_column(primary_key=True); lead_id: Mapped[int]=mapped_column(ForeignKey("leads.id")); start_time: Mapped[datetime]=mapped_column(DateTime(timezone=True), index=True)
    end_time: Mapped[datetime]=mapped_column(DateTime(timezone=True)); timezone: Mapped[str]=mapped_column(String(80)); attendee_name: Mapped[str]=mapped_column(String(100)); attendee_email: Mapped[str]=mapped_column(String(200)); notes: Mapped[str|None]=mapped_column(Text, nullable=True)
    status: Mapped[str]=mapped_column(String(20), default="Confirmed"); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now); updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    slot_id: Mapped[int|None]=mapped_column(ForeignKey("availability_slots.id"), nullable=True, unique=True)
    external_provider: Mapped[str]=mapped_column(String(30), default="local")
    external_event_id: Mapped[str|None]=mapped_column(String(255), nullable=True)
    external_url: Mapped[str|None]=mapped_column(Text, nullable=True)
    sync_status: Mapped[str]=mapped_column(String(30), default="LocalOnly")
    failure_reason: Mapped[str|None]=mapped_column(Text, nullable=True)
    last_synced_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True), nullable=True)

class ActivityLog(Base):
    __tablename__="activity_logs"
    id: Mapped[int]=mapped_column(primary_key=True); lead_id: Mapped[int|None]=mapped_column(ForeignKey("leads.id"), nullable=True); event_type: Mapped[str]=mapped_column(String(80)); message: Mapped[str]=mapped_column(Text); meta: Mapped[dict]=mapped_column("metadata", JSON, default=dict); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)

class AvailabilitySlot(Base):
    __tablename__="availability_slots"; __table_args__=(UniqueConstraint("resource_id","start_time"),)
    id: Mapped[int]=mapped_column(primary_key=True); resource_id: Mapped[str]=mapped_column(String(80), default="julu-sales")
    start_time: Mapped[datetime]=mapped_column(DateTime(timezone=True), index=True); end_time: Mapped[datetime]=mapped_column(DateTime(timezone=True))
    status: Mapped[str]=mapped_column(String(20), default="Available", index=True); held_by_lead_id: Mapped[int|None]=mapped_column(ForeignKey("leads.id"), nullable=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now); updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now, onupdate=now)

class AIInvocation(Base):
    __tablename__="ai_invocations"
    id: Mapped[int]=mapped_column(primary_key=True); lead_id: Mapped[int|None]=mapped_column(ForeignKey("leads.id"), nullable=True, index=True)
    request_id: Mapped[str]=mapped_column(String(100), unique=True); provider: Mapped[str]=mapped_column(String(40)); model_name: Mapped[str]=mapped_column(String(100)); prompt_version: Mapped[str]=mapped_column(String(40))
    input_message_ids: Mapped[list]=mapped_column(JSON, default=list); knowledge_refs: Mapped[list]=mapped_column(JSON, default=list)
    validation_status: Mapped[str]=mapped_column(String(30)); repair_attempts: Mapped[int]=mapped_column(Integer, default=0); latency_ms: Mapped[int|None]=mapped_column(Integer, nullable=True)
    input_tokens: Mapped[int|None]=mapped_column(Integer, nullable=True); output_tokens: Mapped[int|None]=mapped_column(Integer, nullable=True)
    error_type: Mapped[str|None]=mapped_column(String(80), nullable=True); response_summary: Mapped[dict]=mapped_column(JSON, default=dict)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)

class LeadStatusHistory(Base):
    __tablename__="lead_status_history"
    id: Mapped[int]=mapped_column(primary_key=True); lead_id: Mapped[int]=mapped_column(ForeignKey("leads.id"), index=True)
    from_status: Mapped[str|None]=mapped_column(String(30), nullable=True); to_status: Mapped[str]=mapped_column(String(30)); actor: Mapped[str]=mapped_column(String(30)); reason: Mapped[str]=mapped_column(Text)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)

class FollowUpTask(Base):
    __tablename__="follow_up_tasks"; __table_args__=(UniqueConstraint("lead_id","idempotency_key"),)
    id: Mapped[int]=mapped_column(primary_key=True); lead_id: Mapped[int]=mapped_column(ForeignKey("leads.id"), index=True); idempotency_key: Mapped[str]=mapped_column(String(120))
    status: Mapped[str]=mapped_column(String(30), default="PendingApproval", index=True); subject: Mapped[str]=mapped_column(String(200)); content: Mapped[str]=mapped_column(Text)
    scheduled_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), index=True); approved_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True), nullable=True)
    attempts: Mapped[int]=mapped_column(Integer, default=0); max_attempts: Mapped[int]=mapped_column(Integer, default=3); lease_until: Mapped[datetime|None]=mapped_column(DateTime(timezone=True), nullable=True)
    failure_reason: Mapped[str|None]=mapped_column(Text, nullable=True); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now); updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now, onupdate=now)

class EmailDelivery(Base):
    __tablename__="email_deliveries"
    id: Mapped[int]=mapped_column(primary_key=True); lead_id: Mapped[int|None]=mapped_column(ForeignKey("leads.id"), nullable=True, index=True); follow_up_id: Mapped[int|None]=mapped_column(ForeignKey("follow_up_tasks.id"), nullable=True)
    recipient_redacted: Mapped[str]=mapped_column(String(220)); provider: Mapped[str]=mapped_column(String(30)); provider_message_id: Mapped[str|None]=mapped_column(String(255), nullable=True)
    status: Mapped[str]=mapped_column(String(30)); attempts: Mapped[int]=mapped_column(Integer, default=0); error_type: Mapped[str|None]=mapped_column(String(80), nullable=True); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)

class IntegrationEvent(Base):
    __tablename__="integration_events"
    id: Mapped[int]=mapped_column(primary_key=True); provider: Mapped[str]=mapped_column(String(40), index=True); operation: Mapped[str]=mapped_column(String(80)); status: Mapped[str]=mapped_column(String(30)); lead_id: Mapped[int|None]=mapped_column(ForeignKey("leads.id"), nullable=True)
    latency_ms: Mapped[int|None]=mapped_column(Integer, nullable=True); error_type: Mapped[str|None]=mapped_column(String(80), nullable=True); detail: Mapped[dict]=mapped_column(JSON, default=dict); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)

class Quote(Base):
    __tablename__="quotes"
    id: Mapped[int]=mapped_column(primary_key=True); lead_id: Mapped[int]=mapped_column(ForeignKey("leads.id"), index=True)
    quote_number: Mapped[str]=mapped_column(String(60), unique=True, index=True); package_code: Mapped[str]=mapped_column(String(40)); currency: Mapped[str]=mapped_column(String(10), default="CNY")
    subtotal: Mapped[int]=mapped_column(Integer); discount_percent: Mapped[int]=mapped_column(Integer, default=0); total: Mapped[int]=mapped_column(Integer)
    line_items: Mapped[list]=mapped_column(JSON, default=list); assumptions: Mapped[list]=mapped_column(JSON, default=list); status: Mapped[str]=mapped_column(String(30), default="Draft")
    valid_until: Mapped[datetime]=mapped_column(DateTime(timezone=True)); approved_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True), nullable=True); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)

class Proposal(Base):
    __tablename__="proposals"
    id: Mapped[int]=mapped_column(primary_key=True); lead_id: Mapped[int]=mapped_column(ForeignKey("leads.id"), index=True); quote_id: Mapped[int|None]=mapped_column(ForeignKey("quotes.id"), nullable=True)
    proposal_number: Mapped[str]=mapped_column(String(60), unique=True, index=True); language: Mapped[str]=mapped_column(String(10), default="zh-CN"); title: Mapped[str]=mapped_column(String(240)); content_markdown: Mapped[str]=mapped_column(Text)
    knowledge_refs: Mapped[list]=mapped_column(JSON, default=list); status: Mapped[str]=mapped_column(String(30), default="Draft"); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now); updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now, onupdate=now)

class ChannelDelivery(Base):
    __tablename__="channel_deliveries"
    id: Mapped[int]=mapped_column(primary_key=True); lead_id: Mapped[int|None]=mapped_column(ForeignKey("leads.id"), nullable=True, index=True); channel: Mapped[str]=mapped_column(String(30)); recipient_redacted: Mapped[str]=mapped_column(String(220))
    provider: Mapped[str]=mapped_column(String(40)); provider_message_id: Mapped[str|None]=mapped_column(String(255), nullable=True); status: Mapped[str]=mapped_column(String(30)); error_type: Mapped[str|None]=mapped_column(String(80), nullable=True)
    content_summary: Mapped[str]=mapped_column(Text, default=""); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)

class CRMSync(Base):
    __tablename__="crm_syncs"
    id: Mapped[int]=mapped_column(primary_key=True); lead_id: Mapped[int]=mapped_column(ForeignKey("leads.id"), index=True); provider: Mapped[str]=mapped_column(String(30)); operation: Mapped[str]=mapped_column(String(40), default="upsert_lead")
    status: Mapped[str]=mapped_column(String(30)); external_id: Mapped[str|None]=mapped_column(String(255), nullable=True); error_type: Mapped[str|None]=mapped_column(String(80), nullable=True); detail: Mapped[dict]=mapped_column(JSON, default=dict); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)