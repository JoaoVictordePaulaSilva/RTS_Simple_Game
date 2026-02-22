"""
Utilitário para inicializar e gerenciar banco de dados RBC.
Utility for initializing and managing RBC database.
"""
from pathlib import Path
from database import CaseDatabase
from seed_cases import load_seed_cases


def initialize_database(db_path: str = "npc_cases.db", force_reset: bool = False) -> CaseDatabase:
    
    if force_reset:
        Path(db_path).unlink(missing_ok=True)
        print("Banco resetado. Iniciando vazio.")

    db = CaseDatabase(db_path)
    return db


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
        print(f"Total de casos: {stats['total_cases']}")
        print(f"  - Seed cases: {stats['seed_cases']}")
        print(f"  - Casos aprendidos: {stats['learned_cases']}")
        print(f"Taxa média de sucesso: {stats['avg_success_rate']:.2%}")
        print("="*50 + "\n")


if __name__ == "__main__":
    initialize_database(force_reset=False)
    print_database_stats()
