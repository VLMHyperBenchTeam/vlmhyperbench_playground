import asyncio
import logging
import subprocess
import os
import json
import aiodocker
from fastapi import FastAPI, Body, HTTPException
import uvicorn
import redis.asyncio as redis
from orchestrator_core.orchestrator import AsyncBenchmarkOrchestrator
from orchestrator_core.event_bus import Event
from task_registry.manager import RegistryManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="VLMHyperBench Orchestrator Service")

class Bootstrapper:
    def __init__(self):
        self.docker = None
        self.orchestrator = None
        self.redis = None
        self.registry_manager = RegistryManager(root_dir="/workspace/vlmhyperbench/registries", run_mode="dev")

    async def init_docker(self):
        if self.docker is None:
            self.docker = aiodocker.Docker()

    async def run_compose(self):
        """Запуск docker-compose инфраструктуры."""
        logger.info("Starting infrastructure via docker-compose...")
        try:
            # Используем shell=True для простоты запуска в данном контексте
            process = subprocess.run(
                ["docker", "compose", "up", "-d"],
                capture_output=True,
                text=True,
                check=True
            )
            logger.info(f"Docker Compose output: {process.stdout}")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to start docker-compose: {e.stderr}")
            raise

    async def wait_for_healthy(self, timeout=60):
        """Ожидание перехода всех сервисов в состояние healthy."""
        logger.info("Waiting for services to become healthy...")
        start_time = asyncio.get_event_loop().time()
        
        while asyncio.get_event_loop().time() - start_time < timeout:
            containers = await self.docker.containers.list()
            all_healthy = True
            infrastructure_containers = []
            
            # Фильтруем контейнеры нашего проекта (по меткам или именам)
            for container in containers:
                info = await container.show()
                name = info['Name'].lstrip('/')
                if any(service in name for service in ['redis', 'backend', 'web_ui']):
                    infrastructure_containers.append(info)
            
            if not infrastructure_containers:
                logger.warning("No infrastructure containers found yet...")
                all_healthy = False
            else:
                for info in infrastructure_containers:
                    state = info.get('State', {})
                    health = state.get('Health', {})
                    status = health.get('Status', 'none')
                    name = info['Name'].lstrip('/')
                    
                    if status != 'healthy' and 'web_ui' not in name: # web_ui без healthcheck пока
                        logger.info(f"Service {name} is {status}...")
                        all_healthy = False
                        break
                    elif 'web_ui' in name and state.get('Status') != 'running':
                        all_healthy = False
                        break

            if all_healthy:
                logger.info("All infrastructure services are healthy!")
                return True
            
            await asyncio.sleep(2)
        
        raise TimeoutError("Infrastructure services failed to become healthy within timeout")

    async def bootstrap(self):
        """Полный цикл инициализации."""
        try:
            await self.init_docker()
            await self.run_compose()
            await self.wait_for_healthy()
            
            # Инициализация Redis для проброса событий
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            self.redis = redis.from_url(redis_url, decode_responses=True)

            # Инициализация основного оркестратора
            # Монтируем корень проекта как /workspace
            cwd = os.path.abspath(os.path.join(os.getcwd(), "../.."))
            volumes = {
                cwd: "/workspace",
                "/tmp/vlm_model_cache": "/workspace/model_cache"
            }
            
            # Добавляем переменные окружения для контейнеров исполнения
            env = {
                "PYTHONPATH": "/workspace/VLMHyperBench:/workspace/packages/task-registry/src:/workspace/packages/dataset_factory/src:/workspace/packages/metric_registry/src:/workspace/packages/prompt_manager:/workspace/packages/api_wrapper/src",
                "REGISTRY_ROOT": "/workspace/vlmhyperbench/registries",
                "DATA_ROOT": "/workspace/data"
            }
            
            gpu_ids = [0]
            self.orchestrator = AsyncBenchmarkOrchestrator(volumes, gpu_ids, environment=env)
            
            # Подписка на события оркестратора и публикация в Redis
            def on_orchestrator_event(event: Event):
                # Мы не можем использовать await здесь напрямую, так как это синхронный коллбэк
                # Используем create_task
                asyncio.create_task(self.redis.publish(
                    f"experiment:{event.data.get('experiment_id', 'global')}",
                    json.dumps({"type": event.event_type.value, "data": event.data})
                ))
            
            self.orchestrator.event_bus.subscribe(on_orchestrator_event)
            
            logger.info("Orchestrator Service is READY")
        except Exception as e:
            logger.error(f"Bootstrap failed: {e}")
            # Здесь можно добавить логику остановки того, что успело подняться
            raise

bootstrapper = Bootstrapper()

@app.on_event("startup")
async def startup_event():
    # Запускаем bootstrap в фоне, чтобы не блокировать старт самого API
    # Но в реальности лучше дождаться, если это критично
    asyncio.create_task(bootstrapper.bootstrap())

@app.get("/health")
async def health():
    return {"status": "ok", "infra_ready": bootstrapper.orchestrator is not None}

@app.post("/run")
async def run_experiment(payload: dict = Body(...)):
    if bootstrapper.orchestrator is None:
        raise HTTPException(status_code=503, detail="Orchestrator not ready")
    
    experiment_id = payload.get("experiment_id")
    config = payload.get("config")
    
    logger.info(f"Starting experiment {experiment_id}")
    
    # Загружаем конфигурацию запуска из реестра или используем переданную
    # В данном случае предполагаем, что config - это имя run конфигурации (например, 'qwen_snils_extraction')
    # Или словарь с переопределениями
    
    run_name = "qwen_snils_extraction" # Hardcoded for now based on the task
    
    try:
        # Пытаемся загрузить из реестра
        # Путь к реестрам относительно корня проекта (поднимаемся на 4 уровня выше от src/orchestrator_service/main.py)
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
        registry_root = os.path.join(project_root, "vlmhyperbench/registries")
        
        registry = RegistryManager(root_dir=registry_root, run_mode="dev")
        run_config = registry.get_run(run_name)
        
        # Валидация
        registry.validate_run(run_config)
        
        logger.info(f"Loaded run config: {run_config}")
        
        bootstrapper.orchestrator.add_benchmark_run(run_config)
        
    except Exception as e:
        logger.error(f"Failed to load run config: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid run configuration: {str(e)}")
    
    # Запускаем выполнение в фоне
    asyncio.create_task(bootstrapper.orchestrator.run_until_complete())
    
    return {"status": "accepted", "experiment_id": experiment_id}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)