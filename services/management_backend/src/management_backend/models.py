from datetime import datetime
from typing import Optional, Dict, Any
from sqlmodel import SQLModel, Field, JSON, Column
import uuid

class Experiment(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = "PENDING" # PENDING, RUNNING, COMPLETED, FAILED
    
    # Конфигурация эксперимента (ExperimentPlan)
    config: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    
    # Артефакты и результаты
    results_summary: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))

class TaskLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    experiment_id: uuid.UUID = Field(foreign_key="experiment.id")
    task_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    level: str
    message: str