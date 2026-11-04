import { useEffect, useState } from "react";

type Member = {
  id: number;
  full_name: string;
  email: string;
  phone: string;
  join_date: string;
  is_active: boolean;
};

type MemberForm = Omit<Member, "id">;

const emptyForm: MemberForm = {
  full_name: "",
  email: "",
  phone: "",
  join_date: new Date().toISOString().slice(0, 10),
  is_active: true,
};

async function request<T>(url: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(url, {
    ...options,
    headers: { "Content-Type": "application/json", ...options.headers },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `Request failed: ${response.status}`);
  }

  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

const modules = [
  { title: "Members", description: "Maintain gym member records.", icon: "♙" },
  { title: "Trainers", description: "Organize trainers and assignments.", icon: "♧" },
  { title: "Memberships", description: "Track membership plans and status.", icon: "▤" },
  { title: "Attendance", description: "Record daily gym check-ins.", icon: "◷" },
  { title: "Workout plans", description: "Plan exercises and track progress.", icon: "⌁" },
];

export default function App() {
  const [activePage, setActivePage] = useState("Overview");
  const [apiStatus, setApiStatus] = useState("Checking...");
  const [members, setMembers] = useState<Member[]>([]);
  const [selected, setSelected] = useState<Member | null>(null);
  const [form, setForm] = useState<MemberForm>(emptyForm);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  async function loadMembers() {
    setLoading(true);
    try {
      const data = await request<Member[]>("/api/members");
      setMembers(data);
      setApiStatus("Connected");
      setError("");
    } catch (err) {
      setApiStatus("Not connected");
      setError(err instanceof Error ? err.message : "Could not load members.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    request<{ status: string }>("/api/health")
      .then(() => setApiStatus("Connected"))
      .catch(() => setApiStatus("Not connected"));
    void loadMembers();
  }, []);

  useEffect(() => {
    if (activePage === "Members") void loadMembers();
  }, [activePage]);

  function openNewMember() {
    setSelected(null);
    setEditingId(null);
    setForm(emptyForm);
    setShowForm(true);
    setError("");
    setMessage("");
  }

  async function viewMember(id: number) {
    try {
      const member = await request<Member>(`/api/members/${id}`);
      setSelected(member);
      setShowForm(false);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load member.");
    }
  }

  function editMember(member: Member) {
    setSelected(null);
    setEditingId(member.id);
    setForm({
      full_name: member.full_name,
      email: member.email,
      phone: member.phone,
      join_date: member.join_date,
      is_active: member.is_active,
    });
    setShowForm(true);
    setError("");
    setMessage("");
  }

  async function saveMember(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError("");
    setMessage("");

    try {
      if (editingId === null) {
        await request<Member>("/api/members", {
          method: "POST",
          body: JSON.stringify(form),
        });
        setMessage("Member added.");
      } else {
        await request<Member>(`/api/members/${editingId}`, {
          method: "PUT",
          body: JSON.stringify(form),
        });
        setMessage("Member updated.");
      }
      setShowForm(false);
      setEditingId(null);
      setForm(emptyForm);
      await loadMembers();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save member.");
    } finally {
      setSaving(false);
    }
  }

  async function deleteMember(member: Member) {
    if (!window.confirm(`Delete ${member.full_name}?`)) return;

    try {
      await request<void>(`/api/members/${member.id}`, { method: "DELETE" });
      setSelected(null);
      setMessage("Member deleted.");
      await loadMembers();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not delete member.");
    }
  }

  const navigation = ["Overview", "Members", "Trainers", "Memberships", "Attendance", "Workout plans"];
  const activeMembers = members.filter((member) => member.is_active).length;

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
            className={`nav-link ${activePage === item ? "active" : ""}`}
            onClick={() => {
              setActivePage(item);
              setSelected(null);
              setShowForm(false);
              setError("");
              setMessage("");
            }}
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
              <article className="stat-card"><span>Total Members</span><strong>{members.length}</strong><small>Member records</small></article>
              <article className="stat-card"><span>Active Members</span><strong>{activeMembers}</strong><small>Currently active</small></article>
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
          <section className="content-grid member-grid">
            <article className="panel members-panel">
              <div className="panel-header">
                <div><p className="eyebrow">GYM DIRECTORY</p><h3>Members</h3></div>
                <button className="primary-button" onClick={openNewMember}>+ Add member</button>
              </div>
              {message && <p className="message success">{message}</p>}
              {error && <p className="message error">{error}</p>}
              {loading ? <p className="empty-state">Loading members...</p> : members.length === 0 ? (
                <p className="empty-state">No members yet. Add your first member.</p>
              ) : (
                <div className="table-wrap">
                  <table>
                    <thead><tr><th>Member</th><th>Contact</th><th>Status</th><th>Actions</th></tr></thead>
                    <tbody>
                      {members.map((member) => (
                        <tr key={member.id}>
                          <td><strong>{member.full_name}</strong><small className="table-sub">ID #{member.id}</small></td>
                          <td><span>{member.email}</span><small className="table-sub">{member.phone || "No phone"}</small></td>
                          <td><span className={member.is_active ? "status-pill active-pill" : "status-pill inactive-pill"}>{member.is_active ? "Active" : "Inactive"}</span></td>
                          <td>
                            <div className="actions">
                              <button className="text-button" onClick={() => void viewMember(member.id)}>View</button>
                              <button className="text-button" onClick={() => editMember(member)}>Edit</button>
                              <button className="text-button danger-text" onClick={() => void deleteMember(member)}>Delete</button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
              <div className="panel-footer">
                <span>{members.length} member record(s)</span>
                <button className="text-button" onClick={() => void loadMembers()}>Refresh list</button>
              </div>
            </article>

            <article className="panel form-panel">
              <div className="panel-header">
                <div>
                  <p className="eyebrow">{selected ? "MEMBER DETAILS" : "MEMBER FORM"}</p>
                  <h3>{selected ? "Member information" : editingId === null ? "Add a member" : "Edit member"}</h3>
                </div>
              </div>
              {selected ? (
                <div className="details">
                  <div className="detail-avatar">{selected.full_name.slice(0, 1).toUpperCase()}</div>
                  <h4>{selected.full_name}</h4>
                  <span className={selected.is_active ? "status-pill active-pill" : "status-pill inactive-pill"}>{selected.is_active ? "Active" : "Inactive"}</span>
                  <dl>
                    <dt>Member ID</dt><dd>#{selected.id}</dd>
                    <dt>Email</dt><dd>{selected.email}</dd>
                    <dt>Phone</dt><dd>{selected.phone || "Not provided"}</dd>
                    <dt>Join date</dt><dd>{selected.join_date}</dd>
                  </dl>
                  <div className="form-actions">
                    <button className="primary-button" onClick={() => editMember(selected)}>Edit member</button>
                    <button className="secondary-button" onClick={() => setSelected(null)}>Close</button>
                  </div>
                </div>
              ) : showForm ? (
                <form onSubmit={saveMember}>
                  <label htmlFor="full_name">Full name</label>
                  <input id="full_name" required minLength={2} maxLength={100} value={form.full_name} onChange={(event) => setForm({ ...form, full_name: event.target.value })} />
                  <label htmlFor="email">Email address</label>
                  <input id="email" type="email" required value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} />
                  <label htmlFor="phone">Phone number</label>
                  <input id="phone" maxLength={30} value={form.phone} onChange={(event) => setForm({ ...form, phone: event.target.value })} />
                  <label htmlFor="join_date">Join date</label>
                  <input id="join_date" type="date" required value={form.join_date} onChange={(event) => setForm({ ...form, join_date: event.target.value })} />
                  <label className="check-label"><input type="checkbox" checked={form.is_active} onChange={(event) => setForm({ ...form, is_active: event.target.checked })} /> Active member</label>
                  <div className="form-actions">
                    <button className="primary-button" type="submit" disabled={saving}>{saving ? "Saving..." : editingId === null ? "Save member" : "Update member"}</button>
                    <button className="secondary-button" type="button" onClick={() => setShowForm(false)}>Cancel</button>
                  </div>
                </form>
              ) : (
                <p className="empty-state">Select a member to view details, or add a new member.</p>
              )}
            </article>
          </section>
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
