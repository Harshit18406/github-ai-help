import hashlib
import math
import re
from app.core.config import settings

class HashEmbeddingProvider:
    """Deterministic local fallback. Swap with OpenAI/CodeBERT for stronger semantic embeddings."""
    def embed(self, text: str) -> list[float]:
        dim=settings.embedding_dim
        vec=[0.0]*dim
        for tok in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", text.lower()):
            h=int(hashlib.sha256(tok.encode()).hexdigest(),16)
            idx=h%dim; sign=1.0 if (h>>8)&1 else -1.0
            vec[idx]+=sign
        norm=math.sqrt(sum(x*x for x in vec)) or 1.0
        return [x/norm for x in vec]

def cosine(a:list[float], b:list[float])->float:
    return sum(x*y for x,y in zip(a,b))
