import { useState, useRef, useEffect } from "react";
import { sendMessage, uploadFile, deleteFile, listFiles } from "../api.js";

const INTENT_COLORS = {
  specific:  "#10a37f",
  summarize: "#6366f1",
  code:      "#f59e0b",
  general:   "#6b7280",
};

// ── Strip "{chat_id}::" prefix for display ────────────────────
const displayName = (source) =>
  source.includes("::") ? source.split("::", 2)[1] : source;

// ── Markdown renderer ─────────────────────────────────────────
function MarkdownContent({ text }) {
  const parts = [];
  const fenceRe = /```(\w*)\n?([\s\S]*?)```/g;
  let last = 0, match;
  while ((match = fenceRe.exec(text)) !== null) {
    if (match.index > last)
      parts.push({ type: "text", content: text.slice(last, match.index) });
    parts.push({ type: "code", lang: match[1] || "text", content: match[2].trimEnd() });
    last = match.index + match[0].length;
  }
  if (last < text.length) parts.push({ type: "text", content: text.slice(last) });

  return (
    <div className="md-root">
      {parts.map((p, i) =>
        p.type === "code" ? (
          <div key={i} className="code-wrap">
            <div className="code-header">
              <span className="code-lang">{p.lang}</span>
              <button className="copy-btn" onClick={() => navigator.clipboard.writeText(p.content)}>
                Copy code
              </button>
            </div>
            <pre className="code-pre"><code>{p.content}</code></pre>
          </div>
        ) : (
          <div key={i} className="prose">
            {p.content.split("\n").map((line, j) => {
              const trimmed = line.trimStart();
              const isBullet = trimmed.startsWith("- ") || trimmed.startsWith("• ");
              const raw = isBullet ? trimmed.slice(2) : line;
              const toks = raw.split(/(\*\*[^*]+\*\*|`[^`]+`)/g).map((t, k) => {
                if (t.startsWith("**") && t.endsWith("**")) return <strong key={k}>{t.slice(2, -2)}</strong>;
                if (t.startsWith("`") && t.endsWith("`")) return <code key={k} className="inline-code">{t.slice(1, -1)}</code>;
                return t;
              });
              return isBullet
                ? <div key={j} className="bullet"><span className="bullet-dot">•</span><span>{toks}</span></div>
                : <div key={j} className="prose-line">{toks}</div>;
            })}
          </div>
        )
      )}
    </div>
  );
}

// ── Message ───────────────────────────────────────────────────
function Message({ msg }) {
  const isUser = msg.role === "user";
  return (
    <div className={`msg-wrap ${isUser ? "user" : "assistant"}`}>
      {!isUser && <div className="avatar assistant-avatar">✦</div>}
      <div className={`msg-bubble ${isUser ? "user-bubble" : "ai-bubble"}`}>
        {!isUser && msg.intent && (
          <span
            className="intent-pill"
            style={{
              background: INTENT_COLORS[msg.intent] + "22",
              color:      INTENT_COLORS[msg.intent],
              border:     `1px solid ${INTENT_COLORS[msg.intent]}44`,
            }}
          >
            {msg.intent}
          </span>
        )}
        {isUser
          ? <p className="user-text">{msg.content}</p>
          : <MarkdownContent text={msg.content} />}
        {!isUser && msg.sources?.length > 0 && (
          <div className="sources-row">
            <span className="sources-label">Sources:</span>
            {msg.sources.map((s) => (
              <span key={s} className="source-tag">{s}</span>
            ))}
          </div>
        )}
      </div>
      {isUser && <div className="avatar user-avatar">R</div>}
    </div>
  );
}

function Typing() {
  return (
    <div className="msg-wrap assistant">
      <div className="avatar assistant-avatar">✦</div>
      <div className="ai-bubble typing-bubble">
        <span/><span/><span/>
      </div>
    </div>
  );
}

// ── File Panel ────────────────────────────────────────────────
// files: exact metadata.source values "{chat_id}::{file_name}"
// Display strips the prefix; backend always receives the full prefixed key.
function FilePanel({ chatId, sessionId, files, setFiles }) {
  const [uploading, setUploading] = useState(false);
  const [status, setStatus]       = useState(null);
  const inputRef = useRef(null);

  // Sync file list from backend whenever this panel opens for a chat
  useEffect(() => {
    listFiles(chatId, sessionId)
      .then(({ files: f }) => setFiles(chatId, f))
      .catch(() => {});
  }, [chatId, sessionId]);

  const handleUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setStatus(null);
    try {
      // uploadFile returns { file_name: "{chat_id}::{file_name}", chunks }
      const { file_name, chunks } = await uploadFile(file, chatId, sessionId);
      setFiles(chatId, (prev) => [...new Set([...prev, file_name])]);
      setStatus({ ok: true, msg: `✓ "${displayName(file_name)}" — ${chunks} chunks` });
    } catch (err) {
      setStatus({ ok: false, msg: `✕ ${err.message}` });
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  };

  const handleDelete = async (prefixedName) => {
    try {
      await deleteFile(prefixedName, chatId, sessionId);
      setFiles(chatId, (prev) => prev.filter((f) => f !== prefixedName));
      setStatus({ ok: true, msg: `Removed "${displayName(prefixedName)}"` });
    } catch (err) {
      setStatus({ ok: false, msg: err.message });
    }
  };

  return (
    <div className="file-panel">
      <div className="file-panel-title">Documents for this chat</div>
      <label className={`upload-btn ${uploading ? "uploading" : ""}`}>
        <input
          ref={inputRef}
          type="file"
          accept=".pdf"
          hidden
          onChange={handleUpload}
          disabled={uploading}
        />
        {uploading ? "Uploading…" : "+ Upload PDF"}
      </label>
      {status && (
        <div className={`file-status ${status.ok ? "ok" : "err"}`}>{status.msg}</div>
      )}
      <div className="file-list">
        {files.length === 0 ? (
          <p className="no-files">No documents yet</p>
        ) : (
          files.map((f) => (
            <div key={f} className="file-row">
              <span className="file-icon">📄</span>
              {/* Strip prefix for display only */}
              <span className="file-name" title={displayName(f)}>{displayName(f)}</span>
              <button className="file-del" onClick={() => handleDelete(f)}>✕</button>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

// ── Main ChatWindow ───────────────────────────────────────────
export default function ChatWindow({ chat, sessionId, onMessage, onAutoName, onSetFiles }) {
  const [input, setInput]         = useState("");
  const [loading, setLoading]     = useState(false);
  const [showFiles, setShowFiles] = useState(false);
  const bottomRef   = useRef(null);
  const textareaRef = useRef(null);
  const isFirstMsg  = chat.messages.length === 0;

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chat.messages, loading]);

  // Reset loading when switching chats (safety net alongside key={chat.id})
  useEffect(() => {
    setLoading(false);
  }, [chat.id]);

  useEffect(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = Math.min(ta.scrollHeight, 200) + "px";
  }, [input]);

  const handleSend = async () => {
    const q = input.trim();
    if (!q || loading) return;
    setInput("");

    if (chat.name === "New chat") onAutoName(chat.id, q);
    onMessage(chat.id, { role: "user", content: q });
    setLoading(true);

    try {
      // Fix 2: do NOT pass chat.files — backend reads allowed_files from chat_store
      const { answer, intent, sources } = await sendMessage(
        chat.id,
        sessionId,
        q
      );
      onMessage(chat.id, { role: "assistant", content: answer, intent, sources });
    } catch (e) {
      onMessage(chat.id, {
        role:    "assistant",
        content: `Sorry, something went wrong: ${e.message}`,
        intent:  "general",
        sources: [],
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="chat-window">
      {/* Top bar */}
      <div className="chat-topbar">
        <span className="chat-topbar-title">{chat.name}</span>
        <button
          className={`files-toggle-btn ${showFiles ? "active" : ""}`}
          onClick={() => setShowFiles((v) => !v)}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
          </svg>
          Documents {chat.files?.length > 0 && `(${chat.files.length})`}
        </button>
      </div>

      <div className="chat-body">
        {/* Messages */}
        <div className="messages">
          {isFirstMsg && (
            <div className="welcome-screen">
              <div className="welcome-icon">✦</div>
              <h2 className="welcome-title">What can I help you with?</h2>
              <p className="welcome-sub">Upload a PDF using the Documents button, then ask anything about it.</p>
            </div>
          )}
          {chat.messages.map((msg, i) => <Message key={i} msg={msg} />)}
          {loading && <Typing />}
          <div ref={bottomRef} />
        </div>

        {/* File panel */}
        {showFiles && (
          <FilePanel
            chatId={chat.id}
            sessionId={sessionId}
            files={chat.files || []}
            setFiles={onSetFiles}
          />
        )}
      </div>

      {/* Input */}
      <div className="input-area">
        <div className="input-box">
          <textarea
            ref={textareaRef}
            className="input-textarea"
            placeholder="Message DevDocs Copilot…"
            value={input}
            rows={1}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); }
            }}
          />
          <button
            className={`send-btn ${loading || !input.trim() ? "disabled" : ""}`}
            onClick={handleSend}
            disabled={loading || !input.trim()}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
              <path d="M2 21L23 12 2 3v7l15 2-15 2v7z"/>
            </svg>
          </button>
        </div>
        <p className="input-disclaimer">DevDocs Copilot answers based on your uploaded documents only.</p>
      </div>
    </div>
  );
}
