"""
Motor de Raciocínio Baseado em Casos (RBC/CBR) para o NPC.
Case-Based Reasoning engine for NPC decision making.
"""

from typing import Dict, Optional
from dataclasses import asdict
import json

from database.case_database import CaseDatabase

from .rbc_models import Problem, Solution, Outcome


class RBCEngine:
	"""
	Motor de Raciocínio Baseado em Casos.
	Implementa: Recuperação → Adaptação → Execução → Aprendizado
	"""

	def __init__(self, db_path: str = "npc_cases.db") -> None:
		self.db = CaseDatabase(db_path)

		self.player_id = "unknown"
		self.last_case_id: Optional[str] = None
		self.last_problem: Optional[Problem] = None
		self.last_solution: Optional[Solution] = None

		self.epsilon = 0.25
		self.epsilon_min = 0.05
		self.epsilon_decay = 0.85

		self.verbose = True

		self.mode = 'INIT'
		self.episode_count = 0
		self.top_k = 3

		self.cold_start_episodes = 5
		self.cold_macro = None
		self.cold_macro_min_ticks = 20
		self.cold_macro_max_ticks = 50
		self.cold_macro_fire_interval = 30

		self.action_hold_frames = 0
		self.action_hold_min = 12
		self.action_hold_max = 24
		self.explore_hold_min = 8
		self.explore_hold_max = 16

	def set_player(self, player_id: str):
		self.player_id = player_id

	def _random_action(self, problem: Problem) -> Solution:
		import random

		r = random.random()
		if r < 0.25:
			return Solution("wander", {"direction": random.choice([-1, 1]), "speed": random.uniform(0.3, 1.0)})
		elif r < 0.5:
			return Solution("random_rotate", {"direction": random.choice([-1, 1])})
		elif r < 0.75:
			return Solution("fire", {})
		return Solution("search", {})

	def _start_new_cold_macro(self, problem: Problem) -> None:
		import random

		# Sob ameaça imediata de projétil
		projectile_threat = getattr(problem, "projectile_threat_active", False)
		threat_dist = getattr(problem, "projectile_threat_distance", float("inf"))

		if projectile_threat and threat_dist <= 280:
			ang = getattr(problem, "nearest_projectile_angle", 0.0)
			direction = -1 if ang > 0 else 1
			self.cold_macro = {
				"behavior": "evade_projectile",
				"ticks_remaining": random.randint(20, 32),
				"params": {"direction": direction, "speed": 0.9},
				"frame_index": 0,
			}
			return

		if not problem.player_visible:
			# ALVO PERDIDO: Alternar aleatoriamente (estocástico) entre grupos de busca
			# Ações: search, pursue, wander, random_rotate
			choices = ["search_sweep", "pursue_last_known", "wander_relocate", "rotate_scan"]
			behavior = random.choice(choices)
			ticks = random.randint(self.cold_macro_min_ticks, self.cold_macro_max_ticks)

			if behavior == "search_sweep":
				direction = random.choice([-1, 1])
				speed = random.uniform(0.5, 0.8)
				self.cold_macro = {
					"behavior": "search",
					"ticks_remaining": ticks,
					"params": {"direction": direction, "speed": speed},
					"frame_index": 0,
				}
			elif behavior == "pursue_last_known":
				speed = random.uniform(0.6, 1.0)
				self.cold_macro = {
					"behavior": "pursue",
					"ticks_remaining": ticks,
					"params": {"speed": speed, "direction": random.choice([-1, 1])},
					"frame_index": 0,
				}
			elif behavior == "wander_relocate":
				direction = random.choice([-1, 1])
				speed = random.uniform(0.4, 0.9)
				self.cold_macro = {
					"behavior": "wander",
					"ticks_remaining": ticks,
					"params": {"direction": direction, "speed": speed},
					"frame_index": 0,
				}
			else:  # rotate_scan
				direction = random.choice([-1, 1])
				self.cold_macro = {
					"behavior": "random_rotate",
					"ticks_remaining": ticks,
					"params": {"direction": direction},
					"frame_index": 0,
				}

		else:
			# ALVO VISÍVEL: Alternar estocasticamente entre comportamentos de combate
			# Ações: pursue, align_and_fire, fire, wander
			choices = ["pursue_combat", "align_and_fire", "fire_direct", "strafe_combat"]
			behavior = random.choice(choices)
			ticks = random.randint(self.cold_macro_min_ticks, self.cold_macro_max_ticks)
			fire_interval = random.choice([20, 30, 45])

			if behavior == "pursue_combat":
				self.cold_macro = {
					"behavior": "pursue_combat",
					"ticks_remaining": ticks,
					"fire_interval": fire_interval,
					"params": {"speed": random.uniform(0.7, 1.0)},
					"frame_index": 0,
				}
			elif behavior == "align_and_fire":
				self.cold_macro = {
					"behavior": "align_and_fire",
					"ticks_remaining": ticks,
					"params": {},
					"frame_index": 0,
				}
			elif behavior == "fire_direct":
				self.cold_macro = {
					"behavior": "fire",
					"ticks_remaining": ticks,
					"params": {},
					"frame_index": 0,
				}
			else:  # strafe_combat
				direction = random.choice([-1, 1])
				self.cold_macro = {
					"behavior": "strafe_combat",
					"ticks_remaining": ticks,
					"fire_interval": fire_interval,
					"params": {"direction": direction, "speed": random.uniform(0.5, 0.85)},
					"frame_index": 0,
				}

	def decide_action(self, problem: Problem, fallback_solution: Solution, difficulty: str = "Normal") -> Solution:
		import random

		if getattr(self, 'action_hold_frames', 0) > 0 and self.last_solution is not None:
			threat = getattr(problem, 'projectile_threat_active', False)
			was_passive = self.last_solution.action in ("idle", "search", "wander")
			sight_gained = problem.player_visible and was_passive
			if threat or sight_gained:
				self.action_hold_frames = 0
			else:
				self.action_hold_frames -= 1
				return self.last_solution

		if self.episode_count < self.cold_start_episodes:

			self.mode = "COLD_START"

			projectile_threat = getattr(problem, "projectile_threat_active", False)
			threat_dist = getattr(problem, "projectile_threat_distance", float("inf"))
			current_behavior = self.cold_macro.get("behavior", "") if isinstance(self.cold_macro, dict) else ""

			# Regra 2: Destrava Antecipada (Early Release) se o projétil deixou de ser ameaça
			if current_behavior == "evade_projectile" and not projectile_threat:
				self.cold_macro = None
				current_behavior = ""

			# Se houver ameaça urgente de projétil e a macro não for evasão, força reavaliação
			if projectile_threat and threat_dist <= 220 and current_behavior != "evade_projectile":
				self.cold_macro = None

			# Se a visibilidade mudou e não estamos evadindo projétil, ajusta a macro ao contexto tático atual
			if self.cold_macro and current_behavior != "evade_projectile":
				if problem.player_visible and current_behavior in ("search", "random_rotate"):
					self.cold_macro = None
				elif not problem.player_visible and current_behavior in ("fire", "align_and_fire", "pursue_combat", "strafe_combat"):
					self.cold_macro = None

			if not self.cold_macro or self.cold_macro.get("ticks_remaining", 0) <= 0:
				self._start_new_cold_macro(problem)

			macro = self.cold_macro
			macro["ticks_remaining"] -= 1
			macro["frame_index"] += 1
			behavior = macro.get("behavior", "")
			params = macro.get("params", {})

			if behavior in ("search", "pursue", "wander", "random_rotate", "align_and_fire", "fire", "evade_projectile"):
				solution = Solution(behavior, params)
			elif behavior == "pursue_combat":
				if macro["frame_index"] % macro.get("fire_interval", 30) == 0:
					solution = Solution("fire", {})
				else:
					solution = Solution("pursue", params)
			elif behavior == "strafe_combat":
				if macro["frame_index"] % macro.get("fire_interval", 30) == 0:
					solution = Solution("fire", {})
				else:
					solution = Solution("wander", params)
			else:
				solution = self._random_action(problem)

			if macro["ticks_remaining"] <= 0:
				self.cold_macro = None

			self.last_case_id = None
			self.last_problem = problem
			self.last_solution = solution
			return solution

		similar_cases = self.db.get_similar_cases(asdict(problem), threshold=0.45, limit=10, difficulty=difficulty)
		best_similarity = max((case.get("similarity", 0.0) for case in similar_cases), default=0.0)
		effective_epsilon = self.epsilon
		if best_similarity >= 0.8:
			effective_epsilon *= 0.5
		elif best_similarity >= 0.65:
			effective_epsilon *= 0.75
		explore = random.random() < effective_epsilon

		if not similar_cases:
			self.mode = "RANDOM"
			solution = fallback_solution
			self.last_case_id = None
			if self.verbose:
				print("[RBC] Sem casos similares - Fallback ativado")
		elif explore:
			self.mode = "EXPLORE"
			# Escolhe aleatoriamente um dos Top 3 melhores casos
			top_k = similar_cases[:min(3, len(similar_cases))]
			chosen = random.choice(top_k)
			solution = self._adapt_solution(chosen, problem)
			self.last_case_id = chosen["case_id"]
			if self.verbose:
				display_id = chosen['case_id'] if len(chosen['case_id']) <= 12 else chosen['case_id'][-8:]
				print(f"[RBC] EXPLORANDO (Top 3) caso #{display_id} (sim={chosen.get('similarity', 0):.3f})")
		else:
			self.mode = "EXPLOIT"
			# Escolhe o melhor caso (Top 1)
			chosen = similar_cases[0]
			solution = self._adapt_solution(chosen, problem)
			self.last_case_id = chosen["case_id"]
			if self.verbose:
				display_id = chosen['case_id'] if len(chosen['case_id']) <= 12 else chosen['case_id'][-8:]
				print(f"[RBC] EXPLOITANDO (Top 1) caso #{display_id} (sim={chosen.get('similarity', 0):.3f})")

		try:
			if explore or not similar_cases:
				hold_min = max(1, int(self.explore_hold_min))
				hold_max = max(hold_min, int(self.explore_hold_max))
			else:
				hold_min = max(1, int(self.action_hold_min))
				hold_max = max(hold_min, int(self.action_hold_max))
			self.action_hold_frames = random.randint(hold_min, hold_max)
		except Exception:
			self.action_hold_frames = 4

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
		action = case["solution_action"]
		params = json.loads(case["solution_params"]) if case["solution_params"] else {}

		if action == "fire" and "angle_adjustment" in params:
			del params["angle_adjustment"]

		if "move" in action and "speed" in params:
			original_distance = case["problem_distance"]
			new_distance = new_problem.distance
			if new_distance < 100:
				params["speed"] = 0.5
			elif new_distance > 400:
				params["speed"] = 1.0

		return Solution(action=action, params=params)

	def learn(self, case_id: Optional[str], problem: Problem, solution: Solution, outcome: Outcome, session_id: str, difficulty: str) -> None:
		if case_id:
			self.db.update_case_usage(case_id=case_id, success=outcome.success, reward=outcome.reward)
			# Se a experiência for relevante (sucesso, alto reward, dano causado/tomado ou modo EXPLORE/posição),
			# permite ramificar e salvar um novo caso no banco de dados para crescimento constante no modo IA.
			is_novel_or_high_value = (
				outcome.success
				or outcome.reward >= 4.0
				or outcome.damage_dealt > 0
				or outcome.damage_taken > 0
				or outcome.outcome_type in ("hit", "evaded", "positional_tick")
				or self.mode == "EXPLORE"
			)
			if not is_novel_or_high_value:
				return

		# Filtro de idle redundante:

		# Permite salvar a primeira transição para idle (ex: parada estratégica/cooldown),
		# mas descarta salvamentos de idles contínuos idênticos sem evento relevante.
		if solution.action == "idle" and outcome.outcome_type not in ("hit", "damaged", "miss"):
			recent = getattr(problem, 'recent_actions', []) or []
			if len(recent) >= 2 and recent[-1] == "idle" and recent[-2] == "idle":
				return

		new_case = {
			"player_id": self.player_id,
			"problem_distance": problem.distance,
			"problem_angle_diff": problem.angle_diff,
			"problem_nearest_projectile_distance": getattr(problem, 'nearest_projectile_distance', float('inf')),
			"problem_nearest_projectile_angle": getattr(problem, 'nearest_projectile_angle', 0.0),
			"problem_projectiles_nearby_count": getattr(problem, 'projectiles_nearby_count', 0),
			"problem_edge_distance_top": getattr(problem, 'edge_distance_top', float('inf')),
			"problem_edge_distance_bottom": getattr(problem, 'edge_distance_bottom', float('inf')),
			"problem_nearest_edge_distance": getattr(problem, 'nearest_edge_distance', float('inf')),
			"problem_border_pressure": getattr(problem, 'border_pressure', 0.0),
			"problem_border_side": getattr(problem, 'border_side', 0),
			"problem_closing_speed": getattr(problem, 'closing_speed', 0.0),
			"problem_recent_actions": getattr(problem, 'recent_actions', []) or [],
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
			"usage_count": 1,
			"success_count": 1 if outcome.success else 0,
			"total_reward": outcome.reward,
			"avg_reward": outcome.reward,
			"session_id": session_id,
			"difficulty": difficulty,
			"created_by": "learned",
		}

		self.db.insert_case(new_case)

		if self.verbose:
			print(f"[RBC] NOVO CASO APRENDIDO: {solution.action} (reward={outcome.reward:.1f}, sucesso={outcome.success})")

	def get_statistics(self, player_id: Optional[str] = None) -> Dict:
		target_player = player_id if player_id is not None else self.player_id
		stats = self.db.get_statistics(player_id=target_player)
		stats["epsilon"] = self.epsilon
		stats["mode"] = self.mode
		stats["episode"] = self.episode_count
		stats["player_id"] = target_player
		return stats

	def close(self) -> None:
		if hasattr(self, 'db') and self.db:
			self.db.close()
			self.db = None
