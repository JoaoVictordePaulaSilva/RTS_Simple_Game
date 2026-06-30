# Fila de Prioridades - Sistema de Gerenciamento de Tarefas

## 🎯 Problema Identificado

Você tem **picos de CPU** porque todas as tarefas (RBC, física, colisões, renderização) executam **simultaneamente** cada frame. Isso causa:
- Travamentos esporádicos
- Uso inconsistente de CPU
- Difícil escalar para múltiplos NPCs

## ✅ Solução: TaskQueue com Prioridades

Um sistema que distribui tarefas ao longo dos frames, limitando processamento por frame para evitar picos.

### Características

| Feature | Benefício |
|---------|-----------|
| **Fila de Prioridades** | Tarefas críticas sempre executam primeiro |
| **Limite de Tarefas/Frame** | Distribui carga ao longo do tempo |
| **Adaptativo** | Reduz/aumenta carga baseado em CPU em tempo real |
| **Sem Travamentos** | Tarefas podem ficar para o próximo frame |

## 🚀 Quick Start

### 1. Instalação de Dependência

```bash
pip install psutil  # Para monitoramento de CPU
```

### 2. Uso Básico

```python
from utils.task_queue import AdaptiveTaskQueue, TaskPriority

# Inicializa
task_queue = AdaptiveTaskQueue(
    initial_tasks_per_frame=5,  # Max 5 tarefas não-críticas por frame
    cpu_threshold=0.75,          # Reduz se CPU > 75%
    debug=True                   # Mostra logs
)

# No loop do jogo
for frame in range(60 * 60):  # 60 segundos a 60fps
    # Monitora CPU e ajusta automaticamente
    cpu_usage = get_cpu_usage()
    task_queue.update_cpu_usage(cpu_usage)
    
    # Enfileira tarefas
    task_queue.add(
        func=npc.brain.decide_action,
        args=(player,),
        priority=TaskPriority.HIGH,
        name="npc_ai"
    )
    
    task_queue.add(
        func=update_physics,
        priority=TaskPriority.MEDIUM,
        name="physics"
    )
    
    # Processa (executa tarefas até o limite)
    task_queue.process_frame()
    
    # Renderiza depois
    render()
```

## 📊 Níveis de Prioridade

### CRITICAL (0) ⛔ - Sempre Executa
- Entrada do jogador
- Física do jogador
- Detecção de colisões
- **Nunca é adiada!**

### HIGH (1) 🔥 - Executar ASAP
- Decisão do NPC (RBC)
- Física do NPC importante
- Ações críticas para gameplay

### MEDIUM (2) 📌 - Normal
- Atualização de projéteis
- Animações
- Lógica secundária

### LOW (3) 💤 - Pode Esperar
- Logging e debug
- UI updates não essenciais
- Estatísticas

## 📈 Exemplo de Distribuição

```
Frame 1: [CRITICAL] + [HIGH] + [HIGH] + [MEDIUM] + [MEDIUM]  ← 5 tarefas
Frame 2: [CRITICAL] + [HIGH] + [MEDIUM]                      ← 3 tarefas
Frame 3: [CRITICAL] + [HIGH] + [MEDIUM] + [LOW] + [LOW]      ← 5 tarefas
                                        ↑ Adiadas do Frame 2 ↑
```

## 🔧 Configuração Recomendada

```python
# Seu caso: RTS Pygame com 1 NPC
task_queue = AdaptiveTaskQueue(
    initial_tasks_per_frame=5,
    cpu_threshold=0.70,  # Mais sensível para reduzir
    debug=False
)
```

## 📊 Monitoramento

```python
# Ver estatísticas de execução
stats = task_queue.get_stats()

print(f"📊 Estatísticas:")
print(f"  Total executadas: {stats['total_executed']}")
print(f"  Total adiadas: {stats['deferred']}")
print(f"  Tarefas na fila: {stats['queue_size']}")
print(f"  CPU atual: {stats['cpu_usage']:.1%}")
print(f"  Por prioridade: {stats['by_priority']}")
```

## 🎛️ Ajuste Fino

### Se ainda há picos:
```python
# Reduz limite
task_queue.set_max_tasks_per_frame(3)

# Ou ajusta threshold de CPU
task_queue.cpu_threshold = 0.65  # Mais agressivo
```

### Se CPU está baixa:
```python
# Aumenta limite manualmente
task_queue.set_max_tasks_per_frame(10)
```

## 🔍 Debugando

```python
# Ativa logs detalhados
task_queue = AdaptiveTaskQueue(debug=True)

# Após cada frame, você verá:
# [TASK] npc_ai (ID:0, Prioridade:HIGH) enfileirada
# [FRAME] Executadas: 5, Adiadas: 2, Críticas: 1
# [ADAPTIVE] CPU alta (78.5%). Reduzindo tarefas: 5 → 4
```

## ❓ Perguntas Comuns

**P: Por quanto tempo uma tarefa fica adiada?**
R: Até haver espaço na fila. Com limite de 5/frame e ~10 tarefas, tarefas LOW podem ficar ~2 frames.

**P: E se eu adicionar 100 tarefas?**
R: O sistema adapta. Começa reduzindo o limite. Tarefas não-críticas começam a ficar muito atrasadas (você vê isso em `stats['deferred']`).

**P: Isso afeta o gameplay?**
R: Não! Tarefas críticas (entrada, colisões) **nunca** são adiadas. Outras são imperceptíveis.

**P: Quanto melhora em relação aos picos?**
R: Em seu caso, você deve ver:
- Picos reduzidos de ~100% para ~75-80% consistente
- CPU mais previsível
- Menos travamentos

## 📚 Próximos Passos

1. Copie `task_queue.py` para seu projeto
2. Instale: `pip install psutil`
3. Adapte o loop do `jogo.py` seguindo exemplos em `docs/examples/task_queue_integration.py`
4. Teste com `debug=True` para entender o fluxo
5. Ajuste `initial_tasks_per_frame` conforme necessário
6. Considere: Pode ser útil para futuros NPCs também!

---

**Criado para:** RTS em Pygame
**Data:** 2026-06-23
**Compatibilidade:** Python 3.8+
