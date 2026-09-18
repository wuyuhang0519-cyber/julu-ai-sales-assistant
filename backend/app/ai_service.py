import json,re,time,uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast
from pydantic import ValidationError
from openai import OpenAI
from .config import settings
from .schemas import AIResult, Action, Status
from .security import redact

PROMPT_VERSION="sales-qualification-v2.0.0"
FIELDS=["target_market","current_acquisition","current_seo_geo","target_platforms","target_result","pain_points","budget_range","timeline","decision_role","has_website"]

@dataclass
class AIExecution:
    result:AIResult|None;request_id:str;provider:str;model:str;latency_ms:int;validation_status:str;repair_attempts:int=0;input_tokens:int|None=None;output_tokens:int|None=None;error_type:str|None=None;response_summary:dict|None=None

def _dim(score,max_score,evidence):return {"score":score,"max_score":max_score,"evidence":evidence}
def _intent(score):return "High" if score>=70 else "Medium" if score>=40 else "Low"
def intent(score):return _intent(score)

def demo_result(lead,profile,message:str|None,first=False)->AIResult:
    text=(message or lead.initial_requirement or "").strip();low=text.lower();updates:dict[str, str|bool|None]={}
    patterns={"target_market":r"(欧美|欧洲|美国|北美|东南亚|中东|海外|国内)","current_acquisition":r"(google ads|广告|展会|自然搜索|转介绍|linkedin)","target_platforms":r"(chatgpt|google ai|gemini|perplexity|claude|豆包|deepseek)","timeline":r"([一二三四五六七八九十\d]+个?月|本季度|半年|尽快)","budget_range":r"((?:预算|大约|约)?\s*[\d一二三四五六七八九十]+\s*万(?:元)?|预算[^，。；]{0,16})","decision_role":r"(决策负责人|参与决策|创始人|老板|市场负责人|采购负责人)","pain_points":r"(广告成本[^，。；]*|线索少|获客贵|自然询盘[^，。；]*|没有询盘|排名低|看不到品牌)","target_result":r"(获得[^，。；]*询盘|提升[^，。；]*(?:可见度|曝光|排名)|精准获客|品牌推荐)"}
    for field,pattern in patterns.items():
        found=re.search(pattern,text,re.I)
        if found:updates[field]=found.group(0).strip()
    if lead.website:updates["has_website"]=True
    existing={f:getattr(profile,f,None) for f in FIELDS};facts={**{k:v for k,v in existing.items() if v not in (None,"")},**updates}
    blob=" ".join(filter(None,[lead.industry,lead.interested_service,lead.initial_requirement,text])).lower();vague=any(k in low for k in ["先了解","看看资料","刚开始","随便看看","想了解"]);fit=(10 if vague else 23) if any(k in blob for k in ["ai","geo","搜索","官网","智能体","b2b"]) else 8 if vague else 14;pain=22 if facts.get("pain_points") else (4 if vague else 14 if lead.initial_requirement else 6);urgency=18 if facts.get("timeline") else 2 if vague else 6;budget=13 if facts.get("budget_range") else 1 if vague else 3;influence=14 if facts.get("decision_role") else 2 if vague else 4
    breakdown={"业务匹配度":_dim(fit,25,[lead.interested_service,lead.industry]),"痛点明确度":_dim(pain,25,[str(facts.get("pain_points") or "暂无明确证据")]),"时间紧迫度":_dim(urgency,20,[str(facts.get("timeline") or "暂无时间证据")]),"预算可行性":_dim(budget,15,[str(facts.get("budget_range") or "暂无预算证据")]),"决策影响力":_dim(influence,15,[str(facts.get("decision_role") or "暂无角色证据")])};score=sum(x["score"] for x in breakdown.values());missing=[f for f in FIELDS if not facts.get(f)];refuse=any(k in low for k in ["不需要","不要联系","拒绝"]);pricing=any(k in low for k in ["合同","保证效果","排名第一","最低价格","报价承诺"])
    labels={"target_market":"主要目标市场","current_acquisition":"目前主要获客方式","current_seo_geo":"现有 SEO/GEO 基础","target_platforms":"希望覆盖的 AI 平台","target_result":"最希望达成的业务结果","pain_points":"当前最突出痛点","budget_range":"预算范围","timeline":"期望启动时间","decision_role":"决策参与角色","has_website":"是否已有官网"};question=labels[missing[0]] if missing else "下一步实施重点"
    action:Action; suggested:Status
    if refuse:score=5;breakdown={"业务匹配度":_dim(5,25,["客户明确拒绝"]),"痛点明确度":_dim(0,25,[]),"时间紧迫度":_dim(0,20,[]),"预算可行性":_dim(0,15,[]),"决策影响力":_dim(0,15,[])};action="close";suggested="Closed";offer=False;handoff=False;reply="了解，我会停止后续销售跟进。感谢你坦率说明，如未来需要再联系聚路 AI。"
    elif pricing:action="handoff_to_human";suggested="Contacted";offer=False;handoff=True;reply="这涉及具体报价、合同或效果承诺，需要由顾问结合范围确认。我已建议转人工跟进，不会在这里给出未经确认的承诺。"
    elif first:reply=f"{lead.name}，你好。我了解到 {lead.company} 所在的{lead.industry}行业正在关注“{lead.interested_service}”，目标是{lead.initial_requirement or '改善 AI 搜索中的品牌可见度'}。聚路 AI 可以从内容、技术与分发三个层面协助。为了先判断最合适的路径，想优先了解：{question}是什么？";action="continue_qualification";suggested="Contacted";offer=False;handoff=False
    elif score>=70 and sum(bool(facts.get(x)) for x in ["target_market","pain_points","budget_range","timeline","decision_role"])>=3:action="offer_meeting";suggested="Qualified";offer=True;handoff=False;reply="信息已经比较完整：目标市场、启动节奏和业务痛点都很明确。建议下一步由顾问做一次需求诊断，并梳理全球 AI 搜索优化与 GEO 落地页的优先级。你可以直接预约合适时间。"
    else:action="share_material" if "资料" in low else "continue_qualification";suggested="Nurture" if action=="share_material" else "Contacted";offer=False;handoff=False;reply=f"收到，这让我更清楚你们当前的情况。下一项最影响方案判断的是{question}，方便简单说明一下吗？"
    return AIResult(reply=reply,extracted_facts=updates,updated_profile=updates,missing_fields=missing,lead_score=score,intent=cast(Any,_intent(score)),score_breakdown=breakdown,score_reason="；".join(f"{k} {v['score']}/{v['max_score']}" for k,v in breakdown.items()),recommended_service="全球 AI 搜索优化 / GEO 落地页" if "国内" not in blob else "国内 AI 搜索优化",next_action=action,suggested_status=suggested,should_offer_meeting=offer,should_handoff=handoff,handoff_reason="涉及价格、合同或效果承诺" if pricing else None,conversation_summary=f"{lead.company} 正在评估 {lead.interested_service}；已识别 {len(facts)} 项需求信息。",question_reason=f"{question}是当前影响资格判断的最高优先级缺失信息",knowledge_refs=["KB-COMPANY-001","KB-ROUTING-001"],fact_sources={k:[] for k in updates})

def _prompt(lead,profile,messages,first):
    kb=Path(__file__).parent.joinpath("knowledge/company.md").read_text(encoding="utf-8")
    return f"""你是聚路 AI 销售资格判断助手。Prompt版本:{PROMPT_VERSION}。只依据知识库与客户证据，严禁虚构价格、案例、排名或合同承诺。每轮最多两个问题，不重复已知信息。首次接待必须个性化。输出事实来源消息ID、问题原因和知识引用。只输出符合JSON Schema的对象。
评分必须且只能包含五项：业务匹配度 max_score=25、痛点明确度 max_score=25、时间紧迫度 max_score=20、预算可行性 max_score=15、决策影响力 max_score=15。lead_score 必须等于五项 score 之和。证据不足不得高分。fact_sources 的每个值必须是原始消息整数 ID 数组，没有来源时使用空数组。
知识库:\n{kb}\n首次接待:{first}\n客户:{lead.name}/{lead.company}/{lead.industry}/{lead.country}/{lead.interested_service}/{lead.initial_requirement}/{lead.website}\nProfile:{json.dumps({f:getattr(profile,f,None) for f in FIELDS},ensure_ascii=False)}\n历史:{json.dumps([{"id":m.id,"role":m.role,"content":m.content} for m in messages[-12:]],ensure_ascii=False)}"""

def _extract_response(rsp):
    text=getattr(rsp,"output_text",None) or rsp.output[0].content[0].text;usage=getattr(rsp,"usage",None);return text,getattr(usage,"input_tokens",None),getattr(usage,"output_tokens",None)

def _extract_chat_response(rsp):
    text=rsp.choices[0].message.content or "";usage=getattr(rsp,"usage",None);return text,getattr(usage,"prompt_tokens",None),getattr(usage,"completion_tokens",None)

def _provider_settings():
    provider=settings.ai_provider.lower().strip()
    if provider=="deepseek":return provider,settings.deepseek_api_key,settings.deepseek_base_url,settings.deepseek_model
    if provider=="siliconflow":return provider,settings.siliconflow_api_key,settings.siliconflow_base_url,settings.siliconflow_model
    if provider=="openai":return provider,settings.openai_api_key,settings.openai_base_url or None,settings.openai_model
    return provider,"",None,""

def run_ai(lead,profile,messages,first=False)->AIExecution:
    rid=str(uuid.uuid4());start=time.perf_counter()
    if settings.demo_mode:
        result=demo_result(lead,profile,messages[-1].content if messages and messages[-1].role=="user" else None,first)
        return AIExecution(result,rid,"demo","demo-deterministic",int((time.perf_counter()-start)*1000),"Valid",response_summary=redact({"score":result.lead_score,"intent":result.intent,"action":result.next_action}))
    provider,api_key,base_url,model=_provider_settings()
    if provider not in {"openai","deepseek","siliconflow"}:return AIExecution(None,rid,provider,model,0,"Failed",error_type="unsupported_provider")
    if not api_key:return AIExecution(None,rid,provider,model,0,"Failed",error_type="missing_api_key")
    client=OpenAI(api_key=api_key,base_url=base_url,timeout=settings.ai_timeout_seconds,max_retries=settings.ai_max_retries);schema=AIResult.model_json_schema();prompt=_prompt(lead,profile,messages,first);raw="";repair=0
    try:
        for attempt in range(2):
            repair=attempt;instruction=prompt if attempt==0 else f"修复下面输出使其严格符合JSON Schema。只输出JSON。\nSchema:{json.dumps(schema,ensure_ascii=False)}\n原输出:{raw[:8000]}"
            if provider in {"deepseek","siliconflow"}:
                instruction=f"{instruction}\nJSON Schema:{json.dumps(schema,ensure_ascii=False)}"
                chat_rsp=client.chat.completions.create(model=model,messages=[{"role":"system","content":instruction},{"role":"user","content":"请完成销售判断，只输出一个有效的 JSON 对象。"}],response_format={"type":"json_object"},temperature=0)
                raw,it,ot=_extract_chat_response(chat_rsp)
            else:
                response_rsp=client.responses.create(model=model,input=[{"role":"system","content":instruction}],text={"format":{"type":"json_schema","name":"sales_decision","schema":schema,"strict":True}});raw,it,ot=_extract_response(response_rsp)
            try:
                result=AIResult.model_validate_json(raw);lat=int((time.perf_counter()-start)*1000)
                return AIExecution(result,rid,provider,model,lat,"Repaired" if attempt else "Valid",attempt,it,ot,response_summary=redact({"score":result.lead_score,"intent":result.intent,"action":result.next_action,"reply":result.reply[:160]}))
            except (ValidationError,json.JSONDecodeError):
                if attempt==1:raise
    except Exception as e:return AIExecution(None,rid,provider,model,int((time.perf_counter()-start)*1000),"Failed",repair_attempts=repair,error_type=type(e).__name__,response_summary=redact({"error":str(e)}))
    return AIExecution(None,rid,provider,model,int((time.perf_counter()-start)*1000),"Failed",error_type="unknown")
