from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Interaction:
    round: int
    opponent_id: int
    own_action: str
    opponent_action: str
    own_payoff: int
    opponent_payoff: int
    p_cooperate: float
    p_compete: float
    delta_p_cooperate: float
    answer_confidence: float
    direct: bool = True


@dataclass
class Agent:
    id: int
    score: int = 0
    history: list[Interaction] = field(default_factory=list)
    probability_history: list[dict] = field(default_factory=list)
    action_counts: dict[str, int] = field(
        default_factory=lambda: {"COOPERATE": 0, "COMPETE": 0}
    )
    initial_p_cooperate: Optional[float] = None
    initial_p_compete: Optional[float] = None
    initial_confidence: Optional[float] = None

    @property
    def cooperation_rate(self) -> float:
        total = sum(self.action_counts.values())
        return self.action_counts["COOPERATE"] / total if total else 0.0

    @property
    def latest_p_cooperate(self) -> Optional[float]:
        if not self.probability_history:
            return None
        return self.probability_history[-1]["p_cooperate"]
