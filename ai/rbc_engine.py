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

		self.epsilon = 0.6
		self.epsilon_min = 0.05
		self.epsilon_decay = 0.85

		self.verbose = True

		self.mode = 'INIT'
		self.episode_count = 0
		self.top_k = 3

		self.cold_start_episodes = 5
		self.cold_macro = None
		self.cold_macro_min_ticks = 6
		self.cold_macro_max_ticks = 45
		self.cold_macro_fire_interval = 30

		self.action_hold_frames = 0
		self.action_hold_min = 6
		self.action_hold_max = 45

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
		delta = random.uniform(-140, 140)
		target_y = problem.npc_y + delta
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

	def decide_action(self, problem: Problem, fallback_solution: Solution, difficulty: str = "Normal") -> Solution:
		import random

		if getattr(self, 'action_hold_frames', 0) > 0 and self.last_solution is not None:
			self.action_hold_frames -= 1
			return self.last_solution

		if self.episode_count < self.cold_start_episodes:
			self.mode = "COLD_START"
			if self.verbose:
				print("[RBC] COLD START - macro-actions")

			if not self.cold_macro or self.cold_macro.get("ticks_remaining", 0) <= 0:
				self._start_new_cold_macro(problem)

			macro = self.cold_macro
			macro["ticks_remaining"] -= 1
			macro["frame_index"] += 1

			target_y = macro["target_y"]
			behavior = macro["behavior"]
			tol = 8.0

			if behavior in ("move_and_fire", "move_only"):
				if abs(problem.npc_y - target_y) > tol:
					direction = 1 if target_y > problem.npc_y else -1
					speed = 0.7 if behavior == "move_and_fire" else 0.5
					solution = Solution("wander", {"direction": direction, "speed": speed})
				else:
					if behavior == "move_and_fire":
						if macro["frame_index"] % macro["fire_interval"] == 0:
							solution = Solution("fire", {})
						else:
							solution = Solution("idle", {})
					else:
						solution = Solution("idle", {})
			elif behavior == "fire_only":
				if macro["frame_index"] % macro["fire_interval"] == 0:
					solution = Solution("fire", {})
				else:
					solution = Solution("idle", {})
			else:
				solution = self._random_action(problem)

			if macro["ticks_remaining"] <= 0:
				self.cold_macro = None

			self.last_case_id = None
			self.last_problem = problem
			self.last_solution = solution
			return solution

		explore = random.random() < self.epsilon

		similar_cases = self.db.get_similar_cases(asdict(problem), threshold=0.5, limit=5, difficulty=difficulty)

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
			similar_cases_sorted = sorted(similar_cases, key=lambda c: c.get("similarity", 0.0), reverse=True)
			chosen = similar_cases_sorted[0]

			if self.verbose:
				print(f"[RBC] EXPLOITANDO (Determinístico) caso #{chosen['case_id'][:8]} (similaridade={chosen.get('similarity', 0):.3f})")

			solution = self._adapt_solution(chosen, problem)
			self.last_case_id = chosen["case_id"]

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
			return

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

	def get_statistics(self) -> Dict:
		stats = self.db.get_statistics()
		stats["epsilon"] = self.epsilon
		stats["mode"] = self.mode
		stats["episode"] = self.episode_count
		return stats

	def close(self) -> None:
		if hasattr(self, 'db') and self.db:
			self.db.close()
			self.db = None
