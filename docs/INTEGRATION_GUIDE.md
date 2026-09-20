# Documentação de Integração da Fila de Tarefas (TaskQueue)

## 📌 Visão Geral

A classe `AdaptiveTaskQueue` (`utils/task_queue.py`) está integrada ao loop principal do jogo em `game/game.py`. Seu objetivo é evitar picos de consumo de CPU e garantir uma taxa de quadros (FPS) estável, escalonando o processamento de tarefas por nível de prioridade.

---

## 🏗️ Como a TaskQueue é Inicializada

No construtor `__init__` da classe `Game` em `game/game.py`:

```python
from utils.task_queue import AdaptiveTaskQueue, TaskPriority
import psutil
import os

# Inicialização com limite dinâmico inicial de 5 tarefas por frame e threshold de CPU em 70%
self.task_queue = AdaptiveTaskQueue(
    initial_tasks_per_frame=5,
    cpu_threshold=0.70,
    debug=False
)
self.process = psutil.Process(os.getpid())
```

---

## ⚡ Monitoramento de Uso de CPU

A amostragem de CPU é feita através do método `get_cpu_usage()`:

```python
def get_cpu_usage(self) -> float:
    """Retorna a porcentagem de uso de CPU do processo (0.0 a 1.0)."""
    try:
        return self.process.cpu_percent(interval=0.01) / 100.0
    except Exception:
        return 0.0
```

---

## 🔄 Fluxo de Escalonamento em `update(dt)`

A cada frame no estado `"playing"`, as rotinas do jogo são convertidas em tarefas com prioridades distintas e adicionadas à fila:

```python
def update(self, dt):
    if self.state == "playing":
        self.frame_counter += 1
        self._monitor_update_timer += dt

        # 1. Atualização do uso de CPU no motor da fila
        cpu_usage = self.get_cpu_usage()
        self.task_queue.update_cpu_usage(cpu_usage)

        # 2. Enfileiramento de tarefas por prioridade
        
        # CRÍTICO: Entrada do jogador (teclas de movimento)
        self.task_queue.add(
            func=self._handle_player_input,
            args=(dt,),
            priority=TaskPriority.CRITICAL,
            name="player_input"
        )
        
        # CRÍTICO: Atualização de cooldowns das armas
        self.task_queue.add(
            func=self._update_players_cooldown,
            args=(dt,),
            priority=TaskPriority.CRITICAL,
            name="players_cooldown"
        )
        
        # ALTA: Percepção espacial e Tomada de Decisão RBC do NPC
        self.task_queue.add(
            func=self._update_npc_perception_and_ai,
            args=(dt,),
            priority=TaskPriority.HIGH,
            name="npc_perception_ai"
        )
        
        # MÉDIA: Atualização da posição física dos projéteis
        self.task_queue.add(
            func=self._update_all_projectiles,
            args=(dt,),
            priority=TaskPriority.MEDIUM,
            name="update_projectiles"
        )
        
        # CRÍTICO: Detecção de colisões entre projéteis e tanques
        self.task_queue.add(
            func=self._check_all_collisions,
            priority=TaskPriority.CRITICAL,
            name="collision_check"
        )
        
        # CRÍTICO: Verificação de condição de fim de jogo (Game Over)
        self.task_queue.add(
            func=self._update_game_state,
            priority=TaskPriority.CRITICAL,
            name="game_state_check"
        )
        
        # BAIXA: Telemetria Web periodicamente
        self.task_queue.add(
            func=self._update_rbc_monitor_periodic,
            priority=TaskPriority.LOW,
            name="rbc_monitor_update"
        )

        # 3. Execução das tarefas do frame respeitando o limite
        self.task_queue.process_frame()
```

---

## 🎯 Resumo das Prioridades Aplicadas

| Tarefa | Nome do Callback | Prioridade | Comportamento |
| :--- | :--- | :--- | :--- |
| **Input do Jogador** | `_handle_player_input` | `CRITICAL` | Executa no mesmo frame. Nunca é adiada. |
| **Cooldown de Armas** | `_update_players_cooldown` | `CRITICAL` | Executa no mesmo frame. |
| **Colisões Físicas** | `_check_all_collisions` | `CRITICAL` | Executa no mesmo frame para evitar bugs de colisão. |
| **Fim de Jogo** | `_update_game_state` | `CRITICAL` | Executa no mesmo frame. |
| **IA & Percepção NPC** | `_update_npc_perception_and_ai` | `HIGH` | Executada prioritariamente após tarefas críticas. |
| **Movimento de Projéteis**| `_update_all_projectiles` | `MEDIUM` | Escalonada de forma fluida nos quadros. |
| **Telemetria Web** | `_update_rbc_monitor_periodic` | `LOW` | Executada quando há folga de CPU. |

---

## ✅ Benefícios Obtidos

1. **Mitigação de Picos de Processamento**: Tarefas de menor prioridade são adiadas sem prejudicar a responsabilidade dos controles ou a detecção de colisões.
2. **Estabilidade de FPS**: O algoritmo reduz dinamicamente o número de tarefas secundárias por frame se a CPU ultrapassar 70%.
3. **Escalabilidade**: A estrutura facilita a adição de múltiplos NPCs no futuro simplesmente enfileirando iterações como tarefas `HIGH`.
