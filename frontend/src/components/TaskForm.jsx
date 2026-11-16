import { useState } from "react";
import { fieldErrors } from "../api/client";
import { PRIORITIES, STATUSES, userName } from "../constants";
import { Field } from "./ui";

const EMPTY_TASK = { title: "", description: "", status: "todo", priority: "medium", assignee_id: "", due_date: "" };

/**
 * Used both to create a task (project page) and to edit one (task page).
 * `onSubmit(payload)` must return a promise; on a 400 its field errors are shown here.
 */
export default function TaskForm({ task, members, onSubmit, submitLabel, disabled = false }) {
  const [form, setForm] = useState(() =>
    task
      ? {
          title: task.title,
          description: task.description,
          status: task.status,
          priority: task.priority,
          assignee_id: task.assignee?.id ?? "",
          due_date: task.due_date ?? "",
        }
      : EMPTY_TASK,
  );
  const [errors, setErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    if (!form.title.trim()) {
      setErrors({ title: "Title is required." });
      return;
    }
    setErrors({});
    setSubmitting(true);
    try {
      // Empty selects/dates are sent as null, which the API understands as "not set".
      await onSubmit({ ...form, assignee_id: form.assignee_id || null, due_date: form.due_date || null });
      if (!task) setForm(EMPTY_TASK);
    } catch (error) {
      setErrors(fieldErrors(error));
    } finally {
      setSubmitting(false);
    }
  }

  const update = (field) => (event) => setForm({ ...form, [field]: event.target.value });

  return (
    <form className="form" onSubmit={handleSubmit} noValidate>
      <fieldset disabled={disabled || submitting}>
        <Field label="Title" error={errors.title}>
          <input value={form.title} maxLength={200} onChange={update("title")} />
        </Field>
        <Field label="Description" error={errors.description}>
          <textarea rows={4} value={form.description} onChange={update("description")} />
        </Field>
        <div className="row">
          <Field label="Status" error={errors.status}>
            <select value={form.status} onChange={update("status")}>
              {STATUSES.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Priority" error={errors.priority}>
            <select value={form.priority} onChange={update("priority")}>
              {PRIORITIES.map((p) => (
                <option key={p.value} value={p.value}>
                  {p.label}
                </option>
              ))}
            </select>
          </Field>
        </div>
        <div className="row">
          <Field label="Assignee" error={errors.assignee_id}>
            <select value={form.assignee_id} onChange={update("assignee_id")}>
              <option value="">Unassigned</option>
              {members.map((m) => (
                <option key={m.id} value={m.id}>
                  {userName(m)}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Due date" error={errors.due_date}>
            <input type="date" value={form.due_date} onChange={update("due_date")} />
          </Field>
        </div>
        {!disabled && (
          <button className="btn btn-primary" disabled={submitting}>
            {submitting ? "Saving..." : submitLabel}
          </button>
        )}
      </fieldset>
    </form>
  );
}
