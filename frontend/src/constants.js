export const STATUSES = [
  { value: "todo", label: "Todo" },
  { value: "in_progress", label: "In Progress" },
  { value: "completed", label: "Completed" },
];

export const PRIORITIES = [
  { value: "low", label: "Low" },
  { value: "medium", label: "Medium" },
  { value: "high", label: "High" },
];

export const PROJECT_STATUSES = [
  { value: "active", label: "Active" },
  { value: "archived", label: "Archived" },
];

export const labelOf = (options, value) => options.find((o) => o.value === value)?.label || value;

export const userName = (user) =>
  user ? [user.first_name, user.last_name].filter(Boolean).join(" ") || user.email : "Unassigned";

export const formatDate = (value) => (value ? new Date(value).toLocaleDateString() : "—");
