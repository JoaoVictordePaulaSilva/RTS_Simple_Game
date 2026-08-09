"""Small action guards shared by the game loop and tests."""


def should_auto_fire_in_cold_start(mode: str, p_dist: float, p_ang_diff: float, subcone_range: float, subcone_angle: float) -> bool:
	return mode == "COLD_START" and p_dist <= subcone_range and p_ang_diff <= subcone_angle


def should_tactical_fire(mode: str, p_dist: float, p_ang_diff: float, subcone_range: float, subcone_angle: float) -> bool:
	"""
	Determina se o NPC deve disparar um tiro de oportunidade tático.
	Funciona em COLD_START, EXPLOIT, EXPLORE e RANDOM quando o player está no subcone.
	"""
	return p_dist <= subcone_range and p_ang_diff <= subcone_angle