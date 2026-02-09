"""
Módulo de gerenciamento de banco de dados para casos RBC do NPC.
Case-Based Reasoning database management for NPC learning.
"""

import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from pathlib import Path


class CaseDatabase:
    """
    Gerencia persistência de casos RBC em SQLite.
    Manages RBC case persistence in SQLite.
    """

    def __init__(self, db_path: str = "npc_cases.db") -> None:
        """
        Inicializa conexão com banco de dados.
        Initialize database connection.
        
        Args:
            db_path: Caminho para arquivo SQLite / Path to SQLite file
        """
        self.db_path = Path(db_path)
        self.connection: Optional[sqlite3.Connection] = None
        self._initialize_database()

    def _initialize_database(self) -> None:
        """Cria tabelas se não existirem / Create tables if not exist."""
        self.connection = sqlite3.connect(str(self.db_path))
        self.connection.row_factory = sqlite3.Row
        cursor = self.connection.cursor()

        # Tabela de casos RBC
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS rbc_cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id TEXT UNIQUE NOT NULL,
            
            -- PROBLEMA (estado do jogo)
            problem_distance REAL NOT NULL,
            problem_angle_diff REAL NOT NULL,
            problem_npc_health REAL NOT NULL,
            problem_player_health REAL NOT NULL,
            problem_player_visible INTEGER NOT NULL,
            problem_frames_lost INTEGER,
            
            -- SOLUÇÃO (ação tomada)
            solution_action TEXT NOT NULL,
            solution_params TEXT,  -- JSON com parâmetros
            
            -- RESULTADO (feedback da ação)
            result_success INTEGER NOT NULL,
            result_damage_dealt REAL,
            result_damage_taken REAL,
            result_outcome TEXT,  -- 'hit', 'miss', 'evaded', etc
            
            -- METADADOS
            difficulty TEXT,
            session_id TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            usage_count INTEGER DEFAULT 0,
            success_count INTEGER DEFAULT 0,
            success_rate REAL DEFAULT 0.0,
            last_used DATETIME,
            
            created_by TEXT DEFAULT 'seed'  -- 'seed' ou 'learned'
        )
        """)

        # Tabela de sessões
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS game_sessions (
            session_id TEXT PRIMARY KEY,
            start_time DATETIME DEFAULT CURRENT_TIMESTAMP,
            end_time DATETIME,
            difficulty TEXT,
            npc_final_health REAL,
            player_final_health REAL,
            npc_won INTEGER,
            case_count_at_end INTEGER,
            avg_similarity_used REAL
        )
        """)

        # Índices para performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_difficulty ON rbc_cases(difficulty)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_distance ON rbc_cases(problem_distance)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_success_rate ON rbc_cases(success_rate DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_session ON rbc_cases(session_id)")

        self.connection.commit()

    def insert_case(self, case_data: Dict) -> str:
        """
        Insere novo caso no banco.
        Insert new case into database.
        
        Args:
            case_data: Dicionário com dados do caso / Case data dictionary
            
        Returns:
            case_id gerado / Generated case ID
        """
        cursor = self.connection.cursor()
        case_id = case_data.get("case_id", f"case_{datetime.now().timestamp()}")

        cursor.execute("""
        INSERT INTO rbc_cases (
            case_id, problem_distance, problem_angle_diff,
            problem_npc_health, problem_player_health, problem_player_visible,
            problem_frames_lost,
            solution_action, solution_params,
            result_success, result_damage_dealt, result_damage_taken, result_outcome,
            difficulty, session_id, created_by
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            case_id,
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
        ))

        self.connection.commit()
        return case_id

    def get_similar_cases(
        self,
        problem: Dict,
        threshold: float = 0.6,
        limit: int = 5,
        difficulty: Optional[str] = None
    ) -> List[Dict]:
        """
        Recupera casos similares ao problema atual.
        Retrieve cases similar to current problem.
        
        Args:
            problem: Estado atual a ser resolvido / Current problem state
            threshold: Mínimo de similaridade (0-1) / Minimum similarity threshold
            limit: Máximo de casos a retornar / Maximum cases to return
            difficulty: Filtrar por dificuldade (opcional) / Filter by difficulty
            
        Returns:
            Lista de casos similares / List of similar cases
        """
        cursor = self.connection.cursor()

        if difficulty:
            cursor.execute("SELECT * FROM rbc_cases WHERE difficulty = ? ORDER BY success_rate DESC LIMIT 100", (difficulty,))
        else:
            cursor.execute("SELECT * FROM rbc_cases ORDER BY success_rate DESC LIMIT 100")

        all_cases = [dict(row) for row in cursor.fetchall()]
        
        # Calcula similaridade para cada caso
        similar_cases = []
        for case in all_cases:
            similarity = self._calculate_similarity(problem, case)
            if similarity >= threshold:
                case["similarity"] = similarity
                similar_cases.append(case)

        # Ordena por similaridade e retorna
        similar_cases.sort(key=lambda c: c["similarity"], reverse=True)
        return similar_cases[:limit]

    def _calculate_similarity(self, problem: Dict, case: Dict) -> float:
        """
        Calcula similaridade entre problema e caso (0-1).
        Calculate similarity between problem and case (0-1).
        """
        distance_diff = abs(problem.get("distance", 0) - case["problem_distance"])
        angle_diff = abs(problem.get("angle_diff", 0) - case["problem_angle_diff"])
        health_diff = abs(problem.get("npc_health", 100) - case["problem_npc_health"])

        # Normaliza diferenças
        dist_similarity = max(0, 1 - (distance_diff / 800))  # Arena max ~800px
        angle_similarity = max(0, 1 - (angle_diff / 180))
        health_similarity = max(0, 1 - (health_diff / 100))
        visibility_match = 1.0 if (problem.get("player_visible") == bool(case["problem_player_visible"])) else 0.3

        # Pesos: distância é mais importante
        weights = {"distance": 0.4, "angle": 0.2, "health": 0.2, "visibility": 0.2}
        
        similarity = (
            dist_similarity * weights["distance"] +
            angle_similarity * weights["angle"] +
            health_similarity * weights["health"] +
            visibility_match * weights["visibility"]
        )

        return min(1.0, max(0.0, similarity))

    def update_case_usage(self, case_id: str, success: bool) -> None:
        """
        Atualiza estatísticas de uso do caso.
        Update case usage statistics.
        
        Args:
            case_id: ID do caso / Case ID
            success: Se a ação foi bem-sucedida / Whether action was successful
        """
        cursor = self.connection.cursor()
        
        cursor.execute("""
        SELECT usage_count, success_count FROM rbc_cases WHERE case_id = ?
        """, (case_id,))
        
        row = cursor.fetchone()
        if row:
            usage_count = row["usage_count"] + 1
            success_count = row["success_count"] + (1 if success else 0)
            success_rate = success_count / usage_count

            cursor.execute("""
            UPDATE rbc_cases 
            SET usage_count = ?, success_count = ?, success_rate = ?, last_used = CURRENT_TIMESTAMP
            WHERE case_id = ?
            """, (usage_count, success_count, success_rate, case_id))

            self.connection.commit()

    def get_statistics(self) -> Dict:
        """
        Retorna estatísticas do banco.
        Return database statistics.
        """
        cursor = self.connection.cursor()

        cursor.execute("SELECT COUNT(*) as total FROM rbc_cases")
        total = cursor.fetchone()["total"]

        cursor.execute("SELECT COUNT(*) as seed FROM rbc_cases WHERE created_by = 'seed'")
        seed_count = cursor.fetchone()["seed"]

        cursor.execute("SELECT AVG(success_rate) as avg_success FROM rbc_cases")
        avg_success = cursor.fetchone()["avg_success"] or 0.0

        return {
            "total_cases": total,
            "seed_cases": seed_count,
            "learned_cases": total - seed_count,
            "avg_success_rate": avg_success
        }

    def close(self) -> None:
        """Fecha conexão com banco."""
        if self.connection:
            self.connection.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
