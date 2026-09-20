# RTS Tanks com RBC (Raciocínio Baseado em Casos)

## 📋 Visão Geral

Sistema de Inteligência Artificial para NPC em jogo RTS implementando **Raciocínio Baseado em Casos (RBC / CBR)** integrado ao **SQLite** para persistência, evolução contínua de conhecimento e aprendizado adaptativo sob política $\epsilon$-greedy.

---

## 🏗️ Arquitetura

```text
main.py                    (Ponto de entrada da aplicação)
├── game/                  (Loop do jogo, percepção tática, entidades e UI)
├── ai/                    (Cérebro do NPC, motor RBC e modelos de dados)
├── database/              (Gerenciamento SQLite, tabelas e inicialização)
└── utils/                 (TaskQueue, Web RBC Monitor e AnalyticsManager)
```

---

## 📁 Descrição dos Módulos

### `database/`
**Gerenciamento de persistência em SQLite**

- **Classe `CaseDatabase`**: Interface para operações CRUD no banco `npc_cases.db`.
- **Métodos Principais**:
  - `insert_case()`: Armazena novos casos aprendidos durante partidas.
  - `get_similar_cases()`: Recupera os $K$ casos mais semelhantes ponderando similaridade perceptiva e média de recompensa acumulada (`avg_reward`).
  - `_calculate_similarity()`: Calcula a similaridade ponderada entre o vetor de problema atual e os casos salvos.
  - `update_case_usage()`: Atualiza o contador de uso, taxa de sucesso e recompensa acumulada do caso.
  - `insert_match_record()`: Registra dados estatísticos de partidas finalizadas na tabela `match_history`.

**Tabelas:**
- `rbc_cases`: Armazena a base de casos (Problema, Solução, Resultado, Pesos e Recompensas).
- `match_history`: Histórico de partidas para análise temporal de progresso (vitórias, dano, reward e epsilon).

---

### `ai/rbc_engine.py`
**Motor de Raciocínio Baseado em Casos (RBC)**

Dataclasses (`ai/rbc_models.py`):
- **`Problem`**: Representa a percepção completa do NPC:
  - `distance`, `angle_diff`: Distância e alinhamento em relação ao jogador.
  - `npc_health`, `player_health`: Estados de vida.
  - `player_visible`, `frames_lost`: Visibilidade do alvo.
  - `nearest_projectile_distance`, `nearest_projectile_angle`, `projectiles_nearby_count`: Percepção de projéteis inimigos.
  - `projectile_threat_active`, `projectile_threat_distance`: Sinalização de ameaça iminente de projétil.
  - `edge_distance_top`, `edge_distance_bottom`, `nearest_edge_distance`: Distância em relação às paredes da arena.
  - `border_pressure`, `border_side`: Pressão de encurralamento por borda.
  - `closing_speed`: Velocidade de aproximação relativa.
  - `recent_actions`: Histórico das últimas ações executadas.
- **`Solution`**: Ação tática (`action`, `params`).
- **`Outcome`**: Resultado numérico (`success`, `damage_dealt`, `damage_taken`, `outcome_type`, `reward`).

**Classe `RBCEngine`**:
- **Cold Start**: Nos primeiros 5 episódios, executa macros estocásticos para explorar a arena e criar a base inicial de conhecimento.
- **$\epsilon$-Greedy Decay**: Alterna entre exploração (Top-3 casos) e explotação (Top-1 caso), decaindo a taxa de exploração ($\epsilon$) ao término de cada partida.
- `decide_action()`: Decide a ação a ser executada com trava de permanência por quadros (`action_hold_frames`).
- `learn()`: Valida e armazena casos de alto valor tático no banco de dados.

---

### `ai/npc_brain.py`
**Cérebro do NPC e Cálculo de Recompensa**

- Encoda a percepção espacial da arena no objeto `Problem`.
- Trata **comportamentos ineficazes** (detecta se o NPC ficou travado na mesma posição ou repetindo ações sem causar dano, aplicando penalidades e elevando temporariamente a taxa de exploração $\epsilon$).
- Calcula a função de recompensa do agente com base em dano infligido, dano sofrido, esquiva de projéteis e posicionamento relativo às paredes.

---

### `database/initializer.py`
**Utilitário de Inicialização**

- `initialize_database()`: Garante a criação do banco de dados e recupera automaticamente o arquivo se for detectada corrupção de dados.
- `print_database_stats()`: Exibe estatísticas de casos no console.

---

## 📊 Tipos de Ações Disponíveis

| Ação | Descrição | Parâmetros Principais |
|------|-----------|-----------------------|
| `fire` | Dispara projétil direto no alvo visível | `{}` |
| `align_and_fire` | Ajusta posicionamento e dispara | `{}` |
| `pursue` | Persegue o jogador na arena | `speed`, `direction` |
| `search` | Realiza varredura para reencontrar o jogador | `direction`, `speed` |
| `wander` | Movimenta-se para explorar novos ângulos | `direction`, `speed` |
| `random_rotate` | Movimentação estocástica de varredura | `direction` |
| `evade_projectile` | Esquiva lateral imediata contra projéteis inimigos | `direction`, `speed` |
| `idle` | Mantém posição por instante estratégico | `{}` |

---

## 🧮 Cálculo de Similaridade

A similaridade $S \in [0.0, 1.0]$ entre o problema atual e um caso armazenado é calculada no `CaseDatabase` por uma combinação ponderada de fatores:

```python
similarity_weights = {
    "distance": 0.35,       # Distância vertical até o jogador
    "health": 0.15,         # Diferença de saúde dos tanques
    "visibility": 0.15,     # Coincidência de estado de visibilidade
    "border": 0.10,         # Pressão e proximidade de paredes
    "proj_dist": 0.10,      # Distância ao projétil mais próximo
    "proj_angle": 0.05,     # Ângulo do projétil inimigo
    "proj_count": 0.05,     # Quantidade de projéteis próximos
    "closing_speed": 0.05,  # Velocidade de aproximação relativa
}
```

---

## 🚀 Como Executar

### 1. Iniciar o Jogo
```bash
python main.py
```

### 2. Verificar Estatísticas da Base RBC
```bash
python -m database.initializer
```

---

## 📈 Visualização de Analytics e Telemetria

1. **Dashboard Gráfico**: Ao final de cada partida, o `AnalyticsManager` (`utils/analytics_manager.py`) gera e atualiza automaticamente o painel visual `analytics/dashboard.png` com gráficos de recompensa, taxa de vitórias, crescimento de casos e eficiência de combate.
2. **Web RBC Monitor**: O jogo inicia um servidor de telemetria em segundo plano que exibe os logs de decisões RBC no navegador.
