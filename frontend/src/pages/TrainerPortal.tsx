import { useCallback, useEffect, useState, type FormEvent } from "react";
import { api, type GymRow } from "../services/gymtrack";

function localDateValue() {
  const today = new Date();
  const offset = today.getTimezoneOffset();
  return new Date(today.getTime() - offset * 60_000).toISOString().slice(0, 10);
}

type TrainerAssignment = { assignment: GymRow; plan: GymRow; member: GymRow; progress: GymRow[] };
type TrainerDashboardData = { trainer: GymRow; assignments: TrainerAssignment[] };

export default function TrainerPortal() {
  const [data, setData] = useState<TrainerDashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setData(await api<TrainerDashboardData>("/api/trainer/dashboard"));
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load trainer workspace");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  if (loading) return <section className="gt-panel"><p className="gt-empty">Loading your trainer workspace…</p></section>;

  return <div className="gt-page-stack">
    <section className="gt-section-title">
      <div>
        <p className="gt-eyebrow">TRAINER WORKSPACE</p>
        <h2>Assigned members</h2>
        <p className="gt-muted">Review only the workout plans assigned to your trainer account and record member progress.</p>
      </div>
      <button className="gt-secondary" onClick={() => void load()}>Refresh</button>
    </section>
    {error && <div className="gt-alert error">{error}</div>}
    {!data ? <section className="gt-panel"><div className="gt-empty-state"><strong>Trainer workspace unavailable</strong><p>Ask an administrator to check that your trainer profile is active and linked to your registered email.</p></div></section> : <>
      <section className="gt-welcome">
        <div><p className="gt-eyebrow">SIGNED-IN TRAINER</p><h2>{data.trainer.full_name}</h2><p>{data.trainer.specialization || "Gym trainer"} · {data.assignments.length} assigned workout(s)</p></div>
        <span className="gt-role-tag">TRAINER</span>
      </section>
      {!data.assignments.length ? <section className="gt-panel"><div className="gt-empty-state"><strong>No assigned workouts yet</strong><p>An administrator can assign a workout plan to you from Workouts → Assignments.</p></div></section> :
        <div className="gt-member-workouts">{data.assignments.map(item =>
          <TrainerAssignmentCard key={item.assignment.id} item={item} onRefresh={load}/>
        )}</div>
      }
    </>}
  </div>;
}

function TrainerAssignmentCard({ item, onRefresh }: { item: TrainerAssignment; onRefresh: () => Promise<void> }) {
  const [completion, setCompletion] = useState(0);
  const [notes, setNotes] = useState("");
  const [progressDate, setProgressDate] = useState(localDateValue());
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  async function recordProgress(event: FormEvent) {
    event.preventDefault();
    if (saving) return;
    setSaving(true); setError(""); setMessage("");
    try {
      await api("/api/trainer/assignments/" + item.assignment.id + "/progress", "POST", {
        completion_percent: completion,
        notes,
        progress_date: progressDate,
      });
      setNotes("");
      setMessage("Progress saved.");
      await onRefresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not record progress");
    } finally {
      setSaving(false);
    }
  }

  async function changeStatus(status: string) {
    setError(""); setMessage("");
    try {
      await api("/api/trainer/assignments/" + item.assignment.id + "/status", "PATCH", { status });
      setMessage("Workout status updated.");
      await onRefresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not update workout status");
    }
  }

  return <article className="gt-workout-card">
    <div className="gt-panel-head">
      <div><p className="gt-eyebrow">WORKOUT #{item.assignment.id}</p><h3>{item.plan.title}</h3><p className="gt-muted">{item.plan.level} · {item.plan.duration_weeks} weeks</p></div>
      <label className="gt-field">Status
        <select value={item.assignment.status} onChange={e => void changeStatus(e.target.value)}>
          <option value="active">Active</option><option value="completed">Completed</option><option value="cancelled">Cancelled</option>
        </select>
      </label>
    </div>
    <div className="gt-workout-meta"><span>Member: <strong>{item.member.full_name}</strong></span><span>Started: {item.assignment.start_date}</span></div>
    <p className="gt-muted">{item.plan.description || "No additional workout instructions."}</p>
    {error && <div className="gt-alert error">{error}</div>}
    {message && <div className="gt-alert success">{message}</div>}
    <form className="gt-form-grid" onSubmit={recordProgress}>
      <label className="gt-field">Completion percentage
        <input type="number" min={0} max={100} required value={completion} onChange={e => setCompletion(Number(e.target.value))}/>
      </label>
      <label className="gt-field">Progress date
        <input type="date" required value={progressDate} onChange={e => setProgressDate(e.target.value)}/>
      </label>
      <label className="gt-field">Progress notes
        <textarea rows={2} maxLength={1000} value={notes} onChange={e => setNotes(e.target.value)} placeholder="Record form, strength, consistency or next steps."/>
      </label>
      <div className="gt-form-actions"><button className="gt-primary" disabled={saving}>{saving ? "Saving…" : "Save progress"}</button></div>
    </form>
    <h4 className="gt-subheading">Recent progress</h4>
    {!item.progress.length ? <p className="gt-empty">No progress entries recorded for this assignment.</p> : item.progress.slice(0, 4).map(row =>
      <div className="gt-simple-row" key={row.id}><strong>{row.completion_percent}% complete</strong><span>{row.progress_date} · {row.notes || "No note"}</span></div>
    )}
  </article>;
}
