# RTS Tanks - Pygame Demo

## PT-BR

Demo RTS minimalista e profissional implementada em um único arquivo `jogo.py`.

### Recursos
- Dois tanques: jogador (esquerda) e NPC (direita)
- Tanques se movem apenas no eixo Y e podem rotacionar livremente
- Controles do jogador: Setas (Cima/Baixo movimento, Esquerda/Direita rotação), `Espaço` para disparar
- Menu, Opções (dificuldade e velocidade de projéteis), Jogabilidade e tela de Game Over
- **Novo**: Sistema de percepção do NPC - o inimigo vê o que você faz e reage
- **Novo**: Caixa de status mostrando o que o NPC está percebendo
- **Novo**: Movimento limitado à arena (tanques não saem da caixa cinza)

### Requisitos
- Python 3.8+
- `pygame` (listado em `requirements.txt`)

### Início rápido (Windows PowerShell)
```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python jogo.py
```

---

## EN

Minimal, professional-but-simple RTS-like demo implemented in a single `jogo.py` file.

### Features
- Two tanks: player (left) and NPC (right)
- Tanks move only on Y axis and can rotate freely
- Player controls: Arrow keys (Up/Down move, Left/Right rotate), `Space` to fire
- Menu, Options (difficulty and projectile speed), Gameplay and Game Over screen
- **New**: NPC perception system - the enemy sees what you do and reacts
- **New**: Status box showing what the NPC is perceiving
- **New**: Movement limited to arena (tanks stay within gray box)

### Requirements
- Python 3.8+
- `pygame` (listed in `requirements.txt`)

### Quick start (Windows PowerShell)
```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python jogo.py
```