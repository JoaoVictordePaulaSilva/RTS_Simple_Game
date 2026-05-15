# Estrutura do Projeto - RBC System

## 📂 Estrutura de Diretórios

```
d:\Projetos Facul\TCC\RTS em Pygames\
├── jogo.py                 (Arquivo principal do jogo)
├── database.py             (Gerenciamento SQLite)
├── rbc_engine.py          (Motor de RBC)
├── npc_brain.py           (Cérebro do NPC)
├── db_init.py             (Inicialização do BD)
├── test_rbc.py            (Testes unitários)
├── npc_cases.db           (Banco de dados SQLite - criado automaticamente)
├── requirements.txt       (Dependências Python)
├── README.md              (README original)
├── README_RBC.md          (Documentação do RBC)
└── ARQUITETURA.md         (Este arquivo)
```

## 📋 Descrição de Cada Arquivo

### `jogo.py` (820+ linhas)
**Arquivo principal do jogo**

Classes principais:
- `Tank`: Representa um tanque (jogador ou NPC)
- `Projectile`: Representa um projétil
- `NPCPerception`: Percepção sensorial do NPC
- `Button`: Botão da interface
- `Game`: Classe principal que orquestra tudo

Modificações para RBC:
- Import dos módulos: `npc_brain`, `db_init`
- Inicializa `NPCBrain` no `__init__`
- Chama `npc_brain.decide_action()` em `_update_npc_ai()`
- Reporta resultados em colisões via `npc_brain.report_outcome()`
- Exibe estatísticas RBC na tela de game over

---

### `database.py` (~230 linhas)
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

### `rbc_engine.py` (~200 linhas)
**Motor de Raciocínio Baseado em Casos**

Dataclasses:
- `Problem`: Estado do jogo (distance, angle_diff, healths, visibility)
- `Solution`: Ação (action, params)
- `Outcome`: Resultado (success, damage, type)

Classe principal:
- `RBCEngine`: Motor RBC

Métodos públicos:
- `decide_action(problem, fallback, difficulty)`: Recupera e adapta
- `learn(case_id, problem, solution, outcome, session_id, difficulty)`: Aprende
- `get_statistics()`: Retorna stats
- `close()`: Fecha BD

Métodos privados:
- `_adapt_solution(case, new_problem)`: Adapta solução anterior

Fluxo:
1. Recupera casos similares do BD
2. Se encontra: adapta melhor caso
3. Se não: usa fallback (IA básica)
4. Retorna solução a executar

---

### `npc_brain.py` (~220 linhas)
**Cérebro do NPC - Interface entre jogo e RBC**

Classe principal:
- `NPCBrain`: Interface de decisão do NPC

Métodos públicos:
- `decide_action(npc_x, npc_y, ..., difficulty)`: Decide ação via RBC
- `report_outcome(success, damage_dealt, damage_taken, ...)`: Registra resultado
- `set_session(session_id)`: Define sessão atual
- `get_statistics()`: Retorna stats
- `close()`: Fecha conexões

Métodos privados:
- `_encode_problem()`: Codifica estado do jogo como Problem
- `_generate_fallback_action()`: IA básica hardcoded
  - `player_not_visible`: search
  - `close_clear_shot`: fire
  - `medium_range`: align_and_fire
  - `long_range`: pursue
  - default: idle

Tipos de ações:
| Ação | Código |
|------|--------|
| fire | "fire" |
| align_and_fire | "align_and_fire" |
| pursue | "pursue" |
| search | "search" |
| idle | "idle" |

---

<!-- seed_cases removed: bootstrapping is now handled internally by the DB initialization. -->

---

### `db_init.py` (~60 linhas)
**Inicialização e utilitários do BD**

Funções:
- `initialize_database(db_path, force_reset)`: Cria BD com seed cases
- `print_database_stats(db_path)`: Exibe estatísticas

Uso:
```bash
python db_init.py                 # Inicializa se vazio
python db_init.py --force-reset   # Reseta tudo (opcional)
```

---

### `test_rbc.py` (~200 linhas)
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

### `npc_cases.db` (Banco de Dados)
**Banco SQLite criado automaticamente**

Criado automaticamente na primeira execução.
Contém:
- 7 seed cases iniciais
- Casos aprendidos durante o jogo

Tamanho inicial: ~20 KB
Cresce ~10 KB por jogo (dependendo de duração)

---

### `requirements.txt`
```
pygame==2.5.0
```

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

---

## 🔄 Fluxo de Dados

```
┌─────────────────────────────────────────────────────────┐
│ JOGO (jogo.py)                                          │
│ ┌───────────────────────────────────────────────────┐  │
│ │ update() → _update_npc_ai()                       │  │
│ └───────────────────────────────────────────────────┘  │
└──────────────┬──────────────────────────────────────────┘
               │
               ├─ codifica estado
               │
┌──────────────▼──────────────────────────────────────────┐
│ NPC_BRAIN (npc_brain.py)                                │
│ ┌───────────────────────────────────────────────────┐  │
│ │ decide_action()                                  │  │
│ │   └─ Problem(distance, angle, health...)        │  │
│ └───────────────────────────────────────────────────┘  │
└──────────────┬──────────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────────┐
│ RBC_ENGINE (rbc_engine.py)                              │
│ ┌───────────────────────────────────────────────────┐  │
│ │ decide_action()                                  │  │
│ │   ├─ recupera casos similares                   │  │
│ │   ├─ adapta melhor caso (ou fallback)           │  │
│ │   └─ Solution(action, params)                   │  │
│ └───────────────────────────────────────────────────┘  │
└──────────────┬──────────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────────┐
│ DATABASE (database.py)                                  │
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
│ │ Armazena: 7 seed cases + casos aprendidos       │  │
│ └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘

                    APRENDIZADO (feedback)

┌─────────────────────────────────────────────────────────┐
│ JOGO (colisão/evento)                                   │
│   npc_brain.report_outcome(success, damage, type)     │
└──────────────┬──────────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────────┐
│ RBC_ENGINE                                              │
│   learn(case_id, problem, solution, outcome)          │
└──────────────┬──────────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────────┐
│ DATABASE                                                │
│   insert_case(new_case_data)                          │
│   update_case_usage(case_id, success)                 │
└──────────────┬──────────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────────┐
│ SQLITE                                                  │
│   INSERT INTO rbc_cases VALUES (...)                  │
│   UPDATE rbc_cases SET usage_count, success_rate      │
└─────────────────────────────────────────────────────────┘
```

---

## 🎯 Princípios de Design

### 1. **Separação de Responsabilidades**
- `database.py`: Apenas I/O com BD
- `rbc_engine.py`: Apenas lógica RBC
- `npc_brain.py`: Apenas interface com jogo
- `jogo.py`: Apenas renderização e eventos

### 2. **Clean Code**
- ✅ Type hints em tudo
- ✅ Docstrings bilíngues
- ✅ Nomes descritivos
- ✅ Funções pequenas e focadas
- ✅ DRY (Don't Repeat Yourself)

### 3. **Extensibilidade**
- Fácil adicionar novos tipos de ações
- Fácil modificar cálculo de similaridade
- Fácil adicionar novos seed cases

### 4. **Testabilidade**
- Cada classe testável isoladamente
- `test_rbc.py` cobre funcionalidades principais
- BD isolado (não interfere com jogo)

---

## 📊 Estatísticas Coletadas

Cada caso armazena:
- **Problema**: distance, angle_diff, healths, visibility
- **Solução**: action_type, parameters
- **Resultado**: success, damage_dealt, damage_taken, outcome_type
- **Metadados**: timestamp, session_id, difficulty, usage_count, success_rate

Queries úteis:
```sql
-- Ações mais bem-sucedidas
SELECT action, AVG(success_rate) FROM rbc_cases GROUP BY action;

-- Casos mais usados
SELECT case_id, usage_count FROM rbc_cases ORDER BY usage_count DESC;

-- Aprendizado por dificuldade
SELECT difficulty, COUNT(*) FROM rbc_cases WHERE created_by='learned' GROUP BY difficulty;
```

---

## 🚀 Próximos Passos

1. **Análise de Dados**: Extrair insights do BD
2. **Visualização**: Gráficos de evolução
3. **Otimização**: Melhorar similaridade
4. **Expansão**: Mais ações e contextos
5. **Comparação**: RBC vs IA tradicional
6. **Documentação**: Relatório final TCC

