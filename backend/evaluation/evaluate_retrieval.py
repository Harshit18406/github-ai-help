import json
import sys
from pathlib import Path
from app.db.session import SessionLocal
from app.ml.indexer import CodeIndexer


def evaluate(repo_id: int, benchmark_path: str, k: int = 5):
    data=json.loads(Path(benchmark_path).read_text())
    db=SessionLocal(); indexer=CodeIndexer(db)
    recalls=[]; reciprocal=[]
    for item in data:
        hits=indexer.search(repo_id,item['query'],k)
        paths=[c.path for _,c in hits]
        relevant=set(item['relevant_paths'])
        recalls.append(len(relevant.intersection(paths))/max(1,len(relevant)))
        rr=0.0
        for i,path in enumerate(paths,1):
            if path in relevant: rr=1/i; break
        reciprocal.append(rr)
        print(item['query'], '->', paths)
    print({'Recall@K':sum(recalls)/len(recalls),'MRR':sum(reciprocal)/len(reciprocal),'K':k})
    db.close()

if __name__=='__main__':
    if len(sys.argv)<3:
        raise SystemExit('usage: python evaluation/evaluate_retrieval.py <repo_id> <benchmark.json> [k]')
    evaluate(int(sys.argv[1]),sys.argv[2],int(sys.argv[3]) if len(sys.argv)>3 else 5)
