import { useState } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { errorMessage } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { Field } from "../components/ui";

const EMAIL_PATTERN = /^\S+@\S+\.\S+$/;

export default function LoginPage() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [form, setForm] = useState({ email: "", password: "" });
  const [errors, setErrors] = useState({});
  const [formError, setFormError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  if (user) return <Navigate to="/" replace />;

  function validate() {
    const found = {};
    if (!form.email) found.email = "Email is required.";
    else if (!EMAIL_PATTERN.test(form.email)) found.email = "Enter a valid email address.";
    if (!form.password) found.password = "Password is required.";
    return found;
  }

  async function handleSubmit(event) {
    event.preventDefault();
    const found = validate();
    setErrors(found);
    if (Object.keys(found).length) return;

    setSubmitting(true);
    setFormError("");
    try {
      await login(form.email, form.password);
      navigate(location.state?.from || "/", { replace: true });
    } catch (error) {
      setFormError(errorMessage(error));
      setSubmitting(false);
    }
  }

  const update = (field) => (event) => setForm({ ...form, [field]: event.target.value });

  return (
    <div className="auth-page">
      <form className="card auth-card" onSubmit={handleSubmit} noValidate>
        <h1>Log in</h1>
        {formError && <div className="alert">{formError}</div>}
        <Field label="Email" error={errors.email}>
          <input type="email" value={form.email} onChange={update("email")} autoFocus />
        </Field>
        <Field label="Password" error={errors.password}>
          <input type="password" value={form.password} onChange={update("password")} />
        </Field>
        <button className="btn btn-primary btn-block" disabled={submitting}>
          {submitting ? "Logging in..." : "Log in"}
        </button>
        <p className="muted center">
          No account? <Link to="/register">Register</Link>
        </p>
      </form>
    </div>
  );
}
