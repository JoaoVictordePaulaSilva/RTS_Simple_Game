"""
Cérebro do NPC com RBC e IA básica como fallback.
NPC Brain combining RBC and basic AI fallback.
"""

import random
import math
from typing import Dict, Optional, Tuple
from rbc_engine import RBCEngine, Problem, Solution, Outcome


class NPCBrain:
    """
    Cérebro inteligente do NPC que combina RBC com IA básica.
    NPC intelligent brain combining RBC with basic AI fallback.
    """

    def __init__(self, db_path: str = "npc_cases.db") -> None:
        """
        Inicializa o cérebro do NPC.
        
        Args:
            db_path: Caminho para banco de dados de casos
        """
        self.rbc_engine = RBCEngine(db_path)
        self.session_id = "default"
        self.frame_counter = 0
        self.last_action: Optional[Solution] = None
        self.pending_outcome: Optional[Tuple[Problem, Solution]] = None
        self.episode_frame_count = 0  # Conta frames desde início do episódio
        self.episode_frame_limit = 1800  # ~30s a 60fps para penalizar luta longa
        self.verbose = False  # Flag para debug
        
        # === Tracking para detecção de ações ineficazes ===
        self.position_history = []  # Últimas posições (x, y)
        self.action_history = []  # Últimas ações executadas
        self.recent_damage_history = []  # Dano causado nos últimos N frames
        self.max_history = 60  # Rastreia últimos ~1s (60 frames a 60fps)
        self.stuck_frame_count = 0  # Frames consecutivos na mesma área
        self.stuck_threshold_frames = 45  # Threshold para considerar travado
        self.stuck_position_tolerance = 50.0  # px - distância máxima para considerar "mesma posição"
        self.ineffectiveness_boost_base = 0.1  # Incremento base para exploração quando ineficaz

    def set_session(self, session_id: str) -> None:
        """Define ID da sessão atual para logging."""
        self.session_id = session_id
    
    def reset_episode(self) -> None:
        """Reseta contadores de episódio (chamada no início de cada partida/episódio)."""
        self.episode_frame_count = 0
        self.pending_outcome = None
        self.position_history = []
        self.action_history = []
        self.recent_damage_history = []
        self.stuck_frame_count = 0
    
    def _track_action_effectiveness(self, npc_x: float, npc_y: float, action: Solution, damage_dealt: float) -> None:
        """
        Rastreia posição, ação e dano para detectar comportamentos ineficazes.
        
        Args:
            npc_x, npc_y: Posição atual do NPC
            action: Ação executada
            damage_dealt: Dano causado neste frame
        """
        # Rastreia posição
        self.position_history.append((npc_x, npc_y))
        if len(self.position_history) > self.max_history:
            self.position_history.pop(0)
        
        # Rastreia ação
        self.action_history.append(action.action)
        if len(self.action_history) > self.max_history:
            self.action_history.pop(0)
        
        # Rastreia dano
        self.recent_damage_history.append(damage_dealt)
        if len(self.recent_damage_history) > self.max_history:
            self.recent_damage_history.pop(0)
    
    def _detect_ineffectiveness(self) -> Tuple[bool, dict]:
        """
        Detecta se o NPC está em um padrão ineficaz (travado, repetindo ações sem sucesso).
        
        Returns:
            (is_ineffective: bool, metrics: dict com detalhes)
        """
        metrics = {
            "is_stuck_position": False,
            "is_repeating_action": False,
            "total_recent_damage": 0.0,
            "stuck_duration_frames": 0,
        }
        
        if len(self.position_history) < self.stuck_threshold_frames:
            return False, metrics
        
        # Verifica se está na mesma posição
        recent_positions = self.position_history[-self.stuck_threshold_frames:]
        if len(recent_positions) >= self.stuck_threshold_frames:
            first_pos = recent_positions[0]
            same_area_count = 0
            for pos in recent_positions:
                dist = math.sqrt((pos[0] - first_pos[0])**2 + (pos[1] - first_pos[1])**2)
                if dist <= self.stuck_position_tolerance:
                    same_area_count += 1
            
            is_stuck = (same_area_count / len(recent_positions)) > 0.8  # 80%+ dos frames na mesma área
            if is_stuck:
                metrics["is_stuck_position"] = True
                metrics["stuck_duration_frames"] = self.stuck_threshold_frames
        
        # Verifica repetição de ações
        recent_actions = self.action_history[-self.stuck_threshold_frames:]
        if recent_actions:
            most_common_action = max(set(recent_actions), key=recent_actions.count)
            action_repetition = recent_actions.count(most_common_action) / len(recent_actions)
            if action_repetition > 0.7:  # 70%+ repetição
                metrics["is_repeating_action"] = True
        
        # Verifica dano causado
        total_damage = sum(self.recent_damage_history[-self.stuck_threshold_frames:])
        metrics["total_recent_damage"] = total_damage
        
        # Considera ineficaz se está travado OU repetindo e sem causar dano significativo
        is_ineffective = (metrics["is_stuck_position"] and total_damage < 5.0) or \
                        (metrics["is_repeating_action"] and total_damage < 3.0)
        
        return is_ineffective, metrics

    def decide_action(
        self,
        npc_x: float,
        npc_y: float,
        npc_angle: float,
        npc_health: float,
        player_x: float,
        player_y: float,
        player_health: float,
        player_visible: bool,
        frames_since_last_seen: int,
        difficulty: str = "Normal",
        nearest_projectile_distance: float = None,
        nearest_projectile_angle: float = None,
        projectiles_nearby_count: int = 0,
    ):
        """
        Decide ação do NPC baseado no estado atual.
        Decide NPC action based on current game state.
        
        Args:
            npc_x, npc_y: Posição do NPC
            npc_angle: Ângulo de apontamento do NPC
            npc_health: Saúde do NPC
            player_x, player_y: Posição do jogador
            player_health: Saúde do jogador
            player_visible: Se o jogador está visível
            frames_since_last_seen: Frames desde última visão do jogador
            difficulty: Nível de dificuldade
            
        Returns:
            Ação a ser executada
        """
        # Codifica estado atual
        problem = self._encode_problem(
            npc_x, npc_y, npc_angle, npc_health,
            player_x, player_y, player_health,
            player_visible, frames_since_last_seen
            , nearest_projectile_distance, nearest_projectile_angle, projectiles_nearby_count
        )

        # Gera solução padrão como fallback
        fallback_solution = self._generate_fallback_action(problem)

        # Usa RBC para tentar recuperar melhor solução
        solution = self.rbc_engine.decide_action(
            problem,
            fallback_solution,
            difficulty
        )

        # Armazena para aprendizado posterior
        self.last_action = solution
        self.pending_outcome = (problem, solution)
        self.frame_counter += 1
        self.episode_frame_count += 1  # Incrementa contador de frames do episódio
        
        # Rastreia eficácia de ações (para posterior análise)
        # Nota: damage será adicionado em report_outcome, por enquanto usa 0
        self._track_action_effectiveness(npc_x, npc_y, solution, 0.0)

        return solution
    
    def set_player(self, player_id: str):
        self.rbc_engine.set_player(player_id)
    

    def _encode_problem(
        self,
        npc_x: float, npc_y: float, npc_angle: float, npc_health: float,
        player_x: float, player_y: float, player_health: float,
        player_visible: bool, frames_since_last_seen: int
        , nearest_projectile_distance: float = None, nearest_projectile_angle: float = None, projectiles_nearby_count: int = 0
    ) -> Problem:
        """
        Codifica estado do jogo como problema RBC.
        Encode game state as RBC problem.
        """
        # Calcula distância até jogador
        dx = player_x - npc_x
        dy = player_y - npc_y
        distance = math.sqrt(dx * dx + dy * dy)

        # Calcula diferença angular
        angle_to_target = math.degrees(math.atan2(dy, dx))
        angle_diff = abs(angle_to_target - npc_angle)
        if angle_diff > 180:
            angle_diff = 360 - angle_diff

        return Problem(
            distance=distance,
            angle_diff=angle_diff,
            npc_health=npc_health,
            player_health=player_health,
            player_visible=player_visible,
            frames_lost=frames_since_last_seen,
            npc_x=npc_x,
            npc_y=npc_y,
            nearest_projectile_distance=nearest_projectile_distance if nearest_projectile_distance is not None else float('inf'),
            nearest_projectile_angle=nearest_projectile_angle if nearest_projectile_angle is not None else 0.0,
            projectiles_nearby_count=projectiles_nearby_count,
        )

    def _generate_fallback_action(self, problem: Problem) -> Solution:
        """
        Gera ação de exploração inteligente baseada no estado do problema.
        Generate intelligent exploration action based on problem state.
        
        Essa função é usada para EXPLORAÇÃO no cold start do RBC.
        """
        import random

        # Se há projéteis próximos, prioriza evasão
        if getattr(problem, 'projectiles_nearby_count', 0) > 0:
            # direção de evasão baseada no ângulo relativo do projétil
            ang = getattr(problem, 'nearest_projectile_angle', 0.0)
            # se projétil vindo pela 'baixo' (ângulo positivo), sobe; se vindo por cima, desce
            direction = -1 if ang > 0 else 1
            return Solution(action="evade_projectile", params={"direction": direction, "speed": 0.9})

        # Se jogador está visível - prioriza ações ofensivas
        if problem.player_visible:
            # Distribuição baseada no alinhamento
            if problem.angle_diff < 10:
                # Muito bem alinhado - 80% dispara, 20% explora movimento
                if random.random() < 0.8:
                    return Solution(action="fire", params={})
                else:
                    return Solution(
                        action="wander",
                        params={"direction": random.choice([-1, 1]), "speed": 0.6}
                    )
            
            elif problem.angle_diff < 30:
                # Razoavelmente alinhado - 60% alinha e dispara, 40% outras ações
                r = random.random()
                if r < 0.6:
                    return Solution(action="align_and_fire", params={})
                elif r < 0.8:
                    return Solution(action="fire", params={})
                else:
                    return Solution(
                        action="pursue",
                        params={"speed": random.uniform(0.5, 1.0)}
                    )
            
            elif problem.angle_diff < 90:
                # Desalinhado - 70% alinha, 30% tenta outras estratégias
                r = random.random()
                if r < 0.5:
                    return Solution(action="align_and_fire", params={})
                elif r < 0.7:
                    return Solution(
                        action="random_rotate",
                        params={"direction": 1 if problem.angle_diff > 0 else -1}
                    )
                else:
                    return Solution(
                        action="pursue",
                        params={"speed": random.uniform(0.6, 0.9)}
                    )
            
            else:
                # Muito desalinhado - precisa rotacionar bastante
                return Solution(
                    action="random_rotate",
                    params={"direction": random.choice([-1, 1])}
                )
        
        # Se jogador não está visível mas foi visto recentemente
        elif problem.frames_lost < 120:  # Menos de 2 segundos
            r = random.random()
            if r < 0.4:
                return Solution(action="search", params={})
            elif r < 0.7:
                return Solution(
                    action="random_rotate",
                    params={"direction": random.choice([-1, 1])}
                )
            else:
                return Solution(
                    action="wander",
                    params={"direction": random.choice([-1, 1]), "speed": 0.5}
                )
        
        # Jogador não visto há muito tempo - exploração aleatória balanceada
        else:
            r = random.random()
            
            if r < 0.35:  # 35% mover
                return Solution(
                    action="wander",
                    params={
                        "direction": random.choice([-1, 1]),
                        "speed": random.uniform(0.4, 0.8)
                    }
                )
            elif r < 0.70:  # 35% girar
                return Solution(
                    action="random_rotate",
                    params={"direction": random.choice([-1, 1])}
                )
            elif r < 0.85:  # 15% buscar
                return Solution(action="search", params={})
            else:  # 15% tentar disparar (exploratório)
                return Solution(action="fire", params={})

    def report_outcome(
        self,
        success: bool,
        damage_dealt: float = 0.0,
        damage_taken: float = 0.0,
        outcome_type: str = "unknown",
        difficulty: str = "Normal",
    ) -> None:
        """
        Relata resultado da ação para aprendizado.
        Report action outcome for learning.
        
        Args:
            success: Se a ação foi bem-sucedida
            damage_dealt: Dano causado ao jogador
            damage_taken: Dano recebido
            outcome_type: Tipo de resultado ('hit', 'miss', 'evaded', 'safe')
            difficulty: Nível de dificuldade
        """
        if not self.pending_outcome:
            return

        problem, solution = self.pending_outcome
        outcome = Outcome(
            success=success,
            damage_dealt=damage_dealt,
            damage_taken=damage_taken,
            outcome_type=outcome_type
        )
        
        # Atualiza histórico de dano para detecção de eficácia
        if self.recent_damage_history:
            self.recent_damage_history[-1] = damage_dealt  # Atualiza último frame com dano real

        # ===== SISTEMA DE REWARD APRIMORADO =====
        # Reward base começa neutro
        reward = 0.0
        
        # 1. Recompensa por sucesso geral
        if success:
            reward += 10.0
        
        # 2. Dano causado é muito valioso (objetivo principal)
        if damage_dealt > 0:
            reward += damage_dealt * 2.0  # 2 pontos por dano
        
        # 3. Penalidade pesada por receber dano (deve evitar)
        if damage_taken > 0:
            reward -= damage_taken * 3.0  # -3 pontos por dano recebido
        
        # 4. Recompensas específicas por tipo de resultado
        if outcome_type == "hit":
            reward += 15.0  # Bônus grande por acertar
        elif outcome_type == "miss":
            reward -= 5.0  # Penalidade por errar
        elif outcome_type == "evaded":
            reward += 3.0  # Pequeno bônus por evasão bem-sucedida
        elif outcome_type == "safe":
            reward += 1.0  # Pequeno bônus por ficar seguro
        
        # 5. Considera distância e alinhamento para ações ofensivas
        if solution.action in ["fire", "align_and_fire"]:
            # Recompensa por estar bem posicionado ao atirar
            if problem.angle_diff < 15:
                reward += 5.0  # Bem alinhado
            elif problem.angle_diff < 30:
                reward += 2.0  # Razoavelmente alinhado
            
            # Distância ideal de combate (200-400 pixels)
            if 200 <= problem.distance <= 400:
                reward += 3.0
            elif problem.distance < 100:
                reward -= 2.0  # Muito perto é perigoso
        
        # 6. Penalidade por ações ineficientes
        if solution.action == "idle":
            reward -= 3.0  # Desencorajar inatividade
        
        # 7. Pequeno bônus por manter jogador visível
        if problem.player_visible:
            reward += 2.0
        
        # 8. Multiplicador de vitória: se o jogador foi derrotado (damage_dealt >= 100 ou jogador morto)
        # Assumimos que outcome_type == 'hit' com dano alto indica vitória iminente
        player_defeated = damage_dealt >= 100 or outcome_type == "player_dead"
        if player_defeated:
            reward *= 2.5  # Bônus multiplicativo de 250% para vitória
            if self.verbose:
                print(f"[REWARD] Multiplicador de vitória aplicado! Reward final x2.5")
        
        # 9. Penalidade gradual por duração da partida (incentiva vitória rápida)
        # Penaliza progressivamente conforme a partida avança
        if self.episode_frame_count > 0:
            time_penalty = (self.episode_frame_count / self.episode_frame_limit) * 5.0
            reward -= time_penalty
        
        # 10. Detecção de ineficácia: penaliza comportamentos presos/repetitivos e aumenta exploração
        is_ineffective, ineffectiveness_metrics = self._detect_ineffectiveness()
        if is_ineffective:
            # Penaliza por ineficácia
            ineffectiveness_penalty = ineffectiveness_metrics["stuck_duration_frames"] * 0.05
            reward -= ineffectiveness_penalty
            
            # Aumenta epsilon (exploração) dinamicamente
            epsilon_boost = self.ineffectiveness_boost_base * (ineffectiveness_metrics["stuck_duration_frames"] / self.stuck_threshold_frames)
            old_epsilon = self.rbc_engine.epsilon
            self.rbc_engine.epsilon = min(0.9, self.rbc_engine.epsilon + epsilon_boost)
            
            if self.verbose:
                print(f"[INEFFECTIVENESS] Comportamento ineficaz detectado!")
                print(f"  - Travado: {ineffectiveness_metrics['is_stuck_position']}")
                print(f"  - Repetindo ações: {ineffectiveness_metrics['is_repeating_action']}")
                print(f"  - Dano nos últimos {ineffectiveness_metrics['stuck_duration_frames']}f: {ineffectiveness_metrics['total_recent_damage']:.1f}")
                print(f"  - Epsilon aumentou: {old_epsilon:.3f} → {self.rbc_engine.epsilon:.3f}")
                print(f"  - Penalidade aplicada: -{ineffectiveness_penalty:.1f}")
        
        # Garante que reward não seja extremamente negativo (para não desencorajar totalmente)
        reward = max(-25.0, reward)

        outcome.reward = reward

        # Aprende armazenando no banco
        self.rbc_engine.learn(
            case_id=self.rbc_engine.last_case_id,
            problem=problem,
            solution=solution,
            outcome=outcome,
            session_id=self.session_id,
            difficulty=difficulty
        )

        self.pending_outcome = None

    def get_statistics(self) -> Dict:
        """Retorna estatísticas de aprendizado."""
        return self.rbc_engine.get_statistics()

    def close(self) -> None:
        """Fecha conexões do RBC."""
        if hasattr(self, 'rbc_engine') and self.rbc_engine:
            self.rbc_engine.close()
            self.rbc_engine = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()