import { useState } from "react";
import { Link } from "react-router-dom";
import api, { errorMessage } from "../api/client";
import { PRIORITIES, STATUSES, formatDate, labelOf, userName } from "../constants";
import { useApi, useDebounce } from "../hooks";
import TaskForm from "./TaskForm";
import { useToast } from "./Toast";
import { Badge, EmptyState, ErrorState, Pagination, Spinner } from "./ui";

const PAGE_SIZE = 10;

export default function TaskList({ project, members, refreshKey, onChange }) {
  const toast = useToast();
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [priority, setPriority] = useState("");
  const [page, setPage] = useState(1);
  const [showForm, setShowForm] = useState(false);
  const debouncedSearch = useDebounce(search);

  const tasks = useApi(
    () =>
      api.get(`/projects/${project.id}/tasks/`, {
        params: { search: debouncedSearch, status, priority, page, page_size: PAGE_SIZE },
      }),
    [project.id, debouncedSearch, status, priority, page, refreshKey],
  );

  const changeFilter = (setter) => (event) => {
    setter(event.target.value);
    setPage(1);
  };

  async function createTask(payload) {
    try {
      await api.post(`/projects/${project.id}/tasks/`, payload);
      toast.success("Task created.");
      setShowForm(false);
      tasks.reload();
      onChange();
    } catch (error) {
      toast.error(errorMessage(error));
      throw error; // lets TaskForm show field errors
    }
  }

  async function changeStatus(task, newStatus) {
    try {
      await api.patch(`/tasks/${task.id}/`, { status: newStatus });
      toast.success(`Moved to ${labelOf(STATUSES, newStatus)}.`);
      tasks.reload();
    } catch (error) {
      // e.g. "A task needs an assignee, a description and a due date before it can be completed."
      toast.error(errorMessage(error));
    }
  }

  const filtering = search || status || priority;

  return (
    <section className="card">
      <div className="section-header">
        <h2>Tasks</h2>
        <button className="btn btn-primary" onClick={() => setShowForm(!showForm)}>
          {showForm ? "Cancel" : "New task"}
        </button>
      </div>

      {showForm && (
        <div className="subcard">
          <TaskForm members={members} onSubmit={createTask} submitLabel="Create task" />
        </div>
      )}

      <div className="filters">
        <input placeholder="Search tasks..." value={search} onChange={changeFilter(setSearch)} />
        <select value={status} onChange={changeFilter(setStatus)}>
          <option value="">All statuses</option>
          {STATUSES.map((s) => (
            <option key={s.value} value={s.value}>
              {s.label}
            </option>
          ))}
        </select>
        <select value={priority} onChange={changeFilter(setPriority)}>
          <option value="">All priorities</option>
          {PRIORITIES.map((p) => (
            <option key={p.value} value={p.value}>
              {p.label}
            </option>
          ))}
        </select>
      </div>

      {tasks.loading && !tasks.data && <Spinner />}
      {tasks.error && <ErrorState message={tasks.error} onRetry={tasks.reload} />}
      {tasks.data && tasks.data.results.length === 0 && (
        <EmptyState title={filtering ? "No tasks match your filters." : "No tasks yet."} />
      )}
      {tasks.data && tasks.data.results.length > 0 && (
        <>
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Title</th>
                  <th>Status</th>
                  <th>Priority</th>
                  <th>Assignee</th>
                  <th>Due</th>
                </tr>
              </thead>
              <tbody>
                {tasks.data.results.map((task) => (
                  <tr key={task.id}>
                    <td>
                      <Link to={`/tasks/${task.id}`}>{task.title}</Link>
                    </td>
                    <td>
                      <select
                        value={task.status}
                        disabled={!task.permissions.can_update}
                        title={task.permissions.can_update ? "" : "Only the creator or assignee can change this task."}
                        onChange={(e) => changeStatus(task, e.target.value)}
                      >
                        {STATUSES.map((s) => (
                          <option key={s.value} value={s.value}>
                            {s.label}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td>
                      <Badge kind={task.priority}>{labelOf(PRIORITIES, task.priority)}</Badge>
                    </td>
                    <td>{userName(task.assignee)}</td>
                    <td>{formatDate(task.due_date)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Pagination page={page} count={tasks.data.count} pageSize={PAGE_SIZE} onChange={setPage} />
        </>
      )}
    </section>
  );
}
