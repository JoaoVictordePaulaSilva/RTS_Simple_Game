"""RBC data models used by the NPC AI."""

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class Problem:
	"""Representa um problema/estado do jogo a ser resolvido."""
	distance: float
	angle_diff: float
	npc_health: float
	player_health: float
	player_visible: bool
	frames_lost: int = 0
	npc_x: float = 0.0
	npc_y: float = 0.0
	nearest_projectile_distance: float = float('inf')
	nearest_projectile_angle: float = 0.0
	projectiles_nearby_count: int = 0
	projectile_threat_active: bool = False
	projectile_threat_distance: float = float('inf')
	edge_distance_top: float = float('inf')
	edge_distance_bottom: float = float('inf')
	nearest_edge_distance: float = float('inf')
	border_pressure: float = 0.0
	border_side: int = 0
	closing_speed: float = 0.0
	recent_actions: Optional[List[str]] = None


@dataclass
class Solution:
	"""Representa uma solução/ação a ser tomada."""
	action: str
	params: Dict = None

	def __post_init__(self):
		if self.params is None:
			self.params = {}


@dataclass
class Outcome:
	"""Representa o resultado de uma ação executada."""
	success: bool
	damage_dealt: float = 0.0
	damage_taken: float = 0.0
	outcome_type: str = "unknown"
	reward: float = 0.0


__all__ = ["Problem", "Solution", "Outcome"]
