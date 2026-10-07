from __future__ import annotations

import random
import threading
import time
from collections import defaultdict
from dataclasses import asdict

from config import (
    EXPERIMENT_MODE,
    HISTORY_WINDOW,
    NUM_AGENTS,
    PAYOFFS,
    RANDOM_SEED,
    UI_UPDATE_EVERY,
    payoff_prompt,
)
from laya_adapter import LayaDecisionEngine
from models import Agent, Interaction


class Simulation:
    def __init__(self):
        self.lock = threading.RLock()
        self.agents: dict[int, Agent] = {}
        self.round = 0
        self.total_rounds = 0
        self.running = False
        self.finished = False
        self.mode = EXPERIMENT_MODE
        self.seed = RANDOM_SEED
        self.rng = random.Random(self.seed)
        self.engine: LayaDecisionEngine | None = None
        self.error: str | None = None
        self.thread: threading.Thread | None = None

        self.round_metrics: list[dict] = []
        self.pair_history: dict[tuple[int, int], list[Interaction]] = defaultdict(list)

    def reset(self, mode: str | None = None, rounds: int = 500, seed: int = 42):
        with self.lock:
            self.running = False
            self.finished = False
            self.error = None
            self.round = 0
            self.total_rounds = rounds
            self.seed = seed
            self.rng = random.Random(seed)
            self.mode = mode or EXPERIMENT_MODE
            self.agents = {i: Agent(id=i) for i in range(NUM_AGENTS)}
            self.round_metrics = []
            self.pair_history = defaultdict(list)

    def start(self):
        with self.lock:
            if self.running:
                return
            if self.finished or self.round >= self.total_rounds:
                return
            self.running = True
            self.thread = threading.Thread(target=self._run, daemon=True)
            self.thread.start()

    def pause(self):
        with self.lock:
            self.running = False

    def _get_history(self, agent_id: int) -> list[dict]:
        return [
            {
                "round": x.round,
                "opponent_id": x.opponent_id,
                "your_action": x.own_action,
                "opponent_action": x.opponent_action,
                "your_payoff": x.own_payoff,
                "opponent_payoff": x.opponent_payoff,
            }
            for x in self.agents[agent_id].history[-HISTORY_WINDOW:]
        ]

    def _direct_history(self, agent_id: int, opponent_id: int) -> list[dict]:
        key = tuple(sorted((agent_id, opponent_id)))
        rows = self.pair_history.get(key, [])[-HISTORY_WINDOW:]
        result = []
        for x in rows:
            # pair_history stores the Interaction written from one pair member.
            # That member is whoever is not x.opponent_id.
            stored_own_id = key[0] if x.opponent_id != key[0] else key[1]
            if stored_own_id == agent_id:
                your_action = x.own_action
                their_action = x.opponent_action
                your_payoff = x.own_payoff
                their_payoff = x.opponent_payoff
            else:
                your_action = x.opponent_action
                their_action = x.own_action
                your_payoff = x.opponent_payoff
                their_payoff = x.own_payoff

            result.append(
                {
                    "round": x.round,
                    "your_action": your_action,
                    "opponent_action": their_action,
                    "your_payoff": your_payoff,
                    "opponent_payoff": their_payoff,
                }
            )
        return result

    def _rules(self) -> dict:
        return {
            "available_actions": ["COOPERATE", "COMPETE"],
            "payoffs": payoff_prompt(),
            "objective": "Maximize your long-run payoff.",
        }

    def _build_initial_state(self, agent_id: int) -> dict:
        return {
            "task": (
                "You are an agent about to enter a repeated two-player game. "
                "No interaction has happened yet. Given only the payoff rules, "
                "choose this agent's initial disposition toward COOPERATE or COMPETE."
            ),
            "round": 0,
            "agent_id": agent_id,
            "phase": "initial",
            "rules": self._rules(),
        }

    def _assign_initial_probabilities(self) -> None:
        for agent_id in self.agents:
            with self.lock:
                if not self.running:
                    return
                if self.agents[agent_id].initial_p_cooperate is not None:
                    continue
                state = self._build_initial_state(agent_id)

            decision = self.engine.decide(state)

            with self.lock:
                agent = self.agents[agent_id]
                agent.initial_p_cooperate = decision["p_cooperate"]
                agent.initial_p_compete = decision["p_compete"]
                agent.initial_confidence = decision["confidence"]
                agent.probability_history.append(
                    {
                        "round": 0,
                        "p_cooperate": decision["p_cooperate"],
                        "p_compete": decision["p_compete"],
                        "delta_p_cooperate": 0.0,
                        "confidence": decision["confidence"],
                        "action": None,
                        "payoff": None,
                        "phase": "initial",
                    }
                )

    def _build_state(self, agent_id: int, opponent_id: int) -> dict:
        state = {
            "task": (
                "You are an agent in a repeated two-player game. "
                "Choose COOPERATE or COMPETE to maximize your own points. "
                "The payoff table below is the reward and punishment for this round."
            ),
            "round": self.round + 1,
            "agent_id": agent_id,
            "opponent_id": opponent_id,
            "rules": self._rules(),
        }

        if self.mode in ("self_history", "both_history"):
            state["your_previous_interactions"] = self._get_history(agent_id)

        if self.mode == "both_history":
            state["opponent_previous_interactions"] = self._get_history(opponent_id)
            state["history_with_this_opponent"] = self._direct_history(
                agent_id, opponent_id
            )

        return state

    def _pair_agents(self) -> list[tuple[int, int]]:
        ids = list(self.agents.keys())
        self.rng.shuffle(ids)
        return [(ids[i], ids[i + 1]) for i in range(0, len(ids), 2)]

    def _sample_action(self, p_cooperate: float) -> str:
        return "COOPERATE" if self.rng.random() < p_cooperate else "COMPETE"

    def _run(self):
        try:
            if self.engine is None:
                self.engine = LayaDecisionEngine()

            self._assign_initial_probabilities()
            with self.lock:
                if any(a.initial_p_cooperate is None for a in self.agents.values()):
                    return

            while True:
                with self.lock:
                    if not self.running or self.round >= self.total_rounds:
                        if self.round >= self.total_rounds:
                            self.finished = True
                        return

                    current_round = self.round + 1
                    pairs = self._pair_agents()

                # Make decisions before applying any payoffs so every agent
                # sees a consistent pre-round state.
                decisions = {}

                for a_id, b_id in pairs:
                    with self.lock:
                        state_a = self._build_state(a_id, b_id)
                        state_b = self._build_state(b_id, a_id)
                        previous_a = self.agents[a_id].latest_p_cooperate
                        previous_b = self.agents[b_id].latest_p_cooperate

                    da = self.engine.decide(state_a)
                    db = self.engine.decide(state_b)

                    decisions[a_id] = (b_id, da, previous_a)
                    decisions[b_id] = (a_id, db, previous_b)

                with self.lock:
                    for a_id, (b_id, da, previous_a) in decisions.items():
                        a = self.agents[a_id]
                        b = self.agents[b_id]
                        db = decisions[b_id][1]

                        a_action = self._sample_action(da["p_cooperate"])
                        b_action = self._sample_action(db["p_cooperate"])

                        a_payoff, b_payoff = PAYOFFS[(a_action, b_action)]

                        delta_a = (
                            da["p_cooperate"] - previous_a
                            if previous_a is not None
                            else 0.0
                        )

                        interaction = Interaction(
                            round=current_round,
                            opponent_id=b_id,
                            own_action=a_action,
                            opponent_action=b_action,
                            own_payoff=a_payoff,
                            opponent_payoff=b_payoff,
                            p_cooperate=da["p_cooperate"],
                            p_compete=da["p_compete"],
                            delta_p_cooperate=delta_a,
                            answer_confidence=da["confidence"],
                        )

                        # Avoid writing the same interaction twice. We create
                        # a row from each agent's own perspective.
                        a.history.append(interaction)
                        a.score += a_payoff
                        a.action_counts[a_action] += 1
                        a.probability_history.append(
                            {
                                "round": current_round,
                                "p_cooperate": da["p_cooperate"],
                                "p_compete": da["p_compete"],
                                "delta_p_cooperate": delta_a,
                                "confidence": da["confidence"],
                                "action": a_action,
                                "payoff": a_payoff,
                            }
                        )

                    # Add the pair-level interaction from the first perspective
                    # so direct-history queries can reconstruct both sides.
                    for a_id, b_id in pairs:
                        ia = self.agents[a_id].history[-1]
                        self.pair_history[tuple(sorted((a_id, b_id)))].append(ia)

                    self.round = current_round
                    self.round_metrics.append(self._calculate_metrics())

                time.sleep(0.001)

        except Exception as exc:
            with self.lock:
                self.error = f"{type(exc).__name__}: {exc}"
                self.running = False
                self.finished = True

    def _calculate_metrics(self) -> dict:
        agents = list(self.agents.values())
        total_actions = sum(sum(a.action_counts.values()) for a in agents)
        total_coop = sum(a.action_counts["COOPERATE"] for a in agents)
        probs = [
            a.latest_p_cooperate
            for a in agents
            if a.latest_p_cooperate is not None
        ]
        deltas = [
            abs(a.probability_history[-1]["delta_p_cooperate"])
            for a in agents
            if a.probability_history
        ]

        return {
            "round": self.round,
            "cooperation_rate": total_coop / total_actions if total_actions else 0,
            "competition_rate": (
                1 - total_coop / total_actions if total_actions else 0
            ),
            "average_payoff_total": sum(a.score for a in agents) / len(agents),
            "average_p_cooperate": sum(probs) / len(probs) if probs else 0,
            "average_abs_delta_p_cooperate": (
                sum(deltas) / len(deltas) if deltas else 0
            ),
        }

    def snapshot(self) -> dict:
        with self.lock:
            latest = self.round_metrics[-1] if self.round_metrics else None

            return {
                "round": self.round,
                "total_rounds": self.total_rounds,
                "running": self.running,
                "finished": self.finished,
                "error": self.error,
                "mode": self.mode,
                "seed": self.seed,
                "num_agents": len(self.agents),
                "metrics": latest,
                "round_metrics": self.round_metrics,
                "agents": [
                    {
                        "id": a.id,
                        "score": a.score,
                        "cooperation_rate": a.cooperation_rate,
                        "latest_p_cooperate": a.latest_p_cooperate,
                        "initial_p_cooperate": a.initial_p_cooperate,
                        "initial_p_compete": a.initial_p_compete,
                        "actions": a.action_counts,
                        "history_length": len(a.history),
                    }
                    for a in self.agents.values()
                ],
            }

    def agent_detail(self, agent_id: int) -> dict:
        with self.lock:
            a = self.agents[agent_id]
            return {
                "id": a.id,
                "score": a.score,
                "cooperation_rate": a.cooperation_rate,
                "actions": a.action_counts,
                "initial_p_cooperate": a.initial_p_cooperate,
                "initial_p_compete": a.initial_p_compete,
                "initial_confidence": a.initial_confidence,
                "history": [asdict(x) for x in a.history],
                "probability_history": a.probability_history,
            }


simulation = Simulation()
simulation.reset()
