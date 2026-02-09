"""
Testes simples para validar o sistema RBC.
Simple tests for RBC system validation.
"""

import sqlite3
from pathlib import Path
from database import CaseDatabase
from rbc_engine import RBCEngine, Problem, Solution, Outcome
from npc_brain import NPCBrain


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
        "problem_angle_diff": 10.0,
        "problem_npc_health": 100.0,
        "problem_player_health": 100.0,
        "problem_player_visible": True,
    }
    
    # Problema idêntico - deve ser bem parecido
    sim = db._calculate_similarity(case, {
        **case,
        "problem_distance": 100.0,
        "problem_angle_diff": 10.0,
    })
    assert sim > 0.7, f"Similaridade deveria ser alta, obteve {sim}"
    
    # Problema diferente - deve ser baixo
    sim = db._calculate_similarity(case, {
        **case,
        "problem_distance": 500.0,
        "problem_angle_diff": 90.0,
    })
    assert sim < 0.6, f"Similaridade deveria ser baixa, obteve {sim}"
    
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
        angle_diff=16.0,
        npc_health=95.0,
        player_health=95.0,
        player_visible=True
    )
    
    fallback = Solution(action="idle", params={})
    action = engine.decide_action(problem, fallback, "Normal")
    
    assert action.action in ["fire", "idle"], f"Ação inválida: {action.action}"
    
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
