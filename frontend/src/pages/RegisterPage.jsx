import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { errorMessage, fieldErrors } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { useToast } from "../components/Toast";
import { Field } from "../components/ui";

const EMAIL_PATTERN = /^\S+@\S+\.\S+$/;

export default function RegisterPage() {
  const { user, register } = useAuth();
  const navigate = useNavigate();
  const toast = useToast();
  const [form, setForm] = useState({ first_name: "", last_name: "", email: "", password: "", confirm: "" });
  const [errors, setErrors] = useState({});
  const [formError, setFormError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  if (user) return <Navigate to="/" replace />;

  function validate() {
    const found = {};
    if (!form.email) found.email = "Email is required.";
    else if (!EMAIL_PATTERN.test(form.email)) found.email = "Enter a valid email address.";
    if (form.password.length < 8) found.password = "Password must be at least 8 characters.";
    if (form.confirm !== form.password) found.confirm = "Passwords do not match.";
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
      const { confirm, ...fields } = form;
      await register(fields);
      toast.success("Welcome! Your account has been created.");
      navigate("/", { replace: true });
    } catch (error) {
      // Show the server's field messages next to the matching inputs (e.g. "email already exists").
      setErrors(fieldErrors(error));
      setFormError(errorMessage(error));
      setSubmitting(false);
    }
  }

  const update = (field) => (event) => setForm({ ...form, [field]: event.target.value });

  return (
    <div className="auth-page">
      <form className="card auth-card" onSubmit={handleSubmit} noValidate>
        <h1>Create an account</h1>
        {formError && <div className="alert">{formError}</div>}
        <div className="row">
          <Field label="First name" error={errors.first_name}>
            <input value={form.first_name} onChange={update("first_name")} autoFocus />
          </Field>
          <Field label="Last name" error={errors.last_name}>
            <input value={form.last_name} onChange={update("last_name")} />
          </Field>
        </div>
        <Field label="Email" error={errors.email}>
          <input type="email" value={form.email} onChange={update("email")} />
        </Field>
        <Field label="Password" error={errors.password}>
          <input type="password" value={form.password} onChange={update("password")} />
        </Field>
        <Field label="Confirm password" error={errors.confirm}>
          <input type="password" value={form.confirm} onChange={update("confirm")} />
        </Field>
        <button className="btn btn-primary btn-block" disabled={submitting}>
          {submitting ? "Creating account..." : "Register"}
        </button>
        <p className="muted center">
          Already registered? <Link to="/login">Log in</Link>
        </p>
      </form>
    </div>
  );
}
