// auth.js — lightweight auth state manager
// Stores JWT token and user info in localStorage

const TOKEN_KEY = "devdocs_token";
const USER_KEY  = "devdocs_user";

export function getToken()  { return localStorage.getItem(TOKEN_KEY); }
export function getUser()   { return JSON.parse(localStorage.getItem(USER_KEY) || "null"); }
export function isLoggedIn(){ return !!getToken(); }

export function saveAuth(token, user) {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearAuth() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
  localStorage.removeItem("devdocs_session_id");
  localStorage.removeItem("devdocs_active_chat");
}

// Call backend register endpoint
export async function register(name, email, password) {
  const res = await fetch("/api/auth/register", {
    method:  "POST",
    headers: { "Content-Type": "application/json" },
    body:    JSON.stringify({ name, email, password }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "Registration failed");
  saveAuth(data.token, { name: data.name, email: data.email });
  return data;
}

// Call backend login endpoint
export async function login(email, password) {
  const res = await fetch("/api/auth/login", {
    method:  "POST",
    headers: { "Content-Type": "application/json" },
    body:    JSON.stringify({ email, password }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "Login failed");
  saveAuth(data.token, { name: data.name, email: data.email });
  return data;
}
