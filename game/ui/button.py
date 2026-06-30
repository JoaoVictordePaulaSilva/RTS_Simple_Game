import pygame


class Button:
    def __init__(self, rect, text, action=None, font=None):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.action = action
        self.font = font or pygame.font.Font(None, 32)

    def draw(self, surf, mouse_pos):
        color = (200, 200, 200) if self.rect.collidepoint(mouse_pos) else (180, 180, 180)
        pygame.draw.rect(surf, color, self.rect, border_radius=6)
        txt = self.font.render(self.text, True, (20, 20, 20))
        txt_rect = txt.get_rect(center=self.rect.center)
        surf.blit(txt, txt_rect)

    def handle_event(self, ev):
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            if self.rect.collidepoint(ev.pos) and self.action:
                self.action()
