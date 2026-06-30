"""
Utilitário para inicializar e gerenciar banco de dados RBC.
Utility for initializing and managing RBC database.
"""
from pathlib import Path
import sqlite3
from datetime import datetime
import os

from .case_database import CaseDatabase


def initialize_database(db_path: str = "npc_cases.db", force_reset: bool = False) -> CaseDatabase:
    if force_reset:
        Path(db_path).unlink(missing_ok=True)
        print("Banco resetado. Iniciando vazio.")

    # Tenta abrir o DB; se estiver corrompido, move para backup e recria
    try:
        db = CaseDatabase(db_path)
        return db
    except sqlite3.DatabaseError as e:
        # Faz backup do arquivo corrompido com timestamp
        corrupt_path = f"{db_path}.corrupt.{datetime.now().strftime('%Y%m%d%H%M%S')}"
        try:
            if os.path.exists(db_path):
                os.replace(db_path, corrupt_path)
                print(f"Arquivo de banco corrompido detectado. Movido para: {corrupt_path}")
        except Exception as be:
            print(f"Falha ao mover arquivo corrompido: {be}")

        # Tenta recriar o banco limpo
        try:
            db = CaseDatabase(db_path)
            print("Banco recriado a partir do zero.")
            return db
        except Exception as re:
            print(f"Erro ao recriar o banco de dados: {re}")
            raise


def print_database_stats(db_path: str = "npc_cases.db") -> None:
    """
    Imprime estatísticas do banco de dados.
    Print database statistics.
    """
    with CaseDatabase(db_path) as db:
        stats = db.get_statistics()
        print("\n" + "="*50)
        print("ESTATÍSTICAS DO BANCO RBC")
        print("="*50)
        print(f"Total de casos: {stats.get('total_cases', 0)}")
        print(f"Média de recompensa: {stats.get('avg_reward', 0.0):.2f}")
        print(f"Taxa média de sucesso: {stats.get('avg_success_rate', 0):.2%}")
        print("="*50 + "\n")


if __name__ == "__main__":
    initialize_database(force_reset=False)
    print_database_stats()
