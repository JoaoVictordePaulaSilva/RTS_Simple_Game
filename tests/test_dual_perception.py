"""
Teste automatizado para o Sistema de Duplo Cone de Percepção (Dual-Cone Perception):
1. Cone Principal (Player): 800px / 20° (±10°)
2. Cone Periférico (Projéteis): 380px / 70° (±35°) com trajetória de colisão (heading_diff <= 35°)
3. Zona de Reflexo (Projéteis Próximos): 160px com trajetória de colisão
4. Descarte de Projéteis se Afastando (heading_diff > 35°)
"""

from game.entities import Tank, Projectile
from game.perception import NPCPerception

def test_dual_perception():
    npc = Tank(500, 300, (200, 100, 60), is_player=False)
    npc.angle = 180  # Olhando para a esquerda (direção 180°)
    player = Tank(100, 300, (40, 120, 200), is_player=True)
    player.angle = 0   # Olhando para a direita

    perception = NPCPerception(npc)

    # Teste 1: Player no cone principal (dist=400px, angulo=0° diff) -> Deve VER o player
    perception.update(player, dt=0.016, projectiles=[])
    assert perception.last_seen_player_pos is not None, "Player em (100, 300) deveria ser visto no cone principal de 20°"
    print("✓ Teste 1: Player visto no cone principal (20° / 800px)")

    # Teste 2: Player fora do cone principal (dist=400px, angulo diff = 25°) -> NÃO deve ver o player
    player_off = Tank(100, 480, (40, 120, 200), is_player=True) # dy = 180, dx = -400 -> ~156° (diff ~24°)
    perception.update(player_off, dt=0.016, projectiles=[])
    assert perception.last_seen_player_pos is None, "Player a 24° diff NÃO deveria ser visto pelo cone principal de 20°"
    print("✓ Teste 2: Player a 24° diff mantido invisível (preserva desafio de busca)")

    # Teste 3: Projétil vindo na periférica (dist=300px, angulo rel = 25°, heading = 0° indo em direção ao NPC em 180°)
    # Projétil em (200, 440), viajando a 0° (em direção ao NPC em 500, 300)
    proj_threat = Projectile(200, 390, angle=0.0, owner=player, speed=420)
    perception.update(player_off, dt=0.016, projectiles=[proj_threat])
    assert perception.projectile_threat_active, "Projétil em rota de colisão a 25° de rel_ang deveria ativar o cone periférico (70°)"
    print("✓ Teste 3: Projétil periférico em rota de colisão ativou ameaça no cone de 70°")

    # Teste 4: Projétil em (200, 390) mas SE AFASTANDO (angle = 180°, viajando para a esquerda longe do NPC)
    proj_away = Projectile(200, 390, angle=180.0, owner=player, speed=420)
    perception.update(player_off, dt=0.016, projectiles=[proj_away])
    assert not perception.projectile_threat_active, "Projétil se afastando NÃO deve ser considerado ameaça ativa!"
    print("✓ Teste 4: Projétil se afastando (heading_diff > 35°) foi descartado corretamente!")

    # Teste 5: Projétil à queima-roupa na Zona de Reflexo (dist=140px, em rota de colisão)
    proj_close = Projectile(380, 300, angle=0.0, owner=player, speed=420)
    perception.update(player_off, dt=0.016, projectiles=[proj_close])
    assert perception.projectile_threat_active, "Projétil a 140px em rota de colisão deve ser detectado na Zona de Reflexo (160px)"
    print("✓ Teste 5: Projétil na Zona de Reflexo (160px) ativou esquiva imediata!")

    print("\n  ✓ TODOS OS TESTES DO DUPLO CONE PASSARAM COM SUCESSO!")

if __name__ == "__main__":
    test_dual_perception()
