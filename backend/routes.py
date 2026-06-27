from fastapi import Depends, FastAPI, HTTPException, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import asynccontextmanager
from sqlmodel import SQLModel, Session, delete, select, Field, create_engine
from typing import Generic, Annotated, TypeVar
from pydantic import BaseModel

sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

# Engine instance
connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, connect_args=connect_args)


# Create the database
def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


# Create session for engine to interact with database
def get_session():
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]


# Create database on startup with test tables
@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


class Level(SQLModel, table=True):
    level_id: int | None = Field(default=None, primary_key=True)
    level_name: str | None
    creator: str | None
    first_victor: str | None
    completion_link: str | None
    
class LevelCreate(SQLModel):
    level_name: str
    creator: str
    first_victor: str
    completion_link: str

# Generic Response Model
T = TypeVar("T")
class ResponseModel(BaseModel, Generic[T]):
    data: T

app = FastAPI(root_path="/api/v1", lifespan=lifespan)

@app.get("/")
def root():
    return {"Status: Nox List API is currently active!"}


@app.get("/levels", response_model=ResponseModel[list[Level]])
def read_levels(session : SessionDep):
    
    all_levels = session.exec(
        select(Level).order_by(Level.level_id) # type: ignore
        ).all()
    print(all_levels)
    
    try:
        return {"data": all_levels}
    except:
        raise HTTPException(status_code=404, detail="There are no levels to display")
    
@app.post("/levels", response_model=Level)
def create_level(level_id: int, level: LevelCreate, session: SessionDep):
        level_add = Level.model_validate(level)
        session.add(level_add)
        session.commit()
        session.refresh(level_add)
        
        return {"data" : level_add}
    
@app.patch("/levels?id=", response_model=ResponseModel[Level])
def update_level(level: Level, session: SessionDep):
    updated_level = session.get(Level, Level.level_id)
    return ""
    