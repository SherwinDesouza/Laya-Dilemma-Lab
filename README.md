# Laya Multi-Agent Cooperation Experiment

A 100-agent repeated decision-game experiment using the open-weight Laya System 1 decision model.

## What this project does

It simulates 100 persistent agents. Every round, each agent is paired with another agent and asks Laya to choose:

- `COOPERATE`
- `COMPETE`

The simulator records:

- action probabilities (`P(cooperate)`, `P(compete)`)
- sampled action
- payoff
- opponent
- own history
- opponent history as seen by the agent
- change in cooperation probability
- confidence
- population-level cooperation/competition rates
- average payoff
- probability volatility

The web UI lets you inspect the whole population and drill into an individual agent.

## Three experiments

The source switch is in `backend/config.py`:

```python
EXPERIMENT_MODE = "no_history"
```

Allowed values:

```text
no_history
self_history
both_history
```

### 1. no_history

The model only receives the current game state.

### 2. self_history

The model receives the agent's own previous interactions.

### 3. both_history

The model receives:
- the agent's own history
- the current opponent's history
- the direct interaction history between the two agents

The agent does NOT receive the private histories of unrelated agents.

## Important payoff note

The default matrix is intentionally based on the payoff description from the experiment brief:

| You | Opponent | You | Opponent |
|---|---|---:|---:|
| COOPERATE | COOPERATE | 100 | 100 |
| COOPERATE | COMPETE | 0 | 100 |
| COMPETE | COOPERATE | 100 | 0 |
| COMPETE | COMPETE | 100 | 100 |

Change `PAYOFFS` in `backend/config.py` if you want a canonical Prisoner's Dilemma matrix instead.

## Requirements

- Python 3.11+
- Node.js 20+
- A machine capable of running Laya
- First Laya model download requires Hugging Face access
- GPU is strongly recommended for faster experiments; CPU works but will be slower

Laya is open-weight/self-hosted and its current SDK supports structured `choice` outputs with probabilities. See:
https://github.com/LeonaDavinci/laya-system-one

## Backend

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt

python -m uvicorn app:app --reload --port 8000
```

The backend downloads the Laya checkpoint the first time it is needed.

For an NVIDIA GPU, you can optionally set:

```bash
set LAYA_DEVICE=cuda
```

or on Linux/macOS:

```bash
export LAYA_DEVICE=cuda
```

The Laya Python package itself can auto-select the available device.

## Frontend

```bash
cd frontend
npm install
npm run dev
```

Open the Vite URL shown in the terminal, normally:

http://localhost:5173

## Running an experiment

Use the UI:

1. Choose the experiment mode.
2. Set the number of rounds.
3. Press Start.
4. Watch the population evolve.
5. Click an agent to inspect its history.

You can pause, resume, reset, and export the experiment as JSON.

## Reproducibility

The simulator has a configurable random seed. The seed controls:

- initial pairing
- action sampling
- pairing randomness

Laya inference itself is deterministic for a fixed model/device/input in normal use.

## Metrics

The dashboard tracks:

- cooperation rate
- competition rate
- average payoff
- average P(cooperate)
- average P(compete)
- average absolute probability change
- average probability change
- payoff distribution
- action distribution
- per-agent probability trajectory
- per-agent payoff trajectory

## Suggested research workflow

Run the same seed and number of rounds for:

1. `no_history`
2. `self_history`
3. `both_history`

Then compare the exported JSON files.

A useful first run is:

- 100 agents
- 500 rounds
- seed 42

For more stable results, repeat each condition with several seeds.

## Architecture

```text
React frontend
      |
      | REST + polling
      v
FastAPI simulation server
      |
      +---- Simulation engine
      |        |
      |        +---- 100 Agent state objects
      |        +---- pairing
      |        +---- payoff calculation
      |        +---- metrics
      |
      +---- Laya adapter
               |
               v
        Laya decision model
```

The experiment is intentionally designed so the game simulator does not depend on the UI.
