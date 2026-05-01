import { useState, useEffect, useRef } from "react";
import { listFiles, uploadFile, deleteFile } from "../api";

export default function FilePanel({ files, setFiles, onClose }) {
  const [uploading, setUploading] = useState(false);
  const [status, setStatus] = useState(null);
  const inputRef = useRef(null);

  useEffect(() => {
    listFiles().then(({ files }) => setFiles(files)).catch(() => {});
  }, [setFiles]);

  const handleUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setStatus(null);
    try {
      const { file_name, chunks } = await uploadFile(file);
      setFiles((prev) => [...new Set([...prev, file_name])]);
      setStatus({ ok: true, msg: `✓ Ingested "${file_name}" — ${chunks} chunks` });
    } catch (err) {
      setStatus({ ok: false, msg: `✕ ${err.message}` });
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  };

  const handleDelete = async (name) => {
    try {
      await deleteFile(name);
      setFiles((prev) => prev.filter((f) => f !== name));
      setStatus({ ok: true, msg: `Removed "${name}"` });
    } catch (err) {
      setStatus({ ok: false, msg: err.message });
    }
  };

  return (
    <div className="file-panel">
      <div className="file-panel-header">
        <span>Documents</span>
        <button className="icon-btn" onClick={onClose}>✕</button>
      </div>

      <label className={`upload-zone ${uploading ? "uploading" : ""}`}>
        <input
          ref={inputRef}
          type="file"
          accept=".pdf"
          hidden
          onChange={handleUpload}
          disabled={uploading}
        />
        <span className="upload-icon">⊕</span>
        <span>{uploading ? "Ingesting…" : "Click to upload PDF"}</span>
      </label>

      {status && (
        <div className={`upload-status ${status.ok ? "ok" : "err"}`}>
          {status.msg}
        </div>
      )}

      <div className="file-list">
        {files.length === 0 && (
          <p className="no-files">No documents ingested yet.</p>
        )}
        {files.map((f) => (
          <div key={f} className="file-item">
            <span className="file-icon">📄</span>
            <span className="file-name" title={f}>{f}</span>
            <button
              className="icon-btn danger"
              onClick={() => handleDelete(f)}
              title="Remove from DB"
            >✕</button>
          </div>
        ))}
      </div>
    </div>
  );
}
