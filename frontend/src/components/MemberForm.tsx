import type { FormEvent } from "react";
import type { MemberFormValues } from "../types/member";

interface MemberFormProps {
  form: MemberFormValues;
  editingId: number | null;
  saving: boolean;
  onChange: (next: MemberFormValues) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onCancel: () => void;
}

export default function MemberForm({
  form,
  editingId,
  saving,
  onChange,
  onSubmit,
  onCancel,
}: MemberFormProps) {
  return (
    <form onSubmit={onSubmit}>
      <label htmlFor="full_name">Full name</label>
      <input
        id="full_name"
        required
        minLength={2}
        maxLength={100}
        value={form.full_name}
        onChange={(event) => onChange({ ...form, full_name: event.target.value })}
      />

      <label htmlFor="email">Email address</label>
      <input
        id="email"
        type="email"
        required
        value={form.email}
        onChange={(event) => onChange({ ...form, email: event.target.value })}
      />

      <label htmlFor="phone">Phone number</label>
      <input
        id="phone"
        maxLength={30}
        value={form.phone}
        onChange={(event) => onChange({ ...form, phone: event.target.value })}
      />

      <label htmlFor="join_date">Join date</label>
      <input
        id="join_date"
        type="date"
        required
        value={form.join_date}
        onChange={(event) => onChange({ ...form, join_date: event.target.value })}
      />

      <label className="check-label">
        <input
          type="checkbox"
          checked={form.is_active}
          onChange={(event) => onChange({ ...form, is_active: event.target.checked })}
        />
        Active member
      </label>

      <div className="form-actions">
        <button className="primary-button" type="submit" disabled={saving}>
          {saving ? "Saving..." : editingId === null ? "Save member" : "Update member"}
        </button>
        <button className="secondary-button" type="button" onClick={onCancel}>Cancel</button>
      </div>
    </form>
  );
}
