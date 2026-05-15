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
    npc_x: float = 0.0  # Posição X do NPC (opcional)
    npc_y: float = 0.0  # Posição Y do NPC (opcional)
    # Campos de percepção de projéteis (não preditivos)
    nearest_projectile_distance: float = float('inf')  # distância até projétil mais próximo
    nearest_projectile_angle: float = 0.0  # ângulo relativo ao NPC até o projétil mais próximo
    projectiles_nearby_count: int = 0  # número de projéteis num raio relevante


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

        self.player_id = "unknown" 
        self.last_case_id: Optional[str] = None
        self.last_problem: Optional[Problem] = None
        self.last_solution: Optional[Solution] = None
       
        
        # Epsilon-greedy para exploração vs exploitação
        self.epsilon = 0.6 # 60% de exploração inicial
        self.epsilon_min = 0.05  # Mínimo 5% de exploração sempre
        self.epsilon_decay = 0.85  # Decay gradual
        
        self.verbose = True #Flag para debug


        #modo do RBC (INIT - COLD START OU RBC)
        self.mode = 'INIT'
        self.episode_count = 0
        # Top-K selection para recuperação estocástica
        self.top_k = 3

        # Cold-start macro-actions
        self.cold_start_episodes = 5
        self.cold_macro = None  # estrutura: dict com target, behavior, ticks_remaining, fire_counter
        # Cold macro duration (in frames). Reduced to ~0.25s–1.0s at 60fps.
        # Use shorter macros: 0.10s–0.75s -> ~6–45 frames at 60fps
        self.cold_macro_min_ticks = 6    # ~0.10s at 60fps
        self.cold_macro_max_ticks = 45   # ~0.75s at 60fps
        self.cold_macro_fire_interval = 30  # frames between fire attempts during macro

        # Action persistence to avoid frame-to-frame jitter (in frames)
        self.action_hold_frames = 0
        self.action_hold_min = 6   # ~0.10s
        self.action_hold_max = 45  # ~0.75s




    #Método para pegar nome jogador 
    def set_player(self, player_id: str):
        self.player_id = player_id

    #Método - Aleatoriedade - Teste
    def _random_action(self, problem: Problem) -> Solution:
        import random


        r = random.random()
        if r < 0.25:
            return Solution("wander", {
                "direction": random.choice([-1, 1]),
                "speed": random.uniform(0.3, 1.0)
            })

        elif r < 0.5:
            return Solution("random_rotate", {
                "direction": random.choice([-1, 1])
            })

        elif r < 0.75:
            return Solution("fire", {})

        else:
            return Solution("search", {})


    def _start_new_cold_macro(self, problem: Problem) -> None:
        import random
        # escolhe alvo Y aleatório ao redor da posição atual do NPC
        delta = random.uniform(-140, 140)
        target_y = problem.npc_y + delta
        # escolhe comportamento macro
        behavior = random.choice(["move_and_fire", "move_only", "fire_only"])
        ticks = random.randint(self.cold_macro_min_ticks, self.cold_macro_max_ticks)
        fire_interval = random.choice([45, 60, 90])
        self.cold_macro = {
            "target_y": target_y,
            "behavior": behavior,
            "ticks_remaining": ticks,
            "fire_interval": fire_interval,
            "frame_index": 0,
        }


    def decide_action(
        self,
        problem: Problem,
        fallback_solution: Solution,
        difficulty: str = "Normal"
    ) -> Solution:
        """
        Decide ação usando RBC com epsilon-greedy.
        Decide action using RBC with epsilon-greedy exploration.
        
        Args:
            problem: Estado atual do jogo
            fallback_solution: Solução padrão para exploração
            difficulty: Nível de dificuldade para filtrar casos
            
        Returns:
            Solução/ação a ser tomada
        """


        import random

        # If we are holding an action to avoid jitter, return last solution
        if getattr(self, 'action_hold_frames', 0) > 0 and self.last_solution is not None:
            self.action_hold_frames -= 1
            return self.last_solution

        # Cold start: macro-ações estocásticas (motor babbling)
        if self.episode_count < self.cold_start_episodes:
            self.mode = "COLD_START"
            if self.verbose:
                print("[RBC] COLD START - macro-actions")

            # Inicializa macro se necessário
            if not self.cold_macro or self.cold_macro.get("ticks_remaining", 0) <= 0:
                self._start_new_cold_macro(problem)

            macro = self.cold_macro
            macro["ticks_remaining"] -= 1
            macro["frame_index"] += 1

            target_y = macro["target_y"]
            behavior = macro["behavior"]
            tol = 8.0

            # Seção de movimento: use 'wander' para mover verticalmente
            if behavior in ("move_and_fire", "move_only"):
                if abs(problem.npc_y - target_y) > tol:
                    direction = 1 if target_y > problem.npc_y else -1
                    speed = 0.7 if behavior == "move_and_fire" else 0.5
                    solution = Solution("wander", {"direction": direction, "speed": speed})
                else:
                    # chegou ao alvo — se for move_and_fire, decide atirar periodicamente
                    if behavior == "move_and_fire":
                        if macro["frame_index"] % macro["fire_interval"] == 0:
                            solution = Solution("fire", {})
                        else:
                            solution = Solution("idle", {})
                    else:
                        solution = Solution("idle", {})

            elif behavior == "fire_only":
                # tenta atirar periodicamente sem mover
                if macro["frame_index"] % macro["fire_interval"] == 0:
                    solution = Solution("fire", {})
                else:
                    solution = Solution("idle", {})
            else:
                solution = self._random_action(problem)

            # Finaliza macro se ticks esgotados
            if macro["ticks_remaining"] <= 0:
                self.cold_macro = None

            self.last_case_id = None
            self.last_problem = problem
            self.last_solution = solution
            return solution


        # Epsilon-greedy: decide entre explorar (fallback) ou exploitar (RBC)
        explore = random.random() < self.epsilon

        # Recupera casos similares
        similar_cases = self.db.get_similar_cases(
            asdict(problem),
            threshold=0.5,
            limit=5,
            difficulty=difficulty
        )

        # Se deve explorar OU não tem casos, usa fallback
        if explore or not similar_cases:
            self.mode = "RANDOM"
            solution = fallback_solution
            self.last_case_id = None
            
            if self.verbose:
                if explore and similar_cases:
                    print(f"[RBC] EXPLORANDO (epsilon={self.epsilon:.3f})")
                elif not similar_cases:
                    print("[RBC] Sem casos similares - EXPLORANDO")

        else:
            self.mode = "RBC"

            # Recupera Top-K casos por similaridade e escolhe o mais similar (DETERMINÍSTICO)
            similar_cases_sorted = sorted(similar_cases, key=lambda c: c.get("similarity", 0.0), reverse=True)
            chosen = similar_cases_sorted[0]  # Pega o caso com maior similaridade

            if self.verbose:
                print(f"[RBC] EXPLOITANDO (Determinístico) caso #{chosen['case_id'][:8]} (similaridade={chosen.get('similarity', 0):.3f})")

            solution = self._adapt_solution(chosen, problem)
            self.last_case_id = chosen["case_id"]

        # quando escolhemos uma nova solução (RBC ou fallback), segura por alguns frames
        try:
            hold_min = max(1, int(self.action_hold_min))
            hold_max = max(hold_min, int(self.action_hold_max))
            self.action_hold_frames = random.randint(hold_min, hold_max)
        except Exception:
            self.action_hold_frames = 6

        self.last_problem = problem
        self.last_solution = solution
        return solution
    
    def end_episode(self):
        self.episode_count += 1

        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay
            self.epsilon = max(self.epsilon, self.epsilon_min)

        if self.verbose:
            print(f"[RBC] Episódio {self.episode_count} | Novo epsilon: {self.epsilon:.3f}")


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

        # Remove angle_adjustment de ações "fire" para garantir que sempre atira na direção visual
        # Remove angle_adjustment from "fire" actions to ensure it always fires in visual direction
        if action == "fire" and "angle_adjustment" in params:
            del params["angle_adjustment"]

        # Adaptações baseadas no novo problema
        if "move" in action and "speed" in params:
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
            "player_id": self.player_id,
            "problem_distance": problem.distance,
            "problem_angle_diff": problem.angle_diff,
            "problem_nearest_projectile_distance": getattr(problem, 'nearest_projectile_distance', float('inf')),
            "problem_nearest_projectile_angle": getattr(problem, 'nearest_projectile_angle', 0.0),
            "problem_projectiles_nearby_count": getattr(problem, 'projectiles_nearby_count', 0),
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
        
        # Debug: log de aprendizado
        if self.verbose:
            print(f"[RBC] NOVO CASO APRENDIDO: {solution.action} "
                  f"(reward={outcome.reward:.1f}, sucesso={outcome.success})")

    def get_statistics(self) -> Dict:
        stats = self.db.get_statistics()
        stats["epsilon"] = self.epsilon
        stats["mode"] = self.mode
        stats["episode"] = self.episode_count
        return stats

    def close(self) -> None:
        """Fecha conexão com banco de dados."""
        if hasattr(self, 'db') and self.db:
            self.db.close()
            self.db = None
