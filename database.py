"""
Módulo de gerenciamento de banco de dados para casos RBC do NPC.
Case-Based Reasoning database management for NPC learning.
"""
import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path


class CaseDatabase:

    def __init__(self, db_path: str = "npc_cases.db") -> None:
        self.db_path = Path(db_path)
        self.connection: Optional[sqlite3.Connection] = None
        self._initialize_database()

    # ==========================================================
    # INITIALIZATION
    # ==========================================================

    def _initialize_database(self) -> None:
        self.connection = sqlite3.connect(str(self.db_path))
        self.connection.row_factory = sqlite3.Row
        cursor = self.connection.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS rbc_cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id TEXT UNIQUE NOT NULL,
            player_id TEXT, 

            -- PROBLEM
            problem_distance REAL NOT NULL,
            problem_angle_diff REAL NOT NULL,
            problem_npc_health REAL NOT NULL,
            problem_player_health REAL NOT NULL,
            problem_player_visible INTEGER NOT NULL,
            problem_frames_lost INTEGER,

            -- SOLUTION
            solution_action TEXT NOT NULL,
            solution_params TEXT,

            -- RESULT
            result_success INTEGER NOT NULL,
            result_damage_dealt REAL,
            result_damage_taken REAL,
            result_outcome TEXT,

            -- METADATA
            difficulty TEXT,
            session_id TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,

            usage_count INTEGER DEFAULT 0,
            success_count INTEGER DEFAULT 0,
            success_rate REAL DEFAULT 0.0,

            total_reward REAL DEFAULT 0.0,
            avg_reward REAL DEFAULT 0.0,

            last_used DATETIME,
            created_by TEXT DEFAULT 'learned'
        )
        """)

        self.connection.commit()

    # ==========================================================
    # INSERT CASE
    # ==========================================================

    def insert_case(self, case_data: Dict) -> str:

        cursor = self.connection.cursor()
        case_id = case_data.get("case_id", f"case_{datetime.now().timestamp()}")

        usage_count = case_data.get("usage_count", 1)
        success_count = case_data.get(
            "success_count",
            1 if case_data.get("result_success") else 0
        )

        success_rate = success_count / usage_count if usage_count > 0 else 0

        total_reward = case_data.get(
            "total_reward",
            case_data.get("result_reward", 0.0)
        )

        avg_reward = total_reward / usage_count if usage_count > 0 else 0

        cursor.execute("""
            INSERT INTO rbc_cases (
                case_id,
                player_id,
                problem_distance, problem_angle_diff,
                problem_npc_health, problem_player_health, problem_player_visible,
                problem_frames_lost,
                solution_action, solution_params,
                result_success, result_damage_dealt, result_damage_taken, result_outcome,
                difficulty, session_id, created_by,
                usage_count, success_count, success_rate,
                total_reward, avg_reward
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            case_id,
            case_data.get("player_id", "unknown"),
            case_data.get("problem_distance", 0),
            case_data.get("problem_angle_diff", 0),
            case_data.get("problem_npc_health", 100),
            case_data.get("problem_player_health", 100),
            1 if case_data.get("problem_player_visible") else 0,
            case_data.get("problem_frames_lost", 0),
            case_data.get("solution_action", "idle"),
            json.dumps(case_data.get("solution_params", {})),
            1 if case_data.get("result_success") else 0,
            case_data.get("result_damage_dealt", 0),
            case_data.get("result_damage_taken", 0),
            case_data.get("result_outcome", "unknown"),
            case_data.get("difficulty", "Normal"),
            case_data.get("session_id", "default"),
            case_data.get("created_by", "learned"),
            usage_count,
            success_count,
            success_rate,
            total_reward,
            avg_reward
        ))

        self.connection.commit()
        return case_id

    # ==========================================================
    # UPDATE CASE USAGE (Reward acumulativo)
    # ==========================================================

    def update_case_usage(self, case_id: str, success: bool, reward: float) -> None:

        cursor = self.connection.cursor()

        cursor.execute("""
            SELECT usage_count, success_count, total_reward
            FROM rbc_cases
            WHERE case_id = ?
        """, (case_id,))

        row = cursor.fetchone()

        if not row:
            return

        usage_count = row["usage_count"] + 1
        success_count = row["success_count"] + (1 if success else 0)
        total_reward = row["total_reward"] + reward

        success_rate = success_count / usage_count
        avg_reward = total_reward / usage_count

        cursor.execute("""
            UPDATE rbc_cases
            SET usage_count = ?,
                success_count = ?,
                success_rate = ?,
                total_reward = ?,
                avg_reward = ?,
                last_used = CURRENT_TIMESTAMP
            WHERE case_id = ?
        """, (
            usage_count,
            success_count,
            success_rate,
            total_reward,
            avg_reward,
            case_id
        ))

        self.connection.commit()

    # ==========================================================
    # RETRIEVE SIMILAR CASES
    # ==========================================================

    def get_similar_cases(
        self,
        problem: Dict,
        threshold: float = 0.6,
        limit: int = 5,
        difficulty: Optional[str] = None
    ) -> List[Dict]:

        cursor = self.connection.cursor()

        if difficulty:
            cursor.execute(
                "SELECT * FROM rbc_cases WHERE difficulty = ? ORDER BY avg_reward DESC LIMIT 100",
                (difficulty,)
            )
        else:
            cursor.execute(
                "SELECT * FROM rbc_cases ORDER BY avg_reward DESC LIMIT 100"
            )

        all_cases = [dict(row) for row in cursor.fetchall()]

        similar_cases = []
        for case in all_cases:
            similarity = self._calculate_similarity(problem, case)
            if similarity >= threshold:
                case["similarity"] = similarity
                similar_cases.append(case)

        similar_cases.sort(
            key=lambda c: c["similarity"] * c.get("avg_reward", 1.0),
            reverse=True
        )

        return similar_cases[:limit]

    # ==========================================================
    # SIMILARITY FUNCTION
    # ==========================================================

    def _calculate_similarity(self, problem: Dict, case: Dict) -> float:

        distance_diff = abs(problem.get("distance", 0) - case["problem_distance"])
        angle_diff = abs(problem.get("angle_diff", 0) - case["problem_angle_diff"])
        health_diff = abs(problem.get("npc_health", 100) - case["problem_npc_health"])

        dist_similarity = max(0, 1 - (distance_diff / 800))
        angle_similarity = max(0, 1 - (angle_diff / 180))
        health_similarity = max(0, 1 - (health_diff / 100))
        visibility_match = (
            1.0 if problem.get("player_visible") == bool(case["problem_player_visible"])
            else 0.3
        )

        weights = {
            "distance": 0.4,
            "angle": 0.2,
            "health": 0.2,
            "visibility": 0.2
        }

        similarity = (
            dist_similarity * weights["distance"] +
            angle_similarity * weights["angle"] +
            health_similarity * weights["health"] +
            visibility_match * weights["visibility"]
        )

        return min(1.0, max(0.0, similarity))

    # ==========================================================
    # STATISTICS
    # ==========================================================

    def get_statistics(self) -> Dict:

        cursor = self.connection.cursor()

        cursor.execute("SELECT COUNT(*) as total FROM rbc_cases")
        total = cursor.fetchone()["total"]

        cursor.execute("SELECT AVG(avg_reward) as avg_reward FROM rbc_cases")
        avg_reward = cursor.fetchone()["avg_reward"] or 0.0

        cursor.execute("SELECT AVG(success_rate) as avg_success FROM rbc_cases")
        avg_success = cursor.fetchone()["avg_success"] or 0.0

        return {
            "total_cases": total,
            "avg_reward": avg_reward,
            "avg_success_rate": avg_success
        }
    # ==========================================================
    # CLOSE
    # ==========================================================

    def close(self) -> None:
        if self.connection:
            try:
                self.connection.commit()  # Garante que todas as transações sejam finalizadas
                self.connection.close()
                self.connection = None  # Remove referência
            except Exception as e:
                print(f"Erro ao fechar banco de dados: {e}")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()