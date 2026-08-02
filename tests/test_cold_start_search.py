"""
Teste específico para verificar o comportamento estocástico do Cold Start.
"""

import os
from pathlib import Path
from ai.npc_brain import NPCBrain
from ai.rbc_models import Problem

def test_cold_start_target_lost_and_visible():
    db_path = "test_cold_start_search.db"
    Path(db_path).unlink(missing_ok=True)

    brain = NPCBrain(db_path)
    
    # 1. Testar quando o jogador está PERDIDO (player_visible = False)
    actions_when_lost = set()
    for _ in range(300):
        sol = brain.decide_action(
            npc_x=400, npc_y=300, npc_angle=180, npc_health=100,
            player_x=100, player_y=100, player_health=100,
            player_visible=False,
            frames_since_last_seen=30,
            difficulty="Normal"
        )
        actions_when_lost.add(sol.action)
        # Não deve haver tiros no vazio quando o alvo está perdido no Cold Start
        assert sol.action not in ("fire", "align_and_fire"), f"Tiro indesejado no vazio quando alvo perdido: {sol.action}"

    print(f"✓ Ações sorteadas com alvo PERDIDO no Cold Start: {actions_when_lost}")
    assert any(a in actions_when_lost for a in ("search", "pursue", "wander", "random_rotate")), "Deveria haver ações de busca/perseguição/reposicionamento"

    # Reset episode para re-testar
    brain.reset_episode()
    brain.rbc_engine.cold_macro = None

    # 2. Testar quando o jogador está VISÍVEL (player_visible = True)
    actions_when_visible = set()
    for _ in range(300):
        sol = brain.decide_action(
            npc_x=400, npc_y=300, npc_angle=180, npc_health=100,
            player_x=100, player_y=300, player_health=100,
            player_visible=True,
            frames_since_last_seen=0,
            difficulty="Normal"
        )
        actions_when_visible.add(sol.action)

    print(f"✓ Ações sorteadas com alvo VISÍVEL no Cold Start: {actions_when_visible}")

    # Reset episode para re-testar
    brain.reset_episode()
    brain.rbc_engine.cold_macro = None

    # 3. Testar resposta sob AMEAÇA DE PROJÉTIL
    sol_threat = brain.decide_action(
        npc_x=400, npc_y=300, npc_angle=180, npc_health=100,
        player_x=100, player_y=300, player_health=100,
        player_visible=False,
        frames_since_last_seen=100,
        difficulty="Normal",
        projectile_threat_active=True,
        projectile_threat_distance=150.0
    )
    print(f"✓ Ação com ameaça de projétil no Cold Start: {sol_threat.action}")
    assert sol_threat.action == "evade_projectile", f"Deveria evadir projétil, recebeu: {sol_threat.action}"

    brain.close()
    Path(db_path).unlink(missing_ok=True)
    print("  ✓ Teste do Cold Start concluído com sucesso!")

if __name__ == "__main__":
    test_cold_start_target_lost_and_visible()
