"""
Testes simples para validar o sistema RBC.
Simple tests for RBC system validation.
"""

import sqlite3
from pathlib import Path
from database.case_database import CaseDatabase
from ai.rbc_engine import RBCEngine, Problem, Solution, Outcome
from ai.npc_brain import NPCBrain
from utils.action_guards import should_auto_fire_in_cold_start


def test_database_initialization():
    """Testa inicialização do banco de dados."""
    print("✓ Testando inicialização do banco...")
    
    db_path = "test_npc_cases_init.db"
    # Garante que não existe
    Path(db_path).unlink(missing_ok=True)
    
    db = CaseDatabase(db_path)
    stats = db.get_statistics()
    assert stats["total_cases"] == 0, "Banco deveria estar vazio"
    db.close()
    
    Path(db_path).unlink(missing_ok=True)
    print("  ✓ Banco inicializa corretamente")


def test_case_insertion():
    """Testa inserção de casos."""
    print("✓ Testando inserção de casos...")
    
    db_path = "test_npc_cases_insert.db"
    Path(db_path).unlink(missing_ok=True)
    
    db = CaseDatabase(db_path)
    
    # Insere caso de teste
    case_data = {
        "case_id": "test_case_1",
        "problem_distance": 100.0,
        "problem_angle_diff": 15.0,
        "problem_npc_health": 90.0,
        "problem_player_health": 80.0,
        "problem_player_visible": True,
        "solution_action": "fire",
        "solution_params": {"angle": 15},
        "result_success": True,
        "result_damage_dealt": 25.0,
        "result_outcome": "hit",
        "difficulty": "Normal",
    }
    
    case_id = db.insert_case(case_data)
    assert case_id == "test_case_1"
    
    stats = db.get_statistics()
    assert stats["total_cases"] == 1, "Deveria haver 1 caso"
    
    db.close()
    Path(db_path).unlink(missing_ok=True)
    print("  ✓ Casos inserem corretamente")


def test_similarity_calculation():
    """Testa cálculo de similaridade."""
    print("✓ Testando cálculo de similaridade...")
    
    db_path = "test_npc_cases_sim.db"
    Path(db_path).unlink(missing_ok=True)
    
    db = CaseDatabase(db_path)
    
    # Insere caso de referência
    case = {
        "problem_distance": 100.0,
        "problem_angle_diff": 0.0,
        "problem_npc_health": 100.0,
        "problem_player_health": 100.0,
        "problem_player_visible": True,
    }
    
    # Problema idêntico - deve ser bem parecido
    sim = db._calculate_similarity(case, {
        **case,
        "problem_distance": 100.0,
        "problem_angle_diff": 0.0,
    })
    assert sim > 0.7, f"Similaridade deveria ser alta, obteve {sim}"
    
    # Problema diferente - deve ser baixo
    sim = db._calculate_similarity(case, {
        **case,
        "problem_distance": 500.0,
        "problem_angle_diff": 0.0,
    })
    assert sim < 0.7, f"Similaridade deveria ser baixa, obteve {sim}"
    
    db.close()
    Path(db_path).unlink(missing_ok=True)
    print("  ✓ Similaridade calcula corretamente")


def test_rbc_engine():
    """Testa motor RBC."""
    print("✓ Testando motor RBC...")
    
    db_path = "test_npc_cases_engine.db"
    Path(db_path).unlink(missing_ok=True)
    
    # Insere alguns casos no BD
    db = CaseDatabase(db_path)
    
    for i in range(3):
        db.insert_case({
            "case_id": f"seed_{i}",
            "problem_distance": 100.0 + i * 50,
            "problem_angle_diff": 15.0,
            "problem_npc_health": 100.0,
            "problem_player_health": 100.0,
            "problem_player_visible": True,
            "solution_action": "fire",
            "solution_params": {},
            "result_success": True,
            "created_by": "seed"
        })
    db.close()
    
    # Testa motor RBC
    engine = RBCEngine(db_path)
    
    problem = Problem(
        distance=105.0,
        angle_diff=0.0,
        npc_health=95.0,
        player_health=95.0,
        player_visible=True
    )
    
    fallback = Solution(action="idle", params={})
    action = engine.decide_action(problem, fallback, "Normal")
    
    valid_actions = {
        "fire",
        "idle",
        "wander",
        "random_rotate",
        "search",
        "align_and_fire",
        "pursue",
        "evade_projectile",
    }
    assert action.action in valid_actions, f"Ação inválida: {action.action}"
    
    engine.close()
    Path(db_path).unlink(missing_ok=True)
    print("  ✓ Motor RBC funciona corretamente")


def test_npc_brain():
    """Testa cérebro do NPC."""
    print("✓ Testando cérebro do NPC...")
    
    db_path = "test_npc_cases_brain.db"
    Path(db_path).unlink(missing_ok=True)
    
    brain = NPCBrain(db_path)
    brain.set_session("test_session")
    
    # Simula decisão
    action = brain.decide_action(
        npc_x=400, npc_y=300, npc_angle=0, npc_health=100,
        player_x=500, player_y=300, player_health=100,
        player_visible=True, frames_since_last_seen=0,
        difficulty="Normal"
    )
    
    assert action.action is not None, "Ação não foi decidida"
    assert isinstance(action.params, dict), "Parâmetros devem ser dict"
    
    # Testa aprendizado
    brain.report_outcome(
        success=True,
        damage_dealt=25.0,
        damage_taken=0,
        outcome_type="hit",
        difficulty="Normal"
    )
    
    brain.close()
    Path(db_path).unlink(missing_ok=True)
    print("  ✓ Cérebro do NPC funciona corretamente")


def test_evade_requires_real_threat():
    """Testa que o evade depende de ameaça real de projétil."""
    print("✓ Testando evade condicionado à ameaça real...")

    db_path = "test_npc_cases_evade.db"
    Path(db_path).unlink(missing_ok=True)

    brain = NPCBrain(db_path)

    safe_problem = brain._encode_problem(
        npc_x=400, npc_y=300, npc_angle=0, npc_health=100,
        player_x=500, player_y=300, player_health=100,
        player_visible=True, frames_since_last_seen=0,
        nearest_projectile_distance=120,
        nearest_projectile_angle=15,
        projectiles_nearby_count=1,
        projectile_threat_active=False,
        projectile_threat_distance=120,
    )
    safe_action = brain._generate_fallback_action(safe_problem)
    assert safe_action.action != "evade_projectile", "Não deveria evadir sem ameaça real"

    threat_problem = brain._encode_problem(
        npc_x=400, npc_y=300, npc_angle=0, npc_health=100,
        player_x=500, player_y=300, player_health=100,
        player_visible=True, frames_since_last_seen=0,
        nearest_projectile_distance=120,
        nearest_projectile_angle=15,
        projectiles_nearby_count=1,
        projectile_threat_active=True,
        projectile_threat_distance=120,
    )
    threat_action = brain._generate_fallback_action(threat_problem)
    assert threat_action.action == "evade_projectile", "Deveria evadir com ameaça real"

    brain.close()
    Path(db_path).unlink(missing_ok=True)
    print("  ✓ Evade exige ameaça real")


def test_alignment_auto_fire_is_cold_start_only():
    """Testa que o auto-disparo por alinhamento só vale no cold start."""
    print("✓ Testando auto-disparo de alinhamento por modo...")

    assert should_auto_fire_in_cold_start("COLD_START", 120, 8, 900, 12)
    assert not should_auto_fire_in_cold_start("RBC", 120, 8, 900, 12)
    assert not should_auto_fire_in_cold_start("RANDOM", 120, 8, 900, 12)
    assert not should_auto_fire_in_cold_start("COLD_START", 120, 20, 900, 12)

    print("  ✓ Auto-disparo fica restrito ao cold start")


def test_problem_encoding_includes_border_and_closing_speed():
    """Testa que o estado RBC carrega borda, direção e aproximação."""
    print("✓ Testando encoding de borda e closing speed...")

    db_path = "test_npc_cases_border.db"
    Path(db_path).unlink(missing_ok=True)

    brain = NPCBrain(db_path)
    brain.action_history = ["wander", "search", "fire"]
    brain.rbc_engine.last_problem = Problem(
        distance=160.0,
        angle_diff=0.0,
        npc_health=100,
        player_health=100,
        player_visible=True,
    )

    problem = brain._encode_problem(
        npc_x=400, npc_y=110, npc_angle=0, npc_health=100,
        player_x=500, player_y=200, player_health=100,
        player_visible=True, frames_since_last_seen=0,
        nearest_projectile_distance=150,
        nearest_projectile_angle=10,
        projectiles_nearby_count=1,
        projectile_threat_active=False,
        projectile_threat_distance=150,
    )

    assert problem.nearest_edge_distance < float("inf")
    assert problem.border_pressure > 0.0, "Deveria registrar pressão de borda"
    assert problem.border_side == -1, "NPC perto do topo deveria marcar side superior"
    assert problem.closing_speed == 70.0, "Closing speed deveria refletir aproximação ao player"
    assert problem.recent_actions == ["wander", "search", "fire"], "Histórico curto de ações deveria ser salvo"

    brain.close()
    Path(db_path).unlink(missing_ok=True)
    print("  ✓ Encoding inclui borda, histórico e closing speed")


def run_all_tests():
    """Executa todos os testes."""
    print("\n" + "="*50)
    print("EXECUTANDO TESTES DO SISTEMA RBC")
    print("="*50 + "\n")
    
    tests = [
        test_database_initialization,
        test_case_insertion,
        test_similarity_calculation,
        test_rbc_engine,
        test_npc_brain,
        test_evade_requires_real_threat,
        test_alignment_auto_fire_is_cold_start_only,
        test_problem_encoding_includes_border_and_closing_speed,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"  ✗ FALHOU: {e}")
            failed += 1
        except Exception as e:
            print(f"  ✗ ERRO: {e}")
            failed += 1
    
    print("\n" + "="*50)
    print(f"RESULTADOS: {passed} passou(ram), {failed} falhou/falharam")
    print("="*50 + "\n")
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
