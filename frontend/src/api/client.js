import axios from "axios";

// Tokens are kept in localStorage so a page refresh keeps the user logged in.
export const tokens = {
  getAccess: () => localStorage.getItem("access"),
  getRefresh: () => localStorage.getItem("refresh"),
  save({ access, refresh }) {
    if (access) localStorage.setItem("access", access);
    if (refresh) localStorage.setItem("refresh", refresh);
  },
  clear() {
    localStorage.removeItem("access");
    localStorage.removeItem("refresh");
  },
};

const api = axios.create({ baseURL: "/api" });

// Attach the access token to every request.
api.interceptors.request.use((config) => {
  const access = tokens.getAccess();
  if (access) config.headers.Authorization = `Bearer ${access}`;
  return config;
});

// When the access token has expired (401), get a new one with the refresh
// token and retry the original request once. If that fails, log out.
const NO_REFRESH_URLS = ["/auth/login/", "/auth/register/", "/auth/refresh/"];
let refreshRequest = null;

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;
    const canRefresh =
      error.response?.status === 401 &&
      tokens.getRefresh() &&
      !original._retried &&
      !NO_REFRESH_URLS.includes(original.url);

    if (!canRefresh) return Promise.reject(error);

    original._retried = true;
    try {
      // Several requests may fail at once; they all wait for the same refresh call.
      refreshRequest =
        refreshRequest ||
        axios.post("/api/auth/refresh/", { refresh: tokens.getRefresh() }).finally(() => {
          refreshRequest = null;
        });
      const { data } = await refreshRequest;
      tokens.save(data);
      return api(original);
    } catch {
      tokens.clear();
      window.location.href = "/login";
      return Promise.reject(error);
    }
  },
);

// The backend always sends errors as {"error": {"code", "message", "details"}}.
export function errorMessage(error) {
  if (!error.response) return "Cannot reach the server. Please try again.";
  return error.response.data?.error?.message || "Something went wrong.";
}

// Field errors from a 400 response, as {fieldName: "first message"}.
export function fieldErrors(error) {
  const details = error.response?.data?.error?.details || {};
  return Object.fromEntries(
    Object.entries(details).map(([field, messages]) => [field, [].concat(messages)[0]]),
  );
}

export default api;
