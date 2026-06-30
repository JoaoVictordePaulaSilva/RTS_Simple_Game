# Estrutura do Projeto - RBC System

## 📂 Estrutura de Diretórios

```
d:\Projetos Facul\TCC\RTS em Pygames\
├── main.py                (Novo ponto de entrada)
├── jogo.py                (Compatibilidade/launcher legado)
├── ai/                    (Camada de IA e RBC)
├── database/              (Persistência SQLite)
├── game/                  (Loop principal e entidades do jogo)
├── utils/                 (Ferramentas auxiliares)
├── db_init.py             (Inicialização do BD)
├── tests/                 (Testes unitários RBC e TaskQueue)
├── npc_cases.db           (Banco de dados SQLite - criado automaticamente)
├── README_RBC.md          (Documentação do RBC)
└── docs/ARQUITETURA.md    (Este arquivo)
```

## 📋 Descrição de Cada Arquivo

### `main.py`
**Arquivo principal do jogo**

Classe principal:
- `Game`: Classe principal que orquestra tudo

Modificações para a nova estrutura:
- Usa `game.game.Game`
- Mantém a inicialização centralizada no pacote `game`

---

### `database/`
**Gerenciamento de persistência em SQLite**

Classe principal:
- `CaseDatabase`: Interface com BD

Métodos públicos:
- `__init__(db_path)`: Inicializa conexão e cria tabelas
- `insert_case(case_data)`: Armazena novo caso
- `get_similar_cases(problem, threshold, limit)`: Recuperação RBC
- `update_case_usage(case_id, success)`: Atualiza estatísticas
- `get_statistics()`: Retorna stats do BD
- `close()`: Fecha conexão

Métodos privados:
- `_initialize_database()`: Cria tabelas e índices
- `_calculate_similarity(problem, case)`: Calcula similaridade [0,1]

Tabelas SQL:
```sql
rbc_cases (id, case_id, problem_distance, problem_angle_diff, 
           problem_npc_health, problem_player_health, 
           problem_player_visible, problem_frames_lost,
           solution_action, solution_params,
           result_success, result_damage_dealt, result_damage_taken,
           result_outcome, difficulty, session_id, timestamp,
           usage_count, success_count, success_rate, last_used,
           created_by)

game_sessions (session_id, start_time, end_time, difficulty,
               npc_final_health, player_final_health, npc_won,
               case_count_at_end, avg_similarity_used)
```

---

### `ai/`
**Motor de RBC e cérebro do NPC**

Dataclasses:
- `Problem`: Estado do jogo (distance, angle_diff, healths, visibility)
- `Solution`: Ação (action, params)
- `Outcome`: Resultado (success, damage, type)

Classe principal:
- `RBCEngine`: Motor RBC
- `NPCBrain`: Interface entre jogo e RBC

Métodos públicos:
- `decide_action(problem, fallback, difficulty)`: Recupera e adapta
- `learn(case_id, problem, solution, outcome, session_id, difficulty)`: Aprende
- `report_outcome(success, damage_dealt, damage_taken, ...)`: Registra resultado
- `get_statistics()`: Retorna stats
- `close()`: Fecha BD

Fluxo:
1. Recupera casos similares do BD
2. Se encontra: adapta melhor caso
3. Se não: usa fallback (IA básica)
4. Retorna solução a executar

---

### `game/`
**Loop principal, entidades e interface do jogo**

Componentes principais:
- `game.game.Game`
- `game.entities.Tank`
- `game.entities.Projectile`
- `game.perception.NPCPerception`
- `game.ui.button.Button`
- `game.ui.npc_face.NPCFace`

Responsabilidades:
- Estado principal do jogo
- IA do NPC em `_update_npc_ai()`
- Colisões e aprendizado em `report_outcome()`
- Interface, menus e telas de fim de jogo

---

### `utils/`
**Ferramentas auxiliares**

Componentes:
- `utils.task_queue`
- `utils.rbc_monitor`

Responsabilidades:
- Priorização e distribuição de tarefas por frame
- Monitoramento de estatísticas do RBC

---

### `db_init.py`
**Utilitário de inicialização**

Funções:
- `initialize_database(db_path, force_reset)`: Cria BD com seed cases
- `print_database_stats(db_path)`: Exibe estatísticas

Uso:
```bash
python db_init.py
python db_init.py --force-reset
```

---

### `test_rbc.py`
**Suite de testes unitários**

Testes:
1. `test_database_initialization()`: Cria BD vazio
2. `test_case_insertion()`: Insere casos
3. `test_similarity_calculation()`: Calcula similaridade
4. `test_rbc_engine()`: Motor RBC básico
5. `test_npc_brain()`: Cérebro do NPC

Resultado esperado:
```
RESULTADOS: 5 passou(ram), 0 falhou/falharam
```

---

### `test_task_queue.py`
**Suite de testes da fila de tarefas**

Valida:
- Prioridades
- Adaptabilidade
- Performance
- Estatísticas
- Tarefas críticas nunca adiadas

---

### `npc_cases.db` (Banco de Dados)
**Banco SQLite criado automaticamente**

Criado automaticamente na primeira execução.
Contém:
- 7 seed cases iniciais
- Casos aprendidos durante o jogo

Tamanho inicial: ~20 KB
Cresce ~10 KB por jogo (dependendo de duração)

---

### `README_RBC.md`
**Documentação completa do sistema RBC**

Seções:
- Visão geral
- Arquitetura
- Descrição de arquivos
- Fluxo de funcionamento
- Tipos de ações
- Evolução temporal
- Cálculo de similaridade
- Integração com jogo
- Como usar
- Customização
- Métricas coletadas

## 🔄 Fluxo de Dados

```
┌─────────────────────────────────────────────────────────┐
│ JOGO (game/game.py)                                     │
│ ┌───────────────────────────────────────────────────┐  │
│ │ update() → _update_npc_ai()                       │  │
│ └───────────────────────────────────────────────────┘  │
└──────────────┬──────────────────────────────────────────┘
               │
               ├─ codifica estado
               │
┌──────────────▼──────────────────────────────────────────┐
│ NPC_BRAIN (ai/npc_brain.py)                            │
│ ┌───────────────────────────────────────────────────┐  │
│ │ decide_action()                                  │  │
│ │   └─ Problem(distance, angle, health...)        │  │
│ └───────────────────────────────────────────────────┘  │
└──────────────┬──────────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────────┐
│ RBC_ENGINE (ai/rbc_engine.py)                           │
│ ┌───────────────────────────────────────────────────┐  │
│ │ decide_action()                                  │  │
│ │   ├─ recupera casos similares                   │  │
│ │   ├─ adapta melhor caso (ou fallback)           │  │
│ │   └─ Solution(action, params)                   │  │
│ └───────────────────────────────────────────────────┘  │
└──────────────┬──────────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────────┐
│ DATABASE (database/case_database.py)                    │
│ ┌───────────────────────────────────────────────────┐  │
│ │ get_similar_cases()                              │  │
│ │   ├─ SELECT * FROM rbc_cases                    │  │
│ │   ├─ calcula similaridade de cada                │  │
│ │   └─ retorna top N                               │  │
│ └───────────────────────────────────────────────────┘  │
└──────────────┬──────────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────────┐
│ SQLITE (npc_cases.db)                                   │
│ ┌───────────────────────────────────────────────────┐  │
│ │ Armazena: seed cases + casos aprendidos         │  │
│ └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘

                    APRENDIZADO (feedback)
```

---

## 🎯 Próximos Passos

- Expandir métricas de aprendizagem
- Criar gráficos de evolução do NPC
- Separar exemplos de integração em arquivos menores dentro de `docs/`
