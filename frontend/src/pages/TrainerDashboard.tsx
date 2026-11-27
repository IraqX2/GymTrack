import { useCallback, useEffect, useState, type FormEvent } from "react";
import { api, type GymRow } from "../services/gymtrack";

type TrainerAssignment = {
  assignment: GymRow;
  plan: GymRow;
  member: GymRow;
  progress: GymRow[];
};

type TrainerDashboardData = {
  trainer: GymRow;
  summary: {
    assigned_workouts: number;
    assigned_members: number;
  };
  assignments: TrainerAssignment[];
};

type ProgressDraft = {
  completion_percent: number;
  notes: string;
};

const emptyDraft: ProgressDraft = { completion_percent: 0, notes: "" };

export default function TrainerDashboard() {
  const [data, setData] = useState<TrainerDashboardData | null>(null);
  const [drafts, setDrafts] = useState<Record<number, ProgressDraft>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const result = await api<TrainerDashboardData>("/api/trainer/dashboard");
      setData(result);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load trainer assignments");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  function updateDraft(assignmentId: number, changes: Partial<ProgressDraft>) {
    setDrafts(current => ({
      ...current,
      [assignmentId]: { ...emptyDraft, ...current[assignmentId], ...changes },
    }));
  }

  async function submitProgress(event: FormEvent<HTMLFormElement>, assignmentId: number) {
    event.preventDefault();
    const draft = drafts[assignmentId] ?? emptyDraft;
    setSaving(assignmentId);
    setError("");
    setMessage("");
    try {
      await api(
        `/api/trainer/assignments/${assignmentId}/progress`,
        "POST",
        { completion_percent: draft.completion_percent, notes: draft.notes.trim() },
      );
      setDrafts(current => ({ ...current, [assignmentId]: emptyDraft }));
      setMessage("Progress update saved.");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save progress");
    } finally {
      setSaving(null);
    }
  }

  if (loading) {
    return <section className="gt-panel"><p className="gt-empty">Loading your assigned members…</p></section>;
  }

  return (
    <div className="gt-page-stack">
      <section className="gt-section-title">
        <div>
          <p className="gt-eyebrow">TRAINER WORKSPACE</p>
          <h2>My Trainees</h2>
          <p className="gt-muted">Review only the workout assignments allocated to your trainer account and record progress.</p>
        </div>
        <button className="gt-secondary" onClick={() => void load()}>Refresh</button>
      </section>

      {error && <div className="gt-alert error">{error}</div>}
      {message && <div className="gt-alert success">{message}</div>}

      {!data ? (
        <section className="gt-panel">
          <div className="gt-empty-state">
            <strong>Trainer information is unavailable</strong>
            <p>Ask an administrator to check your trainer profile and assigned workouts.</p>
          </div>
        </section>
      ) : (
        <>
          <section className="gt-welcome">
            <div>
              <p className="gt-eyebrow">TRAINER ACCOUNT</p>
              <h2>Welcome, {data.trainer.full_name}</h2>
              <p>{data.trainer.specialization || "General fitness"}</p>
            </div>
            <span className="gt-role-tag">TRAINER</span>
          </section>

          <section className="gt-stat-grid">
            <article className="gt-stat">
              <span>Assigned members</span>
              <strong>{data.summary.assigned_members}</strong>
            </article>
            <article className="gt-stat">
              <span>Assigned workouts</span>
              <strong>{data.summary.assigned_workouts}</strong>
            </article>
          </section>

          {!data.assignments.length ? (
            <section className="gt-panel">
              <div className="gt-empty-state">
                <strong>No workout assignments yet</strong>
                <p>When an administrator assigns a workout plan to you, the member and plan will appear here.</p>
              </div>
            </section>
          ) : (
            <div className="gt-member-workouts">
              {data.assignments.map(({ assignment, plan, member, progress }) => {
                const draft = drafts[assignment.id] ?? emptyDraft;
                return (
                  <article className="gt-workout-card" key={assignment.id}>
                    <div className="gt-panel-head">
                      <div>
                        <p className="gt-eyebrow">WORKOUT ASSIGNMENT #{assignment.id}</p>
                        <h3>{plan.title}</h3>
                        <p className="gt-muted">{plan.level} · {plan.duration_weeks} weeks</p>
                      </div>
                      <span className={assignment.status === "active" ? "gt-status active" : "gt-status"}>
                        {assignment.status}
                      </span>
                    </div>

                    <div className="gt-simple-row">
                      <strong>{member.full_name}</strong>
                      <span>{member.email}</span>
                    </div>
                    {member.phone && <p className="gt-muted">Phone: {member.phone}</p>}
                    <p className="gt-muted">{plan.description || "No additional plan instructions."}</p>
                    <div className="gt-workout-meta">
                      <span>Started: {assignment.start_date}</span>
                      <span>Ends: {assignment.end_date || "Not set"}</span>
                    </div>

                    <h4 className="gt-subheading">Progress history</h4>
                    {progress.length ? (
                      <div className="gt-session-list">
                        {progress.map(entry => (
                          <div className="gt-session-row" key={entry.id}>
                            <div>
                              <strong>{entry.completion_percent}% complete</strong>
                              <small>{new Date(entry.progress_date).toLocaleDateString()} · {new Date(entry.created_at).toLocaleTimeString()}</small>
                              {entry.notes && <small>{entry.notes}</small>}
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="gt-empty">No progress updates have been recorded.</p>
                    )}

                    <form className="gt-invite-form" onSubmit={event => void submitProgress(event, assignment.id)}>
                      <h4>Record a progress update</h4>
                      <label className="gt-field">
                        Completion percentage
                        <input
                          type="number"
                          min={0}
                          max={100}
                          step={1}
                          value={draft.completion_percent}
                          onChange={event => updateDraft(assignment.id, {
                            completion_percent: Math.min(100, Math.max(0, Number(event.target.value) || 0)),
                          })}
                        />
                      </label>
                      <label className="gt-field">
                        Trainer notes
                        <textarea
                          value={draft.notes}
                          onChange={event => updateDraft(assignment.id, { notes: event.target.value })}
                          maxLength={600}
                          rows={3}
                          placeholder="Record a short progress note..."
                        />
                      </label>
                      <button className="gt-primary" disabled={saving === assignment.id}>
                        {saving === assignment.id ? "Saving…" : "Save progress"}
                      </button>
                    </form>
                  </article>
                );
              })}
            </div>
          )}
        </>
      )}
    </div>
  );
}
