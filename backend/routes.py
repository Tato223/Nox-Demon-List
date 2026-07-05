from fastapi import Depends, FastAPI, HTTPException, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import asynccontextmanager
from sqlmodel import SQLModel, Session, delete, select, Field, create_engine, col
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

# Represents each Level in the list
class Level(SQLModel, table=True):
    level_id: int | None = Field(default=None, primary_key=True)
    level_name: str
    creator: str
    first_victor: str
    completion_link: str
    list_position: int = Field(unique=True)

# Response model for creating a new level, no ID field
class LevelCreate(SQLModel):
    level_name: str
    creator: str
    first_victor: str
    completion_link: str
    list_position: int = Field(unique=True)


# Generic Response Model
T = TypeVar("T")
class ResponseModel(BaseModel, Generic[T]):
    data: T


app = FastAPI(root_path="/api/v1", lifespan=lifespan)


# URLs for frontend & backend test servers
origins = ["http://127.0.0.1:8000", "http://127.0.0.1:5500"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"Status: Nox List API is currently active!"}


@app.get("/levels", response_model=ResponseModel[list[Level]])
async def read_all_levels(session: SessionDep):

    try:
        all_levels = get_all_levels(session)
        return {"data": all_levels}

    except:
        raise HTTPException(status_code=404, detail="There are no levels to display")


@app.get("/levels/{pos}", response_model=ResponseModel[Level])
async def read_level_at_pos(session: SessionDep, pos: int):

    try:

        this_level = get_level_by_pos(session, pos)
        return {"data": this_level}

    except:
        raise HTTPException(status_code=404, detail=f"Level with ID {id} not found!")


@app.post("/levels/", response_model=ResponseModel[LevelCreate])
async def create_level(level: LevelCreate, session: SessionDep):

    try:
        new_level_model = Level.model_validate(level)

        all_levels = session.exec(
            select(Level)
            .where(Level.list_position >= new_level_model.list_position)
            .order_by(col(Level.list_position))  
        ).all()

        for lev in all_levels:
            lev.list_position += 1 
            
        all_levels = session.exec(select(Level).order_by(Level.list_position)).all()  # type: ignore

        session.add(new_level_model)
        session.commit()
        session.refresh(new_level_model)

        return {"data": new_level_model}
    except:
        print("Something went wrong.")


@app.patch("/levels/{pos}", response_model=ResponseModel[Level])
async def update_level_pos(session: SessionDep, pos: int, newPos: int):

    # Query database to find level at specificed position
    try:
        this_level = get_level_by_pos(session, pos)
    except:
        raise HTTPException(status_code=404)

    if newPos == pos:
        return {"data": this_level}

    this_level.list_position = -1
    session.flush()

    # level moved up
    if newPos < pos:
        affected = session.exec(
            select(Level)
            .where(Level.list_position >= newPos, Level.list_position < pos)
            .order_by(col(Level.list_position).desc())
        ).all()

        for lev in affected:
            lev.list_position += 1
            session.flush()

    # Level moved down
    elif newPos > pos:
        affected = session.exec(
            select(Level)
            .where(Level.list_position > pos, Level.list_position <= newPos)
            .order_by(col(Level.list_position).asc())
        ).all()

        for lev in affected:
            lev.list_position -= 1
            session.flush()

    this_level.list_position = newPos
    session.commit()
    session.refresh(this_level)
    return {"data": this_level}


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
    session.exec(delete(Level))


def get_level_by_pos(session: SessionDep, pos: int):
    this_level = session.exec(select(Level).where(Level.list_position == pos)).one()

    return this_level


def get_all_levels(session: SessionDep):
    all_levels = session.exec(select(Level).order_by(col(Level.list_position))).all()
    return all_levels
