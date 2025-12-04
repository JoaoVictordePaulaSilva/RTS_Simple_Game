import math
import random
import sys
import pygame

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
        "title": "RTS Tanks - Demo",
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
        "press_enter": "Pressione ENTER para voltar",
        "waiting_events": "Aguardando eventos...",
    },
    "EN": {
        "title": "RTS Tanks - Demo",
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
        "press_enter": "Press Enter to return to menu",
        "waiting_events": "Waiting for events...",
    }
}


class Tank:
    def __init__(self, x, y, color, is_player=False, name="Tank"):
        self.x = x
        self.y = y
        self.color = color
        self.angle = 0  # graus / degrees, 0 -> right
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


class Projectile:
    def __init__(self, x, y, angle, owner, speed=420, damage=25):
        self.x = x
        self.y = y
        self.angle = angle
        self.owner = owner
        self.speed = speed
        self.damage = damage
        self.radius = 6
        self.is_alive = True

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
        pygame.draw.circle(surf, (200, 60, 60), (int(self.x), int(self.y)), self.radius)


class NPCPerception:
    """
    Classe para representar a percepção do NPC
    Class to represent NPC perception
    O NPC observa o inimigo e reage ao que vê
    NPC observes the enemy and reacts to what it sees
    """
    def __init__(self, tank):
        self.tank = tank
        self.vision_range = 400  # distância máxima de visão / max vision distance
        self.vision_angle = 120  # ângulo de visão (graus) / vision angle (degrees)
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
        # Title fonts reused
        self.menu_title_font = pygame.font.Font(None, 64)
        self.section_title_font = pygame.font.Font(None, 48)

        # Idioma / Language
        self.language = "EN"  # Default: English
        
        # states: menu, options, playing, gameover
        self.state = "menu"
        self.running = True

        self.setup_menu()
        self.reset_game()

        # options / opções
        self.options = {"difficulty": "Normal", "projectile_speed": 420}

    def setup_menu(self):
        center_x = SCREEN_WIDTH // 2
        self.buttons = []
        btn_w = 220
        btn_h = 48
        gap = 14
        start_y = SCREEN_HEIGHT // 2 - (btn_h + gap)

        def start_game():
            self.start_new_game()

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
        self.player = Tank(140, SCREEN_HEIGHT // 2, (40, 120, 200), is_player=True, name=STRINGS[self.language]["player"])
        self.npc = Tank(SCREEN_WIDTH - 140, SCREEN_HEIGHT // 2, (200, 100, 60), is_player=False, name=STRINGS[self.language]["enemy"])
        self.npc_perception = NPCPerception(self.npc)
        self.projectiles = []
        self.last_ai_shot = 0
        self.ai_shot_interval = 1.0  # seconds (will vary by difficulty / segundos - varia por dificuldade)

    def start_new_game(self):
        self.reset_game()
        diff = self.options.get("difficulty", "Normal")
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

        self.state = "playing"

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            self.handle_events()
            self.update(dt)
            self.draw()

        pygame.quit()
        sys.exit()

    def handle_events(self):
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                self.running = False
            if self.state == "menu":
                for b in self.buttons:
                    b.handle_event(ev)
            elif self.state == "options":
                if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                    self.state = "menu"
            elif self.state == "playing":
                if ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_ESCAPE:
                        self.state = "menu"
                    if ev.key == pygame.K_SPACE:
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

    def update(self, dt):
        if self.state == "playing":
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
                if p.owner is not self.npc and self._collide_proj_tank(p, self.npc):
                    self.npc.hit(p.damage)
                    p.is_alive = False

            # Remove projéteis mortos / remove dead projectiles
            self.projectiles = [p for p in self.projectiles if p.is_alive]

            # Verifica condições de fim de jogo / check end conditions
            if self.player.health <= 0 or self.npc.health <= 0:
                self.state = "gameover"

    def _collide_proj_tank(self, p, tank):
        # Verifica colisão entre projétil e tanque / Check collision between projectile and tank
        dx = p.x - tank.x
        dy = p.y - tank.y
        dist_sq = dx * dx + dy * dy
        hit_r = 28
        return dist_sq <= (hit_r + p.radius) ** 2

    def _update_npc_ai(self, dt):
        # ===== IA DO NPC - IMPLEMENTAÇÃO BÁSICA =====
        # NPC AI - BASIC IMPLEMENTATION
        # Pode ser expandida com: pathfinding, predição, estratégias avançadas, etc
        # Can be expanded with: pathfinding, prediction, advanced strategies, etc
        
        if self.npc_perception.last_seen_player_pos:
            # NPC VÊ o jogador / NPC SEES the player
            target_y = self.npc_perception.last_seen_player_pos[1]
            
            # 1. Tenta seguir o jogador no eixo Y / Try to follow player on Y axis
            if abs(target_y - self.npc.y) > 10:
                direction = 1 if target_y > self.npc.y else -1
                self.npc.move_y(direction, dt)
            
            # 2. Rotaciona para encarar o jogador / Rotate to face player
            dx = self.npc_perception.last_seen_player_pos[0] - self.npc.x
            dy = self.npc_perception.last_seen_player_pos[1] - self.npc.y
            angle_to_target = math.degrees(math.atan2(dy, dx))
            
            # TODO: REFINAMENTO FUTURO - Adicionar imprecisão (inaccuracy)
            # FUTURE REFINEMENT - Add inaccuracy to shots for difficulty variation
            self.npc.angle = self._approach_angle(self.npc.angle, angle_to_target, self.npc.rot_speed * dt)
            
            # 3. Dispara se tem boa visão do alvo / Fire if has good view of target
            self.last_ai_shot += dt
            if self.last_ai_shot >= self.ai_shot_interval:
                self.last_ai_shot = 0
                # TODO: REFINAMENTO FUTURO - Adicionar delay de reação (reaction delay)
                # FUTURE REFINEMENT - Add reaction delay for human-like AI
                if random.random() < 0.8:  # Chance de acertar / Chance to hit
                    if self.npc.can_fire():
                        self.npc.fire()
                        # TODO: REFINAMENTO FUTURO - Adicionar predição de movimento (lead shots)
                        # FUTURE REFINEMENT - Predict player movement for leading shots
                        proj = Projectile(self.npc.x + math.cos(math.radians(self.npc.angle)) * 40,
                                           self.npc.y + math.sin(math.radians(self.npc.angle)) * 40,
                                           self.npc.angle, self.npc, speed=self.options.get("projectile_speed", 420))
                        self.projectiles.append(proj)
                        self.npc_perception.log_event("SHOT", f"ângulo {int(self.npc.angle)}°")
        else:
            # NPC PERDEU o jogador / NPC LOST the player
            # TODO: REFINAMENTO FUTURO - Implementar busca inteligente / FUTURE: implement smart search
            if random.random() < 0.1:
                self.npc.rotate(random.choice([-1, 1]), dt * 5)
            self.npc_perception.log_event("SEARCHING", "Alvo perdido, procurando...")

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
        title = pygame.font.Font(None, 64).render(STRINGS[self.language]["title"], True, (230, 230, 230))
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 140)))
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

        # Opções de dificuldade / Difficulty options with better formatting
        y = 230
        # aumentar a caixa para caber os botões centralizados
        diff_section_bg = pygame.Rect(40, y - 10, SCREEN_WIDTH - 80, 110)
        pygame.draw.rect(self.screen, (35, 40, 50), diff_section_bg, border_radius=6)
        pygame.draw.rect(self.screen, (80, 100, 120), diff_section_bg, 1, border_radius=6)

        diff_label = self.font.render(STRINGS[self.language]["difficulty"] + ":", True, (210, 210, 210))
        self.screen.blit(diff_label, (60, y))

        diffs = ["Easy", "Normal", "Hard"]
        diffs_display = [STRINGS[self.language]["easy"], STRINGS[self.language]["normal"], STRINGS[self.language]["hard"]]
        y += 30
        # Botões centralizados com largura menor e gap controlado
        btn_w = 120
        btn_h = 40
        btn_gap = 24
        total_w = 3 * btn_w + 2 * btn_gap
        start_x = max(60, (SCREEN_WIDTH - total_w) // 2)

        for i, (d, d_display) in enumerate(zip(diffs, diffs_display)):
            color = (100, 200, 100) if self.options.get("difficulty") == d else (150, 150, 150)
            txt = self.font.render(d_display, True, (20, 20, 20))
            rect = pygame.Rect(start_x + i * (btn_w + btn_gap), y, btn_w, btn_h)
            pygame.draw.rect(self.screen, color, rect, border_radius=6)
            self.screen.blit(txt, txt.get_rect(center=rect.center))
            # clickable
            if pygame.mouse.get_pressed()[0] and rect.collidepoint(pygame.mouse.get_pos()):
                self.options["difficulty"] = d
        # Controle de velocidade de projétil / Projectile speed with better formatting
        # posiciona abaixo da caixa de dificuldade aumentada e centraliza
        y = 370
        speed_section_bg = pygame.Rect(40, y - 10, SCREEN_WIDTH - 80, 70)
        pygame.draw.rect(self.screen, (35, 40, 50), speed_section_bg, border_radius=6)
        pygame.draw.rect(self.screen, (80, 100, 120), speed_section_bg, 1, border_radius=6)

        speed_label = self.font.render(STRINGS[self.language]["projectile_speed"], True, (210, 210, 210))
        self.screen.blit(speed_label, (60, y))

        speed = self.options.get("projectile_speed", 420)
        speed = max(260, min(700, speed))
        # Ajusta com setas / adjust with left/right keys
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:
            speed = max(260, speed - 4)
        if keys[pygame.K_RIGHT]:
            speed = min(700, speed + 4)
        self.options["projectile_speed"] = speed

        # Render value centered in section
        val = self.font.render(str(int(speed)), True, (220, 220, 220))
        val_x = (SCREEN_WIDTH // 2) - (val.get_width() // 2)
        self.screen.blit(val, (val_x, y + 28))

        info = self.font.render(STRINGS[self.language]["esc_menu"], True, (150, 150, 150))
        self.screen.blit(info, (60, SCREEN_HEIGHT - 60))

    def _draw_game(self):
        # Desenha o jogo / Draw the game
        self.screen.fill((50, 120, 50))
        # Limites da arena / simple arena boundaries
        pygame.draw.rect(self.screen, (30, 30, 30), (ARENA_LEFT, ARENA_TOP, ARENA_RIGHT - ARENA_LEFT, ARENA_BOTTOM - ARENA_TOP), 4)

        # Desenha tanques / draw tanks
        self.player.draw(self.screen)
        self.npc.draw(self.screen)

        # Projéteis / projectiles
        for p in self.projectiles:
            p.draw(self.screen)

        # Barras de vida / HUD: health bars
        self._draw_health_bar(self.player, 20, 20)
        self._draw_health_bar(self.npc, SCREEN_WIDTH - 220, 20)
        
        # Caixa de percepção do NPC: apenas log (bilingue) / NPC perception: only the log (bilingual)
        self._draw_perception_log()
        
        # Caixa de informações do jogo / Game info box
        self._draw_game_info_box()

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
    
    def _draw_game_info_box(self):
        # Desenha caixa com informações do jogo / Draw box with game info
        box_x = SCREEN_WIDTH // 2 - 200
        box_y = 10
        box_w = 400
        box_h = 50
        
        # Fundo da caixa / Background
        pygame.draw.rect(self.screen, (30, 30, 40), (box_x, box_y, box_w, box_h), border_radius=6)
        pygame.draw.rect(self.screen, (100, 120, 140), (box_x, box_y, box_w, box_h), 2, border_radius=6)
        
        # Dificuldade / Difficulty
        diff_key = STRINGS[self.language]["difficulty"]
        diff_value = STRINGS[self.language][self.options.get("difficulty", "normal").lower()]
        diff_text = f"{diff_key}: {diff_value}"
        diff_display = self.font.render(diff_text, True, (200, 200, 200))
        self.screen.blit(diff_display, (box_x + 10, box_y + 8))
        
        # Velocidade do projétil / Projectile speed
        speed_key = STRINGS[self.language]["speed_label"]
        speed_value = int(self.options.get("projectile_speed", 420))
        speed_text = f"{speed_key} {speed_value}"
        speed_display = self.font.render(speed_text, True, (200, 200, 200))
        self.screen.blit(speed_display, (box_x + 10, box_y + 28))

    def _draw_gameover(self):
        # Desenha tela de fim de jogo / Draw game over screen
        self.screen.fill((10, 10, 10))
        winner = STRINGS[self.language]["draw"]
        if self.player.health > self.npc.health:
            winner = STRINGS[self.language]["player_wins"]
        elif self.npc.health > self.player.health:
            winner = STRINGS[self.language]["enemy_wins"]

        title = pygame.font.Font(None, 64).render(STRINGS[self.language]["game_over"], True, (240, 240, 240))
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 140)))
        sub = self.font.render(winner, True, (210, 210, 210))
        self.screen.blit(sub, sub.get_rect(center=(SCREEN_WIDTH // 2, 220)))

        hint = self.font.render(STRINGS[self.language]["press_enter"], True, (160, 160, 160))
        self.screen.blit(hint, hint.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 120)))

        # Trata tecla para retornar / handle key to return
        keys = pygame.key.get_pressed()
        if keys[pygame.K_RETURN]:
            self.state = "menu"


if __name__ == "__main__":
    g = Game()
    try:
        g.run()
    except SystemExit:
        pass
