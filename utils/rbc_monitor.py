"""
Auxiliary RBC monitor window using Tkinter.
Shows live RBC stats while the match is running and final match conclusion.
"""

from __future__ import annotations

import queue
import threading
from typing import Dict, Optional, Union


class RBCMonitorWindow:
	def __init__(self) -> None:
		self._queue: "queue.Queue[tuple]" = queue.Queue()
		self._thread: Optional[threading.Thread] = None
		self._running = False
		self._enabled = True

	def start(self) -> None:
		if self._thread and self._thread.is_alive():
			return

		self._running = True
		self._thread = threading.Thread(target=self._run_ui, daemon=True)
		self._thread.start()

	def is_enabled(self) -> bool:
		return self._enabled

	def update_live(self, payload: Dict) -> None:
		if self._running and self._enabled:
			self._queue.put(("live", payload))

	def show_match_conclusion(self, payload: Dict) -> None:
		if self._running and self._enabled:
			self._queue.put(("conclusion", payload))

	def push_decision(self, line: Union[str, Dict]) -> None:
		if self._running and self._enabled:
			self._queue.put(("decision", line))

	def close(self) -> None:
		if self._running:
			self._running = False
			self._queue.put(("close", None))

	def _run_ui(self) -> None:
		try:
			import tkinter as tk
			from tkinter import ttk
		except Exception:
			self._enabled = False
			self._running = False
			return

		root = tk.Tk()
		root.title("RBC Monitor")
		root.geometry("620x430")
		root.configure(bg="#1e2733")

		style = ttk.Style(root)
		style.theme_use("clam")
		style.configure("Card.TFrame", background="#283242")
		style.configure("Title.TLabel", background="#283242", foreground="#dfe8f2", font=("Segoe UI", 11, "bold"))
		style.configure("Body.TLabel", background="#283242", foreground="#c8d4e2", font=("Segoe UI", 10))
		style.configure("Value.TLabel", background="#283242", foreground="#ffffff", font=("Segoe UI", 10, "bold"))
		style.configure("Status.TLabel", background="#1e2733", foreground="#9bc3ff", font=("Segoe UI", 10, "bold"))

		main = ttk.Frame(root, style="Card.TFrame", padding=12)
		main.place(x=12, y=12, width=596, height=396)

		ttk.Label(main, text="RBC - Tempo Real", style="Title.TLabel").grid(row=0, column=0, columnspan=2, sticky="w")

		status_label = ttk.Label(root, text="Aguardando partida...", style="Status.TLabel")
		status_label.place(x=14, y=390)

		labels = [
			"Jogador",
			"Casos armazenados",
			"Modo",
			"Epsilon",
			"Avg Reward",
			"Avg Success",
			"Conclusao",
		]

		self._value_labels = []

		for idx, label in enumerate(labels):
			ttk.Label(main, text=label + ":", style="Body.TLabel").grid(row=idx + 1, column=0, sticky="w", pady=2)
			val_lbl = ttk.Label(main, text='-', style="Value.TLabel")
			val_lbl.grid(row=idx + 1, column=1, sticky="e", pady=2)
			self._value_labels.append(val_lbl)

		ttk.Label(main, text="Decisoes do RBC:", style="Body.TLabel").grid(row=8, column=0, columnspan=2, sticky="w", pady=(8, 2))
		self._decision_text = tk.Text(
			main,
			height=8,
			width=74,
			bg="#141b25",
			fg="#a9f0be",
			insertbackground="#a9f0be",
			relief="flat",
			font=("Consolas", 9)
		)
		self._decision_text.grid(row=9, column=0, columnspan=2, sticky="we")
		self._decision_text.configure(state="disabled")

		decision_entries = []

		def render_decision_entries() -> None:
			self._decision_text.configure(state="normal")
			self._decision_text.delete("1.0", "end")
			for entry in decision_entries:
				if entry["count"] > 1:
					line = f"{entry['text']} ({entry['count']}x)"
				else:
					line = entry["text"]
				self._decision_text.insert("end", line + "\n")
			self._decision_text.see("end")
			self._decision_text.configure(state="disabled")

		def append_decision(payload) -> None:
			if isinstance(payload, dict):
				group_key = str(payload.get("group_key", "generic"))
				compact_text = str(payload.get("compact_text", payload.get("full_text", payload)))
			else:
				group_key = "generic"
				compact_text = str(payload)

			if decision_entries and decision_entries[-1]["key"] == group_key:
				decision_entries[-1]["count"] += 1
			else:
				decision_entries.append({
					"key": group_key,
					"text": compact_text,
					"count": 1,
				})

			if len(decision_entries) > 120:
				decision_entries.pop(0)

			render_decision_entries()

		def process_queue() -> None:
			if not self._running:
				try:
					root.destroy()
				except Exception:
					pass
				return

			while True:
				try:
					message_type, payload = self._queue.get_nowait()
				except queue.Empty:
					break

				if message_type == "close":
					self._running = False
					break

				if message_type == "live":
					stats = payload.get("stats", {})
					lang = payload.get("lang", "PT")
					in_game = payload.get("in_game", False)

					try:
						self._value_labels[0].config(text=str(stats.get("player_id", "-") or "-"))
						self._value_labels[1].config(text=str(stats.get("total_cases", 0)))
						self._value_labels[2].config(text=str(stats.get("mode", "-")))
						self._value_labels[3].config(text=f"{stats.get('epsilon', 0):.3f}")
						self._value_labels[4].config(text=f"{stats.get('avg_reward', 0):.2f}")
						self._value_labels[5].config(text=f"{stats.get('avg_success_rate', 0):.1%}")
					except Exception:
						pass

					if in_game:
						status_label.config(text=("Partida em andamento..." if lang == "PT" else "Match in progress..."))
					else:
						status_label.config(text=("Aguardando partida..." if lang == "PT" else "Waiting for match..."))

				elif message_type == "conclusion":
					lang = payload.get("lang", "PT")
					conclusion = payload.get("conclusion", "-")
					try:
						self._value_labels[6].config(text=conclusion)
						status_label.config(text=("Partida encerrada" if lang == "PT" else "Match ended"))
					except Exception:
						pass

				elif message_type == "decision":
					append_decision(payload)

			root.after(120, process_queue)

		root.after(120, process_queue)

		def on_close() -> None:
			self._enabled = False
			self._running = False
			try:
				root.destroy()
			except Exception:
				pass

		root.protocol("WM_DELETE_WINDOW", on_close)
		root.mainloop()
