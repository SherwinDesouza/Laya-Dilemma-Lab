from __future__ import annotations

from typing import Any

import laya

from config import LAYA_MODEL, action_criteria


class LayaDecisionEngine:
    """
    Thin adapter around Laya.

    We use a two-option typed choice instead of free-form text generation.
    The simulator receives the complete probability distribution and samples
    an action from it.
    """

    def __init__(self) -> None:
        self.agent = laya.load("convaiinnovations/laya", subfolder="typed-decisions")

    def decide(self, state: dict[str, Any]) -> dict[str, Any]:
        questions = {
            "action": {
                "type": "choice",
                "instructions": "Which action should the agent take in this interaction?",
                "criteria": action_criteria(),
            }
        }

        result = self.agent.predict(state, questions)
        answer = result["answers"]["action"]

        probabilities = answer.get("probabilities", {})
        p_cooperate = float(probabilities.get("COOPERATE", 0.0))
        p_compete = float(probabilities.get("COMPETE", 0.0))

        # Defensive normalization in case a model/client version returns
        # slightly different floating-point totals.
        total = p_cooperate + p_compete
        if total <= 0:
            p_cooperate = p_compete = 0.5
        else:
            p_cooperate /= total
            p_compete /= total

        confidence = float(
            answer.get(
                "answer_confidence",
                answer.get("confidence", max(p_cooperate, p_compete)),
            )
        )

        return {
            "p_cooperate": p_cooperate,
            "p_compete": p_compete,
            "confidence": confidence,
            "raw": result,
        }
