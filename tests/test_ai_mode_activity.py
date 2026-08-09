"""
Testes de verificação da atividade e geração de casos no modo IA.
Unit tests verifying AI mode activity, tactical firing, and case generation.
"""

from pathlib import Path
from utils.action_guards import should_tactical_fire
from database.case_database import CaseDatabase
from ai.rbc_engine import RBCEngine, Problem, Solution, Outcome
from ai.npc_brain import NPCBrain


def test_tactical_fire_guard_in_ai_mode():
	"""Testa se o guard de disparo tático aceita modos de IA além do cold start."""
	print("✓ Testando guard de disparo tático no modo IA...")
	assert should_tactical_fire("COLD_START", 100, 5, 900, 15)
	assert should_tactical_fire("EXPLOIT", 100, 5, 900, 15)
	assert should_tactical_fire("EXPLORE", 100, 5, 900, 15)
	assert should_tactical_fire("RANDOM", 100, 5, 900, 15)
	assert not should_tactical_fire("EXPLOIT", 1000, 5, 900, 15)
	print("  ✓ Guard de disparo tático validado para todos os modos.")


def test_ai_mode_case_insertion():
	"""Testa se o modo IA insere novos casos no banco para experiências relevantes."""
	print("✓ Testando inserção de novos casos no modo IA...")
	db_path = "test_npc_cases_ai_insert.db"
	Path(db_path).unlink(missing_ok=True)

	engine = RBCEngine(db_path)
	engine.episode_count = 10  # Força modo IA (fora do COLD_START)
	engine.mode = "EXPLOIT"

	prob = Problem(
		distance=150.0,
		angle_diff=0.0,
		npc_health=100.0,
		player_health=100.0,
		player_visible=True,
		frames_lost=0,
		npc_x=100.0,
		npc_y=200.0
	)
	sol = Solution(action="fire", params={})
	out = Outcome(success=True, damage_dealt=25.0, damage_taken=0.0, outcome_type="hit")

	# Aprende um novo caso com case_id sintético prévio
	initial_count = engine.db.get_statistics()["total_cases"]
	engine.learn(
		case_id="existing_case_123",
		problem=prob,
		solution=sol,
		outcome=out,
		session_id="test_session",
		difficulty="Normal"
	)

	final_count = engine.db.get_statistics()["total_cases"]
	assert final_count > initial_count, f"Deveria ter inserido um novo caso no modo IA (inicial={initial_count}, final={final_count})"
	print(f"  ✓ Novos casos são inseridos no modo IA (total no DB: {final_count}).")

	engine.close()
	Path(db_path).unlink(missing_ok=True)


def test_action_hold_early_release_on_sight():
	"""Testa a liberação antecipada de hold quando o jogador entra no campo de visão."""
	print("✓ Testando liberação antecipada do hold de ação...")
	db_path = "test_hold_release.db"
	Path(db_path).unlink(missing_ok=True)

	engine = RBCEngine(db_path)
	engine.episode_count = 10
	engine.action_hold_frames = 20
	engine.last_solution = Solution(action="wander", params={})

	p_visible = Problem(
		distance=100.0,
		angle_diff=0.0,
		npc_health=100.0,
		player_health=100.0,
		player_visible=True,
		frames_lost=0,
		npc_x=100.0,
		npc_y=200.0
	)

	fallback = Solution(action="search", params={})
	res = engine.decide_action(p_visible, fallback, "Normal")
	# Como o player está visível e a última ação era "wander", o hold deve ser liberado imediatamente
	assert engine.action_hold_frames == 0 or res.action != "wander", "Hold deveria ter sido liberado ao avistar o jogador"
	print("  ✓ Liberação antecipada de hold funciona corretamente.")

	engine.close()
	Path(db_path).unlink(missing_ok=True)


def run_all_ai_mode_tests():
	print("\n==================================================")
	print("EXECUTANDO TESTES DE ATIVIDADE DO MODO IA")
	print("==================================================")
	test_tactical_fire_guard_in_ai_mode()
	test_ai_mode_case_insertion()
	test_action_hold_early_release_on_sight()
	print("==================================================")
	print("TODOS OS TESTES DO MODO IA PASSERAM!")
	print("==================================================\n")


if __name__ == "__main__":
	run_all_ai_mode_tests()
