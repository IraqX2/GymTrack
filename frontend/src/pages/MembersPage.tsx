import { useCallback, useEffect, useState, type FormEvent } from "react";
import MemberDetails from "../components/MemberDetails";
import MemberForm from "../components/MemberForm";
import MemberList from "../components/MemberList";
import { createMember, deleteMember as deleteMemberRequest, getMember, getMembers, updateMember } from "../services/api";
import type { Member, MemberFormValues } from "../types/member";

interface MembersPageProps {
  onApiStatusChange: (status: string) => void;
  onMembersChange: (members: Member[]) => void;
}

const createEmptyForm = (): MemberFormValues => ({
  full_name: "",
  email: "",
  phone: "",
  join_date: new Date().toISOString().slice(0, 10),
  is_active: true,
});

export default function MembersPage({ onApiStatusChange, onMembersChange }: MembersPageProps) {
  const [members, setMembers] = useState<Member[]>([]);
  const [selected, setSelected] = useState<Member | null>(null);
  const [form, setForm] = useState<MemberFormValues>(createEmptyForm);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const loadMembers = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getMembers();
      setMembers(data);
      onMembersChange(data);
      onApiStatusChange("Connected");
      setError("");
    } catch (err) {
      onApiStatusChange("Not connected");
      setError(err instanceof Error ? err.message : "Could not load members.");
    } finally {
      setLoading(false);
    }
  }, [onApiStatusChange, onMembersChange]);

  useEffect(() => {
    void loadMembers();
  }, [loadMembers]);

  function openNewMember() {
    setSelected(null);
    setEditingId(null);
    setForm(createEmptyForm());
    setShowForm(true);
    setError("");
    setMessage("");
  }

  async function viewMember(id: number) {
    try {
      const member = await getMember(id);
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

  async function saveMember(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError("");
    setMessage("");

    try {
      if (editingId === null) {
        await createMember(form);
        setMessage("Member added.");
      } else {
        await updateMember(editingId, form);
        setMessage("Member updated.");
      }

      setShowForm(false);
      setEditingId(null);
      setForm(createEmptyForm());
      await loadMembers();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save member.");
    } finally {
      setSaving(false);
    }
  }

  async function removeMember(member: Member) {
    if (!window.confirm(`Delete ${member.full_name}?`)) return;

    try {
      await deleteMemberRequest(member.id);
      setSelected(null);
      setMessage("Member deleted.");
      await loadMembers();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not delete member.");
    }
  }

  return (
    <section className="content-grid member-grid">
      <MemberList
        members={members}
        loading={loading}
        error={error}
        message={message}
        onAdd={openNewMember}
        onView={(id) => void viewMember(id)}
        onEdit={editMember}
        onDelete={(member) => void removeMember(member)}
        onRefresh={() => void loadMembers()}
      />

      <article className="panel form-panel">
        <div className="panel-header">
          <div>
            <p className="eyebrow">{selected ? "MEMBER DETAILS" : "MEMBER FORM"}</p>
            <h3>{selected ? "Member information" : editingId === null ? "Add a member" : "Edit member"}</h3>
          </div>
        </div>

        {selected ? (
          <MemberDetails
            member={selected}
            onEdit={editMember}
            onClose={() => setSelected(null)}
          />
        ) : showForm ? (
          <MemberForm
            form={form}
            editingId={editingId}
            saving={saving}
            onChange={setForm}
            onSubmit={saveMember}
            onCancel={() => setShowForm(false)}
          />
        ) : (
          <p className="empty-state">Select a member to view details, or add a new member.</p>
        )}
      </article>
    </section>
  );
}
