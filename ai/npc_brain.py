"""
Cérebro do NPC com RBC e IA básica como fallback.
NPC Brain combining RBC and basic AI fallback.
"""

import random
import math
from typing import Dict, Optional, Tuple

from .rbc_engine import RBCEngine
from .rbc_models import Problem, Solution, Outcome

ARENA_TOP = 100
ARENA_BOTTOM = 480


class NPCBrain:
	"""
	Cérebro inteligente do NPC que combina RBC com IA básica.
	NPC intelligent brain combining RBC with basic AI fallback.
	"""

	def __init__(self, db_path: str = "npc_cases.db") -> None:
		self.rbc_engine = RBCEngine(db_path)
		self.session_id = "default"
		self.frame_counter = 0
		self.last_action: Optional[Solution] = None
		self.pending_outcome: Optional[Tuple[Problem, Solution]] = None
		self.episode_frame_count = 0
		self.episode_frame_limit = 1800
		self.verbose = False

		self.position_history = []
		self.action_history = []
		self.recent_damage_history = []
		self.max_history = 60
		self.stuck_frame_count = 0
		self.stuck_threshold_frames = 45
		self.stuck_position_tolerance = 50.0
		self.ineffectiveness_boost_base = 0.1
		self.evade_cooldown_frames = 18
		self.evade_cooldown_remaining = 0

	def set_session(self, session_id: str) -> None:
		self.session_id = session_id

	def reset_episode(self) -> None:
		self.episode_frame_count = 0
		self.pending_outcome = None
		self.position_history = []
		self.action_history = []
		self.recent_damage_history = []
		self.stuck_frame_count = 0

	def _track_action_effectiveness(self, npc_x: float, npc_y: float, action: Solution, damage_dealt: float) -> None:
		self.position_history.append((npc_x, npc_y))
		if len(self.position_history) > self.max_history:
			self.position_history.pop(0)

		self.action_history.append(action.action)
		if len(self.action_history) > self.max_history:
			self.action_history.pop(0)

		self.recent_damage_history.append(damage_dealt)
		if len(self.recent_damage_history) > self.max_history:
			self.recent_damage_history.pop(0)

	def _detect_ineffectiveness(self) -> Tuple[bool, dict]:
		metrics = {"is_stuck_position": False, "is_repeating_action": False, "total_recent_damage": 0.0, "stuck_duration_frames": 0}

		if len(self.position_history) < self.stuck_threshold_frames:
			return False, metrics

		recent_positions = self.position_history[-self.stuck_threshold_frames:]
		if len(recent_positions) >= self.stuck_threshold_frames:
			first_pos = recent_positions[0]
			same_area_count = 0
			for pos in recent_positions:
				dist = math.sqrt((pos[0] - first_pos[0])**2 + (pos[1] - first_pos[1])**2)
				if dist <= self.stuck_position_tolerance:
					same_area_count += 1

			is_stuck = (same_area_count / len(recent_positions)) > 0.8
			if is_stuck:
				metrics["is_stuck_position"] = True
				metrics["stuck_duration_frames"] = self.stuck_threshold_frames

		recent_actions = self.action_history[-self.stuck_threshold_frames:]
		if recent_actions:
			most_common_action = max(set(recent_actions), key=recent_actions.count)
			action_repetition = recent_actions.count(most_common_action) / len(recent_actions)
			if action_repetition > 0.7:
				metrics["is_repeating_action"] = True

		total_damage = sum(self.recent_damage_history[-self.stuck_threshold_frames:])
		metrics["total_recent_damage"] = total_damage

		is_ineffective = (metrics["is_stuck_position"] and total_damage < 5.0) or (metrics["is_repeating_action"] and total_damage < 3.0)

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
		projectile_threat_active: bool = False,
		projectile_threat_distance: float = None,
	):
		problem = self._encode_problem(
			npc_x, npc_y, npc_angle, npc_health,
			player_x, player_y, player_health,
			player_visible, frames_since_last_seen,
			nearest_projectile_distance, nearest_projectile_angle, projectiles_nearby_count,
			projectile_threat_active, projectile_threat_distance
		)

		if self.evade_cooldown_remaining > 0:
			self.evade_cooldown_remaining -= 1

		fallback_solution = self._generate_fallback_action(problem)
		solution = self.rbc_engine.decide_action(problem, fallback_solution, difficulty)

		self.last_action = solution
		self.pending_outcome = (problem, solution)
		self.frame_counter += 1
		self.episode_frame_count += 1

		self._track_action_effectiveness(npc_x, npc_y, solution, 0.0)

		return solution

	def set_player(self, player_id: str):
		self.rbc_engine.set_player(player_id)

	def _encode_problem(
		self,
		npc_x: float, npc_y: float, npc_angle: float, npc_health: float,
		player_x: float, player_y: float, player_health: float,
		player_visible: bool, frames_since_last_seen: int,
		nearest_projectile_distance: float = None, nearest_projectile_angle: float = None, projectiles_nearby_count: int = 0,
		projectile_threat_active: bool = False, projectile_threat_distance: float = None
	) -> Problem:
		# A métrica principal de proximidade pode ser a distância vertical.
		dy = player_y - npc_y
		distance = abs(dy)
		previous_problem = getattr(self.rbc_engine, "last_problem", None)
		closing_speed = 0.0
		if previous_problem is not None:
			closing_speed = previous_problem.distance - distance

		edge_distance_top = max(0.0, npc_y - ARENA_TOP)
		edge_distance_bottom = max(0.0, ARENA_BOTTOM - npc_y)
		nearest_edge_distance = min(edge_distance_top, edge_distance_bottom)
		border_pressure = max(0.0, min(1.0, 1.0 - (nearest_edge_distance / 120.0)))
		if edge_distance_top < edge_distance_bottom:
			border_side = -1
		elif edge_distance_bottom < edge_distance_top:
			border_side = 1
		else:
			border_side = 0
		recent_actions = list(self.action_history[-4:]) if self.action_history else []

		# Ângulo mantido apenas para compatibilidade com o schema e debug.
		# As entidades ainda não usam rotação real no fluxo atual do jogo.
		angle_diff = 0.0

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
			projectile_threat_active=projectile_threat_active,
			projectile_threat_distance=projectile_threat_distance if projectile_threat_distance is not None else float('inf'),
			edge_distance_top=edge_distance_top,
			edge_distance_bottom=edge_distance_bottom,
			nearest_edge_distance=nearest_edge_distance,
			border_pressure=border_pressure,
			border_side=border_side,
			closing_speed=closing_speed,
			recent_actions=recent_actions,
		)

	def _generate_fallback_action(self, problem: Problem) -> Solution:
		import random

		border_pressure = getattr(problem, 'border_pressure', 0.0)
		border_side = getattr(problem, 'border_side', 0)
		edge_escape_direction = 1 if border_side < 0 else -1 if border_side > 0 else random.choice([-1, 1])
		near_border = getattr(problem, 'nearest_edge_distance', float('inf')) <= 80 or border_pressure >= 0.55

		if near_border and self.evade_cooldown_remaining <= 0:
			if problem.player_visible and problem.distance < 40 and random.random() < 0.4:
				return Solution(action="fire", params={})
			if problem.player_visible and problem.distance < 80 and random.random() < 0.35:
				return Solution(action="pursue", params={"speed": 0.85})
			return Solution(action="wander", params={"direction": edge_escape_direction, "speed": 0.85})

		projectile_threat_active = getattr(problem, 'projectile_threat_active', False)
		projectile_threat_distance = getattr(problem, 'projectile_threat_distance', float('inf'))
		if projectile_threat_active and projectile_threat_distance <= 280 and self.evade_cooldown_remaining <= 0:
			ang = getattr(problem, 'nearest_projectile_angle', 0.0)
			direction = -1 if ang > 0 else 1
			self.evade_cooldown_remaining = self.evade_cooldown_frames
			return Solution(action="evade_projectile", params={"direction": direction, "speed": 0.9})

		if problem.player_visible:
			# Sem rotação efetiva, a decisão usa principalmente a distância vertical.
			if problem.distance < 20:
				if random.random() < 0.8:
					return Solution(action="fire", params={})
				return Solution(action="wander", params={"direction": random.choice([-1, 1]), "speed": 0.6})
			elif problem.distance < 60:
				r = random.random()
				if r < 0.6:
					return Solution(action="align_and_fire", params={})
				elif r < 0.8:
					return Solution(action="fire", params={})
				return Solution(action="pursue", params={"speed": random.uniform(0.5, 1.0)})
			elif problem.distance < 140:
				r = random.random()
				if r < 0.5:
					return Solution(action="align_and_fire", params={})
				elif r < 0.7:
					# Nome legado; hoje esta ação representa uma varredura vertical.
					return Solution(action="random_rotate", params={"direction": 1 if problem.distance > 0 else -1})
				return Solution(action="pursue", params={"speed": random.uniform(0.6, 0.9)})
			return Solution(action="random_rotate", params={"direction": random.choice([-1, 1])})

		elif problem.frames_lost < 120:
			r = random.random()
			if r < 0.4:
				return Solution(action="search", params={})
			elif r < 0.7:
				return Solution(action="random_rotate", params={"direction": random.choice([-1, 1])})
			return Solution(action="wander", params={"direction": random.choice([-1, 1]), "speed": 0.5})

		else:
			r = random.random()
			if r < 0.35:
				return Solution(action="wander", params={"direction": random.choice([-1, 1]), "speed": random.uniform(0.4, 0.8)})
			elif r < 0.70:
				return Solution(action="random_rotate", params={"direction": random.choice([-1, 1])})
			elif r < 0.85:
				return Solution(action="search", params={})
			return Solution(action="fire", params={})

	def report_outcome(
		self,
		success: bool,
		damage_dealt: float = 0.0,
		damage_taken: float = 0.0,
		outcome_type: str = "unknown",
		difficulty: str = "Normal",
		problem_override: Optional[Problem] = None,
		solution_override: Optional[Solution] = None,
		case_id_override: Optional[str] = None,
	) -> None:
		if problem_override is not None and solution_override is not None:
			problem = problem_override
			solution = solution_override
			target_case_id = case_id_override
		elif self.pending_outcome:
			problem, solution = self.pending_outcome
			target_case_id = self.rbc_engine.last_case_id
		else:
			return

		outcome = Outcome(success=success, damage_dealt=damage_dealt, damage_taken=damage_taken, outcome_type=outcome_type)

		if self.recent_damage_history:
			self.recent_damage_history[-1] = damage_dealt

		reward = 0.0
		if success:
			reward += 10.0
		if damage_dealt > 0:
			reward += damage_dealt * 2.0
		if damage_taken > 0:
			reward -= damage_taken * 3.0
		if outcome_type == "hit":
			reward += 15.0
		elif outcome_type == "miss":
			reward -= 5.0
		elif outcome_type == "evaded":
			reward += 3.0
		elif outcome_type == "safe":
			reward += 1.0

		# O jogo atual não depende de alinhamento angular real.
		# A recompensa passa a privilegiar a proximidade vertical e a distância útil de tiro.
		if solution.action in ["fire", "align_and_fire"]:
			if problem.distance < 20:
				reward += 5.0
			elif problem.distance < 60:
				reward += 2.0

			if 80 <= problem.distance <= 180:
				reward += 3.0
			elif problem.distance < 35:
				reward -= 2.0

		if solution.action == "idle":
			reward -= 3.0

		if problem.player_visible:
			reward += 2.0

		border_pressure = getattr(problem, "border_pressure", 0.0)
		border_side = getattr(problem, "border_side", 0)
		edge_distance = getattr(problem, "nearest_edge_distance", float("inf"))
		if border_pressure > 0:
			away_direction = 1 if border_side < 0 else -1 if border_side > 0 else 0
			move_direction = None
			if isinstance(solution.params, dict):
				move_direction = solution.params.get("direction")

			if solution.action in ("wander", "search"):
				if move_direction == away_direction and away_direction != 0:
					reward += 4.0 * border_pressure
				else:
					reward -= 4.0 * border_pressure
			elif solution.action == "pursue":
				if edge_distance <= 80:
					reward += 2.0 * border_pressure
				else:
					reward += 0.5
			elif solution.action == "evade_projectile":
				reward += 1.5 * border_pressure
			elif solution.action in ("idle", "random_rotate"):
				reward -= 5.0 * border_pressure

		player_defeated = damage_dealt >= 100 or outcome_type == "player_dead"
		if player_defeated:
			reward *= 2.5
			if self.verbose:
				print(f"[REWARD] Multiplicador de vitória aplicado! Reward final x2.5")

		if self.episode_frame_count > 0:
			time_penalty = (self.episode_frame_count / self.episode_frame_limit) * 5.0
			reward -= time_penalty

		is_ineffective, ineffectiveness_metrics = self._detect_ineffectiveness()
		if is_ineffective:
			ineffectiveness_penalty = ineffectiveness_metrics["stuck_duration_frames"] * 0.05
			reward -= ineffectiveness_penalty

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

		reward = max(-25.0, reward)
		outcome.reward = reward

		if hasattr(self, "analytics_manager") and self.analytics_manager:
			self.analytics_manager.record_reward(reward)
			self.analytics_manager.record_damage(dealt=damage_dealt, taken=damage_taken)

		self.rbc_engine.learn(
			case_id=target_case_id,
			problem=problem,
			solution=solution,
			outcome=outcome,
			session_id=self.session_id,
			difficulty=difficulty
		)

		self.pending_outcome = None

	def get_statistics(self, player_id: Optional[str] = None) -> Dict:
		return self.rbc_engine.get_statistics(player_id=player_id)

	def close(self) -> None:
		if hasattr(self, 'rbc_engine') and self.rbc_engine:
			self.rbc_engine.close()
			self.rbc_engine = None

	def __enter__(self):
		return self

	def __exit__(self, exc_type, exc_val, exc_tb):
		self.close()
