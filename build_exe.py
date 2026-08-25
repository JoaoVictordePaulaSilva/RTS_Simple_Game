"""
Script de automação para compilação do executável do jogo RTS Simple Game.
Compila a aplicação Python usando PyInstaller e copia as dependências de dados (npc_cases.db).
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

# Ajusta codificação de saída para UTF-8 no Windows se necessário
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

def build_executable():
    base_dir = Path(__file__).parent.resolve()
    dist_dir = base_dir / "dist"
    build_dir = base_dir / "build"
    db_file = base_dir / "npc_cases.db"
    
    print("==================================================")
    print("Iniciando compilação do RTS Simple Game...")
    print("==================================================")

    # Garante que o banco de dados exista (inicializa se necessário)
    if not db_file.exists():
        print("Banco de dados npc_cases.db não encontrado. Inicializando banco inicial...")
        try:
            from database.initializer import initialize_database
            initialize_database()
            print("Banco de dados inicializado com sucesso!")
        except Exception as e:
            print(f"Aviso ao inicializar banco de dados: {e}")

    # Comando PyInstaller
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--name=RTS_Simple_Game",
        "--noconsole",  # Janela de jogo sem terminal
        str(base_dir / "main.py")
    ]

    print(f"Executando comando: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(base_dir))

    if result.returncode != 0:
        print("\n[ERRO] Falha durante a compilação com PyInstaller!")
        sys.exit(result.returncode)

    print("\n[OK] Compilação do binário realizada com sucesso!")

    # Copiar npc_cases.db para a pasta dist/ junto ao executável
    if db_file.exists():
        dest_db = dist_dir / "npc_cases.db"
        shutil.copy2(db_file, dest_db)
        print(f"[OK] Banco de dados copiado para: {dest_db}")
    else:
        print("[AVISO] npc_cases.db não foi encontrado para cópia no dist/")

    print("==================================================")
    print(f"Executável pronto em: {dist_dir / 'RTS_Simple_Game.exe'}")
    print("==================================================")

if __name__ == "__main__":
    build_executable()
