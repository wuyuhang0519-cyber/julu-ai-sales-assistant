import json
import secrets
from datetime import datetime,timedelta,timezone
from pathlib import Path
from sqlalchemy.orm import Session
from .config import settings
from .models import Lead,Quote,Proposal
from .rag_service import knowledge_base

CATALOG_PATH=Path(__file__).parent.joinpath("knowledge/pricing.json")

def _catalog()->dict:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))

def create_quote(db:Session,lead:Lead,package_code:str,discount_percent:int=0)->Quote:
    catalog=_catalog();package=catalog["packages"][package_code]
    line_items=[{"name":item["name"],"quantity":1,"unit_price":item["price"],"total":item["price"]} for item in package["items"]]
    subtotal=sum(x["total"] for x in line_items);total=round(subtotal*(100-discount_percent)/100)
    quote=Quote(lead_id=lead.id,quote_number=f"JULU-Q-{datetime.now(timezone.utc):%Y%m%d}-{secrets.token_hex(3).upper()}",package_code=package_code,currency=settings.quote_currency,subtotal=subtotal,discount_percent=discount_percent,total=total,line_items=line_items,assumptions=catalog["assumptions"],status="Draft",valid_until=datetime.now(timezone.utc)+timedelta(days=settings.quote_valid_days))
    db.add(quote);db.flush();return quote

def _profile(lead:Lead)->dict:
    p=lead.profile
    return {k:getattr(p,k,None) for k in ["target_market","current_acquisition","target_platforms","target_result","pain_points","budget_range","timeline","decision_role"]}

def create_proposal(db:Session,lead:Lead,language:str="zh-CN",quote:Quote|None=None)->Proposal:
    profile=_profile(lead);query=" ".join(str(x) for x in [lead.industry,lead.interested_service,*profile.values()] if x)
    context,refs=knowledge_base.context(query)
    amount=f"{quote.currency} {quote.total:,}" if quote else "待顾问确认"
    if language=="en-US":
        title=f"AI Visibility Growth Proposal for {lead.company}"
        content=f"""# {title}

## Executive summary
{lead.company} is evaluating {lead.interested_service}. This draft converts the verified discovery facts into a reviewable delivery plan.

## Confirmed needs
- Target market: {profile.get('target_market') or 'To be confirmed'}
- Pain points: {profile.get('pain_points') or 'To be confirmed'}
- Timeline: {profile.get('timeline') or 'To be confirmed'}
- Target platforms: {profile.get('target_platforms') or 'To be confirmed'}

## Recommended scope
1. Baseline AI visibility and technical audit.
2. GEO content and landing-page priorities.
3. Distribution, monitoring and monthly optimization.
4. Measurement dashboard and sales handoff workflow.

## Draft commercial estimate
{amount}. This is a non-binding draft and becomes valid only after human approval.

## Knowledge basis
{context or 'No matching knowledge chunk; human review required.'}
"""
    elif language=="es-ES":
        title=f"Propuesta de crecimiento de visibilidad IA para {lead.company}"
        content=f"""# {title}

## Resumen
{lead.company} está evaluando {lead.interested_service}. Este borrador usa únicamente los datos confirmados durante la conversación.

## Necesidades confirmadas
- Mercado objetivo: {profile.get('target_market') or 'Por confirmar'}
- Problemas: {profile.get('pain_points') or 'Por confirmar'}
- Plazo: {profile.get('timeline') or 'Por confirmar'}

## Alcance recomendado
1. Auditoría de visibilidad y técnica.
2. Contenido GEO y páginas de destino.
3. Distribución, medición y optimización.
4. Traspaso al equipo comercial.

## Estimación
{amount}. Borrador no vinculante sujeto a aprobación humana.

## Base de conocimiento
{context or 'Sin fragmentos coincidentes; requiere revisión humana.'}
"""
    else:
        title=f"{lead.company} AI 可见度增长方案"
        content=f"""# {title}

## 项目摘要
{lead.company} 正在评估“{lead.interested_service}”。本方案仅使用沟通中确认的客户事实生成，未确认信息会明确标注。

## 已确认需求
- 目标市场：{profile.get('target_market') or '待确认'}
- 当前痛点：{profile.get('pain_points') or '待确认'}
- 启动时间：{profile.get('timeline') or '待确认'}
- 目标平台：{profile.get('target_platforms') or '待确认'}

## 建议范围
1. AI 可见度基线与技术审计。
2. GEO 内容及落地页优先级设计。
3. 内容分发、监测与月度优化。
4. 数据看板、线索跟进及销售交接。

## 报价草案
{amount}。该金额仅为系统草案，必须经销售人员审批后才可对外使用。

## 知识依据
{context or '没有检索到匹配知识片段，需要人工复核。'}
"""
    proposal=Proposal(lead_id=lead.id,quote_id=quote.id if quote else None,proposal_number=f"JULU-P-{datetime.now(timezone.utc):%Y%m%d}-{secrets.token_hex(3).upper()}",language=language,title=title,content_markdown=content,knowledge_refs=refs,status="Draft")
    db.add(proposal);db.flush();return proposal