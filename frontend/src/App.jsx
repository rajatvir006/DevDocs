import { useState, useCallback, useEffect } from "react";
import Sidebar from "./components/Sidebar.jsx";
import ChatWindow from "./components/ChatWindow.jsx";
import { createChat, listChats, loadChat, deleteChat, renameChat } from "./api.js";

// ── Session ID: persisted in localStorage as a lightweight user boundary.
// Never sent to ChromaDB — only used to scope chats in chats.json.
function getOrCreateSessionId() {
  let sid = localStorage.getItem("devdocs_session_id");
  if (!sid) {
    sid = crypto.randomUUID();
    localStorage.setItem("devdocs_session_id", sid);
  }
  return sid;
}
const SESSION_ID = getOrCreateSessionId();

export { SESSION_ID };

export default function App() {
  // chats: [{id, name, messages, files, _loaded}]
  // files contains exact metadata.source values: "{chat_id}::{file_name}"
  const [chats, setChats]     = useState([]);
  const [activeId, setActiveId] = useState(null);

  const activeChat = chats.find((c) => c.id === activeId) || null;

  // ── Hydrate sidebar from backend on mount ───────────────────
  useEffect(() => {
    listChats(SESSION_ID)
      .then(({ chats: serverChats }) => {
        const stubs = serverChats.map((c) => ({
          id:       c.id,
          name:     c.name,
          messages: [],
          files:    [],
          _loaded:  false,
        }));
        setChats(stubs);

        // Restore persisted active chat, or fall back to first chat
        const savedId = localStorage.getItem("devdocs_active_chat");
        const ids = stubs.map((s) => s.id);
        const targetId = (savedId && ids.includes(savedId))
          ? savedId
          : stubs[0]?.id || null;

        if (targetId) {
          localStorage.setItem("devdocs_active_chat", targetId);
          // Immediately load the chat data before setting activeId
          // This avoids the race where activeId effect fires before stubs are committed
          loadChat(targetId, SESSION_ID)
            .then((data) => {
              setChats((prev) =>
                prev.map((c) =>
                  c.id === targetId
                    ? { ...c, messages: data.messages || [], files: data.files || [], _loaded: true }
                    : c
                )
              );
              setActiveId(targetId);
            })
            .catch(() => {
              setActiveId(targetId);
            });
        }
      })
      .catch(() => {});
  }, []);

  // ── Auto-load chat data when activeId changes ───────────────
  // Covers user clicks (mount is handled above to avoid race condition)
  useEffect(() => {
    if (!activeId) return;

    let needsFetch = false;
    setChats((prev) => {
      const chat = prev.find((c) => c.id === activeId);
      // Strict check: only skip if _loaded is exactly true
      if (!chat || chat._loaded === true || chat._loaded === "pending") return prev;
      needsFetch = true;
      return prev.map((c) =>
        c.id === activeId ? { ...c, _loaded: "pending" } : c
      );
    });

    if (!needsFetch) return;

    loadChat(activeId, SESSION_ID)
      .then((data) => {
        setChats((prev) =>
          prev.map((c) =>
            c.id === activeId
              ? { ...c, messages: data.messages || [], files: data.files || [], _loaded: true }
              : c
          )
        );
      })
      .catch(() => {
        setChats((prev) =>
          prev.map((c) => (c.id === activeId ? { ...c, _loaded: true } : c))
        );
      });
  }, [activeId]);

  // ── Select chat (fetch is handled by useEffect on activeId) ──
  const handleSelectChat = useCallback((id) => {
    setActiveId(id);
    localStorage.setItem("devdocs_active_chat", id);
  }, []);

  // ── New chat ────────────────────────────────────────────────
  const handleNewChat = useCallback(async () => {
    const { chat_id, name } = await createChat(SESSION_ID);
    const chat = { id: chat_id, name, messages: [], files: [], _loaded: true };
    setChats((prev) => [chat, ...prev]);
    setActiveId(chat_id);
    localStorage.setItem("devdocs_active_chat", chat_id);
  }, []);

  // ── Delete chat ─────────────────────────────────────────────
  const handleDeleteChat = useCallback(
    async (id) => {
      await deleteChat(id, SESSION_ID).catch(() => {});
      // Compute the next active id from the current list before filtering
      let nextActiveId = null;
      setChats((prev) => {
        const next = prev.filter((c) => c.id !== id);
        if (activeId === id) nextActiveId = next[0]?.id || null;
        return next;
      });
      // setActiveId is called OUTSIDE the updater — safe for side-effects
      if (activeId === id) {
        setActiveId(nextActiveId);
        if (nextActiveId) localStorage.setItem("devdocs_active_chat", nextActiveId);
        else localStorage.removeItem("devdocs_active_chat");
      }
    },
    [activeId]
  );

  // ── Rename chat ─────────────────────────────────────────────
  const handleRenameChat = useCallback(async (id, name) => {
    await renameChat(id, SESSION_ID, name).catch(() => {});
    setChats((prev) => prev.map((c) => (c.id === id ? { ...c, name } : c)));
  }, []);

  // ── Auto-name from first message ────────────────────────────
  const handleAutoName = useCallback(async (id, firstMessage) => {
    const name =
      firstMessage.length > 40
        ? firstMessage.slice(0, 40).trim() + "…"
        : firstMessage.trim();
    await renameChat(id, SESSION_ID, name).catch(() => {});
    setChats((prev) => prev.map((c) => (c.id === id ? { ...c, name } : c)));
  }, []);

  // ── Push a new message into local state ─────────────────────
  const pushMessage = useCallback((chatId, msg) => {
    setChats((prev) =>
      prev.map((c) =>
        c.id === chatId ? { ...c, messages: [...c.messages, msg] } : c
      )
    );
  }, []);

  // ── Update file list for a chat ─────────────────────────────
  // files contain prefixed source keys: "{chat_id}::{file_name}"
  const setFiles = useCallback((chatId, updater) => {
    setChats((prev) =>
      prev.map((c) =>
        c.id === chatId
          ? {
              ...c,
              files:
                typeof updater === "function" ? updater(c.files) : updater,
            }
          : c
      )
    );
  }, []);

  return (
    <div className="shell">
      <Sidebar
        chats={chats}
        activeId={activeId}
        onNew={handleNewChat}
        onSelect={handleSelectChat}
        onDelete={handleDeleteChat}
        onRename={handleRenameChat}
      />
      <div className="main">
        {activeChat ? (
          <ChatWindow
            key={activeChat.id}
            chat={activeChat}
            sessionId={SESSION_ID}
            onMessage={pushMessage}
            onAutoName={handleAutoName}
            onSetFiles={setFiles}
          />
        ) : (
          <div className="landing">
            <div className="landing-logo">✦</div>
            <h1>DevDocs Copilot</h1>
            <p>Ask questions about your documents</p>
            <button className="landing-btn" onClick={handleNewChat}>
              Start a new chat
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
