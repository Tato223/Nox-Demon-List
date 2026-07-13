from sqlmodel import SQLModel, Field


class Level(SQLModel, table=True):
    level_id: int | None = Field(default=None, primary_key=True)
    level_name: str
    creator: str
    first_victor: str
    completion_link: str
    list_position: int = Field(unique=True, ge=1, le=1000)
    
class User(SQLModel, table=True):
    user_id: int | None = Field(default=None, primary_key=True)
    username: str = Field(unique=True)
    email: str = Field(unique=True)
    hashed_password: str
    is_active : bool = Field(default=False)