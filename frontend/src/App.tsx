import { useCallback, useEffect, useState } from "react";
import MembersPage from "./pages/MembersPage";
import { checkApiHealth, getMembers } from "./services/api";
import type { Member } from "./types/member";

const modules = [
  { title: "Members", description: "Maintain gym member records.", icon: "♙" },
  { title: "Trainers", description: "Organize trainers and assignments.", icon: "♧" },
  { title: "Memberships", description: "Track membership plans and status.", icon: "▤" },
  { title: "Attendance", description: "Record daily gym check-ins.", icon: "◷" },
  { title: "Workout plans", description: "Plan exercises and track progress.", icon: "⌁" },
];

const navigation = ["Overview", "Members", "Trainers", "Memberships", "Attendance", "Workout plans"];

export default function App() {
  const [activePage, setActivePage] = useState("Overview");
  const [apiStatus, setApiStatus] = useState("Checking...");
  const [memberCount, setMemberCount] = useState(0);
  const [activeMemberCount, setActiveMemberCount] = useState(0);

  useEffect(() => {
    let isMounted = true;

    checkApiHealth()
      .then(() => {
        if (isMounted) setApiStatus("Connected");
      })
      .catch(() => {
        if (isMounted) setApiStatus("Not connected");
      });

    getMembers()
      .then((members) => {
        if (!isMounted) return;
        setMemberCount(members.length);
        setActiveMemberCount(members.filter((member) => member.is_active).length);
        setApiStatus("Connected");
      })
      .catch(() => {
        if (isMounted) setApiStatus("Not connected");
      });

    return () => {
      isMounted = false;
    };
  }, []);

  const updateMemberCounts = useCallback((members: Member[]) => {
    setMemberCount(members.length);
    setActiveMemberCount(members.filter((member) => member.is_active).length);
  }, []);

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-icon">GT</span>
          <div><strong>GymTrack</strong><small>Management console</small></div>
        </div>
        <p className="nav-label">WORKSPACE</p>
        {navigation.map((item, index) => (
          <button
            key={item}
            className={activePage === item ? "nav-link active" : "nav-link"}
            onClick={() => setActivePage(item)}
          >
            {["▦", "♙", "♧", "▤", "◷", "⌁"][index]} &nbsp; {item}
          </button>
        ))}
        <div className="sidebar-footer">
          <span className="avatar">AD</span>
          <div><strong>Admin Demo</strong><small>Project workspace</small></div>
        </div>
      </aside>

      <main className="main">
        <header className="page-header">
          <div>
            <p className="eyebrow">YOUR GYM, ORGANIZED</p>
            <h1>{activePage}</h1>
            <p className="subheading">
              {activePage === "Overview"
                ? "A simple starting point for managing your gym."
                : activePage === "Members"
                  ? "Add, view and maintain gym member records."
                  : "This module is planned for a later version of GymTrack."}
            </p>
          </div>
          <span className={apiStatus === "Connected" ? "api-status connected" : "api-status"}>
            <span className="status-dot" /> API: {apiStatus}
          </span>
        </header>

        {activePage === "Overview" && (
          <>
            <section className="hero">
              <div>
                <span className="tag">GYM MANAGEMENT</span>
                <h2>Build stronger routines.<br /><em>Run a smarter gym.</em></h2>
                <p>Manage members, trainers, memberships, attendance, and workout plans in one workspace.</p>
              </div>
              <div className="hero-art" aria-hidden="true"><span>GT</span></div>
            </section>

            <section className="stats">
              <article className="stat-card"><span>Total Members</span><strong>{memberCount}</strong><small>Member records</small></article>
              <article className="stat-card"><span>Active Members</span><strong>{activeMemberCount}</strong><small>Currently active</small></article>
              <article className="stat-card"><span>Other Modules</span><strong>4</strong><small>Planned features</small></article>
              <article className="stat-card"><span>Backend</span><strong>{apiStatus === "Connected" ? "Live" : "—"}</strong><small>FastAPI connection</small></article>
            </section>

            <section className="content-grid" id="modules">
              <article className="panel">
                <div className="panel-header">
                  <div><p className="eyebrow">CORE MODULES</p><h3>Project workspace</h3></div>
                  <span className="planned">MVP scope</span>
                </div>
                {modules.map((item, index) => (
                  <button
                    className="module-row module-button"
                    key={item.title}
                    onClick={() => setActivePage(item.title)}
                  >
                    <span className={`module-icon color-${index}`}>{item.icon}</span>
                    <div><strong>{item.title}</strong><p>{item.description}</p></div>
                    <span className="module-state">{index === 0 ? "Available" : "Planned"}</span>
                  </button>
                ))}
              </article>
              <article className="panel api-panel">
                <div className="panel-header">
                  <div><p className="eyebrow">DEVELOPMENT CHECK</p><h3>Backend connection</h3></div>
                  <span className="link-icon">↔</span>
                </div>
                <p className="api-copy">GymTrack uses FastAPI to handle requests from the React frontend.</p>
                <div className="endpoint"><b>GET</b><code>/api/health</code><span>Health check</span></div>
                <div className="endpoint"><b>GET</b><code>/api/members</code><span>Member list</span></div>
                <button className="primary-button overview-button" onClick={() => setActivePage("Members")}>Open members</button>
              </article>
            </section>
          </>
        )}

        {activePage === "Members" && (
          <MembersPage
            onApiStatusChange={setApiStatus}
            onMembersChange={updateMemberCounts}
          />
        )}

        {activePage !== "Overview" && activePage !== "Members" && (
          <section className="panel planned-panel">
            <p className="eyebrow">COMING LATER</p>
            <h3>{activePage}</h3>
            <p>This module is part of the GymTrack project plan, but is not included in the current MVP.</p>
            <button className="secondary-button" onClick={() => setActivePage("Overview")}>Back to overview</button>
          </section>
        )}

        <footer>GymTrack · CSE309 · React + TypeScript / FastAPI + SQLite</footer>
      </main>
    </div>
  );
}
