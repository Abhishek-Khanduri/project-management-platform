import { Link } from "react-router-dom";
import api from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { ErrorState, Spinner } from "../components/ui";
import { userName } from "../constants";
import { useApi } from "../hooks";

const STATS = [
  { key: "total_projects", label: "Total Projects" },
  { key: "active_projects", label: "Active Projects" },
  { key: "total_tasks", label: "Total Tasks" },
  { key: "completed_tasks", label: "Completed Tasks" },
  { key: "pending_tasks", label: "Pending Tasks" },
];

export default function DashboardPage() {
  const { user } = useAuth();
  const { data, loading, error, reload } = useApi(() => api.get("/dashboard/"), []);

  return (
    <>
      <div className="page-header">
        <h1>Welcome, {userName(user)}</h1>
        <Link className="btn btn-primary" to="/projects">
          View projects
        </Link>
      </div>
      {loading && !data && <Spinner />}
      {error && <ErrorState message={error} onRetry={reload} />}
      {data && (
        <div className="stats">
          {STATS.map((stat) => (
            <div key={stat.key} className="card stat">
              <span className="stat-value">{data[stat.key]}</span>
              <span className="stat-label">{stat.label}</span>
            </div>
          ))}
        </div>
      )}
    </>
  );
}
