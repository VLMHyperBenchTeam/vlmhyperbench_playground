from typing import Optional, Dict, Any, List
from pydantic import BaseModel
import uuid
from datetime import datetime

class ExperimentCreate(BaseModel):
    name: str
    description: Optional[str] = None
    config: Dict[str, Any] # Будет валидироваться через ExperimentPlan позже

class ExperimentRead(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str]
    created_at: datetime
    status: str
    config: Dict[str, Any]
    results_summary: Optional[Dict[str, Any]]

    class Config:
        from_attributes = True