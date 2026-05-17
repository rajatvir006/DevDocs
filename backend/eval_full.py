"""
Full system evaluation script — DevDocs Copilot RAG
Tests: retrieval, follow-up, grounding, code, isolation, latency
"""
import requests
import time
import json

BASE = "http://localhost:5000/api"
SESSION_A = "eval-session-A"
SESSION_B = "eval-session-B"

results = []

def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def ask(chat_id, session_id, q, label=""):
    start = time.time()
    r = requests.post(f"{BASE}/chat", json={
        "chat_id": chat_id,
        "session_id": session_id,
        "question": q
    })
    latency = round(time.time() - start, 2)
    data = r.json() if r.status_code == 200 else {"error": r.text}
    tag = f"[{label}] " if label else ""
    print(f"\n{tag}Q: {q}")
    print(f"   Intent : {data.get('intent', 'ERR')}")
    print(f"   Sources: {data.get('sources', [])}")
    print(f"   Latency: {latency}s")
    ans = data.get('answer', data.get('error', 'ERROR'))
    print(f"   A: {ans[:300]}")
    results.append({"label": label, "q": q, "latency": latency,
                    "intent": data.get("intent"), "answer_len": len(ans),
                    "answer_preview": ans[:200]})
    return data, latency

# ── Setup: create chats & upload test PDF ──────────────────────
section("SETUP: Creating chats & uploading test doc")

r = requests.post(f"{BASE}/chats", json={"session_id": SESSION_A})
chat_a = r.json()["chat_id"]
print(f"Chat A: {chat_a[:8]}")

r = requests.post(f"{BASE}/chats", json={"session_id": SESSION_B})
chat_b = r.json()["chat_id"]
print(f"Chat B: {chat_b[:8]}")

# Upload test PDF to Chat A only
with open(r"c:\Users\Rajat\OneDrive\Documents\Desktop\DevDocs\tests\test_data.pdf", "rb") as f:
    r = requests.post(f"{BASE}/files",
        data={"chat_id": chat_a, "session_id": SESSION_A},
        files={"file": ("test_data.pdf", f)})
print(f"Upload to Chat A: {r.status_code} — {r.json()}")

# ── TEST 1: Basic factual retrieval ───────────────────────────
section("TEST 1: Basic Factual Retrieval")
ask(chat_a, SESSION_A, "What is a heap?", "FACTUAL")
ask(chat_a, SESSION_A, "What is a priority queue?", "FACTUAL")

# ── TEST 2: Follow-up chain ──────────────────────────────────
section("TEST 2: Follow-up Chain (Conversational Memory)")
ask(chat_a, SESSION_A, "Explain the heap data structure", "CHAIN-1")
ask(chat_a, SESSION_A, "Tell me more about it", "CHAIN-2 (follow-up)")
ask(chat_a, SESSION_A, "Why is it useful?", "CHAIN-3 (vague)")
ask(chat_a, SESSION_A, "How does it compare to a regular array?", "CHAIN-4 (implicit)")

# ── TEST 3: Multi-concept reasoning ──────────────────────────
section("TEST 3: Multi-Concept Reasoning")
ask(chat_a, SESSION_A, "Explain priority queue and its relation to heap", "MULTI-CONCEPT")

# ── TEST 4: Grounding / anti-hallucination ───────────────────
section("TEST 4: Grounding (Out-of-document)")
ask(chat_a, SESSION_A, "What is the capital of France?", "GROUNDING-1")
ask(chat_a, SESSION_A, "Who is the CEO of Google?", "GROUNDING-2")
ask(chat_a, SESSION_A, "Explain quantum entanglement", "GROUNDING-3")

# ── TEST 5: Code handling ─────────────────────────────────────
section("TEST 5: Code Extraction & Explanation")
ask(chat_a, SESSION_A, "Give code for heap implementation", "CODE-EXTRACT")
ask(chat_a, SESSION_A, "Explain this code", "CODE-EXPLAIN (follow-up)")
ask(chat_a, SESSION_A, "What is the time complexity of this?", "CODE-COMPLEXITY")

# ── TEST 6: Session isolation ─────────────────────────────────
section("TEST 6: Session / File Isolation")
# Chat B has NO files uploaded — must refuse
ask(chat_b, SESSION_B, "What is a heap?", "ISOLATION-no-doc")
ask(chat_b, SESSION_B, "Explain priority queue", "ISOLATION-no-doc-2")

# ── TEST 7: Edge cases ────────────────────────────────────────
section("TEST 7: Edge Cases")
ask(chat_a, SESSION_A, "why?", "EDGE-vague-1")
ask(chat_a, SESSION_A, "what about that?", "EDGE-vague-2")
ask(chat_a, SESSION_A, "ok", "EDGE-too-short")

# ── TEST 8: Duplicate upload ──────────────────────────────────
section("TEST 8: Duplicate Upload Prevention")
with open(r"c:\Users\Rajat\OneDrive\Documents\Desktop\DevDocs\tests\test_data.pdf", "rb") as f:
    r = requests.post(f"{BASE}/files",
        data={"chat_id": chat_a, "session_id": SESSION_A},
        files={"file": ("test_data.pdf", f)})
print(f"Duplicate upload response: {r.status_code} — {r.json()}")

# ── TEST 9: Chat rename & load ───────────────────────────────
section("TEST 9: Chat Management (rename/load)")
r = requests.patch(f"{BASE}/chats/{chat_a}", json={
    "session_id": SESSION_A, "name": "Heap & DS Chat"})
print(f"Rename: {r.status_code} — {r.json()}")
r = requests.get(f"{BASE}/chats/{chat_a}", params={"session_id": SESSION_A})
data = r.json()
print(f"Load: name={data.get('name')} messages={len(data.get('messages',[]))} files={len(data.get('files',[]))}")

# ── SUMMARY ──────────────────────────────────────────────────
section("PERFORMANCE SUMMARY")
latencies = [x["latency"] for x in results]
print(f"Total queries  : {len(results)}")
print(f"Avg latency    : {round(sum(latencies)/len(latencies), 2)}s")
print(f"Max latency    : {max(latencies)}s")
print(f"Min latency    : {min(latencies)}s")
slow = [x for x in results if x["latency"] > 6]
print(f"Slow (>6s)     : {len(slow)} — {[x['label'] for x in slow]}")
