from pydantic import BaseModel, Field

class TaskCreate(BaseModel):
    repository_id: int
    prompt: str = Field(min_length=3)

class TaskOut(BaseModel):
    id: int
    repository_id: int
    prompt: str
    status: str
    model_config = {"from_attributes": True}

class RunOut(BaseModel):
    id: int
    task_id: int
    status: str
    plan: str | None
    iteration: int
    model_config = {"from_attributes": True}

class ApprovalRequest(BaseModel):
    approved: bool
