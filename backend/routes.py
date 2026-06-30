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
    list_position: int | None = Field(default=1, ge=1, unique=True)


class LevelCreate(SQLModel):
    level_name: str | None
    creator: str | None
    first_victor: str | None
    completion_link: str | None
    list_position: int | None =  Field(default=1, ge=1, unique=True)


# Generic Response Model
T = TypeVar("T")


class ResponseModel(BaseModel, Generic[T]):
    data: T


app = FastAPI(root_path="/api/v1", lifespan=lifespan)


@app.get("/")
async def root():
    return {"Status: Nox List API is currently active!"}


@app.get("/levels", response_model=ResponseModel[list[Level]])
async def read_levels(session: SessionDep):

    try:

        all_levels = session.exec(
            select(Level).order_by(Level.list_position)  # type: ignore
        ).all()
        print(all_levels)

        return {"data": all_levels}

    except:
        raise HTTPException(status_code=404, detail="There are no levels to display")


@app.post("/levels/", response_model=ResponseModel[LevelCreate])
async def create_level(level: LevelCreate, session: SessionDep):

    try:
        level_add = Level.model_validate(level)

        all_levels = session.exec(
            select(Level)
            .where(Level.list_position >= level_add.list_position)
            .order_by(Level.list_position.desc())  # type: ignore
        ).all()

        for lev in all_levels:
            lev.list_position += 1  # pyright: ignore[reportGeneralTypeIssues, reportAttributeAccessIssue]

        all_levels = session.exec(select(Level).order_by(Level.list_position)).all() # type: ignore

        session.add(level_add)
        session.commit()
        session.refresh(level_add)

        return {"data": level_add}
    except:
        print("Something went wrong.")


@app.get("/levels/{pos}", response_model=ResponseModel[Level])
async def read_level_at_id(session: SessionDep, pos: int):

    try:

        this_level = session.exec(select(Level).where(Level.list_position == pos)).first()

        return {"data": this_level}

    except:
        raise HTTPException(status_code=404, detail=f"Level with ID {id} not found!")


@app.delete("/levels/{id}", response_model=ResponseModel[list[Level]])
async def delete_level_at_id(session: SessionDep, id: int):

    try:
        this_level = session.get(Level, id)
        session.delete(this_level)
        session.commit()

        all_levels = session.exec(select(Level)).all()

        return {"data": all_levels}

    except:
        raise HTTPException(status_code=404, detail=f"Level with ID {id} not found!")


@app.delete("/levels/", response_model=ResponseModel[list[Level]])
async def delete_all_levels(session: SessionDep):

    all_tasks = session.exec(select(Level)).all()

    for lev in all_tasks:
        session.delete(lev)

        session.commit()
        session.refresh(Level)

    return {"data": all_tasks}