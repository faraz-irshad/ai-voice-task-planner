from datetime import datetime
from typing import Optional, List
import os
import hashlib

from sqlmodel import SQLModel, Field, create_engine, Session, select
import json

DB_URL = os.getenv("DB_URL", "sqlite:///planner.db")
engine = create_engine(DB_URL, echo=False, connect_args={"check_same_thread": False})


class UserAccount(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    password_hash: str


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
        except:
            return None


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
        session.add(plan)
        session.commit()
        session.refresh(plan)
        return plan


def list_plans(user_id: int, limit: int = 5) -> List[Plan]:
    with get_session() as session:
        statement = select(Plan).where(Plan.user_id == user_id).order_by(Plan.created_at.desc()).limit(limit)
        return list(session.exec(statement))
