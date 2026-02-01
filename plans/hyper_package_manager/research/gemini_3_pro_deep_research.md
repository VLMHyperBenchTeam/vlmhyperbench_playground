# **Отчет о стратегическом исследовании и технико-экономическом обосновании спецификации HyperPackageManager (HPM) в экосистеме Python 2026 года**

## **1\. Введение: Эволюция управления зависимостями и архитектурный контекст 2026 года**

К 2026 году ландшафт разработки на Python претерпел фундаментальные изменения, обусловленные как внутренним развитием языка, так и внешними требованиями индустрии к скорости, безопасности и модульности. Эпоха фрагментированных инструментов (pip, poetry, pipenv, setuptools), характерная для начала 2020-х годов, сменилась доминированием высокопроизводительных унифицированных решений, написанных на системных языках, таких как Rust. В этом контексте появление спецификации HyperPackageManager (HPM), предлагающей парадигмы Just-In-Time (JIT) установки и динамической композиции, требует тщательного анализа на предмет ее востребованности и жизнеспособности.  
Данный отчет представляет собой исчерпывающее исследование, целью которого является определение места HPM в экосистеме 2026 года. Мы детально рассмотрим, как предлагаемые концепции соотносятся с возможностями текущих лидеров рынка — uv от Astral и pixi от Prefix.dev, проанализируем проблемы мульти-репозиторной разработки без использования git submodules и оценим целесообразность реализации HPM как надстройки над uv.

### **1.1. Технологический фон 2026 года**

К 2026 году сообщество Python практически единогласно приняло uv в качестве стандарта де\-факто для управления проектами, заменив им традиционные цепочки инструментов. Скорость разрешения зависимостей и установки выросла на порядки (в 10-100 раз по сравнению с классическим pip).1 Это изменение производительности стало катализатором для смены парадигм: операции создания виртуальных окружений, ранее считавшиеся "дорогими" и выполнявшимися редко (обычно при инициализации проекта), теперь стали тривиальными и практически мгновенными.  
Параллельно с этим, в сегменте научных вычислений, машинного обучения и высокопроизводительных вычислений (HPC) укрепились позиции pixi, который эволюционировал из экосистемы Conda, предлагая герметичное управление не только Python-пакетами, но и системными библиотеками, компиляторами и драйверами (например, CUDA).3  
Однако, несмотря на эти успехи, фундаментальная архитектурная проблема "Dependency Hell" (ад зависимостей) не исчезла, а трансформировалась. Если раньше она проявлялась на этапе установки (невозможность разрешить граф зависимостей), то в 2026 году, с ростом популярности модульных монолитов и плагинных архитектур, она переместилась в рантайм. Приложения, состоящие из десятков микросервисов или плагинов, требуют одновременной работы с конфликтующими версиями библиотек в рамках единого процесса или рабочего пространства, что ставит под удар классическую модель "одно окружение — одна версия пакета".5  
Именно в этот разрыв между статическими возможностями современных менеджеров пакетов и динамическими потребностями сложных runtime-систем целится спецификация HPM.

## ---

**2\. Анализ востребованности подхода HPM в 2026 году**

Первый ключевой вопрос исследования касается актуальности подходов JIT installation (установка точно в срок) и dynamic composition (динамическая композиция) в реалиях 2026 года. Анализ показывает, что спрос на эти возможности не просто существует, а является критическим для нескольких быстрорастущих секторов разработки.

### **2.1. Just-In-Time (JIT) Installation: От скриптов к агентам**

Концепция JIT-установки подразумевает, что зависимости не декларируются и устанавливаются заранее в явном шаге build/install, а разрешаются и подтягиваются непосредственно в момент исполнения кода.

#### **2.1.1. Эволюция PEP 723 и Inline Script Metadata**

К 2026 году PEP 723 (Inline Script Metadata) стал повсеместным стандартом для однофайловых скриптов. Инструменты вроде uv и его компонента uvx (аналог npx) позволяют запускать скрипты, содержащие метаданные зависимостей, в изолированных временных окружениях без явного создания venv.7 Это доказывает востребованность JIT-подхода на уровне *инструментария* и *скриптинга*. Разработчики привыкли к тому, что для запуска утилиты не нужно загрязнять глобальное окружение или вручную управлять виртуальными средами.  
Однако HPM предлагает расширить этот подход за пределы однофайловых скриптов — на уровень полноценных приложений и динамически загружаемых модулей. В 2026 году это становится критически важным для разработки **AI-агентов** и **автономных систем**.

#### **2.1.2. Агентные системы и динамическая генерация кода**

Развитие больших языковых моделей (LLM) привело к появлению автономных агентов, способных генерировать и исполнять код для решения задач "на лету".10 Агент, получивший задачу проанализировать новый формат данных, может сгенерировать код, использующий специфическую библиотеку, которая отсутствует в базовом образе контейнера. В классической модели (AOT) агент потерпит неудачу с ошибкой ImportError. В модели HPM (JIT) система перехватит ошибку импорта, автоматически разрешит зависимость, установит её в изолированное окружение и продолжит исполнение. Это снижает хрупкость автономных систем и значительно расширяет их возможности без необходимости постоянной пересборки базовых Docker-образов.11

#### **2.1.3. Риски и ограничения JIT**

Несмотря на востребованность, JIT-подход несет в себе серьезные риски безопасности, связанные с атаками на цепочки поставок (supply chain attacks). Динамическая подгрузка пакетов открывает вектор для тайпосквоттинга и инъекции вредоносного кода, который сложнее отследить, чем при статическом анализе requirements.txt или uv.lock.13 Следовательно, востребованность JIT в корпоративном секторе будет жестко обусловлена наличием мощных механизмов политик безопасности (Policy Engine), которые HPM обязан предоставить.

### **2.2. Dynamic Composition: Решение проблемы "Алмазных зависимостей"**

Динамическая композиция — это способность собирать приложение из разрозненных компонентов (плагинов, модулей) во время выполнения, где каждый компонент может иметь собственные, потенциально конфликтующие требования к окружению.

#### **2.2.1. Кризис статических воркспейсов**

В 2026 году разработчики часто сталкиваются с ситуацией, когда необходимо объединить работу над несколькими микросервисами или библиотеками в одном локальном окружении. Стандартные механизмы uv workspaces требуют, чтобы все члены воркспейса имели единый непротиворечивый граф зависимостей (единый uv.lock).15 Это создает блокирующие проблемы:

* Обновление общей библиотеки (common-lib) в одном сервисе может сломать сборку другого сервиса в том же монорепозитории.  
* Разработчик не может протестировать экспериментальную ветку плагина А с стабильной версией ядра Б, если их транзитивные зависимости конфликтуют (например, разные версии pydantic или numpy).16

#### **2.2.2. Востребованность динамической изоляции**

HPM предлагает подход, при котором каждый компонент композиции может жить в своем изолированном окружении, но при этом взаимодействовать с другими. Это востребовано в:

* **Внутренних платформах разработки (IDP):** Где плагины от разных команд должны работать в едином дашборде.  
* **Сложных Data Science пайплайнах:** Где этап препроцессинга требует старых библиотек, а этап инференса модели — новейших GPU-драйверов и фреймворков.  
* **Тестировании:** Возможность "на лету" подменить одну зависимость на локальную версию (override) без переписывания глобальных лок-файлов.

### **2.3. Вывод по разделу**

Подход HPM является **высоко востребованным** в 2026 году, но не как замена базовым пакетным менеджерам для простых проектов, а как решение для сложных архитектур ("System of Systems"), AI-разработки и управления большими экосистемами плагинов. Рынок перерос статические плоские списки зависимостей и требует инструментов для управления графами окружений.

## ---

**3\. Сравнительный анализ: HPM против uv и pixi в реалиях 2026 года**

Для понимания ниши HPM необходимо детально сравнить его предполагаемый функционал с возможностями гигантов экосистемы — uv и pixi, особенно в контексте работы с рабочими пространствами (workspaces) и переопределениями (overrides).

### **3.1. Работа с Workspaces (Рабочими пространствами)**

#### **3.1.1. uv Workspaces: Статическая строгость**

В 2026 году uv реализует концепцию воркспейсов, вдохновленную Cargo (Rust).

* **Механизм:** Единый корень воркспейса с pyproject.toml, перечисляющим членов (members). Единый uv.lock для всего воркспейса.15  
* **Ограничение:** Строгое требование непротиворечивости версий. Все пакеты воркспейса должны быть совместимы друг с другом. uv не позволяет иметь django==4.0 в одном пакете и django==5.0 в другом в рамках одного воркспейса, если они разрешаются в общее окружение.  
* **Пробел для HPM:** uv ориентирован на монолитную согласованность. HPM может предложить **"Виртуальные воркспейсы"** (Virtual Workspaces), которые объединяют проекты логически, но физически держат их в разных виртуальных окружениях (venv), обеспечивая их взаимодействие через механизмы IPC или суб-интерпретаторы. Это позволяет объединять несовместимые проекты в одну сессию разработки.

#### **3.1.2. pixi Environments: Декларативная гибкость**

pixi пошел дальше uv, предложив концепцию множественных окружений в рамках одного проекта.

* **Механизм:** В pixi.toml можно определить наборы feature, которые комбинируются в environments (например, prod, test, cuda, cpu).3  
* **Преимущество:** Это решает проблему "матрицы тестирования" и поддержки разных аппаратных бэкендов.  
* **Ограничение:** Это все еще статическая, декларативная конфигурация. Добавление нового экспериментального окружения требует редактирования файла конфигурации и пересчета лок-файла (pixi.lock).  
* **Пробел для HPM:** HPM фокусируется на **динамике**. Возможность создать композицию "на лету" из командной строки (например, hpm run \--with plugin-x@local \--with plugin-y@git), не меняя файлы на диске, остается уникальной нишей HPM.

### **3.2. Работа с Overrides (Переопределениями)**

#### **3.2.1. uv Overrides**

В 2026 году uv предоставляет мощные механизмы переопределения:

* tool.uv.sources: Позволяет указать, что пакет foo следует брать не из PyPI, а из локальной папки или git-репозитория.19  
* tool.uv.override-dependencies: Позволяет принудительно указать версию транзитивной зависимости, игнорируя ограничения других пакетов.  
* **Недостаток:** Эти изменения вносятся в pyproject.toml. Это "тяжелая" операция, меняющая состояние репозитория. Для временной отладки (например, проверить, исправляет ли баг локальная версия библиотеки в чужом проекте) это неудобно, так как требует изменения файлов, которые нельзя коммитить.

#### **3.2.2. pixi Overrides**

pixi строго следит за воспроизводимостью. Любое изменение источника пакета должно быть отражено в манифесте и лок-файле. Это делает pixi идеальным для CI/CD, но менее гибким для ad-hoc экспериментов и быстрой локальной отладки "cross-repo".

#### **3.2.3. Подход HPM**

HPM может реализовать **эфемерные переопределения**. Используя скорость uv и механизмы Copy-on-Write (CoW) файловых систем или симлинки, HPM может за секунды создавать временное виртуальное окружение, являющееся копией основного, но с подмененными пакетами ("Overlay Environment").  
Это позволяет разработчику выполнить команду:  
hpm run tests \--override my-lib=../my-lib-fix  
без риска случайно закоммитить локальные пути в pyproject.toml.

### **3.3. Таблица сравнения возможностей (2026 г.)**

| Характеристика | uv (Astral) | pixi (Prefix.dev) | Предлагаемый HPM |
| :---- | :---- | :---- | :---- |
| **Основная цель** | Управление проектами и пакетами Python | Управление бинарными и системными зависимостями | Динамическая оркестрация и JIT-композиция |
| **Workspaces** | Монолитные (единый лок-файл) | Мульти-окружения (feature-based sets) | Виртуальные (изолированные графы) |
| **Разрешение конфликтов** | Строгое (ошибка при конфликте) | Строгое (ошибка при конфликте) | **Изоляция** (разные версии в разных envs) |
| **Overrides** | Через конфиг (pyproject.toml) | Через конфиг (pixi.toml) | **CLI / Runtime** (эфемерные слои) |
| **Скорость (Cold Install)** | Экстремально высокая | Высокая | Зависит от бекенда (использует uv) |
| **Runtime Isolation** | Нет (процесс ОС) | Нет (активация env) | **Да** (Subinterpreters / Import Hooks) |

## ---

**4\. Управление плагинами в мульти-репозиториях без git submodules**

Третий вопрос касается существования готовых аналогов для управления плагинами, разнесенными по разным git-репозиториям, без использования проблематичных git submodules.

### **4.1. Проблема Git Submodules**

К 2026 году индустрия окончательно признала git submodules "антипаттерном" для большинства сценариев разработки из\-за сложности управления состоянием (detached head), проблем с CI/CD и высокого порога входа для новичков.21 Однако потребность собирать проект из множества репозиториев (Poly-repo) никуда не делась.

### **4.2. Существующие аналоги и инструменты**

#### **4.2.1. Мета-инструменты (Meta-repo tools)**

Существует класс инструментов, которые позволяют выполнять git-команды над множеством репозиториев одновременно.

* **Meta / Gita / MyRepos (mr):** Эти инструменты (meta, gita, mr) позволяют определить манифест (YAML/JSON/Conf), перечисляющий репозитории и их пути. Они автоматизируют clone, pull, checkout.23  
* **Недостаток:** Они **агностичны к языку**. Они могут склонировать 10 Python-репозиториев, но они не знают, как связать их в единое окружение Python. Разработчик получает 10 папок, но ему все равно нужно вручную делать pip install \-e. для каждой из них в правильном порядке.

#### **4.2.2. Специфичные для Python решения**

В Python экосистеме долгое время отсутствовал инструмент, который объединял бы управление Git-репозиториями и управление виртуальным окружением.

* **uv (Editable Git Installs):** uv позволяет установить зависимость напрямую из git: uv add git+https://.... В режиме \--editable это создает связь. Но uv ожидает, что это *зависимость*, а не *рабочее пространство*, которое разработчик активно правит. Он не предназначен для синхронизации веток множества репозиториев.19

#### **4.2.3. Аналог Git X-Modules и Subtrees**

Существуют серверные решения (Git X-Modules) и git subtree, которые пытаются эмулировать монорепозиторий, но они часто усложняют историю коммитов и требуют сложной настройки на стороне Git-сервера.26

### **4.3. Решение HPM: Концепция "Виртуального Монорепозитория"**

HPM заполняет пустующую нишу **"Python Poly-repo Manager"**. Он действует как мост между Git-оркестрацией и управлением окружением.  
**Как это работает в HPM:**  
Вместо git submodules используется манифест hpm.yaml:

YAML

workspace:  
  name: "My Complex App"  
  plugins:  
    \- name: "auth-core"  
      git: "git@github.com:company/auth.git"  
      branch: "develop"  
      target: "./plugins/auth"  
    \- name: "ui-lib"  
      git: "git@github.com:company/ui.git"  
      tag: "v2.0.1"

Команда hpm sync выполняет два действия:

1. **Git Layer:** Параллельно клонирует/обновляет репозитории (аналогично gita).28  
2. **Environment Layer:** Генерирует динамический pyproject.toml (или uv.lock), который подключает все склонированные репозитории как editable зависимости.

Это создает иллюзию монорепозитория для разработчика (единый IDE контекст, навигация по коду, тесты), сохраняя при этом физическую изоляцию git-историй. Это решение, которого нет в чистом виде ни в uv, ни в pixi.

## ---

**5\. Архитектурная стратегия: HPM как надстройка над uv**

Четвертый вопрос является стратегическим: имеет ли смысл разрабатывать HPM как надстройку над uv? Ответ однозначный: **Да, это единственно верный путь в 2026 году.**

### **5.1. Почему нельзя разрабатывать собственный Package Manager с нуля**

К 2026 году порог входа на рынок пакетных менеджеров стал запредельно высоким.

* **Сложность Resolver'а:** Написание корректного SAT-солвера (разрешителя зависимостей), такого как PubGrub (используется в uv), требует огромных инженерных усилий. Он должен учитывать тысячи граничных случаев PEP 440, совместимость платформ, маркеры окружения и т.д.  
* **Производительность:** uv задал стандарт производительности, недостижимый для инструментов на чистом Python. Попытка конкурировать с uv в скорости установки пакетов обречена на провал без использования Rust и сложной архитектуры кэширования.1  
* **Стандартизация:** uv уже строго следует всем современным PEP. Дублирование этой логики бессмысленно.

### **5.2. HPM как "Оркестратор" и "Гипервизор Окружений"**

HPM должен позиционироваться не как конкурент uv, а как **мета-инструмент (Superstructure)**, использующий uv в качестве низкоуровневого движка (backend).

#### **5.2.1. Разделение ответственности**

* **uv (Backend):** Отвечает за тяжелую физическую работу. Скачивание колес (wheels), распаковка, разрешение графов зависимостей, создание базовых venv, кэширование.  
* **HPM (Frontend/Orchestrator):** Отвечает за логику высшего порядка.  
  * Парсинг манифестов динамической композиции.  
  * Управление множеством Git-репозиториев.  
  * Принятие решений о том, *сколько* и *каких* виртуальных окружений нужно создать с помощью uv для удовлетворения требований изоляции.  
  * Настройка Runtime (Python Path, Subinterpreters), чтобы связать эти окружения воедино.

### **5.3. Техническая реализация интеграции**

HPM работает как генератор конфигураций для uv.

1. Пользователь запускает hpm run....  
2. HPM анализирует требования, вычисляет необходимые переопределения.  
3. HPM генерирует временные pyproject.toml или вызывает uv pip install с нужными флагами в специфические директории (например, .hpm/envs/layer\_1).29  
4. HPM запускает Python-процесс с модифицированными переменными окружения (PYTHONPATH, UV\_PROJECT\_ENVIRONMENT) или использует кастомный загрузчик (importlib).

## ---

**6\. Глубокое погружение: Технологии Runtime-изоляции (Python 3.14+)**

Самой инновационной частью HPM, отличающей его от простых оберток, является использование возможностей **Python 3.14**, ставших доступными к 2026 году. Речь идет о **суб-интерпретаторах (Subinterpreters)**.

### **6.1. PEP 554 и PEP 734: Суб-интерпретаторы**

До 2026 года изоляция зависимостей возможна была только на уровне процессов ОС (через multiprocessing), что влекло за собой высокие накладные расходы на сериализацию данных (pickle) и межпроцессное взаимодействие (IPC). В Python 3.14 механизм суб-интерпретаторов достиг зрелости. Теперь в рамках одного процесса можно запустить несколько изолированных интерпретаторов Python, каждый из которых имеет свой собственный sys.modules и, что критически важно, свой собственный **Global Interpreter Lock (GIL)** (благодаря PEP 684).31

### **6.2. Роль HPM в управлении суб-интерпретаторами**

Стандартная библиотека concurrent.interpreters предоставляет API для запуска кода, но не решает проблему управления зависимостями. Если просто запустить суб-интерпретатор, он унаследует sys.path основного процесса или будет использовать глобальный site-packages.  
HPM берет на себя роль **Linker'а**:

1. HPM использует uv для создания двух физически разных папок с окружениями: .hpm/envs/env\_a (с pandas 1.0) и .hpm/envs/env\_b (с pandas 2.0).  
2. При запуске суб-интерпретатора A, HPM инициализирует его так, чтобы его sys.path указывал исключительно на .hpm/envs/env\_a.33  
3. Это позволяет загружать конфликтующие бинарные модули (C-extensions) в одно адресное пространство процесса (с оговорками о глобальных символах в C-библиотеках, которые HPM должен отслеживать).35

### **6.3. Динамический импорт и sys.meta\_path**

Для менее сложных случаев (Pure Python пакеты) HPM может использовать кастомные MetaPathFinder.37

* HPM регистрирует хук импорта.  
* Когда код запрашивает import my\_plugin, хук перехватывает запрос.  
* Хук проверяет манифест: "Откуда должен быть загружен my\_plugin?".  
* Хук динамически подгружает модуль из специфической директории, игнорируя глобальный sys.path.38

## ---

**7\. Риски безопасности и управления (Governance)**

Внедрение JIT и динамической композиции в корпоративную среду (Enterprise) невозможно без строгих политик безопасности.

### **7.1. Supply Chain Security**

Динамическая установка пакетов "на лету" делает невозможным предварительный аудит лок-файла человеком.

* **Решение HPM:** Интеграция с политиками. HPM должен поддерживать файл hpm-policy.toml, где администраторы могут:  
  * Запретить использование JIT для внешних индексов (только внутренний Artifactory/PyPI).  
  * Разрешить динамические версии только в диапазоне патчей (semver patch).  
  * Требовать криптографической подписи плагинов.13

### **7.2. Детерминизм и Воспроизводимость**

Динамическая композиция по определению снижает воспроизводимость ("Оно работало, когда я запустил это с плагином версии X, но сегодня плагин версии Y").

* **Решение HPM:** "Snapshotting". После успешной динамической композиции HPM должен уметь сбросить текущее состояние в статический hpm.lock.snapshot, который фиксирует все версии всех динамически подгруженных компонентов. Это позволяет превратить экспериментальную динамическую сессию в воспроизводимый артефакт.

## ---

**8\. Заключение и Дорожная карта (Roadmap)**

### **8.1. Итоговое резюме**

Спецификация HPM описывает инструмент, который заполняет критический разрыв в экосистеме Python 2026 года. В то время как uv блестяще решил проблему **статического** управления зависимостями и скоростью сборки, HPM решает проблему **динамической** оркестрации и **архитектурной композиции** сложных систем.

### **8.2. Ответы на вопросы исследования**

1. **Востребован ли подход?** Да, критически востребован для AI-агентов, IDP-платформ и разработки в стиле "Virtual Monorepo".  
2. **Соотношение с uv/pixi?** HPM дополняет их. Он использует uv как движок, но добавляет слои виртуализации (изоляция воркспейсов, runtime-переопределения), которых нет в uv. Он более динамичен, чем pixi.  
3. **Аналоги без submodules?** Прямых аналогов, объединяющих Git-оркестрацию с глубоким пониманием Python-окружений, нет. HPM может стать де\-факто стандартом для "Python Poly-repo".  
4. **Надстройка над uv?** Да. Разработка HPM как отдельного пакетного менеджера экономически нецелесообразна. HPM должен быть реализован как "Environment Hypervisor", управляющий uv.

### **8.3. Рекомендации по разработке**

Рекомендуется сосредоточить усилия разработки на создании **HPM CLI** как обертки над uv и git.

* **Фаза 1:** Реализация "Virtual Workspaces" (клонирование репозиториев по манифесту \+ генерация uv.lock).  
* **Фаза 2:** Реализация JIT-импортов через перехват ImportError и вызов uv pip install.  
* **Фаза 3:** Интеграция с Python 3.14 Subinterpreters для истинной runtime-изоляции конфликтующих зависимостей.

Создание HPM в 2026 году — это не изобретение очередного "установщика пакетов", а создание инструмента управления сложностью для эры AI и модульных архитектур.

#### **Источники**

1. uv \- Astral Docs, дата последнего обращения: февраля 1, 2026, [https://docs.astral.sh/uv/](https://docs.astral.sh/uv/)  
2. Managing Python Projects With uv: An All-in-One Solution, дата последнего обращения: февраля 1, 2026, [https://realpython.com/python-uv/](https://realpython.com/python-uv/)  
3. Multi Environment \- Pixi by prefix.dev, дата последнего обращения: февраля 1, 2026, [https://pixi.sh/v0.43.3/tutorials/multi\_environment/](https://pixi.sh/v0.43.3/tutorials/multi_environment/)  
4. Introducing Pixi's Multiple Environments \- prefix.dev, дата последнего обращения: февраля 1, 2026, [https://prefix.dev/blog/introducing\_multi\_env\_pixi](https://prefix.dev/blog/introducing_multi_env_pixi)  
5. Conflicting module dependence in python project \- Stack Overflow, дата последнего обращения: февраля 1, 2026, [https://stackoverflow.com/questions/75728785/conflicting-module-dependence-in-python-project](https://stackoverflow.com/questions/75728785/conflicting-module-dependence-in-python-project)  
6. How to deal with conflicting dependencies/versions?, дата последнего обращения: февраля 1, 2026, [https://softwareengineering.stackexchange.com/questions/455193/how-to-deal-with-conflicting-dependencies-versions](https://softwareengineering.stackexchange.com/questions/455193/how-to-deal-with-conflicting-dependencies-versions)  
7. Python Packaging in 2025: Introducing uv, A Speedy New Contender, дата последнего обращения: февраля 1, 2026, [https://medium.com/fhinkel/python-packaging-in-2025-introducing-uv-a-speedy-new-contender-cbf408726687](https://medium.com/fhinkel/python-packaging-in-2025-introducing-uv-a-speedy-new-contender-cbf408726687)  
8. PEP 723 – Inline script metadata \- Python Enhancement Proposals, дата последнего обращения: февраля 1, 2026, [https://peps.python.org/pep-0723/](https://peps.python.org/pep-0723/)  
9. Share Python Scripts Like a Pro: uv and PEP 723 for Easy Deployment, дата последнего обращения: февраля 1, 2026, [https://thisdavej.com/share-python-scripts-like-a-pro-uv-and-pep-723-for-easy-deployment/](https://thisdavej.com/share-python-scripts-like-a-pro-uv-and-pep-723-for-easy-deployment/)  
10. Solving Python Dependency Conflicts with LLMs \- arXiv, дата последнего обращения: февраля 1, 2026, [https://arxiv.org/html/2501.16191v2](https://arxiv.org/html/2501.16191v2)  
11. zackees/isolated-environment: Internal venv management to fix AI ..., дата последнего обращения: февраля 1, 2026, [https://github.com/zackees/isolated-environment](https://github.com/zackees/isolated-environment)  
12. Secure execution of code generated by Large Language Models, дата последнего обращения: февраля 1, 2026, [https://medium.com/@philippkai/secure-execution-of-code-generated-by-large-language-models-625654de951a](https://medium.com/@philippkai/secure-execution-of-code-generated-by-large-language-models-625654de951a)  
13. Security Risks in PEP 723 and uv: Inline Metadata Gone Wrong?, дата последнего обращения: февраля 1, 2026, [https://safedep.io/pep-723-inline-metadata-security/](https://safedep.io/pep-723-inline-metadata-security/)  
14. Python Dependency Injection: How to Do It Safely \- DEV Community, дата последнего обращения: февраля 1, 2026, [https://dev.to/xygenisecurity/python-dependency-injection-how-to-do-it-safely-926](https://dev.to/xygenisecurity/python-dependency-injection-how-to-do-it-safely-926)  
15. Using workspaces | uv \- Astral Docs, дата последнего обращения: февраля 1, 2026, [https://docs.astral.sh/uv/concepts/projects/workspaces/](https://docs.astral.sh/uv/concepts/projects/workspaces/)  
16. Cada: A build plugin for publishing interdependent libraries from uv ..., дата последнего обращения: февраля 1, 2026, [https://www.reddit.com/r/Python/comments/1q01ayz/cada\_a\_build\_plugin\_for\_publishing\_interdependent/](https://www.reddit.com/r/Python/comments/1q01ayz/cada_a_build_plugin_for_publishing_interdependent/)  
17. Resolving Dependency Conflicts in Python for the Python Newbie, дата последнего обращения: февраля 1, 2026, [https://medium.com/@kkang2097/resolving-dependency-conflicts-in-python-for-the-python-newbie-cd8e5023db8d](https://medium.com/@kkang2097/resolving-dependency-conflicts-in-python-for-the-python-newbie-cd8e5023db8d)  
18. Multi Environment \- Pixi \- prefix.dev, дата последнего обращения: февраля 1, 2026, [https://pixi.prefix.dev/latest/workspace/multi\_environment/](https://pixi.prefix.dev/latest/workspace/multi_environment/)  
19. Managing packages | uv \- Astral Docs, дата последнего обращения: февраля 1, 2026, [https://docs.astral.sh/uv/pip/packages/](https://docs.astral.sh/uv/pip/packages/)  
20. uv pip install \--target and workspace · Issue \#5631 · astral-sh/uv, дата последнего обращения: февраля 1, 2026, [https://github.com/astral-sh/uv/issues/5631](https://github.com/astral-sh/uv/issues/5631)  
21. Git submodules or multi-repo manager like myrepos? \- Reddit, дата последнего обращения: февраля 1, 2026, [https://www.reddit.com/r/git/comments/1fc234f/git\_submodules\_or\_multirepo\_manager\_like\_myrepos/](https://www.reddit.com/r/git/comments/1fc234f/git_submodules_or_multirepo_manager_like_myrepos/)  
22. Anyone know a clean way to have nested git projects? Every time I ..., дата последнего обращения: февраля 1, 2026, [https://news.ycombinator.com/item?id=26239575](https://news.ycombinator.com/item?id=26239575)  
23. mani, a CLI Tool to Manage Multiple Repositories \- DEV Community, дата последнего обращения: февраля 1, 2026, [https://dev.to/alajmo/mani-a-cli-tool-to-manage-multiple-repositories-1eg](https://dev.to/alajmo/mani-a-cli-tool-to-manage-multiple-repositories-1eg)  
24. GitHub \- mateodelnorte/meta: tool for turning many repos into a ..., дата последнего обращения: февраля 1, 2026, [https://github.com/mateodelnorte/meta](https://github.com/mateodelnorte/meta)  
25. Gita – a CLI tool to manage multiple Git repos \- Hacker News, дата последнего обращения: февраля 1, 2026, [https://news.ycombinator.com/item?id=19074170](https://news.ycombinator.com/item?id=19074170)  
26. Managing Multiple Git Repositories Within a Single ... \- Medium, дата последнего обращения: февраля 1, 2026, [https://medium.com/@himanshu\_96818/managing-multiple-git-repositories-within-a-single-repository-best-practices-and-approaches-d39a5f0bbf89](https://medium.com/@himanshu_96818/managing-multiple-git-repositories-within-a-single-repository-best-practices-and-approaches-d39a5f0bbf89)  
27. Best way to handle multiple repositories \- Atlassian Community, дата последнего обращения: февраля 1, 2026, [https://community.atlassian.com/forums/Bitbucket-questions/Best-way-to-handle-multiple-repositories-submodules-monorepo-or/qaq-p/1526599](https://community.atlassian.com/forums/Bitbucket-questions/Best-way-to-handle-multiple-repositories-submodules-monorepo-or/qaq-p/1526599)  
28. federicober/git-multi-clone: Declaratively clone git repos \- GitHub, дата последнего обращения: февраля 1, 2026, [https://github.com/federicober/git-multi-clone](https://github.com/federicober/git-multi-clone)  
29. How do I install Python dev-dependencies using uv? \- Stack Overflow, дата последнего обращения: февраля 1, 2026, [https://stackoverflow.com/questions/78902565/how-do-i-install-python-dev-dependencies-using-uv](https://stackoverflow.com/questions/78902565/how-do-i-install-python-dev-dependencies-using-uv)  
30. Installer options | uv \- Astral Docs, дата последнего обращения: февраля 1, 2026, [https://docs.astral.sh/uv/reference/installer/](https://docs.astral.sh/uv/reference/installer/)  
31. PEP 554 – Multiple Interpreters in the Stdlib | peps.python.org, дата последнего обращения: февраля 1, 2026, [https://peps.python.org/pep-0554/](https://peps.python.org/pep-0554/)  
32. What’s new in Python 3.14, дата последнего обращения: февраля 1, 2026, [https://docs.python.org/3/whatsnew/3.14.html](https://docs.python.org/3/whatsnew/3.14.html)  
33. concurrent.interpreters — Multiple interpreters in the same process ..., дата последнего обращения: февраля 1, 2026, [https://docs.python.org/3/library/concurrent.interpreters.html](https://docs.python.org/3/library/concurrent.interpreters.html)  
34. Python sys.meta\_path\[1\] the frozen importer. Does an application ..., дата последнего обращения: февраля 1, 2026, [https://stackoverflow.com/questions/70317963/python-sys-meta-path1-the-frozen-importer-does-an-application-ever-use-it](https://stackoverflow.com/questions/70317963/python-sys-meta-path1-the-frozen-importer-does-an-application-ever-use-it)  
35. Embedding multiple Python sub-interpreters into a C program, дата последнего обращения: февраля 1, 2026, [https://stackoverflow.com/questions/53965865/embedding-multiple-python-sub-interpreters-into-a-c-program](https://stackoverflow.com/questions/53965865/embedding-multiple-python-sub-interpreters-into-a-c-program)  
36. Separating virtualenvs for subinterpreters within a single Python ..., дата последнего обращения: февраля 1, 2026, [https://discuss.python.org/t/separating-virtualenvs-for-subinterpreters-within-a-single-python-process/86043](https://discuss.python.org/t/separating-virtualenvs-for-subinterpreters-within-a-single-python-process/86043)  
37. How to use sys.meta\_path with Python 3.x? \- Stack Overflow, дата последнего обращения: февраля 1, 2026, [https://stackoverflow.com/questions/57126085/how-to-use-sys-meta-path-with-python-3-x](https://stackoverflow.com/questions/57126085/how-to-use-sys-meta-path-with-python-3-x)  
38. Dynamic Loading of Python Code. Or: Fun With importlib \- Medium, дата последнего обращения: февраля 1, 2026, [https://medium.com/@david.bonn.2010/dynamic-loading-of-python-code-2617c04e5f3f](https://medium.com/@david.bonn.2010/dynamic-loading-of-python-code-2617c04e5f3f)  
39. What's the best way to import a module from a directory that's not a ..., дата последнего обращения: февраля 1, 2026, [https://stackoverflow.com/questions/10533679/whats-the-best-way-to-import-a-module-from-a-directory-thats-not-a-package](https://stackoverflow.com/questions/10533679/whats-the-best-way-to-import-a-module-from-a-directory-thats-not-a-package)  
40. Python Dependency Injection: How to Do It Safely \- Xygeni, дата последнего обращения: февраля 1, 2026, [https://xygeni.io/blog/python-dependency-injection-how-to-do-it-safely/](https://xygeni.io/blog/python-dependency-injection-how-to-do-it-safely/)