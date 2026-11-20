import type { Member } from "../types/member";

interface MemberListProps {
  members: Member[];
  loading: boolean;
  error: string;
  message: string;
  onAdd: () => void;
  onView: (id: number) => void;
  onEdit: (member: Member) => void;
  onDelete: (member: Member) => void;
  onRefresh: () => void;
}

export default function MemberList({
  members,
  loading,
  error,
  message,
  onAdd,
  onView,
  onEdit,
  onDelete,
  onRefresh,
}: MemberListProps) {
  return (
    <article className="panel members-panel">
      <div className="panel-header">
        <div><p className="eyebrow">GYM DIRECTORY</p><h3>Members</h3></div>
        <button className="primary-button" onClick={onAdd}>+ Add member</button>
      </div>

      {message && <p className="message success">{message}</p>}
      {error && <p className="message error">{error}</p>}

      {loading ? <p className="empty-state">Loading members...</p> : members.length === 0 ? (
        <p className="empty-state">No members yet. Add your first member.</p>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr><th>Member</th><th>Contact</th><th>Status</th><th>Actions</th></tr>
            </thead>
            <tbody>
              {members.map((member) => (
                <tr key={member.id}>
                  <td>
                    <strong>{member.full_name}</strong>
                    <small className="table-sub">ID #{member.id}</small>
                  </td>
                  <td>
                    <span>{member.email}</span>
                    <small className="table-sub">{member.phone || "No phone"}</small>
                  </td>
                  <td>
                    <span className={member.is_active ? "status-pill active-pill" : "status-pill inactive-pill"}>
                      {member.is_active ? "Active" : "Inactive"}
                    </span>
                  </td>
                  <td>
                    <div className="actions">
                      <button className="text-button" onClick={() => onView(member.id)}>View</button>
                      <button className="text-button" onClick={() => onEdit(member)}>Edit</button>
                      <button className="text-button danger-text" onClick={() => onDelete(member)}>Delete</button>
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
        <button className="text-button" onClick={onRefresh}>Refresh list</button>
      </div>
    </article>
  );
}
