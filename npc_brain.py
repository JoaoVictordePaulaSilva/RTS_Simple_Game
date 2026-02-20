class NPCBrain:
    def __init__(self, db_path): pass
    def set_session(self, session_id): pass
    def decide_action(self, **kwargs):
        from rbc_engine import Solution
        return Solution("idle", {})
    def report_outcome(self, **kwargs): pass
    def get_statistics(self):
        return {'total_cases': 0, 'seed_cases': 0, 'learned_cases': 0, 'avg_success_rate': 0}