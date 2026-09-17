import json,os,sys,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
os.environ.setdefault("DATABASE_URL","sqlite:///./eval_julu.db");os.environ.setdefault("DEMO_MODE","true");os.environ.setdefault("ADMIN_USERNAME","admin");os.environ.setdefault("ADMIN_PASSWORD","eval-only");os.environ.setdefault("SESSION_SECRET","eval-only-session-secret-32-characters")
from fastapi.testclient import TestClient
from backend.app.database import Base,engine
from backend.app.main import app

Base.metadata.drop_all(engine);Base.metadata.create_all(engine);client=TestClient(app);cases=json.loads(Path(__file__).with_name("cases.json").read_text(encoding="utf-8"));results=[]
for case in cases:
    payload={"name":"评测客户","company":"评测企业","email":"eval@example.com","industry":"B2B 制造","country":"中国","interested_service":"全球 AI 搜索优化","initial_requirement":case["initial"]}
    response=client.post("/api/public/leads",json=payload,headers={"Idempotency-Key":f"eval-{case['id']}-{uuid.uuid4()}"});lead=response.json()["lead"];expected=case["expect"];passed=(not expected.get("intent") or lead["intent"]==expected["intent"]) and (not expected.get("status") or lead["status"]==expected["status"]) and lead["next_action"] in expected.get("actions",[lead["next_action"]]);results.append({"id":case["id"],"passed":passed,"actual":{"intent":lead["intent"],"status":lead["status"],"action":lead["next_action"]},"expected":expected})
report={"total":len(results),"passed":sum(x["passed"] for x in results),"results":results};Path(__file__).with_name("report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8");print(json.dumps(report,ensure_ascii=False,indent=2));sys.exit(0 if report["passed"]==report["total"] else 1)
