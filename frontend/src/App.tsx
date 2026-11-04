import { useEffect, useState } from "react";

type Member = {
  id: number;
  full_name: string;
  email: string;
  phone: string;
  join_date: string;
  is_active: boolean;
};

type MemberForm = {
  full_name: string;
  email: string;
  phone: string;
  join_date: string;
  is_active: boolean;
};

const emptyForm: MemberForm = {
  full_name: "",
  email: "",
  phone: "",
  join_date: new Date().toISOString().slice(0, 10),
  is_active: true,
};

async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(path, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${response.status})`);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export default function App() {
  const [members, setMembers] = useState<Member[]>([]);
  const [selected, setSelected] = useState<Member | null>(null);
  const [form, setForm] = useState<MemberForm>(emptyForm);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [apiStatus, setApiStatus] = useState("Checking...");

  async function loadMembers() {
    setLoading(true);
    try {
      const data = await api<Member[]>("/api/members");
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

  useEffect(() => { void loadMembers(); }, []);

  function startCreate() {
    setEditingId(null);
    setSelected(null);
    setForm(emptyForm);
    setNotice("");
    setError("");
  }

  async function viewMember(id: number) {
    setError("");
    try {
      const member = await api<Member>(`/api/members/${id}`);
      setSelected(member);
      setEditingId(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load member.");
    }
  }

  function startEdit(member: Member) {
    setSelected(member);
    setEditingId(member.id);
    setForm({
      full_name: member.full_name,
      email: member.email,
      phone: member.phone,
      join_date: member.join_date,
      is_active: member.is_active,
    });
    setError("");
    setNotice("");
  }

  async function submitForm(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError("");
    setNotice("");
    try {
      if (editingId === null) {
        await api<Member>("/api/members", { method: "POST", body: JSON.stringify(form) });
        setNotice("Member added successfully.");
      } else {
        await api<Member>(`/api/members/${editingId}`, {
          method: "PUT",
          body: JSON.stringify(form),
        });
        setNotice("Member details updated.");
      }
      setEditingId(null);
      setSelected(null);
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
    setError("");
    setNotice("");
    try {
      await api<void>(`/api/members/${member.id}`, { method: "DELETE" });
      setSelected(null);
      setEditingId(null);
      setNotice("Member deleted.");
      await loadMembers();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not delete member.");
    }
  }

  const activeCount = members.filter((member) => member.is_active).length;

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="brand"><span className="brand-icon">GT</span><div><strong>GymTrack</strong><small>Management console</small></div></div>
        <p className="nav-label">WORKSPACE</p>
        <a className="nav-link" href="#overview">▦ &nbsp; Overview</a>
        <a className="nav-link active" href="#members">♙ &nbsp; Members</a>
        <a className="nav-link" href="#members">♧ &nbsp; Trainers</a>
        <a className="nav-link" href="#members">▤ &nbsp; Memberships</a>
        <a className="nav-link" href="#members">◷ &nbsp; Attendance</a>
        <a className="nav-link" href="#members">⌁ &nbsp; Workout plans</a>
        <div className="sidebar-footer"><span className="avatar">AD</span><div><strong>Admin Demo</strong><small>Member management</small></div></div>
      </aside>

      <main className="main" id="overview">
        <header className="page-header">
          <div><p className="eyebrow">YOUR GYM, ORGANIZED</p><h1>Member Management</h1><p className="subheading">Add, view and maintain your gym member records.</p></div>
          <span className={apiStatus === "Connected" ? "api-status connected" : "api-status"}><span className="status-dot" /> API: {apiStatus}</span>
        </header>

        <section className="hero">
          <div><span className="tag">MEMBER RECORDS</span><h2>Know your members.<br /><em>Keep everything in order.</em></h2><p>Manage member information from one place. Records are saved through the GymTrack API.</p></div>
          <div className="hero-art" aria-hidden="true"><span>GT</span></div>
        </section>

        <section className="stats">
          <article className="stat-card"><span>Total Members</span><strong>{members.length}</strong><small>Saved records</small></article>
          <article className="stat-card"><span>Active Members</span><strong>{activeCount}</strong><small>Currently active</small></article>
          <article className="stat-card"><span>Inactive Members</span><strong>{members.length - activeCount}</strong><small>Not active</small></article>
          <article className="stat-card"><span>API Status</span><strong className="status-number">{apiStatus === "Connected" ? "Live" : "—"}</strong><small>FastAPI connection</small></article>
        </section>

        <section className="content-grid member-grid" id="members">
          <article className="panel members-panel">
            <div className="panel-header"><div><p className="eyebrow">GYM DIRECTORY</p><h3>Members</h3></div><button className="primary-button" onClick={startCreate}>+ Add member</button></div>
            {notice && <p className="message success" role="status">{notice}</p>}
            {error && <p className="message error" role="alert">{error}</p>}
            {loading ? <p className="empty-state">Loading members...</p> : members.length === 0 ? <p className="empty-state">No members yet. Add your first member to get started.</p> : (
              <div className="table-wrap"><table><thead><tr><th>Member</th><th>Contact</th><th>Status</th><th>Actions</th></tr></thead><tbody>
                {members.map((member) => <tr key={member.id}>
                  <td><strong>{member.full_name}</strong><small className="table-sub">ID #{member.id}</small></td>
                  <td><span>{member.email}</span><small className="table-sub">{member.phone || "No phone"}</small></td>
                  <td><span className={member.is_active ? "status-pill active-pill" : "status-pill inactive-pill"}>{member.is_active ? "Active" : "Inactive"}</span></td>
                  <td><div className="actions"><button className="text-button" onClick={() => void viewMember(member.id)}>View</button><button className="text-button" onClick={() => startEdit(member)}>Edit</button><button className="text-button danger-text" onClick={() => void deleteMember(member)}>Delete</button></div></td>
                </tr>)}
              </tbody></table></div>
            )}
            <div className="panel-footer"><span>{members.length} member record(s)</span><button className="text-button" onClick={() => void loadMembers()}>Refresh list</button></div>
          </article>

          <article className="panel form-panel">
            <div className="panel-header"><div><p className="eyebrow">{selected && editingId === null ? "MEMBER DETAILS" : "MEMBER FORM"}</p><h3>{selected && editingId === null ? "Member information" : editingId === null ? "Add a member" : "Edit member"}</h3></div></div>
            {selected && editingId === null ? (
              <div className="details">
                <div className="detail-avatar">{selected.full_name.slice(0,1).toUpperCase()}</div>
                <h4>{selected.full_name}</h4><span className={selected.is_active ? "status-pill active-pill" : "status-pill inactive-pill"}>{selected.is_active ? "Active" : "Inactive"}</span>
                <dl><dt>Member ID</dt><dd>#{selected.id}</dd><dt>Email</dt><dd>{selected.email}</dd><dt>Phone</dt><dd>{selected.phone || "Not provided"}</dd><dt>Join date</dt><dd>{selected.join_date}</dd></dl>
                <div className="form-actions"><button className="primary-button" onClick={() => startEdit(selected)}>Edit member</button><button className="secondary-button" onClick={startCreate}>Close</button></div>
              </div>
            ) : (
              <form onSubmit={submitForm}>
                <label htmlFor="full_name">Full name</label><input id="full_name" required minLength={2} maxLength={100} value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} placeholder="Enter full name" />
                <label htmlFor="email">Email address</label><input id="email" type="email" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} placeholder="member@example.com" />
                <label htmlFor="phone">Phone number</label><input id="phone" maxLength={30} value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} placeholder="01XXXXXXXXX" />
                <label htmlFor="join_date">Join date</label><input id="join_date" type="date" required value={form.join_date} onChange={(e) => setForm({ ...form, join_date: e.target.value })} />
                <label className="check-label"><input type="checkbox" checked={form.is_active} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} /> Active member</label>
                <div className="form-actions"><button className="primary-button" type="submit" disabled={saving}>{saving ? "Saving..." : editingId === null ? "Save member" : "Update member"}</button><button className="secondary-button" type="button" onClick={startCreate}>Clear</button></div>
              </form>
            )}
          </article>
        </section>
        <footer>GymTrack · Member Management · React + TypeScript / FastAPI + SQLite</footer>
      </main>
    </div>
  );
}
