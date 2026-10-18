from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.orchestrator import AgentOrchestrator
from app.agents.providers import get_provider
from app.api.deps import current_user
from app.db.session import get_db
from app.ml.indexer import CodeIndexer
from app.models.agent import AgentRun
from app.models.conversation import Conversation, Message
from app.models.task import CodingTask
from app.models.user import User
from app.repositories.repository_repo import RepositoryRepository
from app.schemas.task import ApprovalRequest, RunOut


router = APIRouter()


@router.get("/activity")
def activity(
    limit: int = Query(default=20, ge=1, le=50),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    items: list[dict] = []

    tasks = list(
        db.scalars(
            select(CodingTask)
            .where(CodingTask.user_id == user.id)
            .order_by(CodingTask.id.desc())
            .limit(limit)
        )
    )
    for task in tasks:
        latest_run = max(task.runs, key=lambda item: item.id, default=None)
        items.append(
            {
                "kind": "task",
                "repo_id": task.repository_id,
                "repo_name": task.repository.name if task.repository else None,
                "title": task.prompt,
                "detail": f"Agent task · {task.status.replace('_', ' ')}",
                "run_id": latest_run.id if latest_run else None,
                "status": latest_run.status if latest_run else task.status,
                "created_at": task.created_at.isoformat() if task.created_at else None,
            }
        )

    question_messages = list(
        db.scalars(
            select(Message)
            .join(Conversation)
            .where(
                Conversation.user_id == user.id,
                Message.role == "user",
            )
            .order_by(Message.id.desc())
            .limit(limit)
        )
    )
    for message in question_messages:
        conversation = message.conversation
        items.append(
            {
                "kind": "question",
                "repo_id": conversation.repository_id,
                "repo_name": None,
                "title": message.content,
                "detail": "Repository question",
                "run_id": None,
                "status": "answered",
                "created_at": message.created_at.isoformat() if message.created_at else None,
            }
        )

    items.sort(key=lambda item: item.get("created_at") or "", reverse=True)
    return items[:limit]


@router.post("/tasks/{task_id}/run", response_model=RunOut)
def run(
    task_id: int,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    task = db.scalar(
        select(CodingTask).where(
            CodingTask.id == task_id,
            CodingTask.user_id == user.id,
        )
    )
    if not task:
        raise HTTPException(404, "Task not found")
    return AgentOrchestrator(db).start(task)


@router.post("/runs/{run_id}/approve", response_model=RunOut)
def approve(
    run_id: int,
    data: ApprovalRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    run_obj = db.scalar(
        select(AgentRun)
        .join(CodingTask)
        .where(
            AgentRun.id == run_id,
            CodingTask.user_id == user.id,
        )
    )
    if not run_obj:
        raise HTTPException(404, "Run not found")
    return AgentOrchestrator(db).approve_and_execute(run_obj, data.approved)


@router.get("/runs/{run_id}")
def get_run(
    run_id: int,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    run_obj = db.scalar(
        select(AgentRun)
        .join(CodingTask)
        .where(
            AgentRun.id == run_id,
            CodingTask.user_id == user.id,
        )
    )
    if not run_obj:
        raise HTTPException(404, "Run not found")
    return {
        "id": run_obj.id,
        "status": run_obj.status,
        "plan": run_obj.plan,
        "iteration": run_obj.iteration,
        "steps": [
            {
                "kind": step.kind,
                "detail": step.detail,
                "created_at": step.created_at.isoformat() if step.created_at else None,
            }
            for step in run_obj.steps
        ],
        "changes": [
            {
                "id": change.id,
                "file_path": change.file_path,
                "diff": change.diff,
                "approved": change.approved,
                "applied": change.applied,
            }
            for change in run_obj.changes
        ],
        "tests": [
            {
                "command": test.command,
                "exit_code": test.exit_code,
                "stdout": test.stdout,
                "stderr": test.stderr,
            }
            for test in run_obj.tests
        ],
    }


@router.get("/repositories/{repo_id}/runs")
def repo_runs(
    repo_id: int,
    limit: int = Query(default=10, ge=1, le=50),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if not RepositoryRepository(db).get_owned(repo_id, user.id):
        raise HTTPException(404, "Repository not found")

    runs = list(
        db.scalars(
            select(AgentRun)
            .join(CodingTask)
            .where(
                CodingTask.repository_id == repo_id,
                CodingTask.user_id == user.id,
            )
            .order_by(AgentRun.id.desc())
            .limit(limit)
        )
    )
    return [
        {
            "id": item.id,
            "task_id": item.task_id,
            "status": item.status,
            "plan": item.plan,
            "iteration": item.iteration,
            "created_at": item.created_at.isoformat() if item.created_at else None,
            "prompt": item.task.prompt,
        }
        for item in runs
    ]


@router.get("/repositories/{repo_id}/questions")
def question_history(
    repo_id: int,
    limit: int = Query(default=20, ge=1, le=50),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if not RepositoryRepository(db).get_owned(repo_id, user.id):
        raise HTTPException(404, "Repository not found")

    messages = list(
        db.scalars(
            select(Message)
            .join(Conversation)
            .where(
                Conversation.repository_id == repo_id,
                Conversation.user_id == user.id,
            )
            .order_by(Message.id.desc())
            .limit(limit * 2)
        )
    )
    return [
        {
            "id": message.id,
            "role": message.role,
            "content": message.content,
            "created_at": message.created_at.isoformat() if message.created_at else None,
        }
        for message in reversed(messages)
    ]


@router.get("/repositories/{repo_id}/ask")
def ask(
    repo_id: int,
    q: str = Query(min_length=2, max_length=4000),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    repo = RepositoryRepository(db).get_owned(repo_id, user.id)
    if not repo:
        raise HTTPException(404, "Repository not found")

    hits = CodeIndexer(db).search(repo_id, q, 4)
    if not hits:
        try:
            CodeIndexer(db).index(repo)
            hits = CodeIndexer(db).search(repo_id, q, 4)
        except Exception:
            hits = []

    context = [
        {
            "path": chunk.path,
            "symbol": chunk.symbol,
            "start_line": chunk.start_line,
            "end_line": chunk.end_line,
            "content": chunk.content,
        }
        for _, chunk in hits
    ]

    try:
        answer_text = get_provider().answer(q, context)
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"AI provider is temporarily unavailable: {exc}",
        ) from exc

    try:
        conversation = db.scalar(
            select(Conversation)
            .where(
                Conversation.user_id == user.id,
                Conversation.repository_id == repo_id,
            )
            .order_by(Conversation.id.desc())
        )
        if not conversation:
            conversation = Conversation(
                user_id=user.id,
                repository_id=repo_id,
                title="Repository Q&A",
            )
            db.add(conversation)
            db.flush()
        db.add(Message(conversation_id=conversation.id, role="user", content=q))
        db.add(Message(conversation_id=conversation.id, role="assistant", content=answer_text))
        db.commit()
    except Exception:
        db.rollback()

    return {
        "answer": answer_text,
        "sources": [
            {
                "path": chunk.path,
                "start_line": chunk.start_line,
                "end_line": chunk.end_line,
                "score": round(float(score), 4),
            }
            for score, chunk in hits
        ],
    }
