"""
Exemplo de Integração da TaskQueue no jogo.
Integration example of TaskQueue in the game loop.
"""

from task_queue import TaskQueue, AdaptiveTaskQueue, TaskPriority
import psutil
import os


# ============================================================================
# EXEMPLO 1: Inicialização básica na classe do jogo
# ============================================================================

class GameLoopWithTaskQueue:
    """
    Exemplo de como integrar TaskQueue no loop principal do jogo.
    """
    
    def __init__(self):
        # Usa fila adaptativa para controle automático de CPU
        self.task_queue = AdaptiveTaskQueue(
            initial_tasks_per_frame=5,
            cpu_threshold=0.75,  # Reduz tarefas se CPU > 75%
            debug=True
        )
        
        # Monitoramento de CPU
        self.process = psutil.Process(os.getpid())
        
    def get_cpu_usage(self) -> float:
        """Retorna uso de CPU do processo (0-1)."""
        try:
            # num_cpus normaliza para 0-1
            return self.process.cpu_percent(interval=0.01) / 100.0
        except:
            return 0.0
    
    def add_tasks_to_queue(self, npc, player, projectiles):
        """
        Exemplo de como adicionar tarefas à fila.
        """
        
        # === CRÍTICAS: Sempre executam (sem delay) ===
        self.task_queue.add(
            func=self.handle_player_input,
            priority=TaskPriority.CRITICAL,
            name="player_input"
        )
        
        self.task_queue.add(
            func=self.update_player_physics,
            args=(player,),
            priority=TaskPriority.CRITICAL,
            name="player_physics"
        )
        
        self.task_queue.add(
            func=self.check_collisions,
            args=(player, npc, projectiles),
            priority=TaskPriority.CRITICAL,
            name="collision_check"
        )
        
        # === ALTAS: RBC e lógica importante do NPC ===
        self.task_queue.add(
            func=npc.brain.decide_action,
            args=(player,),
            priority=TaskPriority.HIGH,
            name="npc_rbc_decision"
        )
        
        self.task_queue.add(
            func=self.update_npc_physics,
            args=(npc,),
            priority=TaskPriority.HIGH,
            name="npc_physics"
        )
        
        # === MÉDIAS: Atualizações que podem sofrer pequenos delays ===
        self.task_queue.add(
            func=self.update_projectiles,
            args=(projectiles,),
            priority=TaskPriority.MEDIUM,
            name="update_projectiles"
        )
        
        self.task_queue.add(
            func=self.update_animations,
            priority=TaskPriority.MEDIUM,
            name="update_animations"
        )
        
        # === BAIXAS: UI e logging (podem ser muito atrasados) ===
        self.task_queue.add(
            func=self.update_ui_logs,
            args=(npc,),
            priority=TaskPriority.LOW,
            name="ui_logs"
        )
        
        self.task_queue.add(
            func=self.log_statistics,
            priority=TaskPriority.LOW,
            name="stats_logging"
        )
    
    def game_loop(self, npc, player, projectiles):
        """
        Loop principal do jogo com processamento de tarefas.
        """
        # 1. Atualiza monitoramento de CPU
        cpu_usage = self.get_cpu_usage()
        self.task_queue.update_cpu_usage(cpu_usage)
        
        # 2. Enfileira tarefas do frame
        self.add_tasks_to_queue(npc, player, projectiles)
        
        # 3. Processa tarefas (IMPORTANTE: executa aqui!)
        frame_stats = self.task_queue.process_frame()
        
        # 4. Renderiza (sempre depois de processar tarefas)
        self.render(player, npc, projectiles)
        
        return frame_stats
    
    # Tarefas exemplo
    def handle_player_input(self):
        pass
    
    def update_player_physics(self, player):
        pass
    
    def update_npc_physics(self, npc):
        pass
    
    def check_collisions(self, player, npc, projectiles):
        pass
    
    def update_projectiles(self, projectiles):
        pass
    
    def update_animations(self):
        pass
    
    def update_ui_logs(self, npc):
        pass
    
    def log_statistics(self):
        pass
    
    def render(self, player, npc, projectiles):
        pass


# ============================================================================
# EXEMPLO 2: Integração no jogo.py existente
# ============================================================================

INTEGRATION_CODE = """
# Adicionar no topo de jogo.py:
from task_queue import AdaptiveTaskQueue, TaskPriority
import psutil
import os

# No __init__ ou main:
task_queue = AdaptiveTaskQueue(initial_tasks_per_frame=5, debug=False)
process = psutil.Process(os.getpid())

# No loop principal (antes de render):
def game_frame_with_tasks(clock, screen, player, npc, projectiles):
    '''Exemplo de integração no loop do jogo'''
    
    # Monitorar CPU
    try:
        cpu = process.cpu_percent(interval=0.01) / 100.0
        task_queue.update_cpu_usage(cpu)
    except:
        pass
    
    # CRÍTICAS - Sempre executam primeiro
    task_queue.add(
        func=handle_input,
        priority=TaskPriority.CRITICAL,
        name="input"
    )
    
    # ALTAS - Lógica importante
    task_queue.add(
        func=lambda: npc.brain.decide_action(player),
        priority=TaskPriority.HIGH,
        name="npc_ai"
    )
    
    # MÉDIAS - Lógica normal
    task_queue.add(
        func=lambda: update_physics(player, npc),
        priority=TaskPriority.MEDIUM,
        name="physics"
    )
    
    # BAIXAS - Logging/UI
    task_queue.add(
        func=lambda: update_logs(npc),
        priority=TaskPriority.LOW,
        name="logging"
    )
    
    # Processa tarefas (CRÍTICO!)
    stats = task_queue.process_frame()
    
    # Se muitas tarefas acumuladas, pode mostrar aviso
    if task_queue.get_queue_size() > 10:
        print(f"⚠ Fila acumulando! {task_queue.get_queue_size()} tarefas pendentes")
    
    # Renderiza depois de processar tudo
    render_frame(screen, player, npc, projectiles)
"""


# ============================================================================
# EXEMPLO 3: Dinâmica adaptativa
# ============================================================================

ADAPTIVE_EXPLANATION = """
A fila ADAPTATIVA ajusta automaticamente o limite de tarefas por frame:

1. Se CPU > 75%: Reduz tarefas/frame (menos processamento)
   - Evita picos de CPU
   - Tarefas não-críticas ficam para o próximo frame

2. Se CPU < 37.5%: Aumenta tarefas/frame (mais processamento)
   - Aproveita tempo livre
   - Executa mais tarefas pendentes

RESULTADO: Uso de CPU mais constante e previsível!

Exemplo de monitoramento:
    queue_stats = task_queue.get_stats()
    print(f"CPU: {queue_stats['cpu_usage']:.1%}")
    print(f"Tarefas executadas: {queue_stats['total_executed']}")
    print(f"Tarefas adiadas: {queue_stats['deferred']}")
    print(f"Fila atual: {queue_stats['queue_size']}")
"""

# ============================================================================
# EXEMPLO 4: Valores recomendados por situação
# ============================================================================

RECOMMENDED_SETTINGS = {
    "single_npc_simple": {
        "initial_tasks": 5,
        "cpu_threshold": 0.70,
        "description": "Jogo simples com 1 NPC"
    },
    "multi_npc_medium": {
        "initial_tasks": 8,
        "cpu_threshold": 0.75,
        "description": "Jogo com 3-5 NPCs"
    },
    "heavy_complex": {
        "initial_tasks": 12,
        "cpu_threshold": 0.80,
        "description": "Jogo complexo com muitos NPCs"
    },
    "mobile_constrained": {
        "initial_tasks": 3,
        "cpu_threshold": 0.60,
        "description": "Dispositivo móvel ou hardware limitado"
    }
}

if __name__ == "__main__":
    print("=== RECOMMENDED SETTINGS ===")
    for scenario, settings in RECOMMENDED_SETTINGS.items():
        print(f"\n{scenario.upper()}:")
        for key, value in settings.items():
            if key != "description":
                print(f"  {key}: {value}")
