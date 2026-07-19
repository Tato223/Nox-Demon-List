from pydantic import BaseModel, Field
from typing import TypeVar, Generic
from sqlmodel import SQLModel

# ---------- User Models ---------- #

class UserResponse(BaseModel):
    username: str
    email: str | None
    is_active: bool | None = Field(default=True)
    
class UserUpdateUsername(BaseModel):
    username: str
    
class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    is_active: bool = Field(default=True)
    
class UserRead(BaseModel):
    user_id: int
    username: str
    email: str
    is_active: bool = Field(default=True)
    
class AccessTokenResponseModel(BaseModel):
    access_token: str
    token_type: str
    
# ---------- Level Models ---------- #

class LevelCreate(SQLModel):
    level_name: str
    creator: str
    first_victor: str
    completion_link: str
    list_position: int | None = Field(ge=1, le=1000)

# Generic Response Model
T = TypeVar("T")
class ResponseModel(BaseModel, Generic[T]):
    data: T