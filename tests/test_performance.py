import os
import requests
import time

BASE_URL = "http://localhost:5000/api"
SESSION_ID = "perf-test-session"

res = requests.post(f"{BASE_URL}/chats", json={"session_id": SESSION_ID})
chat_id = res.json()["chat_id"]
test_pdf = os.path.join(os.path.dirname(__file__), "test_data.pdf")
with open(test_pdf, "rb") as f:
    res = requests.post(f"{BASE_URL}/files", data={"chat_id": chat_id, "session_id": SESSION_ID}, files={"file": ("test_data.pdf", f)})

def ask(q):
    print(f"\n--- Q: {q} ---")
    start = time.time()
    res = requests.post(f"{BASE_URL}/chat", json={"chat_id": chat_id, "session_id": SESSION_ID, "question": q})
    latency = time.time() - start
    if res.status_code == 200:
        data = res.json()
        print(f"Latency: {latency:.2f}s")
        print(f"Intent: {data.get('intent')}")
        print(f"A: {data.get('answer')}")
    else:
        print(f"Error: {res.status_code} {res.text}")

print("\n=== TEST 1 ===")
ask("Explain heap data structure in detail")

print("\n=== TEST 2 ===")
ask("Tell more about it")
ask("Why is it useful?")

print("\n=== TEST 3 ===")
ask("Explain priority queue and its relation to heap")

print("\n=== TEST 4 ===")
ask("Give code for heap implementation")
ask("Explain this code")

print("\n=== TEST 5 ===")
ask("why?")
ask("how?")
ask("what about that?")
