import math
import json
import os
import sys
import uuid

import pygame
import psutil

from ai.npc_brain import NPCBrain
from ai.rbc_models import Solution
from database.initializer import initialize_database
from .constants import SCREEN_WIDTH, SCREEN_HEIGHT, FPS, ARENA_TOP, LOG_HEIGHT, ARENA_BOTTOM, ARENA_LEFT, ARENA_RIGHT, STRINGS
from .entities import Tank, Projectile
from .perception import NPCPerception
from .ui import Button, NPCFace
from utils.action_guards import should_auto_fire_in_cold_start
from utils.rbc_monitor import RBCMonitorWindow
from utils.task_queue import AdaptiveTaskQueue, TaskPriority


class Game:
	def __init__(self):
		pygame.init()
		pygame.display.set_caption("RTS Tanks - Demo")
		self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
		self.clock = pygame.time.Clock()
		self.font = pygame.font.Font(None, 28)
		self.small_font = pygame.font.Font(None, 20)
		self.font_small = pygame.font.Font(None, 18)
		self.font_tiny = pygame.font.Font(None, 14)
		self.menu_title_font = pygame.font.Font(None, 64)
		self.section_title_font = pygame.font.Font(None, 48)

		self.language = "EN"
		self.state = "name_input"
		self.player_name = ""
		self.name_input_active = False
		self.running = True

		self.setup_menu()
		self.reset_game()

		self.options = {"difficulty": "Normal", "projectile_speed": 420}

		initialize_database(force_reset=False)
		self.npc_brain = NPCBrain("npc_cases.db")
		self.current_session_id = None
		self.action_frame_counter = 0

		self.npc_face = NPCFace(width=60, height=60)

		self.debug_mode = False
		self.frame_counter = 0

		self.rbc_monitor = RBCMonitorWindow()
		self.rbc_monitor.start()
		self._monitor_update_timer = 0.0
		self.match_result_text = ""
		self.match_conclusion_sent = False
		self._decision_counter = 0

		self.task_queue = AdaptiveTaskQueue(
			initial_tasks_per_frame=5,
			cpu_threshold=0.70,
			debug=False
		)
		self.process = psutil.Process(os.getpid())

	def setup_menu(self):
		center_x = SCREEN_WIDTH // 2
		self.buttons = []
		btn_w = 220
		btn_h = 48
		gap = 14
		start_y = SCREEN_HEIGHT // 2 - (btn_h + gap)

		def start_game():
			if self.player_name.strip():
				self.start_new_game()
			else:
				self.state = "name_input"

		def open_options():
			self.state = "options"

		def quit_game():
			self.running = False

		self.buttons = [
			Button((center_x - btn_w // 2, start_y, btn_w, btn_h), STRINGS[self.language]["start_game"], action=start_game, font=self.font),
			Button((center_x - btn_w // 2, start_y + btn_h + gap, btn_w, btn_h), STRINGS[self.language]["options"], action=open_options, font=self.font),
			Button((center_x - btn_w // 2, start_y + 2 * (btn_h + gap), btn_w, btn_h), STRINGS[self.language]["quit"], action=quit_game, font=self.font),
		]

	def reset_game(self):
		self.player = Tank(140, SCREEN_HEIGHT // 2, (40, 120, 200), is_player=True, name=self.player_name if self.player_name else STRINGS[self.language]["player"])
		self.npc = Tank(SCREEN_WIDTH - 140, SCREEN_HEIGHT // 2, (200, 100, 60), is_player=False, name=STRINGS[self.language]["enemy"])
		self.player.angle = 0
		self.npc.angle = 180
		self.npc_perception = NPCPerception(self.npc)
		self.projectiles = []
		self.last_ai_shot = 0
		self.ai_shot_interval = 1.0

	def start_new_game(self):
		self.reset_game()
		diff = "Normal"
		self.options["difficulty"] = diff
		if diff == "Easy":
			self.ai_shot_interval = 1.6
			self.npc.health = 80
			self.player.health = 140
		elif diff == "Hard":
			self.ai_shot_interval = 0.8
			self.npc.health = 140
			self.player.health = 80
		else:
			self.ai_shot_interval = 1.0
			self.player.health = 100
			self.npc.health = 100

		self.current_session_id = str(uuid.uuid4())
		self.npc_brain.set_session(self.current_session_id)
		self.npc_brain.set_player(self.player_name)
		self.action_frame_counter = 0
		self.match_result_text = ""
		self.match_conclusion_sent = False
		self._monitor_update_timer = 0.0
		self._decision_counter = 0

		self.state = "playing"

	def run(self):
		while self.running:
			dt = self.clock.tick(FPS) / 1000.0
			self.handle_events()
			self.update(dt)
			self.draw()

		self.rbc_monitor.close()
		pygame.quit()
		sys.exit()

	def handle_events(self):
		for ev in pygame.event.get():
			if ev.type == pygame.QUIT:
				self.running = False
			if self.state == "menu":
				for b in self.buttons:
					b.handle_event(ev)
			elif self.state == "name_input":
				if ev.type == pygame.KEYDOWN:
					if ev.key == pygame.K_RETURN:
						self._commit_login(go_to_menu=True)
					elif ev.key == pygame.K_ESCAPE:
						if self.player_name.strip() != "":
							self.state = "menu"
					elif ev.key == pygame.K_BACKSPACE:
						self.player_name = self.player_name[:-1]
					else:
						if len(self.player_name) < 12 and ev.unicode.isprintable() and ev.unicode:
							self.player_name += ev.unicode
			elif self.state == "options":
				if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
					self.state = "menu"
			elif self.state == "playing":
				if ev.type == pygame.KEYDOWN:
					if ev.key == pygame.K_ESCAPE:
						self.state = "menu"
					elif ev.key == pygame.K_d:
						self.debug_mode = not self.debug_mode
						print(f"Debug mode: {'ON' if self.debug_mode else 'OFF'}")
					elif ev.key == pygame.K_r and self.debug_mode:
						self.reset_game_and_database()
					elif ev.key == pygame.K_SPACE:
						if self.player.can_fire():
							self.player.fire()
							proj = Projectile(self.player.x + math.cos(math.radians(self.player.angle)) * 40,
											   self.player.y + math.sin(math.radians(self.player.angle)) * 40,
											   self.player.angle, self.player, speed=self.options.get("projectile_speed", 420))
							self.projectiles.append(proj)
							self.npc_perception.log_event("SHOT", f"ângulo {int(self.player.angle)}°")

	def _set_language(self, lang):
		self.language = lang
		self.setup_menu()
		self.reset_game()

	def _commit_login(self, go_to_menu=True):
		name = self.player_name.strip()
		if not name:
			name = STRINGS[self.language].get("player_name_placeholder", "joguinho")
		self.player_name = name[:12]
		self.reset_game()
		if go_to_menu:
			self.state = "menu"

	def get_cpu_usage(self):
		try:
			return self.process.cpu_percent(interval=0.01) / 100.0
		except:
			return 0.0

	def _handle_player_input(self, dt):
		keys = pygame.key.get_pressed()
		if keys[pygame.K_UP]:
			self.player.move_y(-1, dt)
		if keys[pygame.K_DOWN]:
			self.player.move_y(1, dt)

	def _update_players_cooldown(self, dt):
		self.player.update(dt)
		self.npc.update(dt)

	def _update_npc_perception_and_ai(self, dt):
		self.npc_perception.update(self.player, dt, projectiles=self.projectiles)
		self._update_npc_ai(dt)

	def _update_all_projectiles(self, dt):
		for p in self.projectiles:
			p.update(dt)

	def _check_all_collisions(self):
		for p in list(self.projectiles):
			if not p.is_alive:
				self.projectiles.remove(p)
				continue
			if p.owner is not self.player and self._collide_proj_tank(p, self.player):
				self.player.hit(p.damage)
				p.is_alive = False
				self.npc_brain.report_outcome(
					success=True,
					damage_dealt=p.damage,
					damage_taken=0,
					outcome_type="hit",
					difficulty=self.options.get("difficulty", "Normal")
				)

			if p.owner is not self.npc and self._collide_proj_tank(p, self.npc):
				self.npc.hit(p.damage)
				p.is_alive = False
				self.npc_brain.report_outcome(
					success=False,
					damage_dealt=0,
					damage_taken=p.damage,
					outcome_type="damaged",
					difficulty=self.options.get("difficulty", "Normal")
				)

		self.projectiles = [p for p in self.projectiles if p.is_alive]

	def _update_game_state(self):
		if self.player.health <= 0 or self.npc.health <= 0:
			self.npc_brain.rbc_engine.end_episode()
			self.match_result_text = self._build_match_result_text()
			self.state = "gameover"

	def _update_rbc_monitor_periodic(self):
		if self._monitor_update_timer >= 0.2:
			self._monitor_update_timer = 0.0
			self._update_rbc_monitor(in_game=True)

	def update(self, dt):
		if self.state == "playing":
			self.frame_counter += 1
			self._monitor_update_timer += dt

			cpu_usage = self.get_cpu_usage()
			self.task_queue.update_cpu_usage(cpu_usage)

			self.task_queue.add(func=self._handle_player_input, args=(dt,), priority=TaskPriority.CRITICAL, name="player_input")
			self.task_queue.add(func=self._update_players_cooldown, args=(dt,), priority=TaskPriority.CRITICAL, name="players_cooldown")
			self.task_queue.add(func=self._update_npc_perception_and_ai, args=(dt,), priority=TaskPriority.HIGH, name="npc_perception_ai")
			self.task_queue.add(func=self._update_all_projectiles, args=(dt,), priority=TaskPriority.MEDIUM, name="update_projectiles")
			self.task_queue.add(func=self._check_all_collisions, priority=TaskPriority.CRITICAL, name="collision_check")
			self.task_queue.add(func=self._update_game_state, priority=TaskPriority.CRITICAL, name="game_state_check")
			self.task_queue.add(func=self._update_rbc_monitor_periodic, priority=TaskPriority.LOW, name="rbc_monitor_update")

			self.task_queue.process_frame()
		elif self.state == "gameover":
			if not self.match_conclusion_sent:
				self._update_rbc_monitor(in_game=False)
				self.rbc_monitor.show_match_conclusion({"lang": self.language, "conclusion": self.match_result_text or self._build_match_result_text()})
				self.rbc_monitor.push_decision(f"MATCH_END: {self.match_result_text or self._build_match_result_text()}")
				self.match_conclusion_sent = True
		else:
			self._monitor_update_timer += dt
			if self._monitor_update_timer >= 0.5:
				self._monitor_update_timer = 0.0
				self._update_rbc_monitor(in_game=False)

	def _update_rbc_monitor(self, in_game: bool) -> None:
		if not self.rbc_monitor.is_enabled():
			return
		self.rbc_monitor.update_live({"lang": self.language, "in_game": in_game, "stats": self.npc_brain.get_statistics()})

	def _build_match_result_text(self) -> str:
		if self.player.health > self.npc.health:
			return STRINGS[self.language]["you_win"]
		if self.npc.health > self.player.health:
			return STRINGS[self.language]["you_lose"]
		return STRINGS[self.language]["draw"]

	def _describe_rbc_decision(self, action_name: str, mode: str, can_see: bool, distance: float, angle_diff: float) -> str:
		if self.language == "EN":
			base_map = {"fire": "Firing because target is visible and aligned", "align_and_fire": "Adjusting aim before firing", "pursue": "Pursuing to keep pressure on the player", "search": "Scanning area to reacquire target", "wander": "Repositioning to explore new angle", "random_rotate": "Rotating to open vision cone", "idle": "Holding position briefly"}
			visibility = "target visible" if can_see else "target lost"
			reason = base_map.get(action_name, "Choosing next tactical action")
			return f"{reason}. Context: {visibility}, dist={int(distance)}px, angle={angle_diff:.1f}deg, mode={mode}."

		base_map = {"fire": "Atirando porque o alvo esta visivel e alinhado", "align_and_fire": "Ajustando a mira antes de atirar", "pursue": "Perseguindo para manter pressao no jogador", "search": "Varrendo a area para reencontrar o alvo", "wander": "Reposicionando para explorar novo angulo", "random_rotate": "Rotacionando para abrir o campo de visao", "idle": "Mantendo posicao por um instante"}
		visibility = "alvo visivel" if can_see else "alvo perdido"
		reason = base_map.get(action_name, "Escolhendo a proxima acao tatica")
		return f"{reason}. Contexto: {visibility}, dist={int(distance)}px, angulo={angle_diff:.1f}graus, modo={mode}."

	def _describe_rbc_decision_compact(self, action_name: str, mode: str, can_see: bool) -> str:
		if self.language == "EN":
			map_en = {"fire": "Firing at target", "align_and_fire": "Aiming before firing", "pursue": "Pursuing player", "search": "Scanning area", "wander": "Repositioning", "random_rotate": "Rotating to find target", "idle": "Holding position"}
			state = "target visible" if can_see else "target lost"
			return f"{map_en.get(action_name, 'Choosing tactical action')} [{mode} | {state}]"

		map_pt = {"fire": "Atirando no alvo", "align_and_fire": "Alinhando mira para atirar", "pursue": "Perseguindo jogador", "search": "Varrendo a area", "wander": "Reposicionando", "random_rotate": "Rotacionando para encontrar alvo", "idle": "Mantendo posicao"}
		state = "alvo visivel" if can_see else "alvo perdido"
		return f"{map_pt.get(action_name, 'Escolhendo acao tatica')} [{mode} | {state}]"

	def _collide_proj_tank(self, p, tank):
		dx = p.x - tank.x
		dy = p.y - tank.y
		dist_sq = dx * dx + dy * dy
		hit_r = 28
		return dist_sq <= (hit_r + p.radius) ** 2

	def _update_npc_ai(self, dt):
		frames_since_seen = 0
		if not self.npc_perception.last_seen_player_pos:
			frames_since_seen = self.action_frame_counter

		difficulty = self.options.get("difficulty", "Normal")
		action = self.npc_brain.decide_action(
			npc_x=self.npc.x,
			npc_y=self.npc.y,
			npc_angle=self.npc.angle,
			npc_health=self.npc.health,
			player_x=self.player.x,
			player_y=self.player.y,
			player_health=self.player.health,
			player_visible=self.npc_perception.last_seen_player_pos is not None,
			frames_since_last_seen=frames_since_seen,
			difficulty=difficulty,
			nearest_projectile_distance=self.npc_perception.nearest_projectile_distance,
			nearest_projectile_angle=self.npc_perception.nearest_projectile_angle,
			projectiles_nearby_count=self.npc_perception.projectiles_nearby_count,
			projectile_threat_active=self.npc_perception.projectile_threat_active,
			projectile_threat_distance=self.npc_perception.projectile_threat_distance,
		)

		can_see = self.npc_perception.last_seen_player_pos is not None
		dist = math.sqrt((self.player.x - self.npc.x)**2 + (self.player.y - self.npc.y)**2)
		angle_to_player = math.degrees(math.atan2(self.player.y - self.npc.y, self.player.x - self.npc.x))
		angle_diff = abs(angle_to_player - self.npc.angle)
		if angle_diff > 180:
			angle_diff = 360 - angle_diff

		self.npc_face.update_expression(action=action.action, can_see=can_see, health=self.npc.health, angle_diff=angle_diff)

		if self.debug_mode and self.frame_counter % 30 == 0:
			can_see = self.npc_perception.last_seen_player_pos is not None
			angle_to_player = math.degrees(math.atan2(self.player.y - self.npc.y, self.player.x - self.npc.x))
			angle_diff = abs(angle_to_player - self.npc.angle)
			if angle_diff > 180:
				angle_diff = 360 - angle_diff
			print(f"[GAME] Dist: {dist:.0f}px | Angle diff: {angle_diff:.1f}° | Perception sees: {can_see}")
			print(f"[NPC] Action chosen: {action.action} | last_seen_player_pos: {self.npc_perception.last_seen_player_pos}")

		self._execute_npc_action(action, dt)

		if self.npc_perception.last_seen_player_pos:
			self.action_frame_counter = 0
		else:
			self.action_frame_counter += 1
		self._decision_counter += 1
		if self.rbc_monitor.is_enabled():
			stats = self.npc_brain.get_statistics()
			mode = stats.get("mode", "-")
			readable_reason = self._describe_rbc_decision(action_name=action.action, mode=mode, can_see=can_see, distance=dist, angle_diff=angle_diff)
			params_text = action.params if action.params else {}
			compact_text = self._describe_rbc_decision_compact(action_name=action.action, mode=mode, can_see=can_see)
			line = f"#{self._decision_counter:04d} {readable_reason} [action={action.action} params={params_text}]"
			self.rbc_monitor.push_decision({"group_key": f"{mode}:{action.action}", "compact_text": compact_text, "full_text": line})

	def _execute_npc_action(self, action: Solution, dt: float) -> None:
		action_type = action.action
		if isinstance(action.params, str):
			try:
				params = json.loads(action.params)
			except (json.JSONDecodeError, TypeError):
				params = {}
		else:
			params = action.params if action.params else {}

		if self.npc_perception.last_seen_player_pos:
			pdx = self.player.x - self.npc.x
			pdy = self.player.y - self.npc.y
			p_dist = math.hypot(pdx, pdy)
			p_angle = math.degrees(math.atan2(pdy, pdx))
			p_ang_diff = abs(p_angle - self.npc.angle)
			if p_ang_diff > 180:
				p_ang_diff = 360 - p_ang_diff
			mode = self.npc_brain.rbc_engine.mode

			subcone_angle = 12
			subcone_range = min(self.npc_perception.vision_range, 900)

			if should_auto_fire_in_cold_start(mode, p_dist, p_ang_diff, subcone_range, subcone_angle):
				if self.npc.can_fire():
					self.npc.fire()
					fire_angle = self.npc.angle
					proj = Projectile(self.npc.x + math.cos(math.radians(fire_angle)) * 40, self.npc.y + math.sin(math.radians(fire_angle)) * 40, fire_angle, self.npc, speed=self.options.get("projectile_speed", 420))
					self.projectiles.append(proj)
					self.npc_perception.log_event("FIRE", f"subcone {int(fire_angle)}°")
					if self.debug_mode:
						print(f"[SUBCONE] Fired at NPC angle: dist={p_dist:.0f}px ang_diff={p_ang_diff:.1f}° angle={fire_angle:.0f}°")
					return

		if self.debug_mode and self.frame_counter % 30 == 0:
			print(f"[EXECUTE] Action: {action_type} | Params: {params}")

		if action_type == "fire":
			self.last_ai_shot += dt
			if self.last_ai_shot >= self.ai_shot_interval:
				self.last_ai_shot = 0
				if self.npc.can_fire():
					self.npc.fire()
					fire_angle = self.npc.angle
					proj = Projectile(self.npc.x + math.cos(math.radians(fire_angle)) * 40, self.npc.y + math.sin(math.radians(fire_angle)) * 40, fire_angle, self.npc, speed=self.options.get("projectile_speed", 420))
					self.projectiles.append(proj)
					self.npc_perception.log_event("FIRE", f"ângulo {int(fire_angle)}°")
					if self.debug_mode:
						print(f"  ✓ FIRED at NPC visual angle {fire_angle:.0f}°")

		elif action_type == "align_and_fire":
			self.last_ai_shot += dt
			if self.last_ai_shot >= max(0.2, self.ai_shot_interval * 0.6):
				self.last_ai_shot = 0
				if self.npc.can_fire():
					self.npc.fire()
					proj = Projectile(self.npc.x + math.cos(math.radians(self.npc.angle)) * 40, self.npc.y + math.sin(math.radians(self.npc.angle)) * 40, self.npc.angle, self.npc, speed=self.options.get("projectile_speed", 420))
					self.projectiles.append(proj)
					self.npc_perception.log_event("FIRE", f"ângulo {int(self.npc.angle)}°")
					if self.debug_mode:
						print(f"  ✓ FIRED (no-rotate mode) at angle {self.npc.angle:.0f}°")

		elif action_type == "pursue":
			if self.npc_perception.last_seen_player_pos:
				target_y = self.npc_perception.last_seen_player_pos[1]
				speed_multiplier = params.get("speed", 1.0)
				if speed_multiplier < 0.6:
					speed_multiplier = 0.6
				if speed_multiplier > 1.0:
					speed_multiplier = 1.0

				if abs(target_y - self.npc.y) > 10:
					direction = 1 if target_y > self.npc.y else -1
					self.npc.move_y(direction * speed_multiplier, dt)

		elif action_type == "search":
			direction = params.get("direction", 1)
			self.npc.move_y(direction * 0.45, dt)
			self.npc_perception.log_event("SEARCH", "Varredura vertical...")

		elif action_type == "wander":
			direction = params.get("direction", 1)
			speed = params.get("speed", 0.5)
			if speed > 1.0:
				speed = 1.0
			self.npc.move_y(direction * speed, dt)

		elif action_type == "random_rotate":
			direction = params.get("direction", 1)
			self.npc.move_y(direction * 0.55, dt)

		elif action_type == "idle":
			pass

		elif action_type == "evade_projectile":
			if not getattr(self.npc_perception, 'projectile_threat_active', False):
				return
			direction = params.get("direction", 1)
			speed = params.get("speed", 1.1)
			if speed > 0.95:
				speed = 0.95
			if hasattr(self.npc_perception, 'nearest_projectile_angle'):
				ang = self.npc_perception.nearest_projectile_angle
				if ang > 10:
					direction = -1
				elif ang < -10:
					direction = 1

			self.npc.move_y(direction * max(0.9, speed), dt)
			self.npc_perception.log_event("EVADE", f"dir={direction} sp={speed}")

	def _draw_name_input(self):
		self.screen.fill((20, 26, 36))
		pygame.draw.circle(self.screen, (35, 70, 70), (140, 90), 120)
		pygame.draw.circle(self.screen, (60, 50, 85), (SCREEN_WIDTH - 100, 120), 150)

		panel = pygame.Rect(SCREEN_WIDTH // 2 - 230, 150, 460, 300)
		pygame.draw.rect(self.screen, (25, 30, 42), panel, border_radius=10)
		pygame.draw.rect(self.screen, (70, 95, 120), panel, 2, border_radius=10)

		title = self.section_title_font.render(STRINGS[self.language]["login_title"], True, (235, 240, 245))
		self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 205)))

		subtitle = self.small_font.render(STRINGS[self.language]["login_subtitle"], True, (180, 195, 210))
		self.screen.blit(subtitle, subtitle.get_rect(center=(SCREEN_WIDTH // 2, 235)))

		name_label = self.font.render(STRINGS[self.language]["player_name_label"], True, (215, 220, 230))
		self.screen.blit(name_label, (panel.x + 34, panel.y + 108))

		box = pygame.Rect(panel.x + 30, panel.y + 140, panel.width - 60, 56)
		pygame.draw.rect(self.screen, (40, 46, 62), box, border_radius=8)
		pygame.draw.rect(self.screen, (110, 135, 165), box, 2, border_radius=8)

		display_name = self.player_name
		color = (245, 245, 245)
		if not display_name:
			display_name = STRINGS[self.language]["player_name_placeholder"]
			color = (130, 145, 165)

		name_surface = self.font.render(display_name, True, color)
		self.screen.blit(name_surface, (box.x + 12, box.y + 14))

		if pygame.time.get_ticks() % 1000 < 500 and len(self.player_name) < 12:
			caret_x = box.x + 14 + name_surface.get_width() if self.player_name else box.x + 14
			pygame.draw.line(self.screen, (220, 225, 235), (caret_x, box.y + 12), (caret_x, box.y + 42), 2)

		hint = self.small_font.render(STRINGS[self.language]["login_confirm"], True, (200, 210, 220))
		self.screen.blit(hint, hint.get_rect(center=(SCREEN_WIDTH // 2, panel.y + 236)))

		if self.player_name.strip():
			back_hint = self.small_font.render(STRINGS[self.language]["login_back"], True, (150, 160, 175))
			self.screen.blit(back_hint, back_hint.get_rect(center=(SCREEN_WIDTH // 2, panel.y + 262)))

	def _approach_angle(self, src, trg, step):
		a = (trg - src + 180) % 360 - 180
		if a > 0:
			return (src + min(a, step)) % 360
		return (src + max(a, -step)) % 360

	def draw(self):
		if self.state == "menu":
			self._draw_menu()
		elif self.state == "name_input":
			self._draw_name_input()
		elif self.state == "options":
			self._draw_options()
		elif self.state == "playing":
			self._draw_game()
		elif self.state == "gameover":
			self._draw_gameover()

		pygame.display.flip()

	def _draw_menu(self):
		self.screen.fill((30, 40, 50))
		title = self.menu_title_font.render(STRINGS[self.language]["title"], True, (230, 230, 230))
		self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 140)))

		logged_as = f"{STRINGS[self.language]['logged_as']}: {self.player_name if self.player_name else STRINGS[self.language]['player_name_placeholder']}"
		logged_txt = self.small_font.render(logged_as, True, (180, 195, 210))
		self.screen.blit(logged_txt, logged_txt.get_rect(center=(SCREEN_WIDTH // 2, 185)))

		mouse_pos = pygame.mouse.get_pos()
		for b in self.buttons:
			b.draw(self.screen, mouse_pos)

		hint = self.font.render(STRINGS[self.language]["hint_controls"], True, (200, 200, 200))
		self.screen.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2, SCREEN_HEIGHT - 80))

	def _draw_options(self):
		self.screen.fill((28, 34, 42))
		title = pygame.font.Font(None, 48).render(STRINGS[self.language]["options"], True, (240, 240, 240))
		self.screen.blit(title, (40, 36))

		y = 110
		lang_section_bg = pygame.Rect(40, y - 10, SCREEN_WIDTH - 80, 90)
		pygame.draw.rect(self.screen, (35, 40, 50), lang_section_bg, border_radius=6)
		pygame.draw.rect(self.screen, (80, 100, 120), lang_section_bg, 1, border_radius=6)

		lang_label = self.font.render(STRINGS[self.language]["language"] + ":", True, (210, 210, 210))
		self.screen.blit(lang_label, (60, y))

		btn_w = 140
		btn_h = 40
		btn_gap = 24
		lang_buttons_total = 2 * btn_w + btn_gap
		lang_start_x = max(60, (SCREEN_WIDTH - lang_buttons_total) // 2)

		lang_pt_rect = pygame.Rect(lang_start_x, y + 35, btn_w, btn_h)
		lang_en_rect = pygame.Rect(lang_start_x + btn_w + btn_gap, y + 35, btn_w, btn_h)

		pt_color = (100, 200, 100) if self.language == "PT" else (150, 150, 150)
		pygame.draw.rect(self.screen, pt_color, lang_pt_rect, border_radius=6)
		pt_txt = self.font.render("Português", True, (20, 20, 20))
		self.screen.blit(pt_txt, pt_txt.get_rect(center=lang_pt_rect.center))

		en_color = (100, 200, 100) if self.language == "EN" else (150, 150, 150)
		pygame.draw.rect(self.screen, en_color, lang_en_rect, border_radius=6)
		en_txt = self.font.render("English", True, (20, 20, 20))
		self.screen.blit(en_txt, en_txt.get_rect(center=lang_en_rect.center))

		if pygame.mouse.get_pressed()[0]:
			mouse_pos = pygame.mouse.get_pos()
			if lang_pt_rect.collidepoint(mouse_pos):
				self._set_language("PT")
			elif lang_en_rect.collidepoint(mouse_pos):
				self._set_language("EN")

		y = 240
		account_bg = pygame.Rect(40, y - 10, SCREEN_WIDTH - 80, 90)
		pygame.draw.rect(self.screen, (35, 40, 50), account_bg, border_radius=6)
		pygame.draw.rect(self.screen, (80, 100, 120), account_bg, 1, border_radius=6)

		current_user = self.player_name if self.player_name else STRINGS[self.language]["player_name_placeholder"]
		user_label = self.font.render(f"{STRINGS[self.language]['logged_as']}: {current_user}", True, (210, 210, 210))
		self.screen.blit(user_label, (60, y + 8))

		login_btn_rect = pygame.Rect(SCREEN_WIDTH - 240, y + 32, 160, 40)
		login_hover = login_btn_rect.collidepoint(pygame.mouse.get_pos())
		login_color = (120, 180, 120) if login_hover else (100, 160, 100)
		pygame.draw.rect(self.screen, login_color, login_btn_rect, border_radius=6)
		login_txt = self.small_font.render(STRINGS[self.language]["change_user"], True, (20, 20, 20))
		self.screen.blit(login_txt, login_txt.get_rect(center=login_btn_rect.center))

		if pygame.mouse.get_pressed()[0] and login_btn_rect.collidepoint(pygame.mouse.get_pos()):
			self.state = "name_input"

		y = 350
		diff_title = self.font.render(STRINGS[self.language]["difficulty_in_use"], True, (210, 210, 210))
		self.screen.blit(diff_title, (60, y))
		diff_value = self.small_font.render(STRINGS[self.language]["difficulty_locked"], True, (160, 180, 205))
		self.screen.blit(diff_value, (60, y + 28))

		y = 420
		speed_label = self.font.render(STRINGS[self.language]["projectile_speed"], True, (210, 210, 210))
		self.screen.blit(speed_label, (60, y))

		speed = self.options.get("projectile_speed", 420)
		speed = max(260, min(700, speed))
		keys = pygame.key.get_pressed()
		if keys[pygame.K_LEFT]:
			speed = max(260, speed - 4)
		if keys[pygame.K_RIGHT]:
			speed = min(700, speed + 4)
		self.options["projectile_speed"] = speed

		val = self.font.render(str(int(speed)), True, (220, 220, 220))
		val_x = (SCREEN_WIDTH // 2) - (val.get_width() // 2)
		self.screen.blit(val, (val_x, y + 28))

		info = self.font.render(STRINGS[self.language]["esc_menu"], True, (150, 150, 150))
		self.screen.blit(info, (60, SCREEN_HEIGHT - 60))

		back_btn_rect = pygame.Rect(SCREEN_WIDTH - 260, SCREEN_HEIGHT - 72, 210, 44)
		back_hover = back_btn_rect.collidepoint(pygame.mouse.get_pos())
		back_color = (170, 170, 170) if back_hover else (145, 145, 145)
		pygame.draw.rect(self.screen, back_color, back_btn_rect, border_radius=6)
		back_txt = self.small_font.render(STRINGS[self.language]["back_menu"], True, (20, 20, 20))
		self.screen.blit(back_txt, back_txt.get_rect(center=back_btn_rect.center))

		if pygame.mouse.get_pressed()[0] and back_btn_rect.collidepoint(pygame.mouse.get_pos()):
			self.state = "menu"

	def _draw_game(self):
		self.screen.fill((50, 120, 50))
		pygame.draw.rect(self.screen, (30, 30, 30), (ARENA_LEFT, ARENA_TOP, ARENA_RIGHT - ARENA_LEFT, ARENA_BOTTOM - ARENA_TOP), 4)

		self.player.draw(self.screen)
		self.npc.draw(self.screen)
		for p in self.projectiles:
			p.draw(self.screen)

		if self.debug_mode:
			self._draw_debug()

		self._draw_health_bar(self.player, 20, 20)
		self._draw_health_bar(self.npc, SCREEN_WIDTH - 220, 20)

		status_x = 240
		status_y = 15
		status_w = 230
		status_h = 75

		status_bg = pygame.Rect(status_x, status_y, status_w, status_h)
		pygame.draw.rect(self.screen, (40, 45, 55), status_bg, border_radius=6)
		pygame.draw.rect(self.screen, (70, 90, 110), status_bg, 2, border_radius=6)

		diff_text = STRINGS[self.language]["difficulty"] + ": " + self.options.get("difficulty", "Normal")
		diff_label = self.small_font.render(diff_text, True, (230, 230, 230))
		self.screen.blit(diff_label, (status_x + 10, status_y + 12))

		speed_val = int(self.options.get("projectile_speed", 420))
		speed_text = STRINGS[self.language]["speed_label"] + " " + str(speed_val)
		speed_label = self.small_font.render(speed_text, True, (200, 200, 200))
		self.screen.blit(speed_label, (status_x + 10, status_y + 40))

		face_x = status_x + status_w + 80
		face_y = 15
		self.npc_face.draw(self.screen, face_x, face_y)

		self._draw_perception_log()

	def _draw_health_bar(self, tank, x, y):
		w = 200
		h = 18
		pygame.draw.rect(self.screen, (40, 40, 40), (x, y, w, h), border_radius=6)
		health_ratio = max(0, min(1, tank.health / 100.0))
		inner_w = int(w * health_ratio)
		col = (50, 200, 80) if health_ratio > 0.35 else (220, 70, 60)
		pygame.draw.rect(self.screen, col, (x + 2, y + 2, inner_w - 4 if inner_w > 4 else 0, h - 4), border_radius=6)
		name = self.font.render(tank.name, True, (240, 240, 240))
		self.screen.blit(name, (x, y + h + 6))

	def _draw_debug(self):
		pygame.draw.rect(self.screen, (255, 100, 100), (self.player.x - self.player.width // 2, self.player.y - self.player.height // 2, self.player.width, self.player.height), 2)
		pygame.draw.rect(self.screen, (255, 150, 150), (self.npc.x - self.npc.width // 2, self.npc.y - self.npc.height // 2, self.npc.width, self.npc.height), 2)

		vision_range = self.npc_perception.vision_range
		vision_angle = self.npc_perception.vision_angle

		end_x = self.npc.x + vision_range * math.cos(math.radians(self.npc.angle))
		end_y = self.npc.y + vision_range * math.sin(math.radians(self.npc.angle))
		pygame.draw.line(self.screen, (100, 255, 100), (self.npc.x, self.npc.y), (end_x, end_y), 1)

		points = []
		for angle in range(int(self.npc.angle - vision_angle // 2), int(self.npc.angle + vision_angle // 2) + 1, 5):
			x = self.npc.x + vision_range * math.cos(math.radians(angle))
			y = self.npc.y + vision_range * math.sin(math.radians(angle))
			points.append((int(x), int(y)))

		if len(points) > 1:
			try:
				pygame.draw.lines(self.screen, (100, 255, 100), False, points, 1)
			except TypeError:
				pass

		angle_left = self.npc.angle - vision_angle // 2
		angle_right = self.npc.angle + vision_angle // 2

		x_left = self.npc.x + vision_range * math.cos(math.radians(angle_left))
		y_left = self.npc.y + vision_range * math.sin(math.radians(angle_left))
		pygame.draw.line(self.screen, (100, 255, 100), (self.npc.x, self.npc.y), (x_left, y_left), 1)

		x_right = self.npc.x + vision_range * math.cos(math.radians(angle_right))
		y_right = self.npc.y + vision_range * math.sin(math.radians(angle_right))
		pygame.draw.line(self.screen, (100, 255, 100), (self.npc.x, self.npc.y), (x_right, y_right), 1)

		subcone_angle = 12
		subcone_range = min(vision_range, 900)
		left_sc = self.npc.angle - subcone_angle
		right_sc = self.npc.angle + subcone_angle
		x_left_sc = self.npc.x + subcone_range * math.cos(math.radians(left_sc))
		y_left_sc = self.npc.y + subcone_range * math.sin(math.radians(left_sc))
		x_right_sc = self.npc.x + subcone_range * math.cos(math.radians(right_sc))
		y_right_sc = self.npc.y + subcone_range * math.sin(math.radians(right_sc))
		pygame.draw.line(self.screen, (255, 210, 80), (self.npc.x, self.npc.y), (x_left_sc, y_left_sc), 2)
		pygame.draw.line(self.screen, (255, 210, 80), (self.npc.x, self.npc.y), (x_right_sc, y_right_sc), 2)

		sc_points = []
		step = 2
		for angle in range(int(left_sc), int(right_sc) + 1, step):
			x = self.npc.x + subcone_range * math.cos(math.radians(angle))
			y = self.npc.y + subcone_range * math.sin(math.radians(angle))
			sc_points.append((int(x), int(y)))
		if len(sc_points) > 1:
			pygame.draw.lines(self.screen, (255, 210, 80), False, sc_points, 2)

		if self.npc_perception.last_seen_player_pos:
			pygame.draw.line(self.screen, (0, 255, 0), (int(self.npc.x), int(self.npc.y)), (int(self.npc_perception.last_seen_player_pos[0]), int(self.npc_perception.last_seen_player_pos[1])), 2)
			pygame.draw.circle(self.screen, (0, 255, 0), (int(self.npc_perception.last_seen_player_pos[0]), int(self.npc_perception.last_seen_player_pos[1])), 4, 1)

		pygame.draw.line(self.screen, (200, 100, 200), (int(self.npc.x), int(self.npc.y)), (int(self.player.x), int(self.player.y)), 1)

		dist = math.sqrt((self.player.x - self.npc.x)**2 + (self.player.y - self.npc.y)**2)
		angle_to_player = math.degrees(math.atan2(self.player.y - self.npc.y, self.player.x - self.npc.x))
		angle_diff = abs(angle_to_player - self.npc.angle)
		if angle_diff > 180:
			angle_diff = 360 - angle_diff

		rbc_stats = self.npc_brain.get_statistics()

		debug_info = [
			f"DEBUG MODE (Press D to toggle, R to reset DB)",
			f"Distance: {dist:.0f}px | NPC Angle: {self.npc.angle:.1f}°",
			f"Player Angle: {angle_to_player:.1f}° | Diff: {angle_diff:.1f}°",
			f"Vision: Range={vision_range}px, Cone={vision_angle}°",
			f"Can See: {self.npc_perception.last_seen_player_pos is not None} (need dist < {vision_range} AND angle diff < {vision_angle/2:.0f}°)",
			f"InSubcone: {dist <= subcone_range and angle_diff <= subcone_angle} (need dist < {subcone_range} AND angle diff < {subcone_angle}°)",
			f"RBC: Casos={rbc_stats.get('total_cases', 0)} | Epsilon={rbc_stats.get('epsilon', 0):.3f} | Avg Reward={rbc_stats.get('avg_reward', 0):.1f}",
		]

		y_offset = ARENA_TOP + 10
		for line in debug_info:
			text = self.small_font.render(line, True, (255, 255, 0))
			self.screen.blit(text, (10, y_offset))
			y_offset += 20

	def _draw_npc_perception_box(self):
		box_x = 20
		box_y = SCREEN_HEIGHT - 80
		box_w = 350
		box_h = 60

		pygame.draw.rect(self.screen, (30, 30, 40), (box_x, box_y, box_w, box_h), border_radius=6)
		pygame.draw.rect(self.screen, (100, 120, 140), (box_x, box_y, box_w, box_h), 2, border_radius=6)

		title = self.font.render(STRINGS[self.language]["npc_perception"], True, (200, 200, 200))
		self.screen.blit(title, (box_x + 10, box_y + 5))

		if self.npc_perception.last_seen_player_pos:
			perception_text = f"{STRINGS[self.language]['seeing']} ({int(self.npc_perception.last_seen_player_pos[0])}, {int(self.npc_perception.last_seen_player_pos[1])})"
			text_color = (100, 200, 100)
		else:
			perception_text = STRINGS[self.language]["lost"]
			text_color = (150, 150, 150)

		perception_display = self.font.render(perception_text, True, text_color)
		self.screen.blit(perception_display, (box_x + 10, box_y + 30))

		self._draw_perception_log()

	def _draw_perception_log(self):
		log_margin = 10
		log_x = log_margin
		log_h = LOG_HEIGHT
		log_y = SCREEN_HEIGHT - log_h - log_margin
		log_w = SCREEN_WIDTH - log_margin * 2

		pygame.draw.rect(self.screen, (15, 15, 25), (log_x, log_y, log_w, log_h), border_radius=6)
		pygame.draw.rect(self.screen, (100, 150, 100), (log_x, log_y, log_w, log_h), 2, border_radius=6)

		log_title = self.small_font.render(STRINGS[self.language].get("npc_log_title", "NPC LOG"), True, (100, 200, 100))
		self.screen.blit(log_title, (log_x + 10, log_y + 6))

		all_entries = self.npc_perception.perception_log if self.npc_perception.perception_log else [STRINGS[self.language].get("waiting_events", "Aguardando eventos...")]

		def truncate_to_width(text, font, max_w):
			if font.size(text)[0] <= max_w:
				return text
			ell = "..."
			lo = 0
			hi = len(text)
			while lo < hi:
				mid = (lo + hi) // 2
				candidate = text[:mid].rstrip() + ell
				if font.size(candidate)[0] <= max_w:
					lo = mid + 1
				else:
					hi = mid
			return text[:max(0, lo-1)].rstrip() + ell

		line_h = self.small_font.get_height() + 4
		available_h = log_h - 10 - self.small_font.get_height()
		max_lines = max(1, available_h // line_h)
		log_entries = all_entries[-max_lines:]
		max_text_w = log_w - 20

		for i, entry in enumerate(log_entries):
			log_line = f">> {entry}"
			truncated = truncate_to_width(log_line, self.small_font, max_text_w)
			log_text = self.small_font.render(truncated, True, (150, 200, 150))
			self.screen.blit(log_text, (log_x + 10, log_y + 8 + self.small_font.get_height() + i * line_h))

	def _draw_gameover(self):
		self.screen.fill((20, 26, 36))
		pygame.draw.circle(self.screen, (35, 70, 70), (140, 90), 120)
		pygame.draw.circle(self.screen, (60, 50, 85), (SCREEN_WIDTH - 100, 120), 150)

		panel = pygame.Rect(SCREEN_WIDTH // 2 - 250, 140, 500, 300)
		pygame.draw.rect(self.screen, (25, 30, 42), panel, border_radius=12)
		pygame.draw.rect(self.screen, (70, 95, 120), panel, 2, border_radius=12)

		title = self.section_title_font.render(STRINGS[self.language]["game_over"], True, (235, 240, 245))
		self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 198)))

		result_text = self.match_result_text or self._build_match_result_text()
		if self.player.health > self.npc.health:
			result_color = (120, 220, 140)
		elif self.npc.health > self.player.health:
			result_color = (235, 120, 120)
		else:
			result_color = (220, 220, 220)

		result_surface = self.menu_title_font.render(result_text, True, result_color)
		self.screen.blit(result_surface, result_surface.get_rect(center=(SCREEN_WIDTH // 2, 286)))

		hint = self.small_font.render(STRINGS[self.language]["press_enter"], True, (180, 195, 210))
		self.screen.blit(hint, hint.get_rect(center=(SCREEN_WIDTH // 2, 398)))

		keys = pygame.key.get_pressed()
		if keys[pygame.K_RETURN]:
			self.state = "menu"

	def reset_game_and_database(self):
		print("[DEBUG] Resetando banco de dados RBC...")
		self.npc_brain.close()
		del self.npc_brain

		import gc
		import time
		gc.collect()
		time.sleep(0.15)

		try:
			initialize_database(force_reset=True)
		except PermissionError:
			print("[DEBUG] Arquivo ainda em uso, tentando novamente...")
			time.sleep(0.3)
			gc.collect()
			try:
				initialize_database(force_reset=True)
			except PermissionError as e:
				print(f"[DEBUG] ERRO: Não foi possível deletar o banco: {e}")
				print("[DEBUG] Continuando com banco existente...")

		self.npc_brain = NPCBrain("npc_cases.db")
		self.start_new_game()
		print("[DEBUG] Banco de dados RBC resetado! Partida reiniciada.")


__all__ = ["Game"]
