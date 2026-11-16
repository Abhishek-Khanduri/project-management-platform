import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import api, { errorMessage, fieldErrors } from "../api/client";
import MembersPanel from "../components/MembersPanel";
import TaskList from "../components/TaskList";
import { useToast } from "../components/Toast";
import { Badge, ErrorState, Field, Spinner } from "../components/ui";
import { PROJECT_STATUSES, labelOf, userName } from "../constants";
import { useApi } from "../hooks";

export default function ProjectDetailPage() {
  const { projectId } = useParams();
  const project = useApi(() => api.get(`/projects/${projectId}/`), [projectId]);
  const members = useApi(() => api.get(`/projects/${projectId}/members/`), [projectId]);
  // Bumped when members change, so the task list reloads (removed members' tasks become unassigned).
  const [membersVersion, setMembersVersion] = useState(0);

  if (project.loading && !project.data) return <Spinner />;
  if (project.error) return <ErrorState message={project.error} onRetry={project.reload} />;

  const refreshAll = () => {
    project.reload();
    members.reload();
    setMembersVersion((v) => v + 1);
  };

  return (
    <>
      <Link to="/projects" className="back-link">
        ← All projects
      </Link>
      <ProjectHeader project={project.data} onSaved={project.reload} />
      <div className="detail-layout">
        <TaskList
          project={project.data}
          members={members.data || []}
          refreshKey={membersVersion}
          onChange={project.reload}
        />
        <MembersPanel project={project.data} members={members} onChange={refreshAll} />
      </div>
    </>
  );
}

function ProjectHeader({ project, onSaved }) {
  const navigate = useNavigate();
  const toast = useToast();
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({ name: project.name, description: project.description, status: project.status });
  const [errors, setErrors] = useState({});
  const { can_update, can_delete } = project.permissions;

  async function save(event) {
    event.preventDefault();
    if (!form.name.trim()) {
      setErrors({ name: "Project name is required." });
      return;
    }
    try {
      await api.patch(`/projects/${project.id}/`, form);
      toast.success("Project updated.");
      setEditing(false);
      onSaved();
    } catch (error) {
      setErrors(fieldErrors(error));
      toast.error(errorMessage(error));
    }
  }

  async function remove() {
    if (!window.confirm(`Delete "${project.name}" and all its tasks? This cannot be undone.`)) return;
    try {
      await api.delete(`/projects/${project.id}/`);
      toast.success("Project deleted.");
      navigate("/projects");
    } catch (error) {
      toast.error(errorMessage(error));
    }
  }

  if (editing) {
    return (
      <form className="card form" onSubmit={save} noValidate>
        <Field label="Name" error={errors.name}>
          <input value={form.name} maxLength={150} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        </Field>
        <Field label="Description" error={errors.description}>
          <textarea rows={3} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
        </Field>
        <Field label="Status" error={errors.status}>
          <select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}>
            {PROJECT_STATUSES.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </select>
        </Field>
        <div className="actions">
          <button className="btn btn-primary">Save</button>
          <button type="button" className="btn" onClick={() => setEditing(false)}>
            Cancel
          </button>
        </div>
      </form>
    );
  }

  return (
    <div className="page-header">
      <div>
        <h1>
          {project.name} <Badge kind={project.status}>{labelOf(PROJECT_STATUSES, project.status)}</Badge>
        </h1>
        <p className="muted">{project.description || "No description"}</p>
        <p className="muted small">Owner: {userName(project.owner)}</p>
      </div>
      <div className="actions">
        {can_update && (
          <button className="btn" onClick={() => setEditing(true)}>
            Edit
          </button>
        )}
        {can_delete && (
          <button className="btn btn-danger" onClick={remove}>
            Delete
          </button>
        )}
      </div>
    </div>
  );
}
