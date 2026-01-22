import logging
import os
import httpx
from typing import List
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, WebSocket, WebSocketDisconnect
from sqlmodel import Session, select
import uvicorn

from .database import init_db, get_session
from .models import Experiment
from .schemas import ExperimentCreate, ExperimentRead
from .event_bus import event_bus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="VLMHyperBench Management Backend")

ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "http://host.docker.internal:8002")

@app.on_event("startup")
def on_startup():
    init_db()

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/experiments", response_model=ExperimentRead)
async def create_experiment(
    experiment_in: ExperimentCreate, 
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session)
):
    db_exp = Experiment(
        name=experiment_in.name,
        description=experiment_in.description,
        config=experiment_in.config
    )
    session.add(db_exp)
    session.commit()
    session.refresh(db_exp)
    
    # Запуск в оркестраторе (фоновая задача)
    background_tasks.add_task(run_in_orchestrator, db_exp)
    
    return db_exp

@app.get("/experiments", response_model=List[ExperimentRead])
async def list_experiments(session: Session = Depends(get_session)):
    experiments = session.exec(select(Experiment)).all()
    return experiments

@app.get("/experiments/{experiment_id}", response_model=ExperimentRead)
async def get_experiment(experiment_id: str, session: Session = Depends(get_session)):
    experiment = session.get(Experiment, experiment_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return experiment

@app.websocket("/ws/{experiment_id}")
async def websocket_endpoint(websocket: WebSocket, experiment_id: str):
    await websocket.accept()
    try:
        # Подписываемся на события конкретного эксперимента в Redis
        async for event in event_bus.subscribe(f"experiment:{experiment_id}"):
            await websocket.send_json(event)
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for experiment {experiment_id}")

async def run_in_orchestrator(experiment: Experiment):
    """Отправка задачи в Orchestrator Service."""
    async with httpx.AsyncClient() as client:
        try:
            logger.info(f"Triggering orchestrator for experiment {experiment.id}")
            # В реальности здесь будет проброс RunTask конфигов
            response = await client.post(
                f"{ORCHESTRATOR_URL}/run",
                json={"experiment_id": str(experiment.id), "config": experiment.config}
            )
            response.raise_for_status()
            logger.info(f"Orchestrator accepted experiment {experiment.id}")
        except Exception as e:
            logger.error(f"Failed to trigger orchestrator: {e}")
            # Здесь можно обновить статус эксперимента на FAILED в БД

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)