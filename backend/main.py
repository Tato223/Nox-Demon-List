from fastapi import Depends, FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import asynccontextmanager
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import SQLModel, Session, delete, select, create_engine, col
from typing import Annotated, Sequence
from pydantic import ValidationError

from modules.response_models import ResponseModel, LevelCreate, UserCreate, UserResponse
from modules.tables import Level, User

import bcrypt

# TODO

# Priorites:
# Refactor helper functions to apply to multiple tables
# Organize login into different folders (response models, auth, different endpoints)
# Learn how to implement Oauth2 and JWT
# Create login endpoints

# Later on:
# Implement leaderboard logic
# Migrate to PostgreSQL for easier deployment

# ---------- SQLModel SETUP ---------- #

sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, connect_args=connect_args)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


# ---------- API CONFIG ---------- #

app = FastAPI(root_path="/api/v1", lifespan=lifespan)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

origins = ["*"]  # All origins for now

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- API ENDPOINTS ---------- #


@app.get("/")
async def root():
    return {"Status": "Nox List API is currently active!"}


@app.get("/levels", response_model=ResponseModel[list[Level]])
async def read_all_levels(session: SessionDep, limit=Query(default=50)):

    try:
        all_levels = get_all_levels(session, limit)
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


# token: str = Depends(oauth2_scheme) -- readd later
@app.post("/levels", response_model=ResponseModel[Level], status_code=201)
async def create_level(level: LevelCreate, session: SessionDep):

    try:

        # Find the lowest level on the list
        lowest_level = get_lowest_level(session)

        # Add to the bottom if position is not given
        if level.list_position is None and lowest_level:
            level.list_position = lowest_level.list_position + 1

        new_level_model = Level.model_validate(
            level, update={"list_position": level.list_position}
        )

        # Check if a level already exists at the new position
        level_at_pos = get_level_by_pos(session, new_level_model.list_position)

        if level_at_pos:

            affected_levels = get_affected_levels_post(
                session=session, pos=new_level_model.list_position
            )

            shift_down_levels(
                session=session,
                affected_levels=affected_levels,
            )

        session.add(new_level_model)
        save_changes(session, new_level_model)

        return {"data": new_level_model}

    except ValidationError:
        raise HTTPException(status_code=400, detail="Invalid level data provided.")


# token: str = Depends(oauth2_scheme) -- readd later
@app.patch("/levels/{level_id}", response_model=ResponseModel[Level])
async def update_level_pos(
    session: SessionDep, level_id: int, new_pos: int = Query(ge=1, le=1000)
):

    this_level = get_level_by_id(session, level_id)

    if this_level is None:
        raise HTTPException(
            status_code=404, detail=f"Level with ID {level_id} not found!"
        )

    pos = this_level.list_position

    if new_pos == this_level.list_position:
        raise HTTPException(
            status_code=400, detail="New position is the same as the current position."
        )

    # Sets position to -1 temporarily to avoid unique constraint violation
    this_level.list_position = -1
    session.flush()

    # level moved up
    if new_pos < pos:
        affected_levels = get_affected_levels_reorder(
            session, pos, new_pos, move_levels_up=True
        )
        shift_down_levels(session, affected_levels)

    # Level moved down
    elif new_pos > pos:
        affected_levels = get_affected_levels_reorder(
            session, pos, new_pos, move_levels_up=False
        )
        shift_up_levels(session, affected_levels)

    this_level.list_position = new_pos
    save_changes(session, this_level)

    return {"data": this_level}


@app.delete("/levels/{level_id}")
async def delete_level_at_id(
    session: SessionDep, level_id: int, token: str = Depends(oauth2_scheme)
):
    this_level = get_level_by_id(session, level_id)

    if not this_level:
        raise HTTPException(
            status_code=404, detail=f"Level with id {level_id} not found!"
        )

    original_pos = this_level.list_position
    this_level.list_position = -1

    affected_levels = session.exec(
        select(Level)
        .where(Level.list_position > original_pos)
        .order_by(col(Level.list_position).desc())
    ).all()

    shift_up_levels(session, affected_levels)

    session.delete(this_level)
    session.commit()

    return Response(status_code=204)


@app.delete("/levels")
async def delete_all_levels(session: SessionDep, token: str = Depends(oauth2_scheme)):
    session.exec(delete(Level))
    session.commit()

    return Response(status_code=204)


@app.post("/register", status_code=201)
async def register_user(session: SessionDep, user: UserCreate):

    user_password_input = user.password
    hashed_password = hash_password(password=user_password_input)

    user_in_db = session.exec(
        select(User).where(User.username == user.username)
    ).first()

    if user_in_db is not None:
        raise HTTPException(status_code=200, detail="User already exists!")

    db_user = User.model_validate(user, update={"hashed_password": hashed_password})
    session.add(db_user)
    session.commit()


@app.post("/auth", status_code=200)
async def authenticate_user(session: SessionDep, user: UserCreate):

    user_in_db = session.exec(
        select(User).where(User.username == user.username)
    ).first()

    if user_in_db is None:
        raise HTTPException(status_code=404, detail="Username not found!")

    input_password = user.password

    if not verify_password(input_password, user_in_db.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect username or password!")
    
    # Provide JWT Token


@app.get("/users", response_model=ResponseModel[list[User]])
async def read_all_users(session: SessionDep):

    all_users = session.exec(select(User)).all()

    if all_users == []:
        raise HTTPException(404)

    return {"data": all_users}


@app.put("/users{user_id}", response_model=ResponseModel[UserResponse])
async def update_user(session: SessionDep, user: UserCreate, user_id: int):

    this_user = session.get(User, User.user_id)
    if this_user is not None:
        return {"data": this_user}

    else:
        raise HTTPException(
            status_code=404, detail=f"User with ID {user_id} not found!"
        )


@app.delete("/users", status_code=204)
async def delete_user_at_id(session: SessionDep, user_id: int):

    this_user = session.exec(select(User).where(User.user_id == user_id)).first()

    if this_user is not None:
        session.delete(this_user)
        session.commit()

    else:
        raise HTTPException(404, "User not found!")


# ---------- HELPER FUNCTIONS ---------- #


def hash_password(password: str) -> bytes:
    password_bytes = password.encode("utf-8")
    password_salt = bcrypt.gensalt(12)
    hashed_password = bcrypt.hashpw(password_bytes, password_salt)
    return hashed_password


def verify_password(input_pw: str, stored_pw: str) -> bool:
    stored_pw_bytes = stored_pw.encode("utf-8")
    input_pw_bytes = input_pw.encode("utf-8")
    return bcrypt.checkpw(input_pw_bytes, stored_pw_bytes)


def get_level_by_pos(session: SessionDep, pos: int):
    this_level = session.exec(select(Level).where(Level.list_position == pos)).first()
    return this_level


def get_level_by_id(session: SessionDep, level_id: int):
    this_level = session.get(Level, level_id)
    return this_level


def get_all_levels(session: SessionDep, limit):
    all_levels = session.exec(
        select(Level)
        .where(Level.list_position <= limit)
        .order_by(col(Level.list_position))
    ).all()
    return all_levels


def get_lowest_level(session: SessionDep) -> Level | None:
    lowest_level = session.exec(
        select(Level).order_by(col(Level.list_position).desc())
    ).first()
    return lowest_level


# Grabs all levels that will be affected by the position change when creating a new level
def get_affected_levels_post(session: SessionDep, pos: int):

    affected_levels = session.exec(
        select(Level)
        .where(Level.list_position >= pos)
        .order_by(col(Level.list_position).desc())
    ).all()

    return affected_levels


# Affected levels between new and old position, for reordering existing levels
def get_affected_levels_reorder(
    session: SessionDep, pos: int, new_pos: int, move_levels_up: bool
):

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


# Finds all levels above the new position and shifts each level down the list by 1
# sets the new level's position to the new position
def shift_down_levels(session: SessionDep, affected_levels: Sequence[Level]):

    for lev in affected_levels:
        lev.list_position += 1
        session.flush()


# Finds all levels between the new position and the current position
# shifts each level up the list by 1 before setting the new level's position to the new position
def shift_up_levels(session: SessionDep, affected_levels: Sequence[Level]):

    for lev in affected_levels:
        lev.list_position -= 1
        session.flush()


# Commit and refresh session
def save_changes(session: SessionDep, level: Level):
    session.commit()
    session.refresh(level)
    return level
