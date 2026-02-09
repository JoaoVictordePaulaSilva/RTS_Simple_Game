# Quick Start - RBC System

## 🚀 Começando Rápido

### 1️⃣ Primeira Execução

```bash
cd "d:\Projetos Facul\TCC\RTS em Pygames"
python jogo.py
```

**O que acontece automaticamente:**
- ✅ Verifica se `npc_cases.db` existe
- ✅ Se não existe, cria com 7 seed cases
- ✅ NPC começa a aprender imediatamente

### 2️⃣ Jogar

**Controles:**
- ⬆️ Seta para cima: Mover tanque para cima
- ⬇️ Seta para baixo: Mover tanque para baixo
- ⬅️ Seta esquerda: Rotacionar contra-relógio
- ➡️ Seta direita: Rotacionar no sentido do relógio
- 🔫 Espaço: Disparar

**Menu:**
- Escolha dificuldade (Easy/Normal/Hard)
- Veja estatísticas RBC após cada jogo
- Jogue quantas vezes quiser - NPC aprende!

### 3️⃣ Entender o Aprendizado

Cada jogo:
```
├─ NPC toma ações
├─ Você as avalia (sucesso/fracasso)
├─ RBC aprende e armazena no BD
└─ Próximo jogo: NPC usa o conhecimento
```

---

## 📊 Estatísticas Visíveis

Na tela de Game Over você verá:
```
RBC Statistics
━━━━━━━━━━━━━━━━
Total Cases: 12
Seed: 7 | Learned: 5
Avg Success: 68.5%
```

- **Total Cases**: Todos os casos conhecidos
- **Seed**: Casos iniciais (você não modifica)
- **Learned**: Casos que o NPC aprendeu jogando
- **Avg Success**: Taxa média de sucesso

Ao longo do tempo:
```
Jogo 1:  Total: 7  (só seed cases)
Jogo 2:  Total: 15 (7 seed + 8 aprendidos)
Jogo 5:  Total: 40 (7 seed + 33 aprendidos)
Jogo 10: Total: 80 (7 seed + 73 aprendidos)
```

---

## 🧠 Como o RBC Funciona

### Passo 1: Codificação
NPC vê estado atual:
```
Jogador a 120px, 25° diferença, ambos com 100 HP
→ PROBLEMA: {distance: 120, angle_diff: 25, npc_health: 100, player_health: 100}
```

### Passo 2: Recuperação
RBC busca casos similares no BD:
```
Casos no BD similares a este:
├─ Caso A (dist: 110, angle: 20) - 95% similaridade → DISPARAR
├─ Caso B (dist: 130, angle: 30) - 92% similaridade → ALINHAR_E_DISPARAR
└─ Caso C (dist: 100, angle: 15) - 89% similaridade → DISPARAR
```

### Passo 3: Adaptação
Adapta melhor caso:
```
Melhor caso: "A" (disparar)
  Ângulo no caso A: 20°
  Ângulo agora: 25°
  Diferença: +5°
  → Ajusta para compensar
```

### Passo 4: Execução
Executa a ação adaptada:
```
NPC → DISPARA (com ajuste de +3°)
```

### Passo 5: Aprendizado
Resultado registrado:
```
❌ ERROU! Jogador desviou
  → Armazena novo caso: "Situação parecida, action errou"
  → Próxima vez, considerará outras ações também
```

---

## 🎯 Casos Seed (Iniciais)

Os 7 casos que começam no BD:

| # | Distância | Ângulo | Situação | Ação | Taxa Sucesso |
|---|-----------|--------|----------|------|--------------|
| 1 | 80 px | 8° | Muito próximo, alinhado | DISPARAR | 95% |
| 2 | 200 px | 25° | Médio alcance | ALINHAR_E_DISPARAR | 80% |
| 3 | 350 px | 40° | Longo alcance | PERSEGUIR | 70% |
| 4 | 400 px | 60° | Alvo perdido | BUSCAR | 50% |
| 5 | 200 px | 35° | NPC ferido | PERSEGUIR (defensivo) | 65% |
| 6 | 150 px | 15° | Modo Fácil | ALINHAR_E_DISPARAR | 88% |
| 7 | 120 px | 45° | Modo Difícil | PERSEGUIR (evasivo) | 72% |

---

## 🔧 Personalizar Sistema

### Adicionar Novo Seed Case

Edite `seed_cases.py`:
```python
SEED_CASES = [
    # ... casos existentes ...
    {
        "case_id": "seed_custom_close",
        "problem_distance": 90.0,
        "problem_angle_diff": 5.0,  # Muito alinhado
        "problem_npc_health": 100.0,
        "problem_player_health": 100.0,
        "problem_player_visible": 1,
        "problem_frames_lost": 0,
        "solution_action": "fire",
        "solution_params": '{"angle_adjustment": 0}',
        "result_success": 1,
        "result_damage_dealt": 25.0,
        "result_damage_taken": 0.0,
        "result_outcome": "hit",
        "difficulty": "Normal",
        "created_by": "seed",
        "success_rate": 0.98,  # Muito confiável
    },
]
```

### Resetar Banco (Começar do Zero)

```bash
python db_init.py --force-reset
```

Isso:
- Deleta `npc_cases.db`
- Recria com 7 seed cases apenas
- Limpa todo aprendizado

### Visualizar Banco

```bash
python db_init.py
```

Mostra:
```
==================================================
ESTATÍSTICAS DO BANCO RBC
==================================================
Total de casos: 7
  - Seed cases: 7
  - Casos aprendidos: 0
Taxa média de sucesso: 0.00%
==================================================
```

---

## 🧪 Testar Sistema

```bash
python test_rbc.py
```

Resultado esperado:
```
==================================================
EXECUTANDO TESTES DO SISTEMA RBC
==================================================

✓ Testando inicialização do banco...
  ✓ Banco inicializa corretamente
✓ Testando inserção de casos...
  ✓ Casos inserem corretamente
✓ Testando cálculo de similaridade...
  ✓ Similaridade calcula corretamente
✓ Testando motor RBC...
  ✓ Motor RBC funciona corretamente
✓ Testando cérebro do NPC...
  ✓ Cérebro do NPC funciona corretamente

==================================================
RESULTADOS: 5 passou(ram), 0 falhou/falharam
==================================================
```

---

## 📈 Observar Evolução

### Método 1: Jogar Múltiplas Vezes

Jogue 10 jogos seguidos:
```
Jogo 1: Total Cases: 7    Avg Success: 0%
Jogo 2: Total Cases: 15   Avg Success: 45%
Jogo 3: Total Cases: 22   Avg Success: 52%
Jogo 4: Total Cases: 29   Avg Success: 58%
...
Jogo 10: Total Cases: 70  Avg Success: 72%
```

Você verá o NPC melhorar!

### Método 2: Usar Script Python

```python
from database import CaseDatabase

db = CaseDatabase("npc_cases.db")
stats = db.get_statistics()
print(f"Total: {stats['total_cases']}")
print(f"Taxa sucesso: {stats['avg_success_rate']:.1%}")
db.close()
```

---

## 🎮 Dificuldades e Comportamento

### Easy (Fácil)
- NPC dispara com menos frequência
- NPC tem 80 HP, você tem 140 HP
- Ideal para aprender controles

### Normal (Normal)
- Equilíbrio entre ataque e defesa
- Ambos com 100 HP
- Recomendado para explorar RBC

### Hard (Difícil)
- NPC dispara muito frequentemente
- NPC tem 140 HP, você tem 80 HP
- Ideal para ver RBC em ação avançada

---

## ❓ FAQ

**P: Posso deletar o banco?**
R: Sim! Execute `python db_init.py --force-reset` para começar do zero.

**P: Onde fica o banco?**
R: Em `npc_cases.db` (mesma pasta do jogo).

**P: Quanto tempo leva para o NPC aprender?**
R: Ele aprende imediatamente! A cada jogo, ganha ~10-20 novos casos.

**P: O NPC melhora mesmo?**
R: Sim! A taxa de sucesso aumenta gradualmente nos primeiros 10-20 jogos.

**P: Posso exportar os casos?**
R: Ainda não, mas é possível adicionar isso futuramente.

**P: Como adicionar novos tipos de ação?**
R: Edite `npc_brain.py` e `_generate_fallback_action()`.

---

## 📞 Suporte

Se algo não funcionar:

1. Verifique se tem Python 3.8+
2. Verifique se tem pygame: `pip install pygame`
3. Delete `npc_cases.db` e tente novamente
4. Rode `python test_rbc.py` para verificar sistema

---

**Bom jogo e bom aprendizado do NPC! 🤖**

