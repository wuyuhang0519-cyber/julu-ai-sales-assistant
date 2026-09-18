import hashlib
import math
import re
from dataclasses import dataclass
from pathlib import Path
from .config import settings

@dataclass(frozen=True)
class KnowledgeChunk:
    ref: str
    title: str
    text: str
    source: str
    vector: dict[int,float]

def detect_language(text:str)->str:
    lowered=text.lower()
    if re.search(r"[\u4e00-\u9fff]",text):return "zh-CN"
    if any(x in lowered for x in ["hola","gracias","empresa","precio","mercado","necesito"]):return "es-ES"
    return "en-US"

def _tokens(text:str)->list[str]:
    words=re.findall(r"[a-z0-9][a-z0-9_-]+",text.lower())
    han="".join(re.findall(r"[\u4e00-\u9fff]",text))
    words.extend(han[i:i+2] for i in range(max(0,len(han)-1)))
    words.extend(re.findall(r"[\u4e00-\u9fff]",text))
    return words

def _vector(text:str,size:int=512)->dict[int,float]:
    counts:dict[int,float]={}
    for token in _tokens(text):
        idx=int.from_bytes(hashlib.sha256(token.encode("utf-8")).digest()[:4],"big")%size
        counts[idx]=counts.get(idx,0.0)+1.0
    norm=math.sqrt(sum(v*v for v in counts.values())) or 1.0
    return {k:v/norm for k,v in counts.items()}

def _cosine(a:dict[int,float],b:dict[int,float])->float:
    if len(a)>len(b):a,b=b,a
    return sum(v*b.get(k,0.0) for k,v in a.items())

class KnowledgeBase:
    def __init__(self,root:Path|None=None):
        self.root=root or Path(__file__).parent.joinpath("knowledge")
        self._chunks:list[KnowledgeChunk]=[]
        self.reload()

    def reload(self):
        chunks:list[KnowledgeChunk]=[]
        for path in sorted(self.root.glob("*.md")):
            text=path.read_text(encoding="utf-8")
            sections=re.split(r"(?m)^##+\s+",text)
            for index,section in enumerate(sections):
                section=section.strip()
                if not section:continue
                lines=section.splitlines()
                title=lines[0].strip("# ").strip() if index else path.stem
                body="\n".join(lines[1:] if index else lines).strip()
                if not body:continue
                ref=f"KB-{path.stem.upper()}-{index+1:03d}"
                chunks.append(KnowledgeChunk(ref,title,body,path.name,_vector(f"{title}\n{body}")))
        self._chunks=chunks

    def search(self,query:str,top_k:int|None=None)->list[dict]:
        qv=_vector(query);limit=top_k or settings.rag_top_k
        ranked=sorted(((c,_cosine(qv,c.vector)) for c in self._chunks),key=lambda x:x[1],reverse=True)
        return [{"ref":c.ref,"title":c.title,"text":c.text,"source":c.source,"score":round(score,4)} for c,score in ranked[:limit] if score>=settings.rag_min_score]

    def context(self,query:str,top_k:int|None=None)->tuple[str,list[str]]:
        hits=self.search(query,top_k)
        context="\n\n".join(f"[{x['ref']}] {x['title']}\n{x['text']}" for x in hits)
        return context,[x["ref"] for x in hits]

knowledge_base=KnowledgeBase()