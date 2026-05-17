import { useState, useRef, useEffect } from "react";

export default function Sidebar({ chats, activeId, onNew, onSelect, onDelete, onRename, user, onLogout }) {
  const [editingId, setEditingId] = useState(null);
  const [editVal, setEditVal]     = useState("");
  const inputRef = useRef(null);

  useEffect(() => { if (editingId) inputRef.current?.focus(); }, [editingId]);

  const startEdit = (e, chat) => {
    e.stopPropagation();
    setEditingId(chat.id);
    setEditVal(chat.name);
  };

  const commitEdit = (id) => {
    if (editVal.trim()) onRename(id, editVal.trim());
    setEditingId(null);
  };

  // Group chats by Today / Yesterday / Older (by index since we don't persist dates)
  const grouped = [
    { label: "Today", items: chats.slice(0, 5) },
    { label: "Previous", items: chats.slice(5) },
  ].filter((g) => g.items.length > 0);

  return (
    <aside className="sidebar">
      <div className="sidebar-top">
        <button className="new-chat-btn" onClick={onNew} title="New chat">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 5v14M5 12h14"/>
          </svg>
          New chat
        </button>
      </div>

      <div className="chat-list">
        {chats.length === 0 && (
          <p className="sidebar-empty">No chats yet</p>
        )}
        {grouped.map((group) => (
          <div key={group.label} className="chat-group">
            <div className="chat-group-label">{group.label}</div>
            {group.items.map((chat) => (
              <div
                key={chat.id}
                className={`chat-item ${chat.id === activeId ? "active" : ""}`}
                onClick={() => onSelect(chat.id)}
              >
                {editingId === chat.id ? (
                  <input
                    ref={inputRef}
                    className="rename-input"
                    value={editVal}
                    onChange={(e) => setEditVal(e.target.value)}
                    onBlur={() => commitEdit(chat.id)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") commitEdit(chat.id);
                      if (e.key === "Escape") setEditingId(null);
                    }}
                    onClick={(e) => e.stopPropagation()}
                  />
                ) : (
                  <>
                    <span className="chat-item-name">{chat.name}</span>
                    <div className="chat-item-actions">
                      <button
                        className="action-btn"
                        title="Rename"
                        onClick={(e) => startEdit(e, chat)}
                      >
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                          <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                        </svg>
                      </button>
                      <button
                        className="action-btn danger"
                        title="Delete"
                        onClick={(e) => { e.stopPropagation(); onDelete(chat.id); }}
                      >
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/>
                          <path d="M10 11v6M14 11v6"/><path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/>
                        </svg>
                      </button>
                    </div>
                  </>
                )}
              </div>
            ))}
          </div>
        ))}
      </div>

      <div className="sidebar-footer">
        <div className="sidebar-footer-info">
          <span className="footer-dot" />
          {user?.name || "DevDocs Copilot"}
        </div>
        <button className="logout-btn" onClick={onLogout} title="Sign out">
          ⎋ Sign out
        </button>
      </div>
    </aside>
  );
}
