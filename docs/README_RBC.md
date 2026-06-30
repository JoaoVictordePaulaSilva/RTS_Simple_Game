# RTS Tanks com RBC (Raciocínio Baseado em Casos)

## 📋 Visão Geral

Sistema de IA para NPC em jogo RTS implementando **RBC (Raciocínio Baseado em Casos)** integrado com **SQLite** para persistência de conhecimento.

## 🏗️ Arquitetura

```
main.py                    (Novo ponto de entrada)
├── game/                  (Loop principal do jogo)
├── ai/                    (Interface de IA do NPC e motor RBC)
├── database/              (Gerenciamento SQLite)
└── db_init.py             (Inicialização do banco)
```

## 📁 Descrição dos Arquivos

### `database/`
**Gerenciamento de persistência em SQLite**

- Classe `CaseDatabase`: Interface para operações no BD
- Métodos principais:
  - `insert_case()`: Armazena novo caso
  - `get_similar_cases()`: Recupera casos similares (Recuperação RBC)
  - `_calculate_similarity()`: Calcula similaridade entre problema e caso
  - `update_case_usage()`: Atualiza estatísticas de sucesso

**Tabelas:**
- `rbc_cases`: Armazena casos (problema + solução + resultado)
- `game_sessions`: Metadados de sessões de jogo

### `ai/rbc_engine.py`
**Motor de Raciocínio Baseado em Casos**

Classes:
- `Problem`: Representa estado do jogo (distância, ângulo, saúde, visibilidade)
- `Solution`: Representa ação/solução (tipo de ação + parâmetros)
- `Outcome`: Representa resultado (sucesso, dano, tipo)

Classe `RBCEngine`:
- `decide_action()`: Decide ação usando RBC (com fallback para IA básica)
- `_adapt_solution()`: Adapta solução de caso anterior ao novo problema
- `learn()`: Armazena novo caso no banco

### `ai/npc_brain.py`
**Cérebro do NPC integrando RBC e IA básica**

Classe `NPCBrain`:
- `decide_action()`: Interface principal para decidir ações do NPC
- `_encode_problem()`: Converte estado do jogo em estrutura de Problema
- `_generate_fallback_action()`: IA básica hardcoded como fallback
- `report_outcome()`: Registra resultado para aprendizado
- `get_statistics()`: Retorna estatísticas de aprendizado

<!-- seed_cases removed: initial cases are now handled internally by `db_init.py` / `CaseDatabase`. -->

### `db_init.py`
**Utilitário de inicialização**

- `initialize_database()`: Cria BD com seed cases
- `print_database_stats()`: Exibe estatísticas

## 🔄 Fluxo de Funcionamento

### Decisão de Ação (por frame)
```
1. NPC codifica estado atual → Problem
2. RBC tenta recuperar casos similares
   ├─ Se encontra: Adapta melhor caso
   └─ Se não encontra: Usa IA básica como fallback
3. Executa ação
4. Aguarda resultado
```

### Aprendizado (após ação)
```
1. Jogador relata sucesso/fracasso da ação
2. RBC cria novo Caso e armazena no BD
3. Atualiza estatísticas de casos similares usados
4. BD cresce com experiência do NPC
```

## 📊 Tipos de Ações Disponíveis

| Ação | Descrição | Parâmetros |
|------|-----------|------------|
| `fire` | Dispara na direção atual | `angle_adjustment` |
| `align_and_fire` | Alinha antes de disparar | `target_angle`, `speed` |
| `pursue` | Persegue o jogador | `speed`, `rotate` |
| `search` | Procura pelo jogador | `rotation_direction` |
| `idle` | Fica parado | - |

## 📈 Evolução Temporal

### Jogo 1 (BD vazio)
- Usa 7 seed cases
- Comportamento previsível
- Cria ~10-20 novos casos

### Jogo 5-10 (BD ~100 casos)
- RBC funciona parcialmente
- Recupera alguns casos similares
- Comportamento melhora gradualmente

### Jogo 20+ (BD ~500+ casos)
- RBC é principal
- Comportamento adaptativo
- Aprendizado especializado por dificuldade

## 🧮 Cálculo de Similaridade

Implementa métrica ponderada baseada em:

```python
similarity = (
    distance_similarity × 0.4 +      # Distância: 40%
    angle_similarity × 0.2 +         # Ângulo: 20%
    health_similarity × 0.2 +        # Saúde: 20%
    visibility_match × 0.2           # Visibilidade: 20%
)
```

Intervalo: [0.0, 1.0] onde 1.0 = caso idêntico

## 🎮 Integração com Jogo

### Modificações em `jogo.py`

1. **Inicialização** (`__init__`):
```python
from ai.npc_brain import NPCBrain
self.npc_brain = NPCBrain("npc_cases.db")
```

2. **Decisão** (`_update_npc_ai`):
```python
action = self.npc_brain.decide_action(
    npc_x, npc_y, npc_angle, npc_health,
    player_x, player_y, player_health,
    player_visible, frames_since_last_seen,
    difficulty
)
self._execute_npc_action(action, dt)
```

3. **Aprendizado** (colisões):
```python
self.npc_brain.report_outcome(
    success=True,
    damage_dealt=25,
    damage_taken=0,
    outcome_type="hit",
    difficulty=difficulty
)
```

## 📊 Estatísticas Exibidas

Na tela de Game Over, o jogo exibe:
- Total de casos no banco
- Quantidade de seed cases vs casos aprendidos
- Taxa média de sucesso

## 🚀 Como Usar

### Primeira Execução
```bash
python jogo.py
```
O sistema automaticamente:
1. Verifica se BD existe
2. Se vazio, cria o esquema inicial do banco
3. Começa o jogo

### Resetar Banco (opcional)
```bash
python db_init.py --force-reset
```

### Ver Estatísticas
```bash
python db_init.py
```

## 🔧 Customização

### Adicionar Casos Iniciais
Para adicionar casos iniciais (seed) você pode:

- Inserir diretamente no banco via um script Python que use `CaseDatabase.insert_case()`;
- Ou estender `db_init.py` para popular casos quando o banco for criado.

Exemplo rápido (inserir via script):

```python
from database.case_database import CaseDatabase

db = CaseDatabase('npc_cases.db')
db.insert_case({
    'case_id': 'seed_custom',
    'problem_distance': 200.0,
    'problem_angle_diff': 10.0,
    'problem_npc_health': 100,
    'problem_player_health': 100,
    'problem_player_visible': True,
    'solution_action': 'align_and_fire',
    'solution_params': {},
    'result_success': True,
    'result_damage_dealt': 25,
    'difficulty': 'Normal',
})
```

### Ajustar Pesos de Similaridade
Em `database/case_database.py`, função `_calculate_similarity()`:

```python
weights = {
    "distance": 0.4,    # Aumentar para priorizar distância
    "angle": 0.2,
    "health": 0.2,
    "visibility": 0.2
}
```

### Adicionar Novas Ações
1. Defina em `ai/npc_brain.py`, método `_generate_fallback_action()`
2. Implemente execução em `_execute_npc_action()`

## 📈 Métricas Coletadas

O banco automaticamente rastreia:
- **Uso**: Quantas vezes cada caso foi usado
- **Sucesso**: Quantas vezes resultou em sucesso
- **Taxa de Sucesso**: Percentual de sucessos
- **Último Uso**: Timestamp do último uso
- **Dificuldade**: Associação com nível de dificuldade

## ✅ Clean Code Practices

✓ Separação de responsabilidades  
✓ Type hints em todas as funções  
✓ Docstrings em português/inglês  
✓ Nomes descritivos (sem abreviaturas)  
✓ Context managers para gerenciamento de recursos  
✓ Dataclasses para estruturas simples  
✓ Evita magic numbers (constantes nomeadas)  

## 🎯 Próximos Passos (Futuro)

1. **Análise de Dados**: Extrair insights do BD
2. **Visualização**: Gráficos de evolução do aprendizado
3. **Otimização**: Melhorar cálculo de similaridade
4. **Expansão**: Mais tipos de ação e parâmetros
5. **Comparação**: RBC vs IA tradicional
6. **Multiplayer**: Sincronizar BD entre sessões

## 📝 Licença
