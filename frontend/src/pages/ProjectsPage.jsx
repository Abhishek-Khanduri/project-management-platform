import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import api, { errorMessage, fieldErrors } from "../api/client";
import { useToast } from "../components/Toast";
import { Badge, EmptyState, ErrorState, Field, Pagination, Spinner } from "../components/ui";
import { PROJECT_STATUSES, labelOf, userName } from "../constants";
import { useApi, useDebounce } from "../hooks";

const PAGE_SIZE = 9;

export default function ProjectsPage() {
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  const [showForm, setShowForm] = useState(false);
  const debouncedSearch = useDebounce(search);

  const { data, loading, error, reload } = useApi(
    () => api.get("/projects/", { params: { search: debouncedSearch, status, page, page_size: PAGE_SIZE } }),
    [debouncedSearch, status, page],
  );

  // Changing a filter always goes back to the first page.
  const changeFilter = (setter) => (event) => {
    setter(event.target.value);
    setPage(1);
  };

  return (
    <>
      <div className="page-header">
        <h1>Projects</h1>
        <button className="btn btn-primary" onClick={() => setShowForm(!showForm)}>
          {showForm ? "Cancel" : "New project"}
        </button>
      </div>

      {showForm && <CreateProjectForm />}

      <div className="filters">
        <input placeholder="Search projects..." value={search} onChange={changeFilter(setSearch)} />
        <select value={status} onChange={changeFilter(setStatus)}>
          <option value="">All statuses</option>
          {PROJECT_STATUSES.map((s) => (
            <option key={s.value} value={s.value}>
              {s.label}
            </option>
          ))}
        </select>
      </div>

      {loading && !data && <Spinner />}
      {error && <ErrorState message={error} onRetry={reload} />}
      {data && data.results.length === 0 && (
        <EmptyState title={search || status ? "No projects match your filters." : "You have no projects yet."}>
          {!search && !status && <p className="muted">Create your first project to get started.</p>}
        </EmptyState>
      )}
      {data && data.results.length > 0 && (
        <>
          <div className="grid">
            {data.results.map((project) => (
              <Link key={project.id} to={`/projects/${project.id}`} className="card project-card">
                <div className="project-card-head">
                  <h3>{project.name}</h3>
                  <Badge kind={project.status}>{labelOf(PROJECT_STATUSES, project.status)}</Badge>
                </div>
                <p className="muted clamp">{project.description || "No description"}</p>
                <p className="muted small">
                  {project.task_count} tasks · {project.member_count} members · Owner: {userName(project.owner)}
                </p>
              </Link>
            ))}
          </div>
          <Pagination page={page} count={data.count} pageSize={PAGE_SIZE} onChange={setPage} />
        </>
      )}
    </>
  );
}

function CreateProjectForm() {
  const navigate = useNavigate();
  const toast = useToast();
  const [form, setForm] = useState({ name: "", description: "" });
  const [errors, setErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    if (!form.name.trim()) {
      setErrors({ name: "Project name is required." });
      return;
    }
    setSubmitting(true);
    try {
      const { data } = await api.post("/projects/", form);
      toast.success("Project created.");
      navigate(`/projects/${data.id}`);
    } catch (error) {
      setErrors(fieldErrors(error));
      toast.error(errorMessage(error));
      setSubmitting(false);
    }
  }

  return (
    <form className="card form" onSubmit={handleSubmit} noValidate>
      <Field label="Name" error={errors.name}>
        <input value={form.name} maxLength={150} onChange={(e) => setForm({ ...form, name: e.target.value })} autoFocus />
      </Field>
      <Field label="Description" error={errors.description}>
        <textarea rows={3} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
      </Field>
      <button className="btn btn-primary" disabled={submitting}>
        {submitting ? "Creating..." : "Create project"}
      </button>
    </form>
  );
}
