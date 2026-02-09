"""
Utilitário para inicializar e gerenciar banco de dados RBC.
Utility for initializing and managing RBC database.
"""

from database import CaseDatabase
from seed_cases import load_seed_cases


def initialize_database(db_path: str = "npc_cases.db", force_reset: bool = False) -> CaseDatabase:
    """
    Inicializa banco de dados com seed cases se vazio.
    Initialize database with seed cases if empty.
    
    Args:
        db_path: Caminho do banco de dados
        force_reset: Se True, recria banco do zero
        
    Returns:
        Instância de CaseDatabase inicializada
    """
    db = CaseDatabase(db_path)

    stats = db.get_statistics()
    
    if force_reset or stats["total_cases"] == 0:
        print("Carregando seed cases iniciais...")
        seed_cases = load_seed_cases()
        
        for case in seed_cases:
            db.insert_case(case)
        
        stats = db.get_statistics()
        print(f"✓ Banco inicializado com {stats['seed_cases']} seed cases")
    else:
        print(f"✓ Banco já possui {stats['total_cases']} casos")

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
