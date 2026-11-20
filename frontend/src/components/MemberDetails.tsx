import type { Member } from "../types/member";

interface MemberDetailsProps {
  member: Member;
  onEdit: (member: Member) => void;
  onClose: () => void;
}

export default function MemberDetails({ member, onEdit, onClose }: MemberDetailsProps) {
  return (
    <div className="details">
      <div className="detail-avatar">{member.full_name.slice(0, 1).toUpperCase()}</div>
      <h4>{member.full_name}</h4>
      <span className={member.is_active ? "status-pill active-pill" : "status-pill inactive-pill"}>
        {member.is_active ? "Active" : "Inactive"}
      </span>
      <dl>
        <dt>Member ID</dt><dd>#{member.id}</dd>
        <dt>Email</dt><dd>{member.email}</dd>
        <dt>Phone</dt><dd>{member.phone || "Not provided"}</dd>
        <dt>Join date</dt><dd>{member.join_date}</dd>
      </dl>
      <div className="form-actions">
        <button className="primary-button" onClick={() => onEdit(member)}>Edit member</button>
        <button className="secondary-button" onClick={onClose}>Close</button>
      </div>
    </div>
  );
}
