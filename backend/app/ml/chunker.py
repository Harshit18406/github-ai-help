from __future__ import annotations
import ast
from pathlib import Path
from dataclasses import dataclass, asdict

@dataclass
class Chunk:
    path: str
    language: str | None
    symbol: str | None
    start_line: int
    end_line: int
    content: str
    metadata: dict

LANG = {".py":"python", ".js":"javascript", ".ts":"typescript", ".tsx":"typescript", ".jsx":"javascript", ".java":"java", ".go":"go", ".rs":"rust", ".cpp":"cpp", ".c":"c"}

def python_chunks(path: str, source: str) -> list[Chunk]:
    lines = source.splitlines()
    try: tree = ast.parse(source)
    except SyntaxError: return [Chunk(path,"python",None,1,len(lines),source,{})]
    chunks=[]
    imports=[]
    for node in tree.body:
        if isinstance(node,(ast.Import,ast.ImportFrom)):
            imports.append(ast.get_source_segment(source,node) or "")
    for node in tree.body:
        if isinstance(node,(ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            start=node.lineno; end=getattr(node,"end_lineno",start)
            chunks.append(Chunk(path,"python",getattr(node,"name",None),start,end,"\n".join(lines[start-1:end]),{"imports":imports,"kind":type(node).__name__}))
    if not chunks: chunks.append(Chunk(path,"python",None,1,max(1,len(lines)),source,{"imports":imports}))
    return chunks

def chunk_file(path: str, source: str) -> list[Chunk]:
    suffix=Path(path).suffix.lower(); language=LANG.get(suffix)
    if language=="python": return python_chunks(path,source)
    lines=source.splitlines(); size=120
    return [Chunk(path,language,None,i+1,min(i+size,len(lines)),"\n".join(lines[i:i+size]),{"chunking":"line-window"}) for i in range(0,max(1,len(lines)),size)]
