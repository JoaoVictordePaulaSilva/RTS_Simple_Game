"""
INTEGRAÇÃO PRÁTICA: TaskQueue no jogo.py
PRACTICAL INTEGRATION: TaskQueue in jogo.py
"""

# ============================================================================
# PASSO 1: Adicionar imports no topo do jogo.py
# ============================================================================

IMPORTS_TO_ADD = """
import psutil
import os
from task_queue import AdaptiveTaskQueue, TaskPriority
"""

# ============================================================================
# PASSO 2: Adicionar no __init__ de Game (junto com outros inicializadores)
# ============================================================================

INIT_CODE = """
def __init__(self):
    # ... código existente ...
    
    # === NOVO: Inicializa fila de tarefas ===
    self.task_queue = AdaptiveTaskQueue(
        initial_tasks_per_frame=5,
        cpu_threshold=0.75,
        debug=False  # Mude para True se quiser ver logs
    )
    
    # Para monitorar CPU
    self.process = psutil.Process(os.getpid())
    
    # ... resto do código ...
"""

# ============================================================================
# PASSO 3: Adicionar método helper para CPU
# ============================================================================

HELPER_METHOD = """
def get_cpu_usage(self) -> float:
    '''Retorna uso de CPU do processo (0-1).'''
    try:
        return self.process.cpu_percent(interval=0.01) / 100.0
    except:
        return 0.0
"""

# ============================================================================
# PASSO 4: MODIFICAR o método update() - PARTE CRÍTICA
# ============================================================================

UPDATE_BEFORE = """
    def update(self, dt):
        if self.state == "playing":
            self.frame_counter += 1
            self._monitor_update_timer += dt
            
            keys = pygame.key.get_pressed()
            # Movimento do jogador: apenas eixo Y / Player movement: only Y axis
            if keys[pygame.K_UP]:
                self.player.move_y(-1, dt)
            if keys[pygame.K_DOWN]:
                self.player.move_y(1, dt)

            # Atualização de cooldown / Player cooldown update
            self.player.update(dt)
            self.npc.update(dt)
            
            # Atualiza percepção do NPC / Update NPC perception
            self.npc_perception.update(self.player, dt, projectiles=self.projectiles)

            # ===== IA DO NPC =====
            self._update_npc_ai(dt)

            # Atualiza projéteis / update projectiles
            for p in self.projectiles:
                p.update(dt)

            # Colisões / collisions
            # ... resto do código ...
"""

UPDATE_AFTER = """
    def update(self, dt):
        if self.state == "playing":
            self.frame_counter += 1
            self._monitor_update_timer += dt
            
            # ===== NOVO: Monitorar CPU e adaptar ===
            cpu_usage = self.get_cpu_usage()
            self.task_queue.update_cpu_usage(cpu_usage)
            
            # ===== NOVO: Input é CRÍTICO (sempre executa) ===
            def handle_player_input():
                keys = pygame.key.get_pressed()
                if keys[pygame.K_UP]:
                    self.player.move_y(-1, dt)
                if keys[pygame.K_DOWN]:
                    self.player.move_y(1, dt)
            
            self.task_queue.add(
                func=handle_player_input,
                priority=TaskPriority.CRITICAL,
                name="player_input"
            )
            
            # ===== NOVO: Atualizar cooldown do jogador (CRÍTICO) ===
            self.task_queue.add(
                func=self.player.update,
                args=(dt,),
                priority=TaskPriority.CRITICAL,
                name="player_cooldown"
            )
            
            # ===== Atualização do NPC (ALTA prioridade) ===
            self.task_queue.add(
                func=self.npc.update,
                args=(dt,),
                priority=TaskPriority.HIGH,
                name="npc_update"
            )
            
            # ===== Percepção do NPC (ALTA prioridade - afeta IA) ===
            self.task_queue.add(
                func=self.npc_perception.update,
                args=(self.player, dt),
                kwargs={"projectiles": self.projectiles},
                priority=TaskPriority.HIGH,
                name="npc_perception"
            )
            
            # ===== IA do NPC (ALTA prioridade - RBC) ===
            self.task_queue.add(
                func=self._update_npc_ai,
                args=(dt,),
                priority=TaskPriority.HIGH,
                name="npc_ai"
            )
            
            # ===== Atualizar projéteis (MÉDIA prioridade) ===
            def update_projectiles():
                for p in self.projectiles:
                    p.update(dt)
            
            self.task_queue.add(
                func=update_projectiles,
                priority=TaskPriority.MEDIUM,
                name="update_projectiles"
            )
            
            # ===== Detecção de colisões (CRÍTICO - afeta gameplay) ===
            self.task_queue.add(
                func=self._check_collisions,
                priority=TaskPriority.CRITICAL,
                name="collision_check"
            )
            
            # ===== Logging/UI (BAIXA prioridade - pode esperar) ===
            self.task_queue.add(
                func=self._update_monitoring,
                priority=TaskPriority.LOW,
                name="monitoring"
            )
            
            # ===== NOVO: Processa todas as tarefas ===
            frame_stats = self.task_queue.process_frame()
            
            # ===== DEBUG: Mostrar se fila está acumulando ===
            if self.task_queue.get_queue_size() > 15:
                print(f"⚠️ Fila acumulando: {self.task_queue.get_queue_size()} tarefas")
            
            # ... resto do código do update que não foi refatorado ...
"""

# ============================================================================
# PASSO 5: Refatorar métodos grandes em métodos helper
# ============================================================================

NEW_METHODS = """
def _check_collisions(self):
    '''Colisão de projéteis com tanques.'''
    for p in list(self.projectiles):
        if not p.is_alive:
            self.projectiles.remove(p)
            continue
        # Verifica colisão com tanques
        if p.owner is not self.player and self._collide_proj_tank(p, self.player):
            self.player.hit(p.damage)
            p.is_alive = False
            # NPC acertou
            self.npc_brain.report_outcome(
                success=True,
                damage_dealt=p.damage,
                outcome_type="hit"
            )
        elif p.owner is not self.npc and self._collide_proj_tank(p, self.npc):
            self.npc.hit(p.damage)
            p.is_alive = False
            # Jogador acertou
            self.npc_brain.report_outcome(
                success=False,
                damage_taken=p.damage,
                outcome_type="hit_by_player"
            )

def _update_monitoring(self):
    '''Atualiza monitoring e logging (LOW priority).'''
    self._monitor_update_timer -= self.dt
    if self._monitor_update_timer <= 0:
        # Envia stats para monitor
        self.rbc_monitor.update_live({
            "player_health": self.player.health,
            "npc_health": self.npc.health,
            "frame": self.frame_counter
        })
        self._monitor_update_timer = 0.5
"""

# ============================================================================
# PASSO 6: Resumo das mudanças
# ============================================================================

SUMMARY = """
RESUMO DAS MUDANÇAS:

1. ✅ Imports (imports psutil, task_queue)
2. ✅ Inicializa TaskQueue no __init__
3. ✅ Adiciona método get_cpu_usage()
4. ✅ Refatora update() para usar task_queue:
   - Input → CRITICAL
   - Física jogador → CRITICAL
   - Colisões → CRITICAL
   - NPC AI → HIGH
   - Projéteis → MEDIUM
   - Logging → LOW
5. ✅ Extrai colisões em _check_collisions()
6. ✅ Extrai monitoring em _update_monitoring()

RESULTADO:
- Tarefas críticas executam sempre
- Tarefas não-críticas distribuídas nos frames
- CPU mais estável e previsível
- Escalável para múltiplos NPCs

PRÓXIMO PASSO:
Se tiver 2+ NPCs:
- Copie a lógica do NPC_AI em um loop
- Cada iteração é uma tarefa HIGH
"""

# ============================================================================
# EXEMPLO: Versão completa do update() refatorado
# ============================================================================

COMPLETE_REFACTORED_UPDATE = """
def update(self, dt):
    if self.state == "playing":
        self.frame_counter += 1
        self._monitor_update_timer += dt
        self.dt = dt  # Salva dt para usar em _check_collisions
        
        # ===== NOVA: Monitorar CPU e adaptar fila =====
        cpu_usage = self.get_cpu_usage()
        self.task_queue.update_cpu_usage(cpu_usage)
        
        # ===== ENFILEIRA TAREFAS =====
        
        # 1. CRÍTICA: Input do jogador
        def handle_player_input():
            keys = pygame.key.get_pressed()
            if keys[pygame.K_UP]:
                self.player.move_y(-1, dt)
            if keys[pygame.K_DOWN]:
                self.player.move_y(1, dt)
        
        self.task_queue.add(
            func=handle_player_input,
            priority=TaskPriority.CRITICAL,
            name="player_input"
        )
        
        # 2. CRÍTICA: Cooldown do jogador
        self.task_queue.add(
            func=self.player.update,
            args=(dt,),
            priority=TaskPriority.CRITICAL,
            name="player_cooldown"
        )
        
        # 3. ALTA: Update do NPC
        self.task_queue.add(
            func=self.npc.update,
            args=(dt,),
            priority=TaskPriority.HIGH,
            name="npc_update"
        )
        
        # 4. ALTA: Percepção do NPC
        self.task_queue.add(
            func=self.npc_perception.update,
            args=(self.player, dt),
            kwargs={"projectiles": self.projectiles},
            priority=TaskPriority.HIGH,
            name="npc_perception"
        )
        
        # 5. ALTA: Decisão do NPC (RBC)
        self.task_queue.add(
            func=self._update_npc_ai,
            args=(dt,),
            priority=TaskPriority.HIGH,
            name="npc_ai"
        )
        
        # 6. MÉDIA: Atualizar projéteis
        def update_projectiles():
            for p in self.projectiles:
                p.update(dt)
        
        self.task_queue.add(
            func=update_projectiles,
            priority=TaskPriority.MEDIUM,
            name="update_projectiles"
        )
        
        # 7. CRÍTICA: Colisões (afeta gameplay imediatamente)
        self.task_queue.add(
            func=self._check_collisions,
            priority=TaskPriority.CRITICAL,
            name="collision_check"
        )
        
        # 8. BAIXA: Monitoring e logs
        self.task_queue.add(
            func=self._update_monitoring,
            priority=TaskPriority.LOW,
            name="monitoring"
        )
        
        # ===== PROCESSA TAREFAS =====
        frame_stats = self.task_queue.process_frame()
        
        # ===== DEBUG =====
        if self.debug_mode and self.task_queue.get_queue_size() > 15:
            print(f"[GAME] Fila acumulando: {self.task_queue.get_queue_size()} tarefas")
        
        # ===== VERIFICA FIM DE JOGO =====
        self._check_game_over()
"""

if __name__ == "__main__":
    print("=" * 70)
    print("GUIA DE INTEGRAÇÃO: TaskQueue no jogo.py")
    print("=" * 70)
    print()
    print("PASSO 1: Adicionar imports")
    print(IMPORTS_TO_ADD)
    print()
    print("PASSO 2: Adicionar ao __init__")
    print(INIT_CODE)
    print()
    print("PASSO 3: Adicionar método helper")
    print(HELPER_METHOD)
    print()
    print("PASSO 4-6:")
    print(SUMMARY)
