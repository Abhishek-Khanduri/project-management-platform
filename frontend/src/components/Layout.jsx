import { Navigate, NavLink, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { userName } from "../constants";
import { Spinner } from "./ui";

/** Wraps every logged-in page: redirects to /login if needed, and shows the top bar. */
export default function Layout() {
  const { user, loading, logout } = useAuth();
  const location = useLocation();

  if (loading) return <Spinner />;
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />;

  return (
    <>
      <header className="topbar">
        <nav className="topbar-inner">
          <span className="brand">ProjectHub</span>
          <NavLink to="/" end>
            Dashboard
          </NavLink>
          <NavLink to="/projects">Projects</NavLink>
          <span className="spacer" />
          <span className="muted">{userName(user)}</span>
          <button className="btn btn-small" onClick={logout}>
            Log out
          </button>
        </nav>
      </header>
      <main className="container">
        <Outlet />
      </main>
    </>
  );
}
