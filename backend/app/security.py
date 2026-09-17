import re, secrets, time
from collections import defaultdict, deque
from fastapi import HTTPException, Request
from .config import settings

SENSITIVE_KEYS={"authorization","cookie","api_key","token","password","secret","private_key"}
EMAIL_RE=re.compile(r"\b([A-Za-z0-9._%+-])[A-Za-z0-9._%+-]*(@[A-Za-z0-9.-]+\.[A-Za-z]{2,})\b")
PHONE_RE=re.compile(r"(?<!\d)(?:\+?\d[\d -]{7,}\d)(?!\d)")
TOKEN_RE=re.compile(r"(?i)(bearer\s+|sk-[A-Za-z0-9_-]{8,}|api[_-]?key[=: ]+)[A-Za-z0-9._-]+")

def redact_text(value:str|None)->str|None:
    if value is None:return None
    value=EMAIL_RE.sub(r"\1***\2",str(value)); value=PHONE_RE.sub("[PHONE_REDACTED]",value); value=TOKEN_RE.sub("[TOKEN_REDACTED]",value)
    return value[:4000]

def redact(value):
    if isinstance(value,dict): return {k:("[REDACTED]" if any(x in k.lower() for x in SENSITIVE_KEYS) else redact(v)) for k,v in value.items()}
    if isinstance(value,list): return [redact(x) for x in value]
    return redact_text(value) if isinstance(value,str) else value

def redact_email(email:str)->str:
    local,_,domain=email.partition("@")
    return f"{local[:1]}***@{domain}" if domain else "[REDACTED]"

class LoginLimiter:
    def __init__(self): self.attempts=defaultdict(deque)
    def check(self,key:str):
        now=time.time(); q=self.attempts[key]
        while q and now-q[0]>300:q.popleft()
        if len(q)>=5: raise HTTPException(429,detail={"code":"login_rate_limited","message":"登录失败次数过多，请稍后重试"})
    def fail(self,key:str): self.attempts[key].append(time.time())
    def clear(self,key:str): self.attempts.pop(key,None)

login_limiter=LoginLimiter()

def csrf_token()->str:return secrets.token_urlsafe(32)

def require_csrf(request:Request):
    if not settings.csrf_enabled or request.method in {"GET","HEAD","OPTIONS"}:return
    cookie=request.cookies.get("julu_csrf"); header=request.headers.get("X-CSRF-Token")
    if not cookie or not header or not secrets.compare_digest(cookie,header):
        raise HTTPException(403,detail={"code":"csrf_failed","message":"安全校验失败，请刷新页面重试"})

