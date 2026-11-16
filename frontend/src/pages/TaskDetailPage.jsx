import { Link, useNavigate, useParams } from "react-router-dom";
import api, { errorMessage } from "../api/client";
import TaskForm from "../components/TaskForm";
import { useToast } from "../components/Toast";
import { ErrorState, Spinner } from "../components/ui";
import { formatDate, userName } from "../constants";
import { useApi } from "../hooks";

export default function TaskDetailPage() {
  const { taskId } = useParams();
  const navigate = useNavigate();
  const toast = useToast();
  const task = useApi(() => api.get(`/tasks/${taskId}/`), [taskId]);
  const projectId = task.data?.project;
  const members = useApi(
    () => (projectId ? api.get(`/projects/${projectId}/members/`) : Promise.resolve({ data: [] })),
    [projectId],
  );

  if (task.loading && !task.data) return <Spinner />;
  if (task.error) return <ErrorState message={task.error} onRetry={task.reload} />;

  const { can_update, can_delete } = task.data.permissions;

  async function save(payload) {
    try {
      await api.patch(`/tasks/${taskId}/`, payload);
      toast.success("Task saved.");
      task.reload();
    } catch (error) {
      toast.error(errorMessage(error));
      throw error;
    }
  }

  async function remove() {
    if (!window.confirm("Delete this task? This cannot be undone.")) return;
    try {
      await api.delete(`/tasks/${taskId}/`);
      toast.success("Task deleted.");
      navigate(`/projects/${projectId}`);
    } catch (error) {
      toast.error(errorMessage(error));
    }
  }

  return (
    <>
      <Link to={`/projects/${projectId}`} className="back-link">
        ← Back to project
      </Link>
      <div className="page-header">
        <h1>{task.data.title}</h1>
        {can_delete && (
          <button className="btn btn-danger" onClick={remove}>
            Delete task
          </button>
        )}
      </div>
      <div className="detail-layout">
        <section className="card">
          {!can_update && (
            <div className="alert alert-info">Only the task's creator or assignee can edit this task.</div>
          )}
          {members.data && (
            <TaskForm
              key={task.data.updated_at}
              task={task.data}
              members={members.data}
              onSubmit={save}
              submitLabel="Save changes"
              disabled={!can_update}
            />
          )}
        </section>
        <section className="card">
          <h2>Details</h2>
          <dl className="details">
            <dt>Created by</dt>
            <dd>{userName(task.data.created_by)}</dd>
            <dt>Created</dt>
            <dd>{formatDate(task.data.created_at)}</dd>
            <dt>Last updated</dt>
            <dd>{formatDate(task.data.updated_at)}</dd>
            <dt>Completed</dt>
            <dd>{formatDate(task.data.completed_at)}</dd>
          </dl>
          <p className="muted small">
            A task can be marked Completed once it has an assignee, a description and a due date. Only the project
            owner can delete a task, and only while it is in Todo.
          </p>
        </section>
      </div>
    </>
  );
}
