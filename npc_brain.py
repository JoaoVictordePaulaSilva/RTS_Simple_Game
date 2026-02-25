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

    def set_session(self, session_id: str) -> None:
        """Define ID da sessão atual para logging."""
        self.session_id = session_id

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
        difficulty: str = "Normal"
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

        return solution

    def _encode_problem(
        self,
        npc_x: float, npc_y: float, npc_angle: float, npc_health: float,
        player_x: float, player_y: float, player_health: float,
        player_visible: bool, frames_since_last_seen: int
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
            frames_lost=frames_since_last_seen
        )

    def _generate_fallback_action(self, problem: Problem) -> Solution:
        """
        Gera ação de exploração inteligente baseada no estado do problema.
        Generate intelligent exploration action based on problem state.
        
        Essa função é usada para EXPLORAÇÃO no cold start do RBC.
        """
        import random

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
        
        # Garante que reward não seja extremamente negativo (para não desencorajar totalmente)
        reward = max(-20.0, reward)

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