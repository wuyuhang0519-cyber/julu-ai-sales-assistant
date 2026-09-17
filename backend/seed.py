"""可重复 Demo 数据：python -m backend.seed"""
from fastapi.testclient import TestClient
from backend.app.main import app

client=TestClient(app)
scenarios=[
 ("seed-high",{"name":"陈经理","company":"华东工业设备","email":"chen@example.com","industry":"B2B 制造","country":"中国","website":"https://example.com","interested_service":"全球 AI 搜索优化","initial_requirement":"计划进入欧美市场，当前依靠 Google Ads，三个月启动，有初步预算，我参与决策，希望提升 ChatGPT 和 Google AI 可见度与询盘"}),
 ("seed-low",{"name":"周女士","company":"新芽设计工作室","email":"zhou@example.com","industry":"专业服务","country":"中国","interested_service":"GEO 官网及落地页建设","initial_requirement":"刚开始了解 GEO，目标、预算和启动时间还没确定，只想先看看资料"})]
for key,payload in scenarios:
    response=client.post("/api/public/leads",json=payload,headers={"Idempotency-Key":key})
    print(key,response.status_code,response.json().get("lead",{}).get("id"))

