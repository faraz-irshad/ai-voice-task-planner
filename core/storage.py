from datetime import datetime
from typing import Optional, List
import os
import hashlib

from sqlmodel import SQLModel, Field, create_engine, Session, select
import json
from sqlalchemy.exc import IntegrityError

DB_URL = os.getenv("DB_URL", "sqlite:///planner.db")
engine = create_engine(DB_URL, echo=False, connect_args={"check_same_thread": False})

# Streamlit reloads can keep old metadata around; clear to avoid duplicate table errors.
SQLModel.metadata.clear()


class UserAccount(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    password_hash: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Plan(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="useraccount.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    title: str
    transcript: str
    tasks_json: str
    prioritized_json: str
    schedule_json: str
    blocks_json: str


def init_db():
    SQLModel.metadata.create_all(engine)
    _run_migrations()


def _run_migrations():
    """Lightweight, in-app migrations to keep SQLite schema aligned."""
    with engine.begin() as conn:
        columns = conn.exec_driver_sql("PRAGMA table_info('plan')").fetchall()
        column_names = {col[1] for col in columns}
        if "user_id" not in column_names:
            conn.exec_driver_sql('ALTER TABLE "plan" ADD COLUMN user_id INTEGER')
            conn.exec_driver_sql('UPDATE "plan" SET user_id = 1 WHERE user_id IS NULL')


def get_session():
    return Session(engine)


def create_user(username: str, password: str) -> Optional[dict]:
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    user = UserAccount(username=username, password_hash=password_hash)
    with get_session() as session:
        try:
            session.add(user)
            session.commit()
            session.refresh(user)
            return {"id": user.id, "username": user.username}
        except IntegrityError as exc:
            session.rollback()
            raise ValueError("Username already taken") from exc
        except Exception as exc:
            session.rollback()
            raise RuntimeError(f"Failed to create user: {exc}") from exc


def authenticate_user(username: str, password: str) -> Optional[dict]:
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    with get_session() as session:
        statement = select(UserAccount).where(UserAccount.username == username, UserAccount.password_hash == password_hash)
        user = session.exec(statement).first()
        if user:
            return {"id": user.id, "username": user.username}
        return None


def save_plan(
    user_id: int,
    title: Optional[str],
    transcript: str,
    tasks: list,
    prioritized: list,
    schedule: dict,
    blocks: dict,
) -> Plan:
    if not title:
        title = datetime.utcnow().strftime("Plan %Y-%m-%d %H:%M")
    plan = Plan(
        user_id=user_id,
        title=title,
        transcript=transcript or "",
        tasks_json=json.dumps(tasks),
        prioritized_json=json.dumps(prioritized),
        schedule_json=json.dumps(schedule),
        blocks_json=json.dumps(blocks),
    )
    with get_session() as session:
        try:
            session.add(plan)
            session.commit()
            session.refresh(plan)
            return plan
        except Exception as exc:
            session.rollback()
            raise RuntimeError(f"Failed to save plan: {exc}") from exc


def list_plans(user_id: int, limit: int = 5) -> List[Plan]:
    with get_session() as session:
        try:
            statement = select(Plan).where(Plan.user_id == user_id).order_by(Plan.created_at.desc()).limit(limit)
            return list(session.exec(statement))
        except Exception as exc:
            raise RuntimeError(f"Failed to load plans: {exc}") from exc
