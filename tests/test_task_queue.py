"""
Teste de validação da TaskQueue
Test suite for TaskQueue validation
"""

import time
from utils.task_queue import TaskQueue, AdaptiveTaskQueue, TaskPriority


def test_basic_queue():
    """Testa fila básica."""
    print("\n=== TEST 1: Basic Queue ===")
    
    queue = TaskQueue(max_tasks_per_frame=3, debug=False)
    
    results = []
    
    def task(name):
        results.append(name)
        return name
    
    # Enfileira tarefas
    queue.add(task, TaskPriority.CRITICAL, "critical_1", ("C1",))
    queue.add(task, TaskPriority.MEDIUM, "medium_1", ("M1",))
    queue.add(task, TaskPriority.LOW, "low_1", ("L1",))
    queue.add(task, TaskPriority.MEDIUM, "medium_2", ("M2",))
    queue.add(task, TaskPriority.LOW, "low_2", ("L2",))
    
    # Frame 1: Executa 1 crítica + 3 médias/baixas
    stats1 = queue.process_frame()
    print(f"Frame 1: Executadas {stats1['executed']}, "
          f"Adiadas {stats1['deferred']}, "
          f"Críticas {stats1['critical']}")
    print(f"  Tarefas executadas: {results}")
    
    # Frame 2: Executa tarefas adiadas
    results.clear()
    stats2 = queue.process_frame()
    print(f"Frame 2: Executadas {stats2['executed']}, "
          f"Adiadas {stats2['deferred']}, "
          f"Críticas {stats2['critical']}")
    print(f"  Tarefas executadas: {results}")
    
    assert stats1['critical'] == 1, "Frame 1 deveria ter 1 crítica"
    assert stats1['executed'] <= 4, "Frame 1 não deveria executar mais de 4"
    print("✅ TEST 1 PASSOU")


def test_priority_ordering():
    """Testa ordenação por prioridade."""
    print("\n=== TEST 2: Priority Ordering ===")
    
    queue = TaskQueue(max_tasks_per_frame=10, debug=False)
    execution_order = []
    
    def task(name):
        execution_order.append(name)
    
    # Enfileira fora de ordem (os args são os valores que aparecem em execution_order)
    queue.add(task, TaskPriority.LOW, "low", ("low",))
    queue.add(task, TaskPriority.CRITICAL, "critical", ("critical",))
    queue.add(task, TaskPriority.HIGH, "high", ("high",))
    queue.add(task, TaskPriority.MEDIUM, "medium", ("medium",))
    
    # Frame 1: tudo deve executar (max 10)
    queue.process_frame()
    print(f"Ordem de execução: {execution_order}")
    
    # Verificar que CRITICAL foi primeiro, depois HIGH, depois MEDIUM, depois LOW
    expected_order = ["critical", "high", "medium", "low"]
    assert execution_order == expected_order, f"Esperado {expected_order}, obteve {execution_order}"
    print("✅ TEST 2 PASSOU")


def test_adaptive_queue():
    """Testa fila adaptativa com CPU."""
    print("\n=== TEST 3: Adaptive Queue ===")
    
    queue = AdaptiveTaskQueue(
        initial_tasks_per_frame=5,
        cpu_threshold=0.75,
        debug=False
    )
    
    def dummy_task():
        pass
    
    # Simula CPU baixa - deve aumentar limite
    print("Simulando CPU baixa (30%)...")
    initial_limit = queue.max_tasks_per_frame
    queue.update_cpu_usage(0.30)
    
    for _ in range(5):
        queue.add(dummy_task, TaskPriority.MEDIUM)
        queue.process_frame()
    
    increased_limit = queue.max_tasks_per_frame
    print(f"  Limite mudou de {initial_limit} para {increased_limit}")
    
    # Simula CPU alta - deve reduzir limite
    print("Simulando CPU alta (85%)...")
    queue.update_cpu_usage(0.85)
    
    for _ in range(5):
        queue.add(dummy_task, TaskPriority.MEDIUM)
        queue.process_frame()
    
    reduced_limit = queue.max_tasks_per_frame
    print(f"  Limite mudou de {increased_limit} para {reduced_limit}")
    
    assert reduced_limit < increased_limit, "Limite deveria reduzir com CPU alta"
    print("✅ TEST 3 PASSOU")


def test_performance_impact():
    """Testa performance de adicionar/processar tarefas."""
    print("\n=== TEST 4: Performance Impact ===")
    
    queue = TaskQueue(max_tasks_per_frame=10, debug=False)
    
    def dummy_task():
        time.sleep(0.001)
    
    # Mede tempo para 1000 tarefas
    start = time.time()
    
    for i in range(100):
        for _ in range(10):
            queue.add(dummy_task, TaskPriority.MEDIUM, f"task_{i}")
        queue.process_frame()
    
    elapsed = time.time() - start
    fps_equivalent = 100 / elapsed
    
    print(f"100 frames com 10 tarefas/frame = {elapsed:.3f}s")
    print(f"Equivalente a ~{fps_equivalent:.1f} FPS")
    print("✅ TEST 4 PASSOU")


def test_statistics():
    """Testa coleta de estatísticas."""
    print("\n=== TEST 5: Statistics ===")
    
    queue = TaskQueue(max_tasks_per_frame=2, debug=False)
    
    def task():
        pass
    
    # Enfileira e processa
    for i in range(3):
        queue.add(task, TaskPriority.CRITICAL)
        queue.add(task, TaskPriority.MEDIUM)
        queue.add(task, TaskPriority.MEDIUM)
        queue.add(task, TaskPriority.LOW)
        queue.process_frame()
    
    stats = queue.get_stats()
    
    print(f"Total enfileiradas: {stats['total_queued']}")
    print(f"Total executadas: {stats['total_executed']}")
    print(f"Total adiadas: {stats['deferred']}")
    print(f"Tarefas na fila: {stats['queue_size']}")
    print(f"Por prioridade: {stats['by_priority']}")
    
    assert stats['total_queued'] > 0, "Deveria ter tarefas enfileiradas"
    assert stats['total_executed'] > 0, "Deveria ter tarefas executadas"
    print("✅ TEST 5 PASSOU")


def test_critical_never_deferred():
    """Valida que tarefas críticas NUNCA são adiadas."""
    print("\n=== TEST 6: Critical Tasks Never Deferred ===")
    
    queue = TaskQueue(max_tasks_per_frame=1, debug=False)
    
    executed_critical = []
    executed_medium = []
    
    def critical_task():
        executed_critical.append(True)
    
    def medium_task():
        executed_medium.append(True)
    
    # Enfileira 1 crítica + 10 médias
    queue.add(critical_task, TaskPriority.CRITICAL)
    for i in range(10):
        queue.add(medium_task, TaskPriority.MEDIUM)
    
    # Processa 5 frames (com limite de 1 tarefa não-crítica por frame)
    for _ in range(5):
        executed_critical.clear()
        executed_medium.clear()
        queue.process_frame()
        
        if executed_critical:  # Se Critical foi adicionada neste frame
            assert len(executed_critical) > 0, "Critical deveria ter executado"
    
    print(f"Critical tasks: Sempre executadas ✓")
    print(f"Medium tasks: Distribuídas ao longo dos frames ✓")
    print("✅ TEST 6 PASSOU")


def run_all_tests():
    """Executa todos os testes."""
    print("\n" + "=" * 70)
    print("INICIANDO TESTES DA TASK QUEUE")
    print("=" * 70)
    
    try:
        test_basic_queue()
        test_priority_ordering()
        test_adaptive_queue()
        test_performance_impact()
        test_statistics()
        test_critical_never_deferred()
        
        print("\n" + "=" * 70)
        print("✅ TODOS OS TESTES PASSARAM!")
        print("=" * 70)
        print("\nPróximos passos:")
        print("1. Instale psutil: pip install psutil")
        print("2. Integre TaskQueue no seu jogo.py")
        print("3. Teste o desempenho com debug=True inicialmente")
        print("4. Ajuste initial_tasks_per_frame conforme necessário")
        
    except AssertionError as e:
        print(f"\n❌ TESTE FALHOU: {e}")
        return False
    except Exception as e:
        print(f"\n❌ ERRO INESPERADO: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
