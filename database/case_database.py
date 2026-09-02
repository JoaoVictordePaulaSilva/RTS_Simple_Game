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

        # Migração leve: adiciona colunas de percepção de projéteis se faltarem
        cursor.execute("PRAGMA table_info(rbc_cases)")
        existing_cols = {row['name'] for row in cursor.fetchall()}
        # Campos novos: distância/ângulo/proj_count
        if 'problem_nearest_projectile_distance' not in existing_cols:
            cursor.execute("ALTER TABLE rbc_cases ADD COLUMN problem_nearest_projectile_distance REAL DEFAULT 999999")
        if 'problem_nearest_projectile_angle' not in existing_cols:
            cursor.execute("ALTER TABLE rbc_cases ADD COLUMN problem_nearest_projectile_angle REAL DEFAULT 0.0")
        if 'problem_projectiles_nearby_count' not in existing_cols:
            cursor.execute("ALTER TABLE rbc_cases ADD COLUMN problem_projectiles_nearby_count INTEGER DEFAULT 0")
        if 'problem_edge_distance_top' not in existing_cols:
            cursor.execute("ALTER TABLE rbc_cases ADD COLUMN problem_edge_distance_top REAL DEFAULT 999999")
        if 'problem_edge_distance_bottom' not in existing_cols:
            cursor.execute("ALTER TABLE rbc_cases ADD COLUMN problem_edge_distance_bottom REAL DEFAULT 999999")
        if 'problem_nearest_edge_distance' not in existing_cols:
            cursor.execute("ALTER TABLE rbc_cases ADD COLUMN problem_nearest_edge_distance REAL DEFAULT 999999")
        if 'problem_border_pressure' not in existing_cols:
            cursor.execute("ALTER TABLE rbc_cases ADD COLUMN problem_border_pressure REAL DEFAULT 0.0")
        if 'problem_border_side' not in existing_cols:
            cursor.execute("ALTER TABLE rbc_cases ADD COLUMN problem_border_side INTEGER DEFAULT 0")
        if 'problem_closing_speed' not in existing_cols:
            cursor.execute("ALTER TABLE rbc_cases ADD COLUMN problem_closing_speed REAL DEFAULT 0.0")
        if 'problem_recent_actions' not in existing_cols:
            cursor.execute("ALTER TABLE rbc_cases ADD COLUMN problem_recent_actions TEXT DEFAULT '[]'")

        # Tabela de histórico de partidas para análise de desempenho
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS match_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            match_number INTEGER,
            session_id TEXT,
            player_id TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            duration_seconds REAL,
            duration_frames INTEGER,
            winner TEXT,
            player_final_health REAL,
            npc_final_health REAL,
            npc_damage_dealt REAL,
            npc_damage_taken REAL,
            total_cases_count INTEGER,
            new_cases_created INTEGER,
            match_total_reward REAL,
            match_avg_reward REAL,
            overall_avg_reward REAL,
            npc_win_rate REAL,
            epsilon REAL
        )
        """)

        self.connection.commit()

        # Pesos de similaridade configuráveis (soma = 1.0)
        self.similarity_weights = {
            "distance": 0.35,
            "angle": 0.0,
            "health": 0.15,
            "visibility": 0.15,
            "proj_dist": 0.10,
            "proj_angle": 0.05,
            "proj_count": 0.05,
            "border": 0.10,
            "age": 0.0,
            "outcome": 0.0,
            "action_history": 0.0,
            "closing_speed": 0.05,
        }

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
                problem_nearest_projectile_distance, problem_nearest_projectile_angle, problem_projectiles_nearby_count,
                problem_edge_distance_top, problem_edge_distance_bottom, problem_nearest_edge_distance,
                problem_border_pressure, problem_border_side, problem_closing_speed, problem_recent_actions,
                problem_npc_health, problem_player_health, problem_player_visible,
                problem_frames_lost,
                solution_action, solution_params,
                result_success, result_damage_dealt, result_damage_taken, result_outcome,
                difficulty, session_id, created_by,
                usage_count, success_count, success_rate,
                total_reward, avg_reward
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            case_id,
            case_data.get("player_id", "unknown"),
            case_data.get("problem_distance", 0),
            case_data.get("problem_angle_diff", 0),
            case_data.get("problem_nearest_projectile_distance", 999999),
            case_data.get("problem_nearest_projectile_angle", 0.0),
            case_data.get("problem_projectiles_nearby_count", 0),
            case_data.get("problem_edge_distance_top", 999999),
            case_data.get("problem_edge_distance_bottom", 999999),
            case_data.get("problem_nearest_edge_distance", 999999),
            case_data.get("problem_border_pressure", 0.0),
            case_data.get("problem_border_side", 0),
            case_data.get("problem_closing_speed", 0.0),
            json.dumps(case_data.get("problem_recent_actions", [])),
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
                "SELECT * FROM rbc_cases WHERE difficulty = ?",
                (difficulty,)
            )
        else:
            cursor.execute(
                "SELECT * FROM rbc_cases"
            )

        all_cases = [dict(row) for row in cursor.fetchall()]

        similar_cases = []
        for case in all_cases:
            similarity = self._calculate_similarity(problem, case)
            if similarity >= threshold:
                case["similarity"] = similarity
                similar_cases.append(case)

        def case_rank_score(c: Dict) -> float:
            avg_r = c.get("avg_reward", 0.0) or 0.0
            norm_reward = max(0.1, (avg_r + 25.0) / 75.0)
            return c["similarity"] * norm_reward

        similar_cases.sort(key=case_rank_score, reverse=True)

        return similar_cases[:limit]

    # ==========================================================
    # SIMILARITY FUNCTION
    # ==========================================================

    def _calculate_similarity(self, problem: Dict, case: Dict) -> float:
        distance_diff = abs(problem.get("distance", 0) - case["problem_distance"])
        angle_diff = abs(problem.get("angle_diff", 0) - case["problem_angle_diff"])
        health_diff = abs(problem.get("npc_health", 100) - case["problem_npc_health"])
        border_pressure_diff = abs(problem.get("border_pressure", 0.0) - (case.get("problem_border_pressure", 0.0) or 0.0))

        # Similaridade básica para distância/ângulo/vida/visibilidade
        dist_similarity = max(0, 1 - (distance_diff / 800))
        angle_similarity = max(0, 1 - (angle_diff / 180))
        health_similarity = max(0, 1 - (health_diff / 100))
        visibility_match = (
            1.0 if problem.get("player_visible") == bool(case["problem_player_visible"])
            else 0.3
        )

        # Percepção de projéteis (não preditiva)
        p_nearest_prob = problem.get("nearest_projectile_distance", float('inf'))
        c_nearest_prob = case.get("problem_nearest_projectile_distance", 999999)
        # Se ambos não têm projéteis, similaridade alta
        if (p_nearest_prob == float('inf') or p_nearest_prob >= 999999) and (c_nearest_prob is None or c_nearest_prob >= 999999):
            proj_dist_similarity = 1.0
        elif p_nearest_prob == float('inf') or p_nearest_prob >= 999999 or c_nearest_prob is None or c_nearest_prob >= 999999:
            proj_dist_similarity = 0.0
        else:
            proj_dist_similarity = max(0, 1 - (abs(p_nearest_prob - c_nearest_prob) / 800))

        p_nearest_ang = problem.get("nearest_projectile_angle", 0.0)
        c_nearest_ang = case.get("problem_nearest_projectile_angle", 0.0)
        ang_diff_proj = abs(p_nearest_ang - c_nearest_ang)
        if ang_diff_proj > 180:
            ang_diff_proj = 360 - ang_diff_proj
        proj_angle_similarity = max(0, 1 - (ang_diff_proj / 180))

        p_count = problem.get("projectiles_nearby_count", 0)
        c_count = case.get("problem_projectiles_nearby_count", 0)
        # Similaridade por count (normalizado em 0..5)
        proj_count_similarity = max(0, 1 - (abs(p_count - c_count) / 5))

        p_border_side = problem.get("border_side", 0)
        c_border_side = case.get("problem_border_side", 0) or 0
        p_edge = problem.get("nearest_edge_distance", float('inf'))
        c_edge = case.get("problem_nearest_edge_distance", 999999)
        if (p_edge == float('inf') or p_edge >= 999999) and (c_edge is None or c_edge >= 999999):
            edge_similarity = 1.0
        elif p_edge == float('inf') or p_edge >= 999999 or c_edge is None or c_edge >= 999999:
            edge_similarity = 0.0
        else:
            edge_similarity = max(0, 1 - (abs(p_edge - c_edge) / 120))
        if p_border_side != 0 and c_border_side != 0 and p_border_side == c_border_side:
            edge_similarity = min(1.0, edge_similarity + 0.1)

        # Componentes novos: idade do caso, estatísticas de outcome, histórico de ações, velocidade de aproximação

        # --- Age / temporalidade ---
        age_similarity = 0.5
        try:
            case_ts = case.get("timestamp")
            if case_ts:
                # SQLite CURRENT_TIMESTAMP format: 'YYYY-MM-DD HH:MM:SS'
                try:
                    case_dt = datetime.strptime(case_ts, "%Y-%m-%d %H:%M:%S")
                except Exception:
                    # fallback para ISO parse
                    case_dt = datetime.fromisoformat(case_ts)
                age_seconds = (datetime.now() - case_dt).total_seconds()
                max_age = 60 * 60 * 24  # 1 dia em segundos
                age_similarity = max(0.0, 1.0 - (age_seconds / max_age))
        except Exception:
            age_similarity = 0.5

        # --- Outcomes estatísticos mais finos ---
        # Usa avg_reward e success_rate quando disponíveis
        avg_reward = case.get("avg_reward", 0.0) or 0.0
        success_rate = case.get("success_rate", 0.0) or 0.0
        # Normaliza avg_reward em faixa [-20, +50] -> [0,1]
        min_r, max_r = -20.0, 50.0
        norm_avg_reward = (max(min(avg_reward, max_r), min_r) - min_r) / (max_r - min_r)
        outcome_similarity = (0.6 * norm_avg_reward) + (0.4 * success_rate)

        # --- Histórico de ações curtas (opcional) ---
        action_history_similarity = 0.5
        try:
            p_hist = problem.get("recent_actions") or []
            c_hist = case.get("problem_recent_actions") or case.get("recent_actions") or []
            if isinstance(c_hist, str):
                c_hist = json.loads(c_hist)
            if p_hist and c_hist:
                set_p = set(p_hist)
                set_c = set(c_hist)
                inter = len(set_p.intersection(set_c))
                uni = len(set_p.union(set_c))
                if uni > 0:
                    action_history_similarity = inter / uni
        except Exception:
            action_history_similarity = 0.5

        # --- Velocidade relativa / closing speed (opcional) ---
        closing_similarity = 0.5
        try:
            p_closing = problem.get("closing_speed")
            c_closing = case.get("problem_closing_speed")
            if p_closing is not None and c_closing is not None:
                max_speed = 600.0
                closing_similarity = max(0.0, 1.0 - (abs(p_closing - c_closing) / max_speed))
                # reforça se ambos têm sinal de aproximação/afastamento igual
                if (p_closing >= 0) == (c_closing >= 0):
                    closing_similarity = min(1.0, closing_similarity + 0.1)
        except Exception:
            closing_similarity = 0.5

        # Recupera pesos configuráveis
        weights = self.similarity_weights

        similarity = (
            dist_similarity * weights.get("distance", 0.0) +
            angle_similarity * weights.get("angle", 0.0) +
            health_similarity * weights.get("health", 0.0) +
            visibility_match * weights.get("visibility", 0.0) +
            proj_dist_similarity * weights.get("proj_dist", 0.0) +
            proj_angle_similarity * weights.get("proj_angle", 0.0) +
            proj_count_similarity * weights.get("proj_count", 0.0) +
            edge_similarity * weights.get("border", 0.0) +
            age_similarity * weights.get("age", 0.0) +
            outcome_similarity * weights.get("outcome", 0.0) +
            action_history_similarity * weights.get("action_history", 0.0) +
            closing_similarity * weights.get("closing_speed", 0.0)
        )

        return min(1.0, max(0.0, similarity))

    # ==========================================================
    # STATISTICS
    # ==========================================================

    def get_statistics(self, player_id: Optional[str] = None) -> Dict:

        cursor = self.connection.cursor()

        if player_id:
            cursor.execute("SELECT COUNT(*) as total FROM rbc_cases WHERE player_id = ?", (player_id,))
            total = cursor.fetchone()["total"]

            cursor.execute("SELECT AVG(avg_reward) as avg_reward FROM rbc_cases WHERE player_id = ?", (player_id,))
            avg_reward = cursor.fetchone()["avg_reward"] or 0.0

            cursor.execute("SELECT AVG(success_rate) as avg_success FROM rbc_cases WHERE player_id = ?", (player_id,))
            avg_success = cursor.fetchone()["avg_success"] or 0.0
        else:
            cursor.execute("SELECT COUNT(*) as total FROM rbc_cases")
            total = cursor.fetchone()["total"]

            cursor.execute("SELECT AVG(avg_reward) as avg_reward FROM rbc_cases")
            avg_reward = cursor.fetchone()["avg_reward"] or 0.0

            cursor.execute("SELECT AVG(success_rate) as avg_success FROM rbc_cases")
            avg_success = cursor.fetchone()["avg_success"] or 0.0

        return {
            "player_id": player_id,
            "total_cases": total,
            "avg_reward": avg_reward,
            "avg_success_rate": avg_success
        }

    # ==========================================================
    # MATCH HISTORY & ANALYTICS
    # ==========================================================

    def insert_match_record(self, match_data: Dict) -> int:
        cursor = self.connection.cursor()
        
        cursor.execute("SELECT COUNT(*) as cnt FROM match_history")
        count = cursor.fetchone()["cnt"] or 0
        match_number = match_data.get("match_number", count + 1)

        cursor.execute("""
            INSERT INTO match_history (
                match_number, session_id, player_id, duration_seconds, duration_frames,
                winner, player_final_health, npc_final_health, npc_damage_dealt, npc_damage_taken,
                total_cases_count, new_cases_created, match_total_reward, match_avg_reward,
                overall_avg_reward, npc_win_rate, epsilon
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            match_number,
            match_data.get("session_id", "default"),
            match_data.get("player_id", "player"),
            match_data.get("duration_seconds", 0.0),
            match_data.get("duration_frames", 0),
            match_data.get("winner", "Draw"),
            match_data.get("player_final_health", 0.0),
            match_data.get("npc_final_health", 0.0),
            match_data.get("npc_damage_dealt", 0.0),
            match_data.get("npc_damage_taken", 0.0),
            match_data.get("total_cases_count", 0),
            match_data.get("new_cases_created", 0),
            match_data.get("match_total_reward", 0.0),
            match_data.get("match_avg_reward", 0.0),
            match_data.get("overall_avg_reward", 0.0),
            match_data.get("npc_win_rate", 0.0),
            match_data.get("epsilon", 0.0),
        ))
        self.connection.commit()
        return cursor.lastrowid

    def get_match_history(self, limit: Optional[int] = None) -> List[Dict]:
        cursor = self.connection.cursor()
        query = "SELECT * FROM match_history ORDER BY match_number ASC"
        if limit:
            query = f"SELECT * FROM ({query} DESC LIMIT {limit}) ORDER BY match_number ASC"
        cursor.execute(query)
        return [dict(row) for row in cursor.fetchall()]
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
