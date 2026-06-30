"""NPC perception model."""

import math


class NPCPerception:
	"""
	Classe para representar a percepção do NPC
	Class to represent NPC perception
	O NPC observa o inimigo e reage ao que vê
	NPC observes the enemy and reacts to what it sees
	"""
	def __init__(self, tank):
		self.tank = tank
		self.vision_range = 800
		self.vision_angle = 75
		self.last_seen_player_pos = None
		self.last_seen_player_angle = None
		self.perception_memory = []
		self.perception_log = []
		self.last_player_y = None
		self.last_player_angle = None
		self.player_moving_up_time = 0
		self.player_moving_down_time = 0
		self.nearest_projectile_distance = float('inf')
		self.nearest_projectile_angle = 0.0
		self.projectiles_nearby_count = 0

	def can_see(self, other_tank):
		dx = other_tank.x - self.tank.x
		dy = other_tank.y - self.tank.y
		dist = math.sqrt(dx * dx + dy * dy)

		if dist > self.vision_range:
			return False

		angle_to_target = math.degrees(math.atan2(dy, dx))
		angle_diff = abs(angle_to_target - self.tank.angle)
		if angle_diff > 180:
			angle_diff = 360 - angle_diff

		return angle_diff < self.vision_angle / 2

	def update(self, player_tank, dt, projectiles=None):
		if self.can_see(player_tank):
			self.last_seen_player_pos = (player_tank.x, player_tank.y)
			self.last_seen_player_angle = player_tank.angle
			self.perception_memory.append(("see", player_tank.x, player_tank.y))
		else:
			self.perception_memory.append(("lost", None, None))

		if self.last_player_y is not None:
			if player_tank.y < self.last_player_y:
				self.player_moving_up_time += dt
				self.player_moving_down_time = 0
				if int(self.player_moving_up_time * 10) % 20 == 0:
					self.log_event("MOVE_UP", f"{self.player_moving_up_time:.1f}s")
			elif player_tank.y > self.last_player_y:
				self.player_moving_down_time += dt
				self.player_moving_up_time = 0
				if int(self.player_moving_down_time * 10) % 20 == 0:
					self.log_event("MOVE_DOWN", f"{self.player_moving_down_time:.1f}s")
			else:
				self.player_moving_up_time = 0
				self.player_moving_down_time = 0

		if self.last_player_angle is not None:
			if abs(player_tank.angle - self.last_player_angle) > 5:
				direction = "CCW" if (player_tank.angle - self.last_player_angle) % 360 < 180 else "CW"
				self.log_event("ROTATE", direction)

		self.last_player_y = player_tank.y
		self.last_player_angle = player_tank.angle

		if len(self.perception_memory) > 30:
			self.perception_memory.pop(0)

		self.nearest_projectile_distance = float('inf')
		self.nearest_projectile_angle = 0.0
		self.projectiles_nearby_count = 0
		if projectiles:
			nx, ny = self.tank.x, self.tank.y
			for p in projectiles:
				dx = p.x - nx
				dy = p.y - ny
				dist = math.hypot(dx, dy)
				if dist < self.nearest_projectile_distance:
					self.nearest_projectile_distance = dist
					ang = math.degrees(math.atan2(dy, dx))
					rel_ang = ang - self.tank.angle
					if rel_ang > 180:
						rel_ang -= 360
					if rel_ang < -180:
						rel_ang += 360
					self.nearest_projectile_angle = rel_ang
				if dist <= 300:
					self.projectiles_nearby_count += 1

	def log_event(self, event_type, details=""):
		timestamp = len(self.perception_log)
		self.perception_log.append(f"[{timestamp}] {event_type}: {details}")
		if len(self.perception_log) > 15:
			self.perception_log.pop(0)

	def get_perception_text(self):
		if self.last_seen_player_pos:
			return f"SEEING: Player at ({int(self.last_seen_player_pos[0])}, {int(self.last_seen_player_pos[1])})"
		return "STATUS: Lost target"


__all__ = ["NPCPerception"]
