"""Game entities used by the RTS loop."""

import math

import pygame

from .constants import ARENA_TOP, ARENA_BOTTOM, ARENA_LEFT, ARENA_RIGHT


class Tank:
	def __init__(self, x, y, color, is_player=False, name="Tank"):
		self.x = x
		self.y = y
		self.color = color
		self.angle = 180  # graus / degrees, 0 -> right
		self.width = 60
		self.height = 36
		self.speed = 180  # pixels per second (only along Y / apenas eixo Y)
		self.rot_speed = 140  # degrees per second / graus por segundo
		self.health = 100
		self.is_player = is_player
		self.name = name
		self.fire_cooldown = 0.5
		self.fire_timer = 0

	def rect_center(self):
		return (self.x, self.y)

	def update(self, dt):
		if self.fire_timer > 0:
			self.fire_timer = max(0, self.fire_timer - dt)

	def move_y(self, direction, dt):
		self.y += direction * self.speed * dt
		self.y = max(ARENA_TOP, min(ARENA_BOTTOM, self.y))

	def rotate(self, direction, dt):
		self.angle += direction * self.rot_speed * dt
		self.angle %= 360

	def can_fire(self):
		return self.fire_timer <= 0

	def fire(self):
		self.fire_timer = self.fire_cooldown

	def hit(self, dmg):
		self.health -= dmg

	def draw(self, surf):
		tank_surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
		body_rect = pygame.Rect(0, 0, self.width, self.height)
		pygame.draw.rect(tank_surf, self.color, body_rect, border_radius=6)
		turret = pygame.Rect(self.width - 10, self.height // 2 - 6, 24, 12)
		pygame.draw.rect(tank_surf, (40, 40, 40), turret, border_radius=3)

		rotated = pygame.transform.rotate(tank_surf, -self.angle)
		rect = rotated.get_rect(center=(self.x, self.y))
		surf.blit(rotated, rect.topleft)

		font = pygame.font.Font(None, 22)
		name_surface = font.render(self.name, True, (255, 255, 255))
		name_rect = name_surface.get_rect(center=(self.x, self.y - self.height // 2 - 12))
		surf.blit(name_surface, name_rect)


class Projectile:
	def __init__(self, x, y, angle, owner, speed=420, damage=25, color=None, origin_problem=None, origin_solution=None, origin_case_id=None):
		self.x = x
		self.y = y
		self.angle = angle
		self.owner = owner
		self.speed = speed
		self.damage = damage
		self.radius = 6
		self.is_alive = True
		self.color = color if color else owner.color
		self.origin_problem = origin_problem
		self.origin_solution = origin_solution
		self.origin_case_id = origin_case_id

	def update(self, dt):
		rad = math.radians(self.angle)
		self.x += math.cos(rad) * self.speed * dt
		self.y += math.sin(rad) * self.speed * dt
		if self.x < ARENA_LEFT or self.x > ARENA_RIGHT or self.y < ARENA_TOP or self.y > ARENA_BOTTOM:
			self.is_alive = False

	def draw(self, surf):
		pygame.draw.circle(surf, self.color, (int(self.x), int(self.y)), self.radius)


__all__ = ["Tank", "Projectile"]
