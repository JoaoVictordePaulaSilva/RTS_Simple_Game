"""
Motor de Raciocínio Baseado em Casos (RBC/CBR) para o NPC.
Case-Based Reasoning engine for NPC decision making.
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import json
from database import CaseDatabase


@dataclass
class Problem:
    """Representa um problema/estado do jogo a ser resolvido."""
    distance: float  # Distância até jogador em pixels
    angle_diff: float  # Diferença angular em graus
    npc_health: float  # Saúde do NPC (0-100)
    player_health: float  # Saúde do jogador (0-100)
    player_visible: bool  # Jogador está visível?
    frames_lost: int = 0  # Frames desde última visão


@dataclass
class Solution:
    """Representa uma solução/ação a ser tomada."""
    action: str  # 'fire', 'move_up', 'move_down', 'rotate', 'idle', 'search'
    params: Dict = None  # Parâmetros adicionais (ângulo, velocidade, etc)
    
    def __post_init__(self):
        if self.params is None:
            self.params = {}


@dataclass
class Outcome:
    """Representa o resultado de uma ação executada."""
    success: bool  # Ação teve sucesso?
    damage_dealt: float = 0.0  # Dano causado
    damage_taken: float = 0.0  # Dano recebido
    outcome_type: str = "unknown"  # 'hit', 'miss', 'evaded', 'safe'
    reward: float = 0.0 # Sistema de pontos para o RBC


class RBCEngine:
    """
    Motor de Raciocínio Baseado em Casos.
    Implementa: Recuperação → Adaptação → Execução → Aprendizado
    """

    def __init__(self, db_path: str = "npc_cases.db") -> None:
        """
        Inicializa o motor RBC.
        
        Args:
            db_path: Caminho para banco de dados SQLite
        """
        self.db = CaseDatabase(db_path)
        self.last_case_id: Optional[str] = None
        self.last_problem: Optional[Problem] = None
        self.last_solution: Optional[Solution] = None

    def decide_action(
        self,
        problem: Problem,
        fallback_solution: Solution,
        difficulty: str = "Normal"
    ) -> Solution:
        """
        Decide ação usando RBC. Se não encontrar casos similares, usa fallback.
        Decide action using RBC. Falls back to default AI if no similar cases found.
        
        Args:
            problem: Estado atual do jogo
            fallback_solution: Solução padrão se nenhum caso similar for encontrado
            difficulty: Nível de dificuldade para filtrar casos
            
        Returns:
            Solução/ação a ser tomada
        """
        # Recupera casos similares
        similar_cases = self.db.get_similar_cases(
            asdict(problem),
            threshold=0.6,
            limit=3,
            difficulty=difficulty
        )

        if similar_cases:
            best_score = -9999
            best_case = None

            for case in similar_cases:
                similarity = case.get("similarity", 0)
                reward = case.get("result_reward", 1.0)

                score = similarity * reward

                if score > best_score:
                    best_score = score
                    best_case = case

            solution = self._adapt_solution(best_case, problem)
            self.last_case_id = best_case["case_id"]
        else:
            # Fallback: Usa IA básica padrão
            solution = fallback_solution
            self.last_case_id = None

        self.last_problem = problem
        self.last_solution = solution
        return solution

    def _adapt_solution(self, case: Dict, new_problem: Problem) -> Solution:
        """
        Adapta solução de caso anterior para novo problema.
        Adapt solution from previous case to new problem.
        
        Args:
            case: Caso recuperado do banco
            new_problem: Novo problema a resolver
            
        Returns:
            Solução adaptada
        """
        action = case["solution_action"]
        params = json.loads(case["solution_params"]) if case["solution_params"] else {}

        # Adaptações baseadas no novo problema
        if action == "fire" and "angle_adjustment" in params:
            # Ajusta ângulo de disparo baseado na diferença angular
            original_angle_diff = case["problem_angle_diff"]
            new_angle_diff = new_problem.angle_diff
            angle_delta = new_angle_diff - original_angle_diff
            params["angle_adjustment"] = params["angle_adjustment"] + (angle_delta * 0.3)

        elif "move" in action and "speed" in params:
            # Ajusta velocidade de movimento baseado na distância
            original_distance = case["problem_distance"]
            new_distance = new_problem.distance
            if new_distance < 100:
                params["speed"] = 0.5
            elif new_distance > 400:
                params["speed"] = 1.0

        return Solution(action=action, params=params)

    def learn(
        self,
        case_id: Optional[str],
        problem: Problem,
        solution: Solution,
        outcome: Outcome,
        session_id: str,
        difficulty: str
    ) -> None:

        # 🔥 Caso já existente → atualizar estatísticas
        if case_id:
            self.db.update_case_usage(
                case_id=case_id,
                success=outcome.success,
                reward=outcome.reward
            )
            return

        # 🔥 Caso novo
        new_case = {
            "problem_distance": problem.distance,
            "problem_angle_diff": problem.angle_diff,
            "problem_npc_health": problem.npc_health,
            "problem_player_health": problem.player_health,
            "problem_player_visible": problem.player_visible,
            "problem_frames_lost": problem.frames_lost,

            "solution_action": solution.action,
            "solution_params": solution.params,

            "result_success": outcome.success,
            "result_damage_dealt": outcome.damage_dealt,
            "result_damage_taken": outcome.damage_taken,
            "result_outcome": outcome.outcome_type,
            "result_reward": outcome.reward,

            # 🔥 Estatísticas iniciais
            "usage_count": 1,
            "success_count": 1 if outcome.success else 0,
            "total_reward": outcome.reward,
            "avg_reward": outcome.reward,

            "session_id": session_id,
            "difficulty": difficulty,
            "created_by": "learned",
        }

        self.db.insert_case(new_case)

    def get_statistics(self) -> Dict:
        """Retorna estatísticas do motor RBC."""
        return self.db.get_statistics()

    def close(self) -> None:
        """Fecha conexão com banco de dados."""
        self.db.close()
