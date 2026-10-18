from pydantic import BaseModel, Field

class RepositoryCreate(BaseModel):
    clone_url: str = Field(min_length=5)
    name: str | None = None

class RepositoryOut(BaseModel):
    id: int
    name: str
    clone_url: str
    default_branch: str
    model_config = {"from_attributes": True}

class FileNode(BaseModel):
    path: str
    name: str
    type: str

class FileContent(BaseModel):
    path: str
    content: str
