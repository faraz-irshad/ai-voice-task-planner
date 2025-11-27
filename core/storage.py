from datetime import datetime
from typing import Optional, List

from sqlmodel import SQLModel, Field, create_engine, Session, select
import json

DB_URL = "sqlite:///planner.db"
engine = create_engine(DB_URL, echo=False)


class Plan(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    title: str
    transcript: str
    tasks_json: str
    prioritized_json: str
    schedule_json: str
    blocks_json: str


def init_db():
    SQLModel.metadata.create_all(engine)


def save_plan(
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
        title=title,
        transcript=transcript or "",
        tasks_json=json.dumps(tasks),
        prioritized_json=json.dumps(prioritized),
        schedule_json=json.dumps(schedule),
        blocks_json=json.dumps(blocks),
    )
    with Session(engine) as session:
        session.add(plan)
        session.commit()
        session.refresh(plan)
        return plan


def list_plans(limit: int = 5) -> List[Plan]:
    with Session(engine) as session:
        statement = select(Plan).order_by(Plan.created_at.desc()).limit(limit)
        return list(session.exec(statement))
