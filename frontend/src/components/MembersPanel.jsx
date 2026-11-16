import { useState } from "react";
import api, { errorMessage } from "../api/client";
import { useToast } from "./Toast";
import { Badge, ErrorState, Spinner } from "./ui";
import { userName } from "../constants";

export default function MembersPanel({ project, members, onChange }) {
  const toast = useToast();
  const [email, setEmail] = useState("");
  const [adding, setAdding] = useState(false);
  const canManage = project.permissions.can_manage_members;

  async function addMember(event) {
    event.preventDefault();
    if (!email.trim()) return;
    setAdding(true);
    try {
      await api.post(`/projects/${project.id}/members/`, { email });
      toast.success("Member added.");
      setEmail("");
      onChange();
    } catch (error) {
      toast.error(errorMessage(error));
    } finally {
      setAdding(false);
    }
  }

  async function removeMember(member) {
    if (!window.confirm(`Remove ${userName(member)} from this project? Their tasks will be unassigned.`)) return;
    try {
      await api.delete(`/projects/${project.id}/members/${member.id}/`);
      toast.success("Member removed.");
      onChange();
    } catch (error) {
      toast.error(errorMessage(error));
    }
  }

  return (
    <section className="card">
      <h2>Members</h2>
      {members.loading && !members.data && <Spinner />}
      {members.error && <ErrorState message={members.error} onRetry={members.reload} />}
      {members.data && (
        <ul className="member-list">
          {members.data.map((member) => (
            <li key={member.id}>
              <div>
                <strong>{userName(member)}</strong>
                <div className="muted small">{member.email}</div>
              </div>
              {member.is_owner ? (
                <Badge kind="owner">Owner</Badge>
              ) : (
                canManage && (
                  <button className="btn btn-small btn-danger" onClick={() => removeMember(member)}>
                    Remove
                  </button>
                )
              )}
            </li>
          ))}
        </ul>
      )}
      {canManage && (
        <form className="inline-form" onSubmit={addMember}>
          <input type="email" placeholder="Add member by email" value={email} onChange={(e) => setEmail(e.target.value)} />
          <button className="btn" disabled={adding}>
            {adding ? "Adding..." : "Add"}
          </button>
        </form>
      )}
    </section>
  );
}
