import React, { useEffect, useMemo, useState } from "react";
import {
  Activity,
  ChevronRight,
  CirclePause,
  Download,
  FlaskConical,
  Play,
  RotateCcw,
  Search,
  Shield,
  Sparkles,
  Users,
  X,
} from "lucide-react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const API = "http://localhost:8000/api";

const pct = (x) => `${(Number(x || 0) * 100).toFixed(1)}%`;
const num = (x) => Number(x || 0).toFixed(1);

function Stat({ label, value, sub }) {
  return (
    <div className="stat">
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
      {sub && <div className="stat-sub">{sub}</div>}
    </div>
  );
}

function ModeCard({ mode, active, onClick }) {
  return (
    <button className={`mode-card ${active ? "active" : ""}`} onClick={onClick}>
      <div className="mode-dot">{active ? "●" : "○"}</div>
      <div>
        <div className="mode-title">{mode.name}</div>
        <div className="mode-desc">{mode.description}</div>
      </div>
    </button>
  );
}

function AgentTable({ agents, selected, onSelect }) {
  const [query, setQuery] = useState("");

  const filtered = useMemo(
    () =>
      agents.filter((a) =>
        String(a.id).includes(query.trim())
      ),
    [agents, query]
  );

  return (
    <section className="panel agents-panel">
      <div className="panel-head">
        <div>
          <div className="eyebrow">POPULATION</div>
          <h2>100 agents</h2>
        </div>
        <div className="search">
          <Search size={15} />
          <input
            placeholder="Find agent"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
      </div>

      <div className="agent-grid">
        {filtered.map((agent) => (
          <button
            key={agent.id}
            className={`agent-card ${selected === agent.id ? "selected" : ""}`}
            onClick={() => onSelect(agent.id)}
          >
            <div className="agent-top">
              <span>Agent {agent.id}</span>
              <ChevronRight size={14} />
            </div>
            <div className="agent-prob">
              {agent.latest_p_cooperate == null
                ? "—"
                : pct(agent.latest_p_cooperate)}
            </div>
            {agent.initial_p_cooperate != null && (
              <div className="agent-initial">
                initial {pct(agent.initial_p_cooperate)}
              </div>
            )}
            <div className="mini-track">
              <div
                style={{
                  width: `${(agent.latest_p_cooperate || 0) * 100}%`,
                }}
              />
            </div>
            <div className="agent-bottom">
              <span>{agent.actions.COOPERATE} C</span>
              <span>{agent.actions.COMPETE} X</span>
              <span>{agent.score} pts</span>
            </div>
          </button>
        ))}
      </div>
    </section>
  );
}

function AgentDrawer({ agentId, onClose }) {
  const [data, setData] = useState(null);

  useEffect(() => {
    if (agentId == null) return undefined;
    let timer;
    const poll = async () => {
      try {
        const res = await fetch(`${API}/agents/${agentId}`);
        setData(await res.json());
      } finally {
        timer = setTimeout(poll, 800);
      }
    };
    setData(null);
    poll();
    return () => clearTimeout(timer);
  }, [agentId]);

  if (agentId == null) return null;

  return (
    <aside className="drawer">
      <div className="drawer-head">
        <div>
          <div className="eyebrow">AGENT DETAIL</div>
          <h2>Agent {agentId}</h2>
        </div>
        <button className="icon-button" onClick={onClose}>
          <X size={18} />
        </button>
      </div>

      {!data ? (
        <div className="loading">Loading agent…</div>
      ) : (
        <>
          <div className="drawer-stats">
            <Stat label="Score" value={data.score} />
            <Stat label="Cooperate" value={pct(data.cooperation_rate)} />
            <Stat
              label="Initial P(C)"
              value={data.initial_p_cooperate == null ? "—" : pct(data.initial_p_cooperate)}
            />
            <Stat label="Decisions" value={data.history.length} />
          </div>

          <div className="chart-title">Probability over time</div>
          <div className="drawer-chart">
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={data.probability_history}>
                <CartesianGrid strokeDasharray="3 3" opacity={0.08} />
                <XAxis dataKey="round" tickLine={false} axisLine={false} />
                <YAxis
                  domain={[0, 1]}
                  tickFormatter={(v) => `${v * 100}%`}
                  tickLine={false}
                  axisLine={false}
                />
                <Tooltip
                  formatter={(v) => pct(v)}
                  contentStyle={{
                    background: "#15161a",
                    border: "1px solid #292b31",
                    borderRadius: 10,
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="p_cooperate"
                  stroke="#f2f2f2"
                  dot={false}
                  strokeWidth={2}
                  name="P(Cooperate)"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>

          <div className="chart-title">Decision history</div>
          <div className="history">
            {data.initial_p_cooperate != null && (
              <div className="history-row initial">
                <div className="action init">P0</div>
                <div className="history-main">
                  <b>Initial (Laya)</b>
                  <span>assigned before any round</span>
                </div>
                <div className="history-metric">
                  <b>P(C) {pct(data.initial_p_cooperate)}</b>
                  <span>P(X) {pct(data.initial_p_compete)}</span>
                </div>
              </div>
            )}
            {[...data.history].reverse().slice(0, 80).map((row) => (
              <div className="history-row" key={`${row.round}-${row.opponent_id}`}>
                <div className={`action ${row.own_action === "COOPERATE" ? "coop" : "comp"}`}>
                  {row.own_action === "COOPERATE" ? "C" : "X"}
                </div>
                <div className="history-main">
                  <b>Round {row.round}</b>
                  <span>vs Agent {row.opponent_id}</span>
                </div>
                <div className="history-metric">
                  <b>P(C) {pct(row.p_cooperate)}</b>
                  <span>P(X) {pct(row.p_compete)} · {row.own_payoff} pts</span>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </aside>
  );
}

export default function App() {
  const [config, setConfig] = useState(null);
  const [state, setState] = useState(null);
  const [mode, setMode] = useState("both_history");
  const [rounds, setRounds] = useState(500);
  const [seed, setSeed] = useState(42);
  const [selectedAgent, setSelectedAgent] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    fetch(`${API}/config`).then((r) => r.json()).then((x) => {
      setConfig(x);
      setMode(x.modes[2].id);
    });
  }, []);

  useEffect(() => {
    let timer;
    const poll = async () => {
      try {
        const res = await fetch(`${API}/state`);
        setState(await res.json());
      } finally {
        timer = setTimeout(poll, 800);
      }
    };
    poll();
    return () => clearTimeout(timer);
  }, []);

  const reset = async () => {
    setBusy(true);
    const res = await fetch(`${API}/reset`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mode, rounds: Number(rounds), seed: Number(seed) }),
    });
    setState(await res.json());
    setSelectedAgent(null);
    setBusy(false);
  };

  const start = async () => {
    await fetch(`${API}/start`, { method: "POST" });
  };

  const pause = async () => {
    await fetch(`${API}/pause`, { method: "POST" });
  };

  const exportData = () => {
    if (!state) return;
    const blob = new Blob([JSON.stringify(state, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `laya-${mode}-seed-${seed}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (!config || !state) {
    return <div className="loading-screen">Loading experiment…</div>;
  }

  const metrics = state.metrics || {
    cooperation_rate: 0,
    competition_rate: 0,
    average_payoff_total: 0,
    average_p_cooperate: 0,
    average_abs_delta_p_cooperate: 0,
  };

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark"><FlaskConical size={17} /></div>
          <span>Laya Dilemma Lab</span>
          <span className="version">100 AGENTS</span>
        </div>
        <div className="status">
          <span className={`status-dot ${state.running ? "live" : ""}`} />
          {state.error ? "Error" : state.running ? "Running" : state.finished ? "Complete" : "Ready"}
        </div>
      </header>

      <main className="layout">
        <section className="hero">
          <div>
            <div className="eyebrow">MULTI-AGENT EXPERIMENT</div>
            <h1>Does cooperation emerge?</h1>
            <p>
              Track how 100 Laya decision agents change their beliefs,
              actions and payoffs over repeated interactions.
            </p>
          </div>

          <div className="controls">
            <button className="primary" onClick={state.running ? pause : start}>
              {state.running ? <CirclePause size={16} /> : <Play size={16} />}
              {state.running ? "Pause" : "Run"}
            </button>
            <button className="secondary" onClick={reset} disabled={busy}>
              <RotateCcw size={15} />
              Reset
            </button>
            <button className="secondary" onClick={exportData}>
              <Download size={15} />
              Export
            </button>
          </div>
        </section>

        <section className="panel experiment-panel">
          <div className="panel-head">
            <div>
              <div className="eyebrow">EXPERIMENT CONDITION</div>
              <h2>What does each agent get to remember?</h2>
            </div>
            <div className="settings">
              <label>
                Rounds
                <input type="number" min="1" max="10000" value={rounds}
                  onChange={(e) => setRounds(e.target.value)} />
              </label>
              <label>
                Seed
                <input type="number" min="0" value={seed}
                  onChange={(e) => setSeed(e.target.value)} />
              </label>
            </div>
          </div>
          <div className="modes">
            {config.modes.map((m) => (
              <ModeCard key={m.id} mode={m} active={mode === m.id} onClick={() => {
                if (!state.running) setMode(m.id);
              }} />
            ))}
          </div>
        </section>

        {state.error && <div className="error">{state.error}</div>}

        <section className="stats-grid">
          <Stat label="ROUND" value={`${state.round} / ${state.total_rounds}`} />
          <Stat label="COOPERATION" value={pct(metrics.cooperation_rate)} sub="actual actions" />
          <Stat label="P(COOPERATE)" value={pct(metrics.average_p_cooperate)} sub="population mean" />
          <Stat label="AVG PAYOFF" value={num(metrics.average_payoff_total)} sub="per agent" />
          <Stat label="PROBABILITY MOVEMENT" value={num(metrics.average_abs_delta_p_cooperate)} sub="mean |ΔP| this round" />
        </section>

        <section className="panel chart-panel">
          <div className="panel-head">
            <div>
              <div className="eyebrow">POPULATION DYNAMICS</div>
              <h2>Belief vs behavior</h2>
            </div>
            <div className="legend">
              <span><i className="line-light" /> P(Cooperate)</span>
              <span><i className="line-dim" /> Actual cooperation</span>
            </div>
          </div>
          <div className="big-chart">
            <ResponsiveContainer width="100%" height={330}>
              <AreaChart data={state.round_metrics}>
                <defs>
                  <linearGradient id="fade" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopOpacity={0.16} />
                    <stop offset="100%" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" opacity={0.07} />
                <XAxis dataKey="round" tickLine={false} axisLine={false} />
                <YAxis
                  domain={[0, 1]}
                  tickFormatter={(v) => `${Math.round(v * 100)}%`}
                  tickLine={false}
                  axisLine={false}
                />
                <Tooltip
                  formatter={(v) => pct(v)}
                  contentStyle={{
                    background: "#15161a",
                    border: "1px solid #292b31",
                    borderRadius: 10,
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="average_p_cooperate"
                  stroke="#f4f4f5"
                  fill="url(#fade)"
                  strokeWidth={2}
                  name="P(Cooperate)"
                />
                <Line
                  type="monotone"
                  dataKey="cooperation_rate"
                  stroke="#777b85"
                  dot={false}
                  strokeWidth={2}
                  name="Actual cooperation"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </section>

        <AgentTable
          agents={state.agents}
          selected={selectedAgent}
          onSelect={setSelectedAgent}
        />

        <section className="bottom-note">
          <Shield size={15} />
          <span>
            Each agent only receives the information defined by the selected
            condition. The simulator records probabilities before sampling the
            actual action, so belief and behavior can be compared directly.
          </span>
        </section>
      </main>

      <AgentDrawer
        agentId={selectedAgent}
        onClose={() => setSelectedAgent(null)}
      />
    </div>
  );
}
