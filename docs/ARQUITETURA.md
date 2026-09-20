# Estrutura do Projeto - RTS Tanks RBC System

## 📂 Estrutura de Diretórios

```text
RTS_Simple_Game/
├── main.py                (Ponto de entrada unificado)
├── build_exe.py           # Automação da compilação PyInstaller (.exe)
├── dist/                  (Executável compilado e npc_cases.db)
├── analytics/             (Gráficos dashboard.png e relatórios CSV)
├── ai/                    (Camada de Inteligência Artificial e RBC)
│   ├── npc_brain.py       (Cérebro do NPC, codificação de problemas e recompensa)
│   ├── rbc_engine.py      (Motor RBC: Cold Start, Epsilon-Greedy, Adaptação)
│   └── rbc_models.py      (Dataclasses: Problem, Solution, Outcome)
├── database/              (Camada de Persistência SQLite)
│   ├── case_database.py   (Interface de banco, tabelas SQL e função de similaridade)
│   └── initializer.py     (Inicialização, recuperação de corrupção e stats)
├── game/                  (Game loop principal, entidades e UI)
│   ├── game.py            (Orquestrador do jogo, integração com TaskQueue e RBC)
│   ├── entities.py        (Tanques e Projéteis com detecção de origem de caso)
│   ├── perception.py      (Percepção visual, subcones de tiro e ameaças)
│   └── ui/                (Botões e Expressão facial dinâmica do NPC)
├── utils/                 (Utilitários de infraestrutura e otimização)
│   ├── task_queue.py      (Fila de Tarefas Adaptativa por Prioridades)
│   ├── rbc_monitor.py     (Servidor Web local e Dashboard de Telemetria)
│   ├── analytics_manager.py (Coleta de métricas e geração de gráficos Matplotlib)
│   └── action_guards.py   (Guardiões de tiro tático e travas de cold start)
└── docs/                  (Documentação técnica e guias)
```

---

## 📋 Descrição dos Componentes e Arquivos

### `main.py`
**Ponto de entrada centralizado**
- Instancia e executa a classe `game.game.Game`.

---

### `database/`
**Gerenciamento de persistência em SQLite**

Classe principal:
- `CaseDatabase`: Interface com o banco de dados `npc_cases.db`.

Métodos públicos:
- `__init__(db_path)`: Conecta e garante a existência das tabelas e índices.
- `insert_case(case_data)`: Armazena um novo caso aprendido.
- `get_similar_cases(problem, threshold, limit, difficulty)`: Recupera os casos mais semelhantes aplicando ranking ponderado por similaridade e recompensa acumulada (`avg_reward`).
- `update_case_usage(case_id, success, reward)`: Atualiza `usage_count`, `success_rate` e `avg_reward` do caso.
- `insert_match_record(match_data)`: Registra métricas de fim de partida na tabela `match_history`.
- `get_match_history(limit)`: Retorna histórico de partidas.
- `get_statistics(player_id)`: Retorna métricas agregadas.

Tabelas SQL:
```sql
rbc_cases (
    id INTEGER PRIMARY KEY,
    case_id TEXT UNIQUE,
    player_id TEXT,
    problem_distance REAL, problem_angle_diff REAL,
    problem_nearest_projectile_distance REAL, problem_nearest_projectile_angle REAL,
    problem_projectiles_nearby_count INTEGER,
    problem_edge_distance_top REAL, problem_edge_distance_bottom REAL, problem_nearest_edge_distance REAL,
    problem_border_pressure REAL, problem_border_side INTEGER, problem_closing_speed REAL,
    problem_recent_actions TEXT,
    problem_npc_health REAL, problem_player_health REAL, problem_player_visible INTEGER,
    problem_frames_lost INTEGER,
    solution_action TEXT, solution_params TEXT,
    result_success INTEGER, result_damage_dealt REAL, result_damage_taken REAL, result_outcome TEXT,
    difficulty TEXT, session_id TEXT, timestamp DATETIME,
    usage_count INTEGER, success_count INTEGER, success_rate REAL,
    total_reward REAL, avg_reward REAL,
    last_used DATETIME, created_by TEXT
);

match_history (
    id INTEGER PRIMARY KEY,
    match_number INTEGER, session_id TEXT, player_id TEXT, timestamp DATETIME,
    duration_seconds REAL, duration_frames INTEGER, winner TEXT,
    player_final_health REAL, npc_final_health REAL, npc_damage_dealt REAL, npc_damage_taken REAL,
    total_cases_count INTEGER, new_cases_created INTEGER,
    match_total_reward REAL, match_avg_reward REAL, overall_avg_reward REAL,
    npc_win_rate REAL, epsilon REAL
);
```

---

### `ai/`
**Motor RBC e Inteligência do Agente**

Dataclasses (`ai/rbc_models.py`):
- `Problem`: Estado perceptivo completo (distância vertical, vida, visibilidade, ameaça de projéteis, distância das bordas da arena, pressão de parede, velocidade de aproximação `closing_speed`, histórico de ações recentes).
- `Solution`: Ação tática a executar (`action`, `params`).
- `Outcome`: Recompensa e impacto numérico (`success`, `damage_dealt`, `damage_taken`, `outcome_type`, `reward`).

Classes principais:
- `RBCEngine`: Gerencia as fases de **Cold Start** (macros estocásticos), **Exploração vs Explotação ($\epsilon$-greedy decay)**, recuperação top-K e função de adaptação de soluções.
- `NPCBrain`: Interface entre a simulação e o RBC. Transforma a percepção em `Problem`, calcula funções de recompensa dinâmicas (penalização por ineficácia/posição travada) e chama `RBCEngine.learn()`.

---

### `game/`
**Game Loop, Simulação Física e Interface**

Componentes:
- `game.game.Game`: Orquestra o ciclo de quadros, enfileira chamadas na `AdaptiveTaskQueue`, gerencia telas (Menu, Login de Jogador, Opções, Game Over) e dispara a gravação de métricas.
- `game.entities.Tank` e `Projectile`: Entidades físicas do jogo. Projéteis do NPC guardam a referência da decisão de origem (`origin_problem`, `origin_solution`, `origin_case_id`) para reportar *hit* ou *miss* com precisão.
- `game.perception.NPCPerception`: Processa visibilidade, subcones de varredura e detecta projéteis inimigos em rota de colisão.
- `game.ui.NPCFace`: Renderiza dinamicamente a expressão do NPC com base na ação escolhida e estado de saúde.

---

### `utils/`
**Infraestrutura e Ferramentas Auxiliares**

- `utils.task_queue.AdaptiveTaskQueue`: Distribui o processamento por frame dividindo tarefas em prioridades (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`) e reduzindo dynamicamente o limite conforme o uso de CPU (`psutil`).
- `utils.rbc_monitor.RBCMonitorWindow`: Servidor web integrado e janela de telemetria em tempo real das decisões do RBC.
- `utils.analytics_manager.AnalyticsManager`: Registra estatísticas por partida em arquivo CSV (`analytics/match_history.csv`) e gera de forma assíncrona dashboards gráficos (`analytics/dashboard.png`) via Matplotlib.
- `utils.action_guards`: Guardiões lógicos para otimizar disparo tático e cold start.

---

### `database/initializer.py`
**Utilitário de Inicialização**

Funções:
- `initialize_database(db_path, force_reset)`: Inicializa o banco de dados SQLite, realizando recuperações automáticas caso o arquivo esteja corrompido.
- `print_database_stats(db_path)`: Imprime relatório de estatísticas no console.

Uso:
```bash
python -m database.initializer
```

---

## 🔄 Fluxo de Dados e Decisão

```
┌──────────────────────────────────────────────────────────────────────────┐
│ JOGO (game/game.py)                                                      │
│ ┌────────────────────────────────────────────────────────────────────┐   │
│ │ update() → Enfileira tarefas na AdaptiveTaskQueue                   │   │
│ └────────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────┬───────────────────────────────────────┘
                                   │
                                   ├─ 1. Codifica percepção completa
                                   │
┌──────────────────────────────────▼───────────────────────────────────────┐
│ NPC_BRAIN (ai/npc_brain.py)                                             │
│ ┌────────────────────────────────────────────────────────────────────┐   │
│ │ decide_action() → Problem(dist, health, proj_threat, border...)    │   │
│ └──────────────────────────────────┬─────────────────────────────────┘   │
└────────────────────────────────────┼─────────────────────────────────────┘
                                     │
┌────────────────────────────────────▼─────────────────────────────────────┐
│ RBC_ENGINE (ai/rbc_engine.py)                                            │
│ ┌────────────────────────────────────────────────────────────────────┐   │
│ │ decide_action()                                                    │   │
│ │   ├─ Cold Start (Episódios 0..4) → Macros estocásticos              │   │
│ │   ├─ Epsilon-Greedy (Episódios 5+)                                 │   │
│ │   ├─ Recupera casos (threshold=0.45) e adapta                      │   │
│ │   └─ Solution(action, params)                                      │   │
│ └──────────────────────────────────┬─────────────────────────────────┘   │
└────────────────────────────────────┼─────────────────────────────────────┘
                                     │
┌────────────────────────────────────▼─────────────────────────────────────┐
│ DATABASE (database/case_database.py)                                     │
│ ┌────────────────────────────────────────────────────────────────────┐   │
│ │ get_similar_cases()                                                │   │
│ │   ├─ SELECT * FROM rbc_cases                                       │   │
│ │   ├─ Métrica de similaridade ponderada por 12 fatores              │   │
│ │   └─ Ranking ponderado por similaridade × reward                   │   │
│ └──────────────────────────────────┬─────────────────────────────────┘   │
└────────────────────────────────────┼─────────────────────────────────────┘
                                     │
┌────────────────────────────────────▼─────────────────────────────────────┐
│ SQLITE (npc_cases.db)                                                    │
│ ┌────────────────────────────────────────────────────────────────────┐   │
│ │ Armazena: rbc_cases (conhecimento) + match_history (métricas)      │   │
│ └────────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────┘

                    APRENDIZADO (report_outcome + learn)
```
