# 🚀 Quick Start - Guia de Início Rápido

## Visão Geral

Este guia mostra como configurar o ambiente, inicializar o banco de dados de inteligência RBC e rodar a simulação do jogo.

---

## 3 Passos para Rodar a Aplicação

### 1. Instalar Dependências (1 min)

Abra o terminal no diretório do projeto e instale as bibliotecas necessárias:

```bash
pip install pygame psutil matplotlib
```

---

### 2. Inicializar o Banco de Dados (30 seg)

Execute o módulo de inicialização para verificar ou recriar a estrutura de tabelas SQLite e seed de conhecimento inicial:

```bash
python -m database.initializer
```

Você verá no console:
```text
==================================================
ESTATÍSTICAS DO BANCO RBC
==================================================
Total de casos: XXX
Média de recompensa: Y.YY
Taxa média de sucesso: ZZ.ZZ%
==================================================
```

---

### 3. Iniciar o Jogo (1 min)

Execute o ponto de entrada principal:

```bash
python main.py
```

---

## 🎮 Controles e Atalhos do Jogo

| Tecla / Ação | Função |
| :--- | :--- |
| **Seta Para Cima / Baixo** | Movimenta o tanque do jogador no eixo vertical |
| **Barra de Espaço** | Dispara projétil do jogador |
| **D** | Liga/Desliga o modo **Debug** no console |
| **F11 / Alt + Enter** | Alterna entre Tela Cheia e Modo Janela |
| **ESC** | Retorna ao Menu Principal / Cancela Login |

---

## 📊 Telemetria e Gráficos Automáticos

- **RBC Monitor Web**: Ao rodar o jogo, uma janela web local é iniciada exibindo em tempo real os logs de decisão do motor RBC.
- **Gráficos de Analytics**: Ao final de cada partida, o sistema gera automaticamente o arquivo `analytics/dashboard.png` com o histórico de recompensas, taxa de vitórias, crescimento da base de casos e eficiência de combate.

---

## ❓ Resolução de Problemas

1. **Módulo não encontrado (`ModuleNotFoundError`)**:
   Certifique-se de executar os comandos a partir da raiz do repositório (`RTS_Simple_Game`).
2. **Problemas com Pygame ou áudio**:
   Atualize o Pygame com `pip install --upgrade pygame`.
3. **Banco de dados corrompido**:
   Execute `python -m database.initializer` que o sistema detectará o erro e recriará o banco limpo automaticamente.
