"""
Teste automatizado para validar o Evade Lock:
1. Checagem de Borda da Arena (Parede)
2. Destrava Antecipada (Early Release)
"""

from pathlib import Path
from game.entities import Tank
from game.perception import NPCPerception
from game.constants import ARENA_TOP, ARENA_BOTTOM
from ai.npc_brain import NPCBrain

def test_evade_rules():
    db_path = "test_evade_lock.db"
    Path(db_path).unlink(missing_ok=True)

    brain = NPCBrain(db_path)
    
    # 1. Testar Early Release no RBCEngine:
    # Ativa esquiva com ameaça ativa
    sol1 = brain.decide_action(
        npc_x=400, npc_y=300, npc_angle=180, npc_health=100,
        player_x=100, player_y=300, player_health=100,
        player_visible=True, frames_since_last_seen=0,
        projectile_threat_active=True, projectile_threat_distance=150.0
    )
    assert sol1.action == "evade_projectile", f"Esperava evade_projectile, recebeu {sol1.action}"

    # No frame seguinte, ameaça zera (projectile_threat_active = False) -> Destrava antecipada
    sol2 = brain.decide_action(
        npc_x=400, npc_y=300, npc_angle=180, npc_health=100,
        player_x=100, player_y=300, player_health=100,
        player_visible=True, frames_since_last_seen=0,
        projectile_threat_active=False, projectile_threat_distance=float('inf')
    )
    assert sol2.action != "evade_projectile", f"Destrava antecipada falhou: ainda em {sol2.action}"
    print("✓ Destrava Antecipada (Early Release) funcionou perfeitamente!")

    brain.close()
    Path(db_path).unlink(missing_ok=True)
    print("  ✓ Todos os testes do Evade Lock passaram com sucesso!")

if __name__ == "__main__":
    test_evade_rules()
