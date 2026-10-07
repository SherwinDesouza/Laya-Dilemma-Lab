from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from config import EXPERIMENT_MODE
from simulation import simulation

app = FastAPI(title="Laya Multi-Agent Dilemma Experiment")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class StartRequest(BaseModel):
    mode: str = EXPERIMENT_MODE
    rounds: int = Field(default=500, ge=1, le=10000)
    seed: int = Field(default=42, ge=0)


@app.get("/api/config")
def config():
    return {
        "num_agents": 100,
        "default_rounds": 500,
        "modes": [
            {
                "id": "no_history",
                "name": "No history",
                "description": "Only the current game state is shown.",
            },
            {
                "id": "self_history",
                "name": "Self history",
                "description": "Each agent sees its own previous interactions.",
            },
            {
                "id": "both_history",
                "name": "Both histories",
                "description": "Each agent sees its own, its opponent's, and their direct interaction history.",
            },
        ],
    }


@app.post("/api/reset")
def reset(req: StartRequest):
    if req.mode not in {"no_history", "self_history", "both_history"}:
        raise HTTPException(status_code=400, detail="Invalid experiment mode.")
    simulation.reset(req.mode, req.rounds, req.seed)
    return simulation.snapshot()


@app.post("/api/start")
def start():
    simulation.start()
    return simulation.snapshot()


@app.post("/api/pause")
def pause():
    simulation.pause()
    return simulation.snapshot()


@app.get("/api/state")
def state():
    return simulation.snapshot()


@app.get("/api/agents/{agent_id}")
def agent(agent_id: int):
    if agent_id not in simulation.agents:
        raise HTTPException(status_code=404, detail="Agent not found.")
    return simulation.agent_detail(agent_id)
