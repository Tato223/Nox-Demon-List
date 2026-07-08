from fastapi import Depends, FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import asynccontextmanager
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import SQLModel, Session, delete, select, Field, create_engine, col
from typing import Generic, Annotated, Sequence, TypeVar
from pydantic import BaseModel, ValidationError

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
    list_position: int = Field(unique=True, ge=1, le=1000)


# Response model for creating a new level, no ID field
class LevelCreate(SQLModel):
    level_name: str
    creator: str
    first_victor: str
    completion_link: str
    list_position: int = Field(ge=1, le=1000)


# Generic Response Model
T = TypeVar("T")


class ResponseModel(BaseModel, Generic[T]):
    data: T


app = FastAPI(root_path="/api/v1", lifespan=lifespan)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


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
    return {"Status": "Nox List API is currently active!"}


@app.get("/levels", response_model=ResponseModel[list[Level]])
async def read_all_levels(session: SessionDep):

    try:
        all_levels = get_all_levels(session)
        return {"data": all_levels}

    except:
        raise HTTPException(status_code=404, detail="There are no levels to display")


@app.get("/levels/{level_id}", response_model=ResponseModel[Level])
async def read_level_at_id(session: SessionDep, level_id: int):

    try:

        this_level = get_level_by_id(session, level_id)
        return {"data": this_level}

    except:
        raise HTTPException(
            status_code=404, detail=f"Level with ID {level_id} not found!"
        )


@app.get("/levels/pos/{pos}", response_model=ResponseModel[Level])
async def read_level_at_pos(session: SessionDep, pos: int):

    this_level = get_level_by_pos(session, pos)
    if this_level is None:
        raise HTTPException(
            status_code=404, detail=f"Level at position {pos} not found!"
        )

    return {"data": this_level}


@app.post("/levels", response_model=ResponseModel[Level], status_code=201)
async def create_level(
    level: LevelCreate, session: SessionDep, token: str = Depends(oauth2_scheme)
):

    try:
        new_level_model = Level.model_validate(level)

        # Check if a level already exists at the new position
        level_at_pos = session.exec(
            select(Level).where(Level.list_position == new_level_model.list_position)
        ).first()

        if level_at_pos:
            affected_levels = get_affected_levels_post(
                session=session, pos=new_level_model.list_position, move_levels_up=True
            )
            shift_down_levels(
                session=session,
                new_pos=new_level_model.list_position,
                affected_levels=affected_levels,
            )

        save_changes(session, new_level_model)

        return {"data": new_level_model}

    except ValidationError:
        raise HTTPException(status_code=400, detail="Invalid level data provided.")


@app.patch("/levels/{level_id}", response_model=ResponseModel[Level])
async def update_level_pos(
    session: SessionDep,
    level_id: int,
    new_pos: int = Query(ge=1, le=1000),
    token: str = Depends(oauth2_scheme),
):

    this_level = get_level_by_id(session, level_id)
    pos = this_level.list_position
    
    if this_level is None:
        raise HTTPException(
            status_code=404, detail=f"Level with ID {level_id} not found!"
        )

    if new_pos == this_level.list_position:
        raise HTTPException(
            status_code=400, detail="New position is the same as the current position."
        )


    # Sets position to -1 temporarily to avoid unique constraint violation
    this_level.list_position = -1
    session.flush()

    # level moved up
    if new_pos < pos:
        affected_levels = get_affected_levels_reorder(session, pos, new_pos, move_levels_up=True)
        shift_down_levels(session, new_pos, affected_levels)

    # Level moved down
    elif new_pos > pos:
        affected_levels = get_affected_levels_reorder(session, pos, new_pos, move_levels_up=False)
        shift_up_levels(session, new_pos, affected_levels)

    this_level.list_position = new_pos
    save_changes(session, this_level)

    return {"data": this_level}


@app.delete("/levels/{level_id}")
async def delete_level_at_id(
    session: SessionDep, level_id: int, token: str = Depends(oauth2_scheme)
):
    this_level = get_level_by_id(session, level_id)
    
    original_pos = this_level.list_position
    this_level.list_position = -1

    affected_levels = session.exec(
        select(Level)
        .where(Level.list_position > original_pos)
        .order_by(col(Level.list_position))
    ).all()
    
    for lev in affected_levels:
        lev.list_position -= 1
        session.flush()
        
    session.delete(this_level)
    session.commit()
    
    return Response(status_code=204)


@app.delete("/levels")
async def delete_all_levels(session: SessionDep, token: str = Depends(oauth2_scheme)):
    session.exec(delete(Level))
    session.commit()
    
    return Response(status_code=204)


# ---------- HELPER FUNCTIONS ----------


def get_level_by_pos(session: SessionDep, pos: int):
    this_level = session.exec(select(Level).where(Level.list_position == pos)).first()
    if this_level is None:
        raise HTTPException(
            status_code=404, detail=f"Level at position {pos} not found!"
        )
    return this_level


def get_level_by_id(session: SessionDep, level_id: int):
    this_level = session.get(Level, level_id)
    if this_level is None:
        raise HTTPException(
            status_code=404, detail=f"Level with ID {level_id} not found!"
        )
    return this_level


def get_all_levels(session: SessionDep):
    all_levels = session.exec(select(Level).order_by(col(Level.list_position))).all()
    return all_levels


# Grabs all levels that will be affected by the position change when creating a new level
def get_affected_levels_post(session: SessionDep, pos: int, move_levels_up: bool):

    if move_levels_up:
        affected_levels = session.exec(
            select(Level)
            .where(Level.list_position >= pos)
            .order_by(col(Level.list_position))
        ).all()

    else:
        affected_levels = session.exec(
            select(Level)
            .where(Level.list_position <= pos)
            .order_by(col(Level.list_position).desc())
        ).all()

    return affected_levels

# Affected levels between new and old position, for reordering existing levels
def get_affected_levels_reorder(session: SessionDep, pos: int, new_pos: int, move_levels_up: bool):

    if move_levels_up:
        affected_levels = session.exec(
            select(Level)
            .where(Level.list_position >= new_pos, Level.list_position < pos)
            .order_by(col(Level.list_position))
        ).all()

    else:
        affected_levels = session.exec(
            select(Level)
            .where(Level.list_position <= new_pos, Level.list_position > pos)
            .order_by(col(Level.list_position).desc())
        ).all()

    return affected_levels

# Finds all levels above the new position and lowers their position by 1
# sets the new level's position to the new position
def shift_down_levels(
    session: SessionDep, new_pos: int, affected_levels: Sequence[Level]
):

    for lev in affected_levels:
        lev.list_position += 1
        session.flush()


# Finds all levels between the new position and the current position
# raises their position by 1 before setting the new level's position to the new position
def shift_up_levels(
    session: SessionDep, new_pos: int, affected_levels: Sequence[Level]
):

    for lev in affected_levels:
        lev.list_position -= 1
        session.flush()


# Commit and refresh session
def save_changes(session: SessionDep, level: Level):
    session.commit()
    session.refresh(level)
    return level
