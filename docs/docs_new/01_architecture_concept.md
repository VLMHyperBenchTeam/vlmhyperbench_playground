# Архитектурная концепция VLMHyperBench

VLMHyperBench — это модульный, расширяемый фреймворк для оценки Vision Language Models (VLM), построенный на принципах **микросервисной архитектуры** и **строгой изоляции окружений**.

## 1. Философия

1.  **Изоляция превыше всего**: Мы не пытаемся установить все библиотеки в один Python environment. Каждая модель и каждый этап оценки запускаются в собственном изолированном контейнере.
2.  **Everything is a Registry**: Модели, Задачи, Метрики — это подключаемые модули (плагины), регистрируемые в системе. Ядро фреймворка агностично к конкретным реализациям.
3.  **Configuration as Code**: Весь эксперимент описывается декларативными конфигурационными файлами (CSV/JSON).
4.  **Environment Agnostic**: Код этапа не знает, где он выполняется (локальный Docker, Kubernetes Pod или HPC Singularity).

## 2. Компонентная модель (C4 Container Diagram)

Система состоит из управляющего слоя (Control Plane) и слоя исполнения (Execution Plane).

```mermaid
graph TD
    User["Пользователь"] -->|"Config (CSV)"| Orchestrator
    
    subgraph "Control Plane (Host)"
        Orchestrator[Benchmark Orchestrator]
        
        subgraph "Registries"
            ModelReg[Model Registry]
            TaskReg[Task Registry]
            MetricReg[Metric Registry]
        end
        
        subgraph "Managers"
            WorkerMgr[Worker Manager]
            EnvMgr[Environment Manager]
        end
    end
    
    subgraph "Execution Plane (Isolated Environments)"
        subgraph "Inference Container (GPU)"
            APIWrapper[API Wrapper]
            ModelBackend[vLLM / HF / SGLang]
            APIWrapper --> ModelBackend
        end
        
        subgraph "Eval Container (CPU)"
            MetricEval[Metric Evaluator]
        end
        
        subgraph "Report Container (CPU)"
            ReportGen[Report Generator]
        end
    end
    
    subgraph "Data Layer"
        FS["Shared FS / S3"]
    end

    Orchestrator --> ModelReg
    Orchestrator --> WorkerMgr
    WorkerMgr --> EnvMgr
    EnvMgr -->|"Spawns & Manages"| Inference Container
    EnvMgr -->|"Spawns & Manages"| Eval Container
    
    Inference Container -->|"Reads/Writes"| FS
    Eval Container -->|"Reads/Writes"| FS
    ReportGen -->|"Reads/Writes"| FS
```

## 3. Ключевые компоненты

### 3.1. Benchmark Orchestrator
Центральный мозг системы.
*   Читает пользовательский конфиг.
*   Разрешает зависимости через Реестры.
*   Планирует задачи и распределяет их по воркерам.

### 3.2. Environment Manager (`EnvManager`)
Абстракция для управления изолированными средами.
*   **DockerEnvManager**: Для локального запуска в Docker.
*   **RunPodEnvManager**: Для запуска в облаке RunPod.
*   **SingularityEnvManager**: Для запуска на HPC кластерах.
*   **Функции**: `setup()`, `run()`, `cleanup()`, `mount_data()`.

### 3.3. Inference Stage & API Wrapper
Для унификации работы с разными бэкендами (HuggingFace, vLLM) используется **API Wrapper**:
*   Запускается внутри контейнера модели.
*   Предоставляет единый API (`/v1/chat/completions`).
*   Автоматически замеряет метрики производительности (TTFT, Latency, Peak Memory) и возвращает их вместе с ответом.

### 3.4. Registries & Plugins
Система расширяется через Python-пакеты, реализующие стандартные интерфейсы:
*   `Task`: Определяет формат данных и стратегию промптинга.
*   `ModelInterface`: Адаптер для загрузки и инференса модели.
*   `Metric`: Логика сравнения предсказания с эталоном (Ground Truth).

## 4. Поток данных (Workflow)

1.  **Initialization**: Оркестратор парсит конфиг, подготавливает план запуска.
2.  **Environment Setup**: `EnvManager` поднимает контейнер. Выполняется **Dynamic Dependency Injection** (установка драйверов модели и библиотек метрик).
3.  **Data Sync**: Если требуется, данные скачиваются из S3 на локальный диск (Smart Sync).
4.  **Inference**: Запуск модели, генерация ответов -> `answers.csv`.
5.  **Evaluation**: Запуск легкого контейнера оценки. Расчет метрик -> `metrics.csv`.
6.  **Reporting**: Агрегация результатов и генерация отчета -> `report.md`.

## 5. Технологический стек
*   **Core**: Python 3.10+, Pydantic.
*   **Containerization**: Docker SDK.
*   **Inference Backends**: vLLM, Transformers, SGLang.
*   **Data**: Pandas, Polars.
