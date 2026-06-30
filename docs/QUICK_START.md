# 🚀 Quick Start - Fila de Prioridades

## O Que Foi Criado?

| Arquivo | Propósito |
|---------|-----------|
| **task_queue.py** | 🎯 Motor principal - copie para seu projeto |
| **TASK_QUEUE_README.md** | 📖 Documentação completa |
| **INTEGRATION_GUIDE.md** | 🔧 Como integrar no jogo.py |
| **test_task_queue.py** | ✅ Testes - valida que tudo funciona |
| **docs/examples/task_queue_integration.py** | 💡 Exemplos práticos |

## 3 Passos para Começar

### ✅ PASSO 1: Instalar Dependência (1 min)

```bash
pip install psutil
```

### ✅ PASSO 2: Testar o Sistema (2 min)

```bash
python -m tests.test_task_queue
```

Você verá:
```
✅ TODOS OS TESTES PASSARAM!
```

### ✅ PASSO 3: Integrar no jogo.py (5-10 min)

Siga **INTEGRATION_GUIDE.md** passo a passo:

1. Adicione imports
2. Inicialize TaskQueue no `__init__`
3. Refatore o método `update()` para enfileirar tarefas
4. Chame `task_queue.process_frame()` após enfileirar

## Exemplo Mínimo (Copia e Cola)

```python
from utils.task_queue import AdaptiveTaskQueue, TaskPriority
import psutil
import os

# No __init__
self.task_queue = AdaptiveTaskQueue(initial_tasks_per_frame=5, debug=False)
self.process = psutil.Process(os.getpid())

# No update()
def get_cpu_usage():
    try:
        return self.process.cpu_percent(interval=0.01) / 100.0
    except:
        return 0.0

# Monitorar CPU
cpu_usage = get_cpu_usage()
self.task_queue.update_cpu_usage(cpu_usage)

# Enfileirar tarefas
self.task_queue.add(
    func=self.handle_input,
    priority=TaskPriority.CRITICAL,
    name="input"
)

self.task_queue.add(
    func=self._update_npc_ai,
    args=(dt,),
    priority=TaskPriority.HIGH,
    name="npc_ai"
)

# Processar
self.task_queue.process_frame()
```

## Valores de Prioridade Prontos

Copie e use:

```python
# Sua situação: 1 NPC, jogo RTS simples
task_queue = AdaptiveTaskQueue(
    initial_tasks_per_frame=5,
    cpu_threshold=0.70,
    debug=False
)
```

| Situação | inicial_tasks | cpu_threshold |
|----------|--------------|----------------|
| 1 NPC simples | 5 | 0.70 |
| 3-5 NPCs | 8 | 0.75 |
| Muitos NPCs | 12 | 0.80 |
| Mobile/Fraco | 3 | 0.60 |

## Resultado Esperado

### Antes (Sem Fila)
```
CPU: 🔴 100% (picos)
Travamentos: Ocasionais
FPS: Instável
```

### Depois (Com Fila)
```
CPU: 🟢 75-80% (estável)
Travamentos: Nenhum
FPS: Consistente
```

## Próximas Melhorias (Opcional)

- [ ] Adicionar 2º NPC (use HIGH priority)
- [ ] Plotar gráfico de CPU antes/depois
- [ ] Experimentar diferentes `initial_tasks`

## Ajuda

**Não funciona?** Verifique:
1. `pip list | grep psutil` (instalado?)
2. `python -m tests.test_task_queue` (testes passam?)
3. Debug: mude `debug=True` para ver logs

**Muita latência?** Aumente:
```python
task_queue.set_max_tasks_per_frame(8)
```

**Ainda picos?** Reduza:
```python
task_queue.set_max_tasks_per_frame(3)
```

---

**Status:** ✅ Pronto para usar  
**Tempo para integração:** ~10 minutos  
**Compatibilidade:** Python 3.8+, Pygame 2.0+
