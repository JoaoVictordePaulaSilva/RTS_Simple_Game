"""
Fila de Prioridades para Gerenciamento de Tarefas do Jogo.
Priority Queue for game task management to prevent CPU spikes.
"""

import heapq
import time
from enum import Enum
from typing import Callable, Any, Optional, List, Dict
from dataclasses import dataclass, field


class TaskPriority(Enum):
    """Níveis de prioridade para tarefas."""
    CRITICAL = 0    # Físicas, entrada do jogador (sempre executam)
    HIGH = 1        # RBC do NPC, colisões importantes
    MEDIUM = 2      # Atualização de posições, animações
    LOW = 3         # Logging, UI, operações não críticas


@dataclass(order=True)
class Task:
    """Representa uma tarefa na fila."""
    priority: int
    timestamp: float = field(default_factory=time.time)
    task_id: int = field(default_factory=lambda: id(object()))
    name: str = field(default="unnamed")
    func: Callable = field(default=None, compare=False)
    args: tuple = field(default_factory=tuple, compare=False)
    kwargs: dict = field(default_factory=dict, compare=False)
    
    def execute(self) -> Any:
        """Executa a tarefa."""
        if self.func is None:
            return None
        try:
            return self.func(*self.args, **self.kwargs)
        except Exception as e:
            print(f"Erro ao executar tarefa '{self.name}': {e}")
            return None


class TaskQueue:
    """
    Gerenciador de fila de prioridades com controle de distribuição de tarefas.
    Limita o processamento por frame para evitar picos de CPU.
    """
    
    def __init__(self, max_tasks_per_frame: int = 5, debug: bool = False):
        """
        Inicializa a fila de tarefas.
        
        Args:
            max_tasks_per_frame: Máximo de tarefas não-críticas por frame
            debug: Ativa logging de debug
        """
        self.queue: List[Task] = []
        self.max_tasks_per_frame = max_tasks_per_frame
        self.debug = debug
        self.task_counter = 0
        self.executed_this_frame = 0
        self.stats = {
            "total_executed": 0,
            "total_queued": 0,
            "deferred": 0,
            "by_priority": {p.name: 0 for p in TaskPriority}
        }
    
    def add(self, 
            func: Callable, 
            priority: TaskPriority = TaskPriority.MEDIUM,
            name: str = None,
            args: tuple = (),
            kwargs: dict = None) -> int:
        """
        Adiciona uma tarefa à fila.
        
        Args:
            func: Função a executar
            priority: Nível de prioridade
            name: Nome descritivo da tarefa
            args: Argumentos posicionais
            kwargs: Argumentos nomeados
            
        Returns:
            ID da tarefa
        """
        if kwargs is None:
            kwargs = {}
        
        task_id = self.task_counter
        self.task_counter += 1
        
        task = Task(
            priority=priority.value,
            task_id=task_id,
            name=name or func.__name__,
            func=func,
            args=args,
            kwargs=kwargs
        )
        
        heapq.heappush(self.queue, task)
        self.stats["total_queued"] += 1
        self.stats["by_priority"][priority.name] += 1
        
        if self.debug:
            print(f"[TASK] {task.name} (ID:{task_id}, Prioridade:{priority.name}) enfileirada")
        
        return task_id
    
    def process_frame(self) -> Dict[str, Any]:
        """
        Processa tarefas para este frame.
        Tarefas críticas sempre executam. Outras são limitadas por max_tasks_per_frame.
        
        Returns:
            Dicionário com estatísticas de execução
        """
        self.executed_this_frame = 0
        frame_stats = {
            "executed": 0,
            "deferred": 0,
            "critical": 0,
            "by_priority": {p.name: 0 for p in TaskPriority}
        }
        
        # Separa críticas das não-críticas
        critical_tasks = []
        deferred_queue = []
        
        while self.queue:
            task = heapq.heappop(self.queue)
            if task.priority == TaskPriority.CRITICAL.value:
                critical_tasks.append(task)
            else:
                deferred_queue.append(task)
        
        # Executa críticas sempre
        for task in critical_tasks:
            task.execute()
            self.executed_this_frame += 1
            frame_stats["executed"] += 1
            frame_stats["critical"] += 1
            
            priority_name = TaskPriority(task.priority).name
            frame_stats["by_priority"][priority_name] += 1
        
        # Executa até max_tasks_per_frame das não-críticas
        remaining_capacity = self.max_tasks_per_frame
        while deferred_queue and remaining_capacity > 0:
            task = deferred_queue.pop(0)
            task.execute()
            self.executed_this_frame += 1
            remaining_capacity -= 1
            frame_stats["executed"] += 1
            
            priority_name = TaskPriority(task.priority).name
            frame_stats["by_priority"][priority_name] += 1
        
        # Re-enfileira tarefas não executadas
        for task in deferred_queue:
            heapq.heappush(self.queue, task)
            frame_stats["deferred"] += 1
        
        self.stats["deferred"] += frame_stats["deferred"]
        self.stats["total_executed"] += frame_stats["executed"]
        
        if self.debug and (frame_stats["executed"] > 0 or frame_stats["deferred"] > 0):
            print(f"[FRAME] Executadas: {frame_stats['executed']}, "
                  f"Adiadas: {frame_stats['deferred']}, "
                  f"Críticas: {frame_stats['critical']}")
        
        return frame_stats
    
    def get_queue_size(self) -> int:
        """Retorna o tamanho atual da fila."""
        return len(self.queue)
    
    def get_stats(self) -> Dict:
        """Retorna estatísticas de execução."""
        return {
            **self.stats,
            "queue_size": self.get_queue_size()
        }
    
    def set_max_tasks_per_frame(self, max_tasks: int) -> None:
        """Ajusta dinamicamente o máximo de tarefas por frame."""
        self.max_tasks_per_frame = max(1, max_tasks)
    
    def clear(self) -> None:
        """Limpa toda a fila."""
        self.queue.clear()
        if self.debug:
            print("[QUEUE] Fila limpa")


class AdaptiveTaskQueue(TaskQueue):
    """
    Fila de tarefas adaptativa que ajusta automaticamente o limite de tarefas
    baseado na carga de CPU.
    """
    
    def __init__(self, 
                 initial_tasks_per_frame: int = 5,
                 cpu_threshold: float = 0.75,
                 debug: bool = False):
        """
        Inicializa fila adaptativa.
        
        Args:
            initial_tasks_per_frame: Limite inicial
            cpu_threshold: Limite de uso de CPU (0-1) para desencadear redução
            debug: Ativa logging
        """
        super().__init__(initial_tasks_per_frame, debug)
        self.cpu_threshold = cpu_threshold
        self.last_cpu_usage = 0.0
    
    def update_cpu_usage(self, cpu_usage: float) -> None:
        """
        Atualiza uso de CPU e ajusta limite de tarefas.
        
        Args:
            cpu_usage: Uso de CPU em porcentagem (0-1)
        """
        self.last_cpu_usage = cpu_usage
        
        if cpu_usage > self.cpu_threshold:
            # Reduz carga
            new_limit = max(1, self.max_tasks_per_frame - 1)
            if new_limit != self.max_tasks_per_frame:
                if self.debug:
                    print(f"[ADAPTIVE] CPU alta ({cpu_usage:.1%}). "
                          f"Reduzindo tarefas: {self.max_tasks_per_frame} → {new_limit}")
                self.set_max_tasks_per_frame(new_limit)
        elif cpu_usage < (self.cpu_threshold * 0.5):
            # Aumenta carga (gradualmente)
            new_limit = self.max_tasks_per_frame + 1
            if self.debug:
                print(f"[ADAPTIVE] CPU baixa ({cpu_usage:.1%}). "
                      f"Aumentando tarefas: {self.max_tasks_per_frame} → {new_limit}")
            self.set_max_tasks_per_frame(new_limit)
    
    def get_stats(self) -> Dict:
        """Retorna estatísticas incluindo CPU."""
        stats = super().get_stats()
        stats["cpu_usage"] = self.last_cpu_usage
        return stats
