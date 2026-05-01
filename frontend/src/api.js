const BASE = "/api";

async function req(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, options);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }));
    throw new Error(err.error || res.statusText);
  }
  return res.json();
}

// ── Chats ──────────────────────────────────────────────────────
export const createChat = (sessionId) =>
  req("/chats", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId }),
  });

export const listChats  = (sessionId) => req(`/chats?session_id=${sessionId}`);

export const loadChat   = (chatId, sessionId) =>
  req(`/chats/${chatId}?session_id=${sessionId}`);

export const deleteChat = (chatId, sessionId) =>
  req(`/chats/${chatId}?session_id=${sessionId}`, { method: "DELETE" });

export const renameChat = (chatId, sessionId, name) =>
  req(`/chats/${chatId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, name }),
  });

// ── Messages ───────────────────────────────────────────────────
// Fix 2: files are NOT sent by the frontend — backend reads them from chat_store
export const sendMessage = (chatId, sessionId, question) =>
  req("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ chat_id: chatId, session_id: sessionId, question }),
  });

// ── Files ──────────────────────────────────────────────────────
export const listFiles = (chatId, sessionId) =>
  req(`/files?chat_id=${chatId}&session_id=${sessionId}`);

export const uploadFile = (file, chatId, sessionId) => {
  const fd = new FormData();
  fd.append("file", file);
  fd.append("chat_id", chatId);
  fd.append("session_id", sessionId);
  return req("/files", { method: "POST", body: fd });
};

// fileName should be the prefixed source key returned by the backend
export const deleteFile = (fileName, chatId, sessionId) =>
  req(`/files/${encodeURIComponent(fileName)}?chat_id=${chatId}&session_id=${sessionId}`, {
    method: "DELETE",
  });