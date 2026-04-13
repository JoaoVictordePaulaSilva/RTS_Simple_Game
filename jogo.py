import math
import random
import sys
import pygame
import uuid
import json

from npc_brain import NPCBrain
from rbc_engine import Solution
from db_init import initialize_database
from npc_face import NPCFace
from rbc_monitor import RBCMonitorWindow

# Simples demo RTS com dois tanques (jogador + NPC)
# Simple professional-but-small RTS-like demo with two tanks (player + NPC)
# Controles / Controls: Setas para cima/baixo e rotação, Espaço para disparar
# Arrow keys to move up/down and rotate, Space to fire

SCREEN_WIDTH = 900
SCREEN_HEIGHT = 600
FPS = 60

# Arena boundaries (limites da arena)
ARENA_TOP = 100
# Reserve a bottom area for the NPC log so the game plays above it
LOG_HEIGHT = 120
ARENA_BOTTOM = SCREEN_HEIGHT - LOG_HEIGHT - 20
ARENA_LEFT = 80
ARENA_RIGHT = 820

# Language strings / Dicionário de idiomas
STRINGS = {
    "PT": {
        "title": "joguinho",
        "start_game": "Iniciar Jogo",
        "options": "Opções",
        "language": "Idioma",
        "quit": "Sair",
        "difficulty": "Dificuldade",
        "easy": "Fácil",
        "normal": "Normal",
        "hard": "Difícil",
        "projectile_speed": "Velocidade do Projétil:",
        "speed_label": "Vel. Projétil:",
        "esc_menu": "Pressione ESC para voltar",
        "hint_controls": "Use setas para mover/rotacionar. Espaço para disparar.",
        "player": "Jogador",
        "enemy": "Inimigo",
        "npc_perception": "Percepção NPC:",
        "npc_log_title": "LOG NPC",
        "seeing": "VENDO: Jogador em",
        "lost": "STATUS: Alvo Perdido",
        "game_over": "Fim de Jogo",
        "player_wins": "Jogador Vence",
        "enemy_wins": "Inimigo Vence",
        "draw": "Empate",
        "you_win": "Voce venceu",
        "you_lose": "Voce perdeu",
        "press_enter": "Pressione ENTER para voltar",
        "waiting_events": "Aguardando eventos...",
        "login_title": "Entrar no jogo",
        "login_subtitle": "Defina seu nome de jogador para continuar",
        "player_name_label": "Nome do jogador",
        "player_name_placeholder": "joguinho",
        "login_confirm": "ENTER para confirmar",
        "login_back": "ESC para voltar",
        "change_user": "Trocar usuário",
        "logged_as": "Logado como",
        "difficulty_in_use": "Dificuldade em uso",
        "difficulty_locked": "Normal (fixa)",
        "back_menu": "Voltar ao menu",
    },
    "EN": {
        "title": "joguinho",
        "start_game": "Start Game",
        "options": "Options",
        "language": "Language",
        "quit": "Quit",
        "difficulty": "Difficulty",
        "easy": "Easy",
        "normal": "Normal",
        "hard": "Hard",
        "projectile_speed": "Projectile speed:",
        "speed_label": "Projectile speed:",
        "esc_menu": "Press ESC to return to menu",
        "hint_controls": "Use arrows to move/rotate in-game. Space to fire.",
        "player": "Player",
        "enemy": "Enemy",
        "npc_perception": "NPC Perception:",
        "npc_log_title": "NPC LOG",
        "seeing": "SEEING: Player at",
        "lost": "STATUS: Lost target",
        "game_over": "Game Over",
        "player_wins": "Player Wins",
        "enemy_wins": "Enemy Wins",
        "draw": "Draw",
        "you_win": "You won",
        "you_lose": "You lost",
        "press_enter": "Press Enter to return to menu",
        "waiting_events": "Waiting for events...",
        "login_title": "Sign in",
        "login_subtitle": "Set your player name to continue",
        "player_name_label": "Player name",
        "player_name_placeholder": "joguinho",
        "login_confirm": "Press ENTER to confirm",
        "login_back": "Press ESC to return",
        "change_user": "Change user",
        "logged_as": "Logged as",
        "difficulty_in_use": "Difficulty in use",
        "difficulty_locked": "Normal (locked)",
        "back_menu": "Back to menu",
    }
}


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
        # Atualiza cooldown de tiro / Update fire cooldown
        if self.fire_timer > 0:
            self.fire_timer = max(0, self.fire_timer - dt)

    def move_y(self, direction, dt):
        # Movimento apenas no eixo Y, preso na arena
        # Move only along Y axis, constrained to arena
        self.y += direction * self.speed * dt
        # Limita ao interior da arena / Constrain to arena boundaries
        self.y = max(ARENA_TOP, min(ARENA_BOTTOM, self.y))

    def rotate(self, direction, dt):
        # Rotação do tanque / Rotate tank
        # direction: -1 esquerda (ccw), +1 direita (cw)
        # direction: -1 left (ccw), +1 right (cw)
        self.angle += direction * self.rot_speed * dt
        self.angle %= 360

    def can_fire(self):
        # Verifica se pode disparar / Check if can fire
        return self.fire_timer <= 0

    def fire(self):
        # Inicia cooldown de tiro / Start fire cooldown
        self.fire_timer = self.fire_cooldown

    def hit(self, dmg):
        # Recebe dano / Take damage
        self.health -= dmg

    def draw(self, surf):
        # Desenha tanque como retângulo rotacionado com torres
        # Draw tank as rotated rectangle with turret
        tank_surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        body_rect = pygame.Rect(0, 0, self.width, self.height)
        pygame.draw.rect(tank_surf, self.color, body_rect, border_radius=6)
        # torres menores no centro / smaller turret rect centered
        turret = pygame.Rect(self.width - 10, self.height // 2 - 6, 24, 12)
        pygame.draw.rect(tank_surf, (40, 40, 40), turret, border_radius=3)

        rotated = pygame.transform.rotate(tank_surf, -self.angle)
        rect = rotated.get_rect(center=(self.x, self.y))
        surf.blit(rotated, rect.topleft)

        # Nome acima do tanque // Tank Name
        font = pygame.font.Font(None, 22)

        name_surface = font.render(self.name, True, (255, 255, 255))

        name_rect = name_surface.get_rect(
            center=(self.x, self.y - self.height // 2 - 12)
        )

        surf.blit(name_surface, name_rect)


class Projectile:
    def __init__(self, x, y, angle, owner, speed=420, damage=25, color=None):
        self.x = x
        self.y = y
        self.angle = angle
        self.owner = owner
        self.speed = speed
        self.damage = damage
        self.radius = 6
        self.is_alive = True
        self.color = color if color else owner.color

    def update(self, dt):
        # Atualiza posição / Update position
        rad = math.radians(self.angle)
        self.x += math.cos(rad) * self.speed * dt
        self.y += math.sin(rad) * self.speed * dt
        # Mata se sair dos limites / Kill if out of bounds
        # Keep projectiles inside the arena rectangle; destroy on wall hit
        if self.x < ARENA_LEFT or self.x > ARENA_RIGHT or self.y < ARENA_TOP or self.y > ARENA_BOTTOM:
            self.is_alive = False

    def draw(self, surf):
        # Desenha projetil como círculo vermelho / Draw projectile as red circle
        pygame.draw.circle(surf, self.color, (int(self.x), int(self.y)), self.radius)


class NPCPerception:
    """
    Classe para representar a percepção do NPC
    Class to represent NPC perception
    O NPC observa o inimigo e reage ao que vê
    NPC observes the enemy and reacts to what it sees
    """
    def __init__(self, tank):
        self.tank = tank
        self.vision_range = 800  # distância máxima de visão / max vision distance
        self.vision_angle = 75  # ângulo de visão (graus) / vision angle (degrees) - reduzido para 75°
        self.last_seen_player_pos = None
        self.last_seen_player_angle = None
        self.perception_memory = []
        self.perception_log = []  # Log de percepções / Perception log
        self.last_player_y = None  # Rastreia movimento do jogador / Track player movement
        self.last_player_angle = None
        self.player_moving_up_time = 0
        self.player_moving_down_time = 0
        
    def can_see(self, other_tank):
        # Verifica se pode ver o outro tanque
        # Check if can see the other tank
        dx = other_tank.x - self.tank.x
        dy = other_tank.y - self.tank.y
        dist = math.sqrt(dx * dx + dy * dy)
        
        if dist > self.vision_range:
            return False
        
        # Calcula ângulo até o alvo / Calculate angle to target
        angle_to_target = math.degrees(math.atan2(dy, dx))
        angle_diff = abs(angle_to_target - self.tank.angle)
        # Normaliza diferença de ângulo / Normalize angle difference
        if angle_diff > 180:
            angle_diff = 360 - angle_diff
            
        # Verifica se está no cone de visão / Check if in vision cone
        return angle_diff < self.vision_angle / 2
    
    def update(self, player_tank, dt):
        # Atualiza a percepção do NPC
        # Update NPC perception
        if self.can_see(player_tank):
            self.last_seen_player_pos = (player_tank.x, player_tank.y)
            self.last_seen_player_angle = player_tank.angle
            self.perception_memory.append(("see", player_tank.x, player_tank.y))
        else:
            self.perception_memory.append(("lost", None, None))
        
        # Rastreia movimento do jogador / Track player movement
        if self.last_player_y is not None:
            if player_tank.y < self.last_player_y:
                self.player_moving_up_time += dt
                self.player_moving_down_time = 0
                # Log de movimento para cima / Log upward movement
                if int(self.player_moving_up_time * 10) % 20 == 0:  # A cada ~2 segundos / every ~2 seconds
                    self.log_event("MOVE_UP", f"{self.player_moving_up_time:.1f}s")
            elif player_tank.y > self.last_player_y:
                self.player_moving_down_time += dt
                self.player_moving_up_time = 0
                # Log de movimento para baixo / Log downward movement
                if int(self.player_moving_down_time * 10) % 20 == 0:  # A cada ~2 segundos / every ~2 seconds
                    self.log_event("MOVE_DOWN", f"{self.player_moving_down_time:.1f}s")
            else:
                self.player_moving_up_time = 0
                self.player_moving_down_time = 0
        
        # Rastreia rotação do jogador / Track player rotation
        if self.last_player_angle is not None:
            if abs(player_tank.angle - self.last_player_angle) > 5:  # Mudança significativa / Significant change
                direction = "CCW" if (player_tank.angle - self.last_player_angle) % 360 < 180 else "CW"
                self.log_event("ROTATE", direction)
        
        self.last_player_y = player_tank.y
        self.last_player_angle = player_tank.angle
        
        # Mantém apenas últimos 30 frames de memória / Keep only last 30 frames of memory
        if len(self.perception_memory) > 30:
            self.perception_memory.pop(0)
    
    def log_event(self, event_type, details=""):
        # Registra evento de percepção / Log perception event
        timestamp = len(self.perception_log)
        self.perception_log.append(f"[{timestamp}] {event_type}: {details}")
        # Mantém últimas 15 linhas do log / Keep last 15 lines of log
        if len(self.perception_log) > 15:
            self.perception_log.pop(0)
    
    def get_perception_text(self):
        # Retorna texto descritivo do que o NPC vê
        # Return descriptive text of what NPC sees
        if self.last_seen_player_pos:
            return f"SEEING: Player at ({int(self.last_seen_player_pos[0])}, {int(self.last_seen_player_pos[1])})"
        else:
            return "STATUS: Lost target"


class Button:
    def __init__(self, rect, text, action=None, font=None):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.action = action
        self.font = font or pygame.font.Font(None, 32)

    def draw(self, surf, mouse_pos):
        # Desenha botão com cor hover / Draw button with hover color
        color = (200, 200, 200) if self.rect.collidepoint(mouse_pos) else (180, 180, 180)
        pygame.draw.rect(surf, color, self.rect, border_radius=6)
        txt = self.font.render(self.text, True, (20, 20, 20))
        txt_rect = txt.get_rect(center=self.rect.center)
        surf.blit(txt, txt_rect)

    def handle_event(self, ev):
        # Trata clique no botão / Handle button click
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            if self.rect.collidepoint(ev.pos) and self.action:
                self.action()


class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("RTS Tanks - Demo")
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 28)
        # Small font reused for logs and small UI to avoid recreating every frame
        self.small_font = pygame.font.Font(None, 20)
        self.font_small = pygame.font.Font(None, 18)
        self.font_tiny = pygame.font.Font(None, 14)
        # Title fonts reused
        self.menu_title_font = pygame.font.Font(None, 64)
        self.section_title_font = pygame.font.Font(None, 48)

        # Idioma / Language
        self.language = "EN"  # Default: English
        
        # states: menu, options, playing, gameover, name_input
        self.state = "name_input"
        self.player_name = ""
        self.name_input_active = False
        self.running = True

        self.setup_menu()
        self.reset_game()

        # options / opções
        self.options = {"difficulty": "Normal", "projectile_speed": 420}
        
        # RBC Engine / Motor RBC
        initialize_database(force_reset=False)  # Inicializa BD com seed cases
        self.npc_brain = NPCBrain("npc_cases.db")
        self.current_session_id = None
        self.action_frame_counter = 0  # Para tracking de ações
        
        # NPC Face / Carinha do NPC
        self.npc_face = NPCFace(width=60, height=60)
        
        # Debug mode / Modo debug
        self.debug_mode = False  # Toggle com 'D'
        self.frame_counter = 0  # Para logging periódico

        # Janela auxiliar para monitorar o RBC em tempo real
        self.rbc_monitor = RBCMonitorWindow()
        self.rbc_monitor.start()
        self._monitor_update_timer = 0.0
        self.match_result_text = ""
        self.match_conclusion_sent = False
        self._decision_counter = 0

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
        # Tanques no lado esquerdo e direito
        # Tanks at left and right, constrained to Y movement
        self.player = Tank(140, SCREEN_HEIGHT // 2, (40, 120, 200), is_player=True, name=self.player_name if self.player_name else STRINGS[self.language]["player"])
        self.npc = Tank(SCREEN_WIDTH - 140, SCREEN_HEIGHT // 2, (200, 100, 60), is_player=False, name=STRINGS[self.language]["enemy"])
        self.npc_perception = NPCPerception(self.npc)
        self.projectiles = []
        self.last_ai_shot = 0
        self.ai_shot_interval = 1.0  # seconds (will vary by difficulty / segundos - varia por dificuldade)

    def start_new_game(self):
        self.reset_game()
        # Dificuldade travada em Normal para simplificar UX.
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

        # Inicializa sessão RBC
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
                    elif ev.key == pygame.K_d:  # Toggle debug mode
                        self.debug_mode = not self.debug_mode
                        print(f"Debug mode: {'ON' if self.debug_mode else 'OFF'}")
                    elif ev.key == pygame.K_r and self.debug_mode:  # Reset game and database (debug only)
                        self.reset_game_and_database()
                    elif ev.key == pygame.K_SPACE:
                        # Dispara projétil / Fire projectile
                        if self.player.can_fire():
                            self.player.fire()
                            proj = Projectile(self.player.x + math.cos(math.radians(self.player.angle)) * 40,
                                               self.player.y + math.sin(math.radians(self.player.angle)) * 40,
                                               self.player.angle, self.player, speed=self.options.get("projectile_speed", 420))
                            self.projectiles.append(proj)
                            # Registra disparo do jogador / Log player shot
                            self.npc_perception.log_event("SHOT", f"ângulo {int(self.player.angle)}°")
    
    def _set_language(self, lang):
        # Define idioma e atualiza textos / Set language and update texts
        self.language = lang
        self.setup_menu()  # Reconstrói botões com novo idioma / Rebuild buttons with new language
        self.reset_game()  # Reconstrói jogo com novo idioma / Rebuild game with new language

    def _commit_login(self, go_to_menu=True):
        # Usa placeholder como fallback se usuário confirmar vazio.
        name = self.player_name.strip()
        if not name:
            name = STRINGS[self.language].get("player_name_placeholder", "joguinho")
        self.player_name = name[:12]
        self.reset_game()
        if go_to_menu:
            self.state = "menu"

    def update(self, dt):
        if self.state == "playing":
            self.frame_counter += 1
            self._monitor_update_timer += dt
            
            keys = pygame.key.get_pressed()
            # Movimento do jogador: apenas eixo Y / Player movement: only Y axis
            if keys[pygame.K_UP]:
                self.player.move_y(-1, dt)
            if keys[pygame.K_DOWN]:
                self.player.move_y(1, dt)
            # Rotação / rotation
            if keys[pygame.K_LEFT]:
                self.player.rotate(-1, dt)
            if keys[pygame.K_RIGHT]:
                self.player.rotate(1, dt)

            # Atualização de cooldown / Player cooldown update
            self.player.update(dt)
            self.npc.update(dt)
            
            # Atualiza percepção do NPC / Update NPC perception
            self.npc_perception.update(self.player, dt)

            # ===== IA DO NPC - BÁSICA =====
            # NPC AI - BASIC (pode ser refinada depois / can be refined later)
            self._update_npc_ai(dt)

            # Atualiza projéteis / update projectiles
            for p in self.projectiles:
                p.update(dt)

            # Colisões / collisions
            for p in list(self.projectiles):
                if not p.is_alive:
                    self.projectiles.remove(p)
                    continue
                # Verifica colisão com tanques (ignora o dono) / check collision with tanks (skip owner)
                if p.owner is not self.player and self._collide_proj_tank(p, self.player):
                    self.player.hit(p.damage)
                    p.is_alive = False
                    # NPC acertou: registro de aprendizado
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
                    # NPC recebeu dano
                    self.npc_brain.report_outcome(
                        success=False,
                        damage_dealt=0,
                        damage_taken=p.damage,
                        outcome_type="damaged",
                        difficulty=self.options.get("difficulty", "Normal")
                    )

            # Remove projéteis mortos / remove dead projectiles
            self.projectiles = [p for p in self.projectiles if p.is_alive]

            # Verifica condições de fim de jogo / check end conditions
            if self.player.health <= 0 or self.npc.health <= 0:
                self.npc_brain.rbc_engine.end_episode()
                self.match_result_text = self._build_match_result_text()
                self.state = "gameover"

            # Atualiza monitor RBC em tempo real sem sobrecarregar a UI auxiliar
            if self._monitor_update_timer >= 0.2:
                self._monitor_update_timer = 0.0
                self._update_rbc_monitor(in_game=True)
        elif self.state == "gameover":
            if not self.match_conclusion_sent:
                self._update_rbc_monitor(in_game=False)
                self.rbc_monitor.show_match_conclusion({
                    "lang": self.language,
                    "conclusion": self.match_result_text or self._build_match_result_text(),
                })
                self.rbc_monitor.push_decision(
                    f"MATCH_END: {self.match_result_text or self._build_match_result_text()}"
                )
                self.match_conclusion_sent = True

        else:
            # Mantem janela auxiliar sincronizada fora da partida
            self._monitor_update_timer += dt
            if self._monitor_update_timer >= 0.5:
                self._monitor_update_timer = 0.0
                self._update_rbc_monitor(in_game=False)

    def _update_rbc_monitor(self, in_game: bool) -> None:
        if not self.rbc_monitor.is_enabled():
            return
        self.rbc_monitor.update_live({
            "lang": self.language,
            "in_game": in_game,
            "stats": self.npc_brain.get_statistics(),
        })

    def _build_match_result_text(self) -> str:
        if self.player.health > self.npc.health:
            return STRINGS[self.language]["you_win"]
        if self.npc.health > self.player.health:
            return STRINGS[self.language]["you_lose"]
        return STRINGS[self.language]["draw"]

    def _describe_rbc_decision(self, action_name: str, mode: str, can_see: bool, distance: float, angle_diff: float) -> str:
        """Gera descricao interpretavel da decisao atual do RBC."""
        if self.language == "EN":
            base_map = {
                "fire": "Firing because target is visible and aligned",
                "align_and_fire": "Adjusting aim before firing",
                "pursue": "Pursuing to keep pressure on the player",
                "search": "Scanning area to reacquire target",
                "wander": "Repositioning to explore new angle",
                "random_rotate": "Rotating to open vision cone",
                "idle": "Holding position briefly",
            }
            visibility = "target visible" if can_see else "target lost"
            reason = base_map.get(action_name, "Choosing next tactical action")
            return (
                f"{reason}. Context: {visibility}, dist={int(distance)}px, "
                f"angle={angle_diff:.1f}deg, mode={mode}."
            )

        base_map = {
            "fire": "Atirando porque o alvo esta visivel e alinhado",
            "align_and_fire": "Ajustando a mira antes de atirar",
            "pursue": "Perseguindo para manter pressao no jogador",
            "search": "Varrendo a area para reencontrar o alvo",
            "wander": "Reposicionando para explorar novo angulo",
            "random_rotate": "Rotacionando para abrir o campo de visao",
            "idle": "Mantendo posicao por um instante",
        }
        visibility = "alvo visivel" if can_see else "alvo perdido"
        reason = base_map.get(action_name, "Escolhendo a proxima acao tatica")
        return (
            f"{reason}. Contexto: {visibility}, dist={int(distance)}px, "
            f"angulo={angle_diff:.1f}graus, modo={mode}."
        )

    def _describe_rbc_decision_compact(self, action_name: str, mode: str, can_see: bool) -> str:
        """Descricao curta para visualizacao compacta no monitor RBC."""
        if self.language == "EN":
            map_en = {
                "fire": "Firing at target",
                "align_and_fire": "Aiming before firing",
                "pursue": "Pursuing player",
                "search": "Scanning area",
                "wander": "Repositioning",
                "random_rotate": "Rotating to find target",
                "idle": "Holding position",
            }
            state = "target visible" if can_see else "target lost"
            return f"{map_en.get(action_name, 'Choosing tactical action')} [{mode} | {state}]"

        map_pt = {
            "fire": "Atirando no alvo",
            "align_and_fire": "Alinhando mira para atirar",
            "pursue": "Perseguindo jogador",
            "search": "Varrendo a area",
            "wander": "Reposicionando",
            "random_rotate": "Rotacionando para encontrar alvo",
            "idle": "Mantendo posicao",
        }
        state = "alvo visivel" if can_see else "alvo perdido"
        return f"{map_pt.get(action_name, 'Escolhendo acao tatica')} [{mode} | {state}]"

    def _collide_proj_tank(self, p, tank):
        # Verifica colisão entre projétil e tanque / Check collision between projectile and tank
        dx = p.x - tank.x
        dy = p.y - tank.y
        dist_sq = dx * dx + dy * dy
        hit_r = 28
        return dist_sq <= (hit_r + p.radius) ** 2

    def _update_npc_ai(self, dt):
        """
        IA do NPC usando RBC (Case-Based Reasoning).
        NPC AI using RBC (Case-Based Reasoning).
        """
        # Calcula frames desde última visão do jogador
        frames_since_seen = 0
        if not self.npc_perception.last_seen_player_pos:
            frames_since_seen = self.action_frame_counter

        # Usa RBC Brain para decidir ação
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
            difficulty=difficulty
        )
        
        # Atualiza expressão da carinha do NPC / Update NPC face expression
        can_see = self.npc_perception.last_seen_player_pos is not None
        dist = math.sqrt((self.player.x - self.npc.x)**2 + (self.player.y - self.npc.y)**2)
        angle_to_player = math.degrees(math.atan2(self.player.y - self.npc.y, self.player.x - self.npc.x))
        angle_diff = abs(angle_to_player - self.npc.angle)
        if angle_diff > 180:
            angle_diff = 360 - angle_diff
        
        self.npc_face.update_expression(
            action=action.action,
            can_see=can_see,
            health=self.npc.health,
            angle_diff=angle_diff
        )

        # DEBUG: Mostra estado do NPC
        if self.debug_mode and self.frame_counter % 30 == 0:  # A cada 30 frames (~500ms)
            can_see = self.npc_perception.last_seen_player_pos is not None
            angle_to_player = math.degrees(math.atan2(self.player.y - self.npc.y, self.player.x - self.npc.x))
            angle_diff = abs(angle_to_player - self.npc.angle)
            if angle_diff > 180:
                angle_diff = 360 - angle_diff
            print(f"[GAME] Dist: {dist:.0f}px | Angle diff: {angle_diff:.1f}° | Perception sees: {can_see}")
            print(f"[NPC] Action chosen: {action.action} | last_seen_player_pos: {self.npc_perception.last_seen_player_pos}")

        # Executa ação decidida pelo RBC
        self._execute_npc_action(action, dt)
        
        # Limpa frame counter quando vê o jogador
        if self.npc_perception.last_seen_player_pos:
            self.action_frame_counter = 0
        else:
            self.action_frame_counter += 1
        self._decision_counter += 1
        if self.rbc_monitor.is_enabled():
            stats = self.npc_brain.get_statistics()
            mode = stats.get("mode", "-")
            readable_reason = self._describe_rbc_decision(
                action_name=action.action,
                mode=mode,
                can_see=can_see,
                distance=dist,
                angle_diff=angle_diff,
            )
            params_text = action.params if action.params else {}
            compact_text = self._describe_rbc_decision_compact(
                action_name=action.action,
                mode=mode,
                can_see=can_see,
            )
            line = (
                f"#{self._decision_counter:04d} {readable_reason} "
                f"[action={action.action} params={params_text}]"
            )
            self.rbc_monitor.push_decision({
                "group_key": f"{mode}:{action.action}",
                "compact_text": compact_text,
                "full_text": line,
            })

    def _execute_npc_action(self, action: Solution, dt: float) -> None:
        """
        Executa ação decidida pelo RBC.
        Execute RBC-decided action.
        
        Args:
            action: Solução/ação a executar
            dt: Delta time
        """
        action_type = action.action
        
        # Desserializa params de JSON string para dict / Deserialize params from JSON string to dict
        if isinstance(action.params, str):
            try:
                params = json.loads(action.params)
            except (json.JSONDecodeError, TypeError):
                params = {}
        else:
            params = action.params if action.params else {}

        # Quick sub-cone fire: if the player is inside a tighter firing cone, fire immediately
        # This helps ensure NPC shoots even when it's still rotating to align.
        if self.npc_perception.last_seen_player_pos:
            pdx = self.player.x - self.npc.x
            pdy = self.player.y - self.npc.y
            p_dist = math.hypot(pdx, pdy)
            p_angle = math.degrees(math.atan2(pdy, pdx))
            p_ang_diff = abs(p_angle - self.npc.angle)
            if p_ang_diff > 180:
                p_ang_diff = 360 - p_ang_diff

            # Sub-cone settings
            subcone_angle = 12  # degrees
            subcone_range = min(self.npc_perception.vision_range, 900)

            if p_dist <= subcone_range and p_ang_diff <= subcone_angle:
                # Fire immediately using NPC's current visual angle (must be aligned first)
                if self.npc.can_fire():
                    self.npc.fire()
                    # SEMPRE usa o ângulo visual atual do NPC
                    fire_angle = self.npc.angle
                    proj = Projectile(
                        self.npc.x + math.cos(math.radians(fire_angle)) * 40,
                        self.npc.y + math.sin(math.radians(fire_angle)) * 40,
                        fire_angle, self.npc,
                        speed=self.options.get("projectile_speed", 420)
                    )
                    self.projectiles.append(proj)
                    self.npc_perception.log_event("FIRE", f"subcone {int(fire_angle)}°")
                    if self.debug_mode:
                        print(f"[SUBCONE] Fired at NPC angle: dist={p_dist:.0f}px ang_diff={p_ang_diff:.1f}° angle={fire_angle:.0f}°")
                    # avoid double-firing in this frame by returning early
                    return

        # DEBUG: Log de ações executadas
        if self.debug_mode and self.frame_counter % 30 == 0:
            print(f"[EXECUTE] Action: {action_type} | Params: {params}")

        # Fire: dispara na direção atual (SEMPRE usa ângulo visual do NPC)
        if action_type == "fire":
            self.last_ai_shot += dt
            if self.last_ai_shot >= self.ai_shot_interval:
                self.last_ai_shot = 0
                if self.npc.can_fire():
                    self.npc.fire()
                    # SEMPRE usa o ângulo visual atual do NPC - sem ajustes!
                    fire_angle = self.npc.angle
                    proj = Projectile(
                        self.npc.x + math.cos(math.radians(fire_angle)) * 40,
                        self.npc.y + math.sin(math.radians(fire_angle)) * 40,
                        fire_angle, self.npc,
                        speed=self.options.get("projectile_speed", 420)
                    )
                    self.projectiles.append(proj)
                    self.npc_perception.log_event("FIRE", f"ângulo {int(fire_angle)}°")
                    if self.debug_mode:
                        print(f"  ✓ FIRED at NPC visual angle {fire_angle:.0f}°")

        # Align and fire: alinha antes de disparar
        elif action_type == "align_and_fire":
            # Calcula ângulo absoluto do jogador / Calculate absolute angle to player
            if self.npc_perception.last_seen_player_pos:
                dx = self.npc_perception.last_seen_player_pos[0] - self.npc.x
                dy = self.npc_perception.last_seen_player_pos[1] - self.npc.y
                target_angle = math.degrees(math.atan2(dy, dx))
            else:
                target_angle = self.npc.angle
            
            # Alinha em direção ao alvo / Align toward target
            self.npc.angle = self._approach_angle(self.npc.angle, target_angle, self.npc.rot_speed * dt)
            
            # Tenta disparar após estar alinhado / Try to fire once aligned
            self.last_ai_shot += dt
            # Use a slightly faster rate for align-and-fire attempts so NPC isn't too passive
            if self.last_ai_shot >= max(0.2, self.ai_shot_interval * 0.6):
                self.last_ai_shot = 0
                # Calcula ângulo atual vs alvo / Calculate current angle vs target
                angle_diff = abs(target_angle - self.npc.angle)
                if angle_diff > 180:
                    angle_diff = 360 - angle_diff
                
                # Dispara se alinhado o suficiente / Fire if aligned enough
                # Use tolerância maior para garantir que NPC atire enquanto se ajusta
                if self.npc.can_fire() and angle_diff < 40:  # Tolerância de 40° para ser mais agressivo
                    self.npc.fire()
                    proj = Projectile(
                        self.npc.x + math.cos(math.radians(self.npc.angle)) * 40,
                        self.npc.y + math.sin(math.radians(self.npc.angle)) * 40,
                        self.npc.angle, self.npc,
                        speed=self.options.get("projectile_speed", 420)
                    )
                    self.projectiles.append(proj)
                    self.npc_perception.log_event("FIRE", f"ângulo {int(self.npc.angle)}°")
                    if self.debug_mode:
                        print(f"  ✓ FIRED (aligned) at angle {self.npc.angle:.0f}° | ang_diff={angle_diff:.1f}°")

        # Pursue: persegue o jogador
        elif action_type == "pursue":
            if self.npc_perception.last_seen_player_pos:
                target_y = self.npc_perception.last_seen_player_pos[1]
                speed_multiplier = params.get("speed", 1.0)
                # Prevent too-slow pursuit due to low multipliers; keep reasonable minimum
                if speed_multiplier < 0.6:
                    speed_multiplier = 0.6

                if abs(target_y - self.npc.y) > 10:
                    direction = 1 if target_y > self.npc.y else -1
                    self.npc.move_y(direction * speed_multiplier, dt)
                
                # Rotaciona para encarar jogador
                if params.get("rotate", True):
                    dx = self.npc_perception.last_seen_player_pos[0] - self.npc.x
                    dy = self.npc_perception.last_seen_player_pos[1] - self.npc.y
                    angle_to_target = math.degrees(math.atan2(dy, dx))
                    self.npc.angle = self._approach_angle(self.npc.angle, angle_to_target, self.npc.rot_speed * dt)

        # Search: procura pelo jogador
        elif action_type == "search":
            rotation_dir = params.get("rotation_direction", 1)
            self.npc.rotate(rotation_dir, dt * 0.7)
            self.npc_perception.log_event("SEARCH", "Procurando alvo...")

        elif action_type == "wander":
            direction = params.get("direction", 1)
            speed = params.get("speed", 0.5)
            self.npc.move_y(direction * speed, dt)

        elif action_type == "random_rotate":
            direction = params.get("direction", 1)
            self.npc.rotate(direction, dt)

        # Idle: fica parado
        elif action_type == "idle":
            pass



    def _draw_name_input(self):
        self.screen.fill((20, 26, 36))

        # Fundo com blocos suaves para combinar com a identidade do jogo.
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

        # Cursor piscante para reforçar que é campo de entrada.
        if pygame.time.get_ticks() % 1000 < 500 and len(self.player_name) < 12:
            caret_x = box.x + 14 + name_surface.get_width() if self.player_name else box.x + 14
            pygame.draw.line(self.screen, (220, 225, 235), (caret_x, box.y + 12), (caret_x, box.y + 42), 2)

        hint = self.small_font.render(STRINGS[self.language]["login_confirm"], True, (200, 210, 220))
        self.screen.blit(hint, hint.get_rect(center=(SCREEN_WIDTH // 2, panel.y + 236)))

        if self.player_name.strip():
            back_hint = self.small_font.render(STRINGS[self.language]["login_back"], True, (150, 160, 175))
            self.screen.blit(back_hint, back_hint.get_rect(center=(SCREEN_WIDTH // 2, panel.y + 262)))



    def _approach_angle(self, src, trg, step):
        # Move src toward trg by at most step (degrees), handling wrap-around
        # Rotação suave considerando wrap-around / Smooth rotation handling wrap-around
        a = (trg - src + 180) % 360 - 180
        if a > 0:
            return (src + min(a, step)) % 360
        else:
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
        # Desenha menu principal / Draw main menu
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
        # Desenha tela de opções / Draw options screen
        self.screen.fill((28, 34, 42))
        title = pygame.font.Font(None, 48).render(STRINGS[self.language]["options"], True, (240, 240, 240))
        self.screen.blit(title, (40, 36))

        # Seleção de idioma / Language selection with better formatting
        y = 110
        lang_section_bg = pygame.Rect(40, y - 10, SCREEN_WIDTH - 80, 90)
        pygame.draw.rect(self.screen, (35, 40, 50), lang_section_bg, border_radius=6)
        pygame.draw.rect(self.screen, (80, 100, 120), lang_section_bg, 1, border_radius=6)
        
        lang_label = self.font.render(STRINGS[self.language]["language"] + ":", True, (210, 210, 210))
        self.screen.blit(lang_label, (60, y))
        
        # Botões de idioma / Language buttons with better spacing
        # Botões de idioma / Language buttons centered (padronizado)
        btn_w = 140
        btn_h = 40
        btn_gap = 24
        lang_buttons_total = 2 * btn_w + btn_gap
        lang_start_x = max(60, (SCREEN_WIDTH - lang_buttons_total) // 2)

        lang_pt_rect = pygame.Rect(lang_start_x, y + 35, btn_w, btn_h)
        lang_en_rect = pygame.Rect(lang_start_x + btn_w + btn_gap, y + 35, btn_w, btn_h)

        # PT button
        pt_color = (100, 200, 100) if self.language == "PT" else (150, 150, 150)
        pygame.draw.rect(self.screen, pt_color, lang_pt_rect, border_radius=6)
        pt_txt = self.font.render("Português", True, (20, 20, 20))
        self.screen.blit(pt_txt, pt_txt.get_rect(center=lang_pt_rect.center))

        # EN button
        en_color = (100, 200, 100) if self.language == "EN" else (150, 150, 150)
        pygame.draw.rect(self.screen, en_color, lang_en_rect, border_radius=6)
        en_txt = self.font.render("English", True, (20, 20, 20))
        self.screen.blit(en_txt, en_txt.get_rect(center=lang_en_rect.center))

        # Detecta clique nos botões de idioma / Detect clicks on language buttons
        if pygame.mouse.get_pressed()[0]:
            mouse_pos = pygame.mouse.get_pos()
            if lang_pt_rect.collidepoint(mouse_pos):
                self._set_language("PT")
            elif lang_en_rect.collidepoint(mouse_pos):
                self._set_language("EN")

        # Conta ativa e troca de usuário / Active account and login switch
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

        # Dificuldade em uso (somente leitura)
        y = 350
        diff_title = self.font.render(STRINGS[self.language]["difficulty_in_use"], True, (210, 210, 210))
        self.screen.blit(diff_title, (60, y))
        diff_value = self.small_font.render(STRINGS[self.language]["difficulty_locked"], True, (160, 180, 205))
        self.screen.blit(diff_value, (60, y + 28))

        # Controle de velocidade de projétil / Projectile speed
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
        
        # Opções de dificuldade / Difficulty options - moved to left panel above

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
            # Desenha o jogo / Draw the game
            self.screen.fill((50, 120, 50))
            # Limites da arena
            pygame.draw.rect(self.screen, (30, 30, 30), (ARENA_LEFT, ARENA_TOP, ARENA_RIGHT - ARENA_LEFT, ARENA_BOTTOM - ARENA_TOP), 4)

            # Desenha tanques e projéteis
            self.player.draw(self.screen)
            self.npc.draw(self.screen)
            for p in self.projectiles:
                p.draw(self.screen)

            if self.debug_mode:
                self._draw_debug()

            # 1. Barras de Vida (Mantidas nas extremidades)
            self._draw_health_bar(self.player, 20, 20)
            self._draw_health_bar(self.npc, SCREEN_WIDTH - 220, 20)
            
            # === 2. NOVA BOX DE STATUS (DIFICULDADE + VELOCIDADE) ===
            # Reduzimos a largura para 220 e movemos para a esquerda (x=240)
            status_x = 240 
            status_y = 15
            status_w = 230
            status_h = 75 # Um pouco mais baixa para ficar elegante
            
            status_bg = pygame.Rect(status_x, status_y, status_w, status_h)
            pygame.draw.rect(self.screen, (40, 45, 55), status_bg, border_radius=6)
            pygame.draw.rect(self.screen, (70, 90, 110), status_bg, 2, border_radius=6)
            
            # Textos internos (Dificuldade e Velocidade)
            diff_text = STRINGS[self.language]["difficulty"] + ": " + self.options.get("difficulty", "Normal")
            diff_label = self.small_font.render(diff_text, True, (230, 230, 230))
            self.screen.blit(diff_label, (status_x + 10, status_y + 12))
            
            speed_val = int(self.options.get("projectile_speed", 420))
            speed_text = STRINGS[self.language]["speed_label"] + " " + str(speed_val)
            speed_label = self.small_font.render(speed_text, True, (200, 200, 200))
            self.screen.blit(speed_label, (status_x + 10, status_y + 40))
            
            # === 3. CARINHA DO NPC (AGORA NO CENTRO-DIREITA) ===
            # Posicionada logo após a box de status
            face_x = status_x + status_w + 80
            face_y = 15
            self.npc_face.draw(self.screen, face_x, face_y)
            
            # 4. Log e Percepção
            self._draw_perception_log()
        


    def _draw_health_bar(self, tank, x, y):
        # Desenha barra de vida / Draw health bar
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
        """
        Desenha elementos de debug: hitbox, campo de visão, informações.
        Draw debug elements: hitbox, vision cone, information.
        """
        # Desenha hitbox dos tanques (retângulos)
        # Draw tank hitboxes (rectangles)
        pygame.draw.rect(self.screen, (255, 100, 100), (
            self.player.x - self.player.width // 2,
            self.player.y - self.player.height // 2,
            self.player.width,
            self.player.height
        ), 2)
        
        pygame.draw.rect(self.screen, (255, 150, 150), (
            self.npc.x - self.npc.width // 2,
            self.npc.y - self.npc.height // 2,
            self.npc.width,
            self.npc.height
        ), 2)
        
        # Desenha campo de visão do NPC (cone)
        # Draw NPC vision cone
        vision_range = self.npc_perception.vision_range
        vision_angle = self.npc_perception.vision_angle
        
        # Linha central de visão / Center vision line
        end_x = self.npc.x + vision_range * math.cos(math.radians(self.npc.angle))
        end_y = self.npc.y + vision_range * math.sin(math.radians(self.npc.angle))
        pygame.draw.line(self.screen, (100, 255, 100), (self.npc.x, self.npc.y), (end_x, end_y), 1)
        
        # Arco do cone de visão (usa pontos para desenhar)
        # Vision cone arc
        points = []
        for angle in range(int(self.npc.angle - vision_angle // 2), 
                          int(self.npc.angle + vision_angle // 2) + 1, 5):
            x = self.npc.x + vision_range * math.cos(math.radians(angle))
            y = self.npc.y + vision_range * math.sin(math.radians(angle))
            points.append((int(x), int(y)))
        
        # Desenha arco apenas se temos pontos válidos
        if len(points) > 1:
            try:
                pygame.draw.lines(self.screen, (100, 255, 100), False, points, 1)
            except TypeError:
                pass  # Ignora se houver erro nos pontos
        
        # Linhas laterais do cone / Cone sides
        angle_left = self.npc.angle - vision_angle // 2
        angle_right = self.npc.angle + vision_angle // 2
        
        x_left = self.npc.x + vision_range * math.cos(math.radians(angle_left))
        y_left = self.npc.y + vision_range * math.sin(math.radians(angle_left))
        pygame.draw.line(self.screen, (100, 255, 100), (self.npc.x, self.npc.y), (x_left, y_left), 1)
        
        x_right = self.npc.x + vision_range * math.cos(math.radians(angle_right))
        y_right = self.npc.y + vision_range * math.sin(math.radians(angle_right))
        pygame.draw.line(self.screen, (100, 255, 100), (self.npc.x, self.npc.y), (x_right, y_right), 1)
        
        # Sub-cone de tiro (pequeno ângulo interno) / Small firing sub-cone
        subcone_angle = 12
        subcone_range = min(vision_range, 900)
        left_sc = self.npc.angle - subcone_angle
        right_sc = self.npc.angle + subcone_angle
        x_left_sc = self.npc.x + subcone_range * math.cos(math.radians(left_sc))
        y_left_sc = self.npc.y + subcone_range * math.sin(math.radians(left_sc))
        x_right_sc = self.npc.x + subcone_range * math.cos(math.radians(right_sc))
        y_right_sc = self.npc.y + subcone_range * math.sin(math.radians(right_sc))
        # linhas laterais do subcone em amarelo
        pygame.draw.line(self.screen, (255, 210, 80), (self.npc.x, self.npc.y), (x_left_sc, y_left_sc), 2)
        pygame.draw.line(self.screen, (255, 210, 80), (self.npc.x, self.npc.y), (x_right_sc, y_right_sc), 2)
        # Arco do subcone (mais suave)
        sc_points = []
        step = 2
        for angle in range(int(left_sc), int(right_sc) + 1, step):
            x = self.npc.x + subcone_range * math.cos(math.radians(angle))
            y = self.npc.y + subcone_range * math.sin(math.radians(angle))
            sc_points.append((int(x), int(y)))
        if len(sc_points) > 1:
            pygame.draw.lines(self.screen, (255, 210, 80), False, sc_points, 2)

        # Desenha linha de visão até o jogador / Line to player
        if self.npc_perception.last_seen_player_pos:
            pygame.draw.line(self.screen, (0, 255, 0), 
                            (int(self.npc.x), int(self.npc.y)),
                            (int(self.npc_perception.last_seen_player_pos[0]), 
                             int(self.npc_perception.last_seen_player_pos[1])), 2)
            # Marca última posição vista / Mark last seen position
            pygame.draw.circle(self.screen, (0, 255, 0), 
                             (int(self.npc_perception.last_seen_player_pos[0]), 
                              int(self.npc_perception.last_seen_player_pos[1])), 4, 1)
        
        # Desenha linha até o jogador atual (para referência)
        pygame.draw.line(self.screen, (200, 100, 200), 
                        (int(self.npc.x), int(self.npc.y)),
                        (int(self.player.x), int(self.player.y)), 1)
        
        # Desenha informações de debug no topo / Draw debug info at top
        dist = math.sqrt((self.player.x - self.npc.x)**2 + (self.player.y - self.npc.y)**2)
        angle_to_player = math.degrees(math.atan2(self.player.y - self.npc.y, self.player.x - self.npc.x))
        angle_diff = abs(angle_to_player - self.npc.angle)
        if angle_diff > 180:
            angle_diff = 360 - angle_diff
        
        # Pega estatísticas do RBC
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
        # Desenha caixa mostrando o que o NPC vê / Draw box showing what NPC sees
        box_x = 20
        box_y = SCREEN_HEIGHT - 80
        box_w = 350
        box_h = 60
        
        # Fundo da caixa / Background
        pygame.draw.rect(self.screen, (30, 30, 40), (box_x, box_y, box_w, box_h), border_radius=6)
        pygame.draw.rect(self.screen, (100, 120, 140), (box_x, box_y, box_w, box_h), 2, border_radius=6)
        
        # Título / Title
        title = self.font.render(STRINGS[self.language]["npc_perception"], True, (200, 200, 200))
        self.screen.blit(title, (box_x + 10, box_y + 5))
        
        # Texto de percepção / Perception text
        if self.npc_perception.last_seen_player_pos:
            perception_text = f"{STRINGS[self.language]['seeing']} ({int(self.npc_perception.last_seen_player_pos[0])}, {int(self.npc_perception.last_seen_player_pos[1])})"
            text_color = (100, 200, 100)
        else:
            perception_text = STRINGS[self.language]["lost"]
            text_color = (150, 150, 150)
        
        perception_display = self.font.render(perception_text, True, text_color)
        self.screen.blit(perception_display, (box_x + 10, box_y + 30))
        
        # Desenha log de eventos / Draw event log
        self._draw_perception_log()
    
    def _draw_perception_log(self):
        # Desenha log de eventos do NPC como "terminal" na área inferior ponta-a-ponta
        log_margin = 10
        log_x = log_margin
        log_h = LOG_HEIGHT
        log_y = SCREEN_HEIGHT - log_h - log_margin
        log_w = SCREEN_WIDTH - log_margin * 2
        
        # Fundo do log / Log background
        pygame.draw.rect(self.screen, (15, 15, 25), (log_x, log_y, log_w, log_h), border_radius=6)
        pygame.draw.rect(self.screen, (100, 150, 100), (log_x, log_y, log_w, log_h), 2, border_radius=6)
        
        # Título / Title (localized)
        log_title = self.small_font.render(STRINGS[self.language].get("npc_log_title", "NPC LOG"), True, (100, 200, 100))
        self.screen.blit(log_title, (log_x + 10, log_y + 6))

        # Mostra entradas do log / Show last N lines of log
        all_entries = self.npc_perception.perception_log if self.npc_perception.perception_log else [STRINGS[self.language].get("waiting_events", "Aguardando eventos...")]

        # helper to truncate text to fit in width with ellipsis
        def truncate_to_width(text, font, max_w):
            if font.size(text)[0] <= max_w:
                return text
            ell = "..."
            # Remove characters until it fits
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

        # Compute line height and how many lines fit
        line_h = self.small_font.get_height() + 4
        available_h = log_h - 10 - self.small_font.get_height()
        max_lines = max(1, available_h // line_h)

        # Show most recent entries that fit
        log_entries = all_entries[-max_lines:]
        max_text_w = log_w - 20

        for i, entry in enumerate(log_entries):
            log_line = f">> {entry}"
            truncated = truncate_to_width(log_line, self.small_font, max_text_w)
            log_text = self.small_font.render(truncated, True, (150, 200, 150))
            self.screen.blit(log_text, (log_x + 10, log_y + 8 + self.small_font.get_height() + i * line_h))
    


    def _draw_gameover(self):
        # Desenha tela de fim de jogo / Draw game over screen

        # Fundo com mesma linguagem visual das demais telas
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

        # Trata tecla para retornar / handle key to return
        keys = pygame.key.get_pressed()
        if keys[pygame.K_RETURN]:
            self.state = "menu"
    
    def reset_game_and_database(self):
        """Apaga o banco de dados e reinicia a partida do zero (DEBUG MODE)."""
        print("[DEBUG] Resetando banco de dados RBC...")
        
        # Fecha conexão atual e força liberação do arquivo
        self.npc_brain.close()
        del self.npc_brain  # Remove referência
        
        # Força garbage collection para liberar arquivo no Windows
        import gc
        import time
        gc.collect()
        
        # Aguarda um momento para Windows liberar o arquivo
        time.sleep(0.15)
        
        # Reinicia o banco físico (force_reset apaga o arquivo .db)
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
        
        # Cria novo NPCBrain com banco vazio
        self.npc_brain = NPCBrain("npc_cases.db")
        
        # Reinicia a partida usando método apropriado
        self.start_new_game()
        
        print("[DEBUG] Banco de dados RBC resetado! Partida reiniciada.")

if __name__ == "__main__":
    g = Game()
    try:
        g.run()
    except SystemExit:
        pass