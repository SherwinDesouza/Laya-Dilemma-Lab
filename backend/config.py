from typing import Literal

ExperimentMode = Literal["no_history", "self_history", "both_history"]

# Change this to switch experiments without changing the simulator.
EXPERIMENT_MODE: ExperimentMode = "no_history"

NUM_AGENTS = 10
DEFAULT_ROUNDS = 500
RANDOM_SEED = 42

# How many previous interactions to expose to the model.
# Keeping this bounded prevents history from eventually exceeding Laya's context.
HISTORY_WINDOW = 12

# How many simulation rounds the background worker processes between UI updates.
UI_UPDATE_EVERY = 1

# The payoff matrix follows the experiment description supplied for this project.
# Key: (your_action, opponent_action) -> (your_payoff, opponent_payoff)
PAYOFFS = {
    ("COOPERATE", "COOPERATE"): (50, 50),
    ("COOPERATE", "COMPETE"): (0, 100),
    ("COMPETE", "COOPERATE"): (100, 0),
    ("COMPETE", "COMPETE"): (20, 20),
}

LAYA_MODEL = "english"


def _you(action: str, opponent_action: str) -> int:
    return PAYOFFS[(action, opponent_action)][0]


def _them(action: str, opponent_action: str) -> int:
    return PAYOFFS[(action, opponent_action)][1]


def payoff_prompt() -> dict:
    """Structured payoffs from the deciding agent's point of view."""
    return {
        "unit": "points this round; higher is better for you",
        "outcomes": [
            {
                "you": "COOPERATE",
                "opponent": "COOPERATE",
                "your_payoff": _you("COOPERATE", "COOPERATE"),
                "opponent_payoff": _them("COOPERATE", "COOPERATE"),
                "for_you": "mutual reward",
            },
            {
                "you": "COOPERATE",
                "opponent": "COMPETE",
                "your_payoff": _you("COOPERATE", "COMPETE"),
                "opponent_payoff": _them("COOPERATE", "COMPETE"),
                "for_you": "punishment (you cooperated, they competed)",
            },
            {
                "you": "COMPETE",
                "opponent": "COOPERATE",
                "your_payoff": _you("COMPETE", "COOPERATE"),
                "opponent_payoff": _them("COMPETE", "COOPERATE"),
                "for_you": "reward (you competed, they cooperated)",
            },
            {
                "you": "COMPETE",
                "opponent": "COMPETE",
                "your_payoff": _you("COMPETE", "COMPETE"),
                "opponent_payoff": _them("COMPETE", "COMPETE"),
                "for_you": "mutual punishment",
            },
        ],
    }


def action_criteria() -> dict[str, str]:
    """Choice-head labels. Laya scores these strings, so payoffs must be in them."""
    return {
        "COOPERATE": (
            "Cooperate. "
            f"If the opponent also cooperates, you are rewarded {_you('COOPERATE', 'COOPERATE')} "
            f"and they get {_them('COOPERATE', 'COOPERATE')}. "
            f"If they compete, you are punished with {_you('COOPERATE', 'COMPETE')} "
            f"and they get {_them('COOPERATE', 'COMPETE')}."
        ),
        "COMPETE": (
            "Compete. "
            f"If the opponent cooperates, you are rewarded {_you('COMPETE', 'COOPERATE')} "
            f"and they are punished with {_them('COMPETE', 'COOPERATE')}. "
            f"If they also compete, you both take the mutual-punishment payoff "
            f"{_you('COMPETE', 'COMPETE')}."
        ),
    }
