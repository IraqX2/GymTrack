import { useEffect, useState } from "react";

type HealthResponse = { status: string; service: string };
type HelloResponse = { message: string };

const modules = [
  { title: "Members", description: "Maintain gym member records.", icon: "♙" },
  { title: "Trainers", description: "Organize trainers and assignments.", icon: "♧" },
  { title: "Memberships", description: "Track membership plans and status.", icon: "▤" },
  { title: "Attendance", description: "Record daily gym check-ins.", icon: "◷" },
  { title: "Workout plans", description: "Plan exercises and track progress.", icon: "⌁" }
];

export default function App() {
  const [apiStatus, setApiStatus] = useState("Checking...");
  const [name, setName] = useState("GymTrack");
  const [apiMessage, setApiMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    fetch("/api/health")
      .then((response) => {
        if (!response.ok) throw new Error("API unavailable");
        return response.json() as Promise<HealthResponse>;
      })
      .then((data) => setApiStatus(data.status === "ok" ? "Connected" : "Unknown"))
      .catch(() => setApiStatus("Not connected"));
  }, []);

  async function testApi() {
    setApiMessage("");
    setError("");
    try {
      const params = new URLSearchParams({ name: name.trim() || "World" });
      const response = await fetch(`/api/hello?${params.toString()}`);
      if (!response.ok) throw new Error("Request failed");
      const data = (await response.json()) as HelloResponse;
      setApiMessage(data.message);
    } catch {
      setError("Could not reach FastAPI. Start the backend on port 8000 and try again.");
    }
  }

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="brand"><span className="brand-icon">GT</span><div><strong>GymTrack</strong><small>Management console</small></div></div>
        <p className="nav-label">WORKSPACE</p>
        <a className="nav-link active" href="#overview">▦ &nbsp; Overview</a>
        <a className="nav-link" href="#modules">♙ &nbsp; Members</a>
        <a className="nav-link" href="#modules">♧ &nbsp; Trainers</a>
        <a className="nav-link" href="#modules">▤ &nbsp; Memberships</a>
        <a className="nav-link" href="#modules">◷ &nbsp; Attendance</a>
        <a className="nav-link" href="#modules">⌁ &nbsp; Workout plans</a>
        <div className="sidebar-footer"><span className="avatar">AD</span><div><strong>Admin Demo</strong><small>Project preview</small></div></div>
      </aside>

      <main className="main" id="overview">
        <header className="page-header">
          <div><p className="eyebrow">YOUR GYM, ORGANIZED</p><h1>Overview</h1><p className="subheading">A simple starting point for managing your gym.</p></div>
          <span className={apiStatus === "Connected" ? "api-status connected" : "api-status"}><span className="status-dot" /> API: {apiStatus}</span>
        </header>

        <section className="hero">
          <div><span className="tag">MVP FOUNDATION</span><h2>Build stronger routines.<br /><em>Run a smarter gym.</em></h2><p>Manage members, trainers, memberships, attendance, and workout plans in one workspace.</p></div>
          <div className="hero-art" aria-hidden="true"><span>GT</span></div>
        </section>

        <section className="stats">
          <article className="stat-card"><span>Active Members</span><strong>128</strong><small>Demo data only</small></article>
          <article className="stat-card"><span>Trainers</span><strong>6</strong><small>Sample count</small></article>
          <article className="stat-card"><span>Today's Check-ins</span><strong>42</strong><small>Sample count</small></article>
          <article className="stat-card"><span>Membership Plans</span><strong>4</strong><small>Starter plans</small></article>
        </section>

        <section className="content-grid" id="modules">
          <article className="panel"><div className="panel-header"><div><p className="eyebrow">CORE MODULES</p><h3>Project workspace</h3></div><span className="planned">Planned for MVP</span></div>
            {modules.map((item, index) => <div className="module-row" key={item.title}><span className={`module-icon color-${index}`}>{item.icon}</span><div><strong>{item.title}</strong><p>{item.description}</p></div><span className="module-state">Planned</span></div>)}
          </article>
          <article className="panel api-panel"><div className="panel-header"><div><p className="eyebrow">DEVELOPMENT CHECK</p><h3>Backend connection</h3></div><span className="link-icon">↔</span></div>
            <p className="api-copy">Test that the React frontend can communicate with FastAPI.</p>
            <label htmlFor="test-name">Test message name</label><input id="test-name" value={name} onChange={(event) => setName(event.target.value)} placeholder="Enter a name" />
            <button onClick={testApi}>Send API request</button>
            {apiMessage && <p className="message success">{apiMessage}</p>}{error && <p className="message error">{error}</p>}
            <div className="endpoint"><b>GET</b><code>/api/health</code><span>Health check</span></div>
            <div className="endpoint"><b>GET</b><code>/api/hello</code><span>Demo endpoint</span></div>
          </article>
        </section>
        <footer>GymTrack · CSE309 starter · React + TypeScript / FastAPI + Python</footer>
      </main>
    </div>
  );
}
