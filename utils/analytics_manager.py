"""
Módulo de Análise de Dados e Geração Automática de Gráficos (Analytics Manager).
Registra métricas por partida e gera dashboards visuais sem afetar a gameplay.
"""

import os
import csv
import time
import threading
from pathlib import Path
from typing import Dict, List, Optional

from database.case_database import CaseDatabase


class AnalyticsManager:
	"""
	Gerenciador de métricas e gráficos de desempenho do jogo e do NPC.
	Executa atualizações e geração de gráficos de forma assíncrona (headless).
	"""

	def __init__(self, db_path: str = "npc_cases.db", output_dir: str = "analytics") -> None:
		self.db_path = db_path
		self.output_dir = Path(output_dir)
		self.output_dir.mkdir(parents=True, exist_ok=True)
		self.csv_path = self.output_dir / "match_history.csv"

		self.start_time: float = 0.0
		self.initial_cases_count: int = 0
		self.match_rewards: List[float] = []
		self.match_damage_dealt: float = 0.0
		self.match_damage_taken: float = 0.0

		self._init_csv()

	def _init_csv(self) -> None:
		if not self.csv_path.exists():
			fieldnames = [
				"match_number", "session_id", "player_id", "timestamp",
				"duration_seconds", "duration_frames", "winner",
				"player_final_health", "npc_final_health",
				"npc_damage_dealt", "npc_damage_taken",
				"total_cases_count", "new_cases_created",
				"match_total_reward", "match_avg_reward",
				"overall_avg_reward", "npc_win_rate", "epsilon"
			]
			with open(self.csv_path, mode="w", newline="", encoding="utf-8") as f:
				writer = csv.writer(f)
				writer.writerow(fieldnames)

	def start_match(self, session_id: str = "default", player_id: str = "player") -> None:
		self.start_time = time.time()
		self.match_rewards = []
		self.match_damage_dealt = 0.0
		self.match_damage_taken = 0.0

		try:
			with CaseDatabase(self.db_path) as db:
				stats = db.get_statistics(player_id=player_id)
				self.initial_cases_count = stats.get("total_cases", 0)
		except Exception as e:
			print(f"[ANALYTICS] Erro ao obter contagem inicial de casos: {e}")
			self.initial_cases_count = 0

	def record_reward(self, reward: float) -> None:
		self.match_rewards.append(reward)

	def record_damage(self, dealt: float = 0.0, taken: float = 0.0) -> None:
		self.match_damage_dealt += dealt
		self.match_damage_taken += taken

	def record_match_end(
		self,
		session_id: str,
		player_id: str,
		winner: str,
		player_health: float,
		npc_health: float,
		duration_frames: int,
		duration_seconds: Optional[float] = None,
		epsilon: float = 0.0
	) -> None:
		if duration_seconds is None or duration_seconds <= 0:
			duration_seconds = max(0.1, time.time() - self.start_time)

		match_total_reward = sum(self.match_rewards)
		match_avg_reward = (match_total_reward / len(self.match_rewards)) if self.match_rewards else 0.0

		# Persistir no banco de dados e calcular métricas globais
		try:
			with CaseDatabase(self.db_path) as db:
				stats = db.get_statistics(player_id=player_id)
				total_cases_end = stats.get("total_cases", 0)
				overall_avg_reward = stats.get("avg_reward", 0.0)
				new_cases_created = max(0, total_cases_end - self.initial_cases_count)

				history = db.get_match_history()
				previous_matches = len(history)
				previous_wins = sum(1 for m in history if m.get("winner") == "NPC")
				current_win = 1 if winner == "NPC" else 0
				total_matches = previous_matches + 1
				npc_win_rate = (previous_wins + current_win) / total_matches

				match_data = {
					"match_number": total_matches,
					"session_id": session_id,
					"player_id": player_id,
					"duration_seconds": round(duration_seconds, 2),
					"duration_frames": duration_frames,
					"winner": winner,
					"player_final_health": max(0.0, player_health),
					"npc_final_health": max(0.0, npc_health),
					"npc_damage_dealt": round(self.match_damage_dealt, 2),
					"npc_damage_taken": round(self.match_damage_taken, 2),
					"total_cases_count": total_cases_end,
					"new_cases_created": new_cases_created,
					"match_total_reward": round(match_total_reward, 2),
					"match_avg_reward": round(match_avg_reward, 2),
					"overall_avg_reward": round(overall_avg_reward, 2),
					"npc_win_rate": round(npc_win_rate, 4),
					"epsilon": round(epsilon, 4),
				}

				db.insert_match_record(match_data)
				self._append_to_csv(match_data)

				# Disparar geração de gráficos em thread de segundo plano (silencioso e sem lag)
				thread = threading.Thread(
					target=self._generate_charts_async,
					args=(history + [match_data],),
					daemon=True
				)
				thread.start()

		except Exception as e:
			print(f"[ANALYTICS] Erro ao registrar fim de partida: {e}")

	def _append_to_csv(self, match_data: Dict) -> None:
		try:
			timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
			row = [
				match_data.get("match_number"),
				match_data.get("session_id"),
				match_data.get("player_id"),
				timestamp,
				match_data.get("duration_seconds"),
				match_data.get("duration_frames"),
				match_data.get("winner"),
				match_data.get("player_final_health"),
				match_data.get("npc_final_health"),
				match_data.get("npc_damage_dealt"),
				match_data.get("npc_damage_taken"),
				match_data.get("total_cases_count"),
				match_data.get("new_cases_created"),
				match_data.get("match_total_reward"),
				match_data.get("match_avg_reward"),
				match_data.get("overall_avg_reward"),
				match_data.get("npc_win_rate"),
				match_data.get("epsilon"),
			]
			with open(self.csv_path, mode="a", newline="", encoding="utf-8") as f:
				writer = csv.writer(f)
				writer.writerow(row)
		except Exception as e:
			print(f"[ANALYTICS] Erro ao salvar CSV: {e}")

	def _generate_charts_async(self, history: List[Dict]) -> None:
		"""Gera gráficos de desempenho usando Matplotlib sem interface visual."""
		try:
			import matplotlib
			matplotlib.use("Agg")  # Backend headless (sem GUI)
			import matplotlib.pyplot as plt

			if not history:
				return

			matches = [m.get("match_number", idx + 1) for idx, m in enumerate(history)]
			total_rewards = [m.get("match_total_reward", 0.0) for m in history]
			avg_rewards = [m.get("match_avg_reward", 0.0) for m in history]
			overall_avg_rewards = [m.get("overall_avg_reward", 0.0) for m in history]
			total_cases = [m.get("total_cases_count", 0) for m in history]
			new_cases = [m.get("new_cases_created", 0) for m in history]
			win_rates = [m.get("npc_win_rate", 0.0) * 100.0 for m in history]
			epsilons = [m.get("epsilon", 0.0) for m in history]
			damage_dealt = [m.get("npc_damage_dealt", 0.0) for m in history]
			damage_taken = [m.get("npc_damage_taken", 0.0) for m in history]

			# Estilo moderno e escuro para os gráficos
			plt.style.use("dark_background")
			fig, axs = plt.subplots(2, 2, figsize=(14, 10))
			fig.suptitle("Dashboard de Análise de Desempenho do NPC RBC", fontsize=16, fontweight="bold", color="#7dd3fc", y=0.98)

			bg_color = "#1e293b"
			card_color = "#0f172a"
			text_color = "#f8fafc"
			grid_color = "#334155"

			fig.patch.set_facecolor(bg_color)

			for ax in axs.flat:
				ax.set_facecolor(card_color)
				ax.grid(True, color=grid_color, linestyle="--", alpha=0.5)
				ax.tick_params(colors=text_color)
				for spine in ax.spines.values():
					spine.set_color(grid_color)

			# --- Painel 1: Recompensa por Partida ---
			ax1 = axs[0, 0]
			ax1.plot(matches, total_rewards, marker="o", color="#38bdf8", label="Recompensa Total Match", linewidth=2)
			ax1.plot(matches, overall_avg_rewards, linestyle="--", color="#facc15", label="Recompensa Média Global", linewidth=1.8)
			ax1.set_title("Recompensa do NPC por Partida", fontsize=12, color="#93c5fd", pad=8)
			ax1.set_xlabel("Número da Partida", color=text_color)
			ax1.set_ylabel("Reward", color=text_color)
			ax1.legend(loc="upper left", facecolor=card_color, edgecolor=grid_color)

			# --- Painel 2: Casos Criados ao Longo do Tempo ---
			ax2 = axs[0, 1]
			ax2_bar = ax2.twinx()
			ax2_bar.grid(False)
			bars = ax2_bar.bar(matches, new_cases, alpha=0.35, color="#a78bfa", label="Novos Casos Criados", width=0.4)
			line = ax2.plot(matches, total_cases, marker="s", color="#c084fc", label="Total de Casos na DB", linewidth=2)
			ax2.set_title("Crescimento da Base de Casos (CBR)", fontsize=12, color="#d8b4fe", pad=8)
			ax2.set_xlabel("Número da Partida", color=text_color)
			ax2.set_ylabel("Total de Casos (Acumulado)", color="#c084fc")
			ax2_bar.set_ylabel("Novos Casos na Partida", color="#a78bfa")
			ax2_bar.tick_params(colors="#a78bfa")

			# Unificar legenda
			lines, labels = ax2.get_legend_handles_labels()
			lines2, labels2 = ax2_bar.get_legend_handles_labels()
			ax2.legend(lines + lines2, labels + labels2, loc="upper left", facecolor=card_color, edgecolor=grid_color)

			# --- Painel 3: Taxa de Vitória & Epsilon ---
			ax3 = axs[1, 0]
			ax3_eps = ax3.twinx()
			ax3_eps.grid(False)
			ax3.plot(matches, win_rates, marker="^", color="#4ade80", label="Taxa de Vitória (%)", linewidth=2)
			ax3_eps.plot(matches, epsilons, linestyle=":", color="#fb923c", label="Epsilon (Exploração)", linewidth=2)
			ax3.set_title("Desempenho do NPC (Win Rate & Epsilon)", fontsize=12, color="#86efac", pad=8)
			ax3.set_xlabel("Número da Partida", color=text_color)
			ax3.set_ylabel("Taxa de Vitória (%)", color="#4ade80")
			ax3_eps.set_ylabel("Epsilon (Exploração)", color="#fb923c")
			ax3_eps.tick_params(colors="#fb923c")
			ax3.set_ylim(0, 105)
			ax3_eps.set_ylim(0, 1.05)

			lines3, labels3 = ax3.get_legend_handles_labels()
			lines3_eps, labels3_eps = ax3_eps.get_legend_handles_labels()
			ax3.legend(lines3 + lines3_eps, labels3 + labels3_eps, loc="center left", facecolor=card_color, edgecolor=grid_color)

			# --- Painel 4: Eficiência de Combate (Dano Causado vs Tomado) ---
			ax4 = axs[1, 1]
			width = 0.35
			x_indices = [m - width / 2 for m in matches]
			x_indices_taken = [m + width / 2 for m in matches]

			ax4.bar(x_indices, damage_dealt, width=width, color="#f43f5e", label="Dano Causado ao Player")
			ax4.bar(x_indices_taken, damage_taken, width=width, color="#fb7185", alpha=0.5, label="Dano Sofrido")
			ax4.set_title("Eficiência de Combate por Partida", fontsize=12, color="#fda4af", pad=8)
			ax4.set_xlabel("Número da Partida", color=text_color)
			ax4.set_ylabel("Dano Total", color=text_color)
			ax4.legend(loc="upper left", facecolor=card_color, edgecolor=grid_color)

			plt.tight_layout(rect=[0, 0, 1, 0.96])
			dashboard_path = self.output_dir / "dashboard.png"
			plt.savefig(dashboard_path, dpi=150, facecolor=bg_color)
			plt.close(fig)

		except Exception as e:
			print(f"[ANALYTICS] Erro ao gerar gráficos assíncronos: {e}")
