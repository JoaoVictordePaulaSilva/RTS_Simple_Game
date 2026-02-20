"""
Sistema de expressões faciais do NPC.
NPC facial expression system showing emotion based on action/state.
"""

import pygame
import math


class NPCFace:
    """
    Exibe expressão facial do NPC refletindo seu estado interno.
    Shows NPC facial expression reflecting internal state.
    """

    # Mapeamento de emoções para cores e características
    EMOTIONS = {
        "confused": {"bg": (150, 100, 50), "mouth": "?", "eyes": "o_o"},      # Procurando
        "aggressive": {"bg": (220, 50, 50), "mouth": "frown", "eyes": "angry"},  # Atirando
        "focused": {"bg": (100, 180, 220), "mouth": "line", "eyes": "focused"},   # Apontando
        "determined": {"bg": (200, 150, 50), "mouth": "grin", "eyes": "determined"},  # Perseguindo
        "relaxed": {"bg": (100, 200, 100), "mouth": "smile", "eyes": "closed"},    # Parado
        "hurt": {"bg": (180, 50, 50), "mouth": "x", "eyes": "x"},         # Ferido
        "victorious": {"bg": (255, 215, 0), "mouth": "smile", "eyes": "happy"},  # Vitorioso
        "scared": {"bg": (100, 100, 150), "mouth": "o", "eyes": "wide"},   # Assustado
    }

    def __init__(self, width=80, height=80):
        """
        Inicializa carinha do NPC com placeholder geométrico.
        
        Args:
            width: Largura da carinha (px)
            height: Altura da carinha (px)
        """
        self.width = width
        self.height = height
        self.current_emotion = "relaxed"
        self.font_small = pygame.font.Font(None, 16)
        self.font_large = pygame.font.Font(None, 24)

    def update_expression(self, action, can_see, health, angle_diff=None, success_rate=0.5):
        """
        Atualiza expressão baseado em estado do NPC.
        Update expression based on NPC state.
        
        Args:
            action: Ação do NPC (fire, search, pursue, align_and_fire, idle)
            can_see: Se consegue ver o jogador
            health: Saúde do NPC (0-100)
            angle_diff: Diferença angular com o jogador
            success_rate: Taxa de sucesso dos casos RBC (0-1)
        """
        # Prioridade: saúde crítica > ação
        if health < 30:
            self.current_emotion = "hurt"
        elif action == "fire":
            self.current_emotion = "aggressive"
        elif action == "align_and_fire":
            self.current_emotion = "focused"
        elif action == "pursue":
            self.current_emotion = "determined"
        elif action == "search":
            self.current_emotion = "confused"
        else:  # idle
            self.current_emotion = "relaxed"

    def draw(self, surface, x, y):
        """
        Desenha a carinha no local (x, y).
        Draw face at position (x, y).
        """
        emotion_data = self.EMOTIONS[self.current_emotion]
        bg_color = emotion_data["bg"]
        
        # Fundo da carinha (retângulo arredondado)
        pygame.draw.rect(surface, bg_color, (x, y, self.width, self.height), border_radius=12)
        pygame.draw.rect(surface, (255, 255, 255), (x, y, self.width, self.height), 2, border_radius=12)
        
        # Olhos (2 círculos)
        eye_y = y + self.height // 3
        eye_left_x = x + self.width // 4
        eye_right_x = x + 3 * self.width // 4
        eye_radius = 6
        
        eyes_type = emotion_data["eyes"]
        
        if eyes_type == "closed":
            # Olhos fechados: linha horizontal
            pygame.draw.line(surface, (0, 0, 0), 
                           (eye_left_x - 5, eye_y), 
                           (eye_left_x + 5, eye_y), 2)
            pygame.draw.line(surface, (0, 0, 0), 
                           (eye_right_x - 5, eye_y), 
                           (eye_right_x + 5, eye_y), 2)
        elif eyes_type == "x":
            # Olhos X (morto/ferido)
            pygame.draw.line(surface, (0, 0, 0), 
                           (eye_left_x - 5, eye_y - 5), 
                           (eye_left_x + 5, eye_y + 5), 2)
            pygame.draw.line(surface, (0, 0, 0), 
                           (eye_left_x + 5, eye_y - 5), 
                           (eye_left_x - 5, eye_y + 5), 2)
            pygame.draw.line(surface, (0, 0, 0), 
                           (eye_right_x - 5, eye_y - 5), 
                           (eye_right_x + 5, eye_y + 5), 2)
            pygame.draw.line(surface, (0, 0, 0), 
                           (eye_right_x + 5, eye_y - 5), 
                           (eye_right_x - 5, eye_y + 5), 2)
        elif eyes_type == "wide":
            # Olhos bem abertos (assustado)
            pygame.draw.circle(surface, (255, 255, 255), (eye_left_x, eye_y), eye_radius)
            pygame.draw.circle(surface, (0, 0, 0), (eye_left_x, eye_y), 3)
            pygame.draw.circle(surface, (255, 255, 255), (eye_right_x, eye_y), eye_radius)
            pygame.draw.circle(surface, (0, 0, 0), (eye_right_x, eye_y), 3)
        elif eyes_type == "happy":
            # Olhos felizes: meia-lua
            pygame.draw.arc(surface, (0, 0, 0), 
                          (eye_left_x - eye_radius, eye_y - eye_radius, 
                           eye_radius * 2, eye_radius * 2), 
                          3.14, 0, 2)
            pygame.draw.arc(surface, (0, 0, 0), 
                          (eye_right_x - eye_radius, eye_y - eye_radius, 
                           eye_radius * 2, eye_radius * 2), 
                          3.14, 0, 2)
        elif eyes_type == "angry":
            # Olhos raivosos: sobrancelhas
            pygame.draw.line(surface, (0, 0, 0), 
                           (eye_left_x - 7, eye_y - 3), 
                           (eye_left_x + 7, eye_y + 3), 2)
            pygame.draw.line(surface, (0, 0, 0), 
                           (eye_right_x - 7, eye_y + 3), 
                           (eye_right_x + 7, eye_y - 3), 2)
            pygame.draw.circle(surface, (0, 0, 0), (eye_left_x, eye_y), 3)
            pygame.draw.circle(surface, (0, 0, 0), (eye_right_x, eye_y), 3)
        elif eyes_type == "focused":
            # Olhos focados: linha de mira
            pygame.draw.circle(surface, (0, 0, 0), (eye_left_x, eye_y), 4)
            pygame.draw.circle(surface, (255, 0, 0), (eye_left_x, eye_y), 2)
            pygame.draw.circle(surface, (0, 0, 0), (eye_right_x, eye_y), 4)
            pygame.draw.circle(surface, (255, 0, 0), (eye_right_x, eye_y), 2)
        else:  # o_o (confuso)
            pygame.draw.circle(surface, (0, 0, 0), (eye_left_x, eye_y), eye_radius)
            pygame.draw.circle(surface, (0, 0, 0), (eye_right_x, eye_y), eye_radius)
        
        # Boca
        mouth_y = y + 2 * self.height // 3
        mouth_type = emotion_data["mouth"]
        
        if mouth_type == "smile":
            # Sorriso: arco para cima
            pygame.draw.arc(surface, (0, 0, 0), 
                          (x + self.width // 4, mouth_y, self.width // 2, self.height // 4), 
                          3.14, 0, 3)
        elif mouth_type == "frown":
            # Careta: arco para baixo
            pygame.draw.arc(surface, (0, 0, 0), 
                          (x + self.width // 4, mouth_y - self.height // 8, self.width // 2, self.height // 4), 
                          0, 3.14, 3)
        elif mouth_type == "x":
            # X (morto/dor)
            pygame.draw.line(surface, (0, 0, 0), 
                           (x + self.width // 3, mouth_y), 
                           (x + 2 * self.width // 3, mouth_y + self.height // 8), 3)
            pygame.draw.line(surface, (0, 0, 0), 
                           (x + 2 * self.width // 3, mouth_y), 
                           (x + self.width // 3, mouth_y + self.height // 8), 3)
        elif mouth_type == "o":
            # O (assustado/surpreso)
            pygame.draw.circle(surface, (0, 0, 0), 
                             (x + self.width // 2, mouth_y + self.height // 16), 5)
        elif mouth_type == "line":
            # Linha (séria/apontando)
            pygame.draw.line(surface, (0, 0, 0), 
                           (x + self.width // 4, mouth_y), 
                           (x + 3 * self.width // 4, mouth_y), 2)
        elif mouth_type == "grin":
            # Grin: arco mais pronunciado
            pygame.draw.arc(surface, (0, 0, 0), 
                          (x + self.width // 5, mouth_y - self.height // 6, 3 * self.width // 5, self.height // 3), 
                          3.14, 0, 4)
        
        # Label da emoção (debug / feedback)
        emotion_label = self.font_small.render(self.current_emotion, True, (0, 0, 0))
        surface.blit(emotion_label, (x + 5, y + self.height + 5))
