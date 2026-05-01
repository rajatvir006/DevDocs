import os
import requests
from fpdf import FPDF
import time
import json

BASE_URL = "http://localhost:5000/api"
SESSION_ID = "test-session-123"

class PDF(FPDF):
    pass

pdf = PDF()
pdf.add_page()
pdf.set_font("Arial", size=12)

content = """
# Data Structures: Heap and Priority Queue

A heap is a specialized tree-based data structure that satisfies the heap property. 
In a max heap, for any given node C, if P is a parent node of C, then the key of P is greater than or equal to the key of C.
It is very useful because it allows for efficient extraction of the maximum or minimum element, making it ideal for priority queues.

A priority queue is an abstract data type similar to a regular queue or stack in which each element additionally has a "priority" associated with it. 
In a priority queue, an element with high priority is served before an element with low priority. 
It relates to a heap because a heap is the most efficient and common way to implement a priority queue.

For example, consider a hospital waiting room where patients are assigned a priority number based on the severity of their condition.
A patient with a severe injury (high priority) will be treated before someone with a minor cut (low priority), even if the minor cut arrived earlier.
This example demonstrates how elements are served based on priority rather than insertion order.

Here is a code for heap implementation in Python:
```python
class MinHeap:
    def __init__(self):
        self.heap = []
    
    def insert(self, val):
        self.heap.append(val)
        self._bubble_up(len(self.heap) - 1)
        
    def _bubble_up(self, index):
        parent = (index - 1) // 2
        if index > 0 and self.heap[index] < self.heap[parent]:
            self.heap[index], self.heap[parent] = self.heap[parent], self.heap[index]
            self._bubble_up(parent)
```
The time complexity for insertion in this code is O(log n), because we might need to bubble up the element up to the root of the tree.

Topic A is about Machine Learning. Machine learning is a field of study that gives computers the ability to learn without being explicitly programmed.
Topic B is about Databases. A database is an organized collection of data, generally stored and accessed electronically from a computer system.
"""

pdf.multi_cell(0, 10, content.encode('latin-1', 'replace').decode('latin-1'))
test_pdf = os.path.join(os.path.dirname(__file__), "test_data.pdf")
pdf.output(test_pdf)

res = requests.post(f"{BASE_URL}/chats", json={"session_id": SESSION_ID})
chat_id = res.json()["chat_id"]

with open(test_pdf, "rb") as f:
    res = requests.post(f"{BASE_URL}/files", data={"chat_id": chat_id, "session_id": SESSION_ID}, files={"file": ("test_data.pdf", f)})

def ask(q):
    print(f"\n--- Q: {q} ---")
    res = requests.post(f"{BASE_URL}/chat", json={"chat_id": chat_id, "session_id": SESSION_ID, "question": q})
    if res.status_code == 200:
        data = res.json()
        print(f"Intent: {data.get('intent')}")
        print(f"A: {data.get('answer')}")
    else:
        print(f"Error: {res.status_code} {res.text}")

print("\n=== TEST 1 ===")
ask("What is a heap?")
ask("Tell more about it")
ask("Why is it useful?")

print("\n=== TEST 2 ===")
ask("Explain priority queue")
ask("How does it relate to heap?")
ask("Give an example")
ask("Explain that example")

print("\n=== TEST 3 ===")
ask("Give code for heap implementation")
ask("Explain this code")
ask("What is the time complexity?")

print("\n=== TEST 4 ===")
ask("Tell me about Topic A")
ask("Tell me about Topic B")
ask("Explain it more")

print("\n=== TEST 5 ===")
ask("Explain more")
ask("why?")
ask("what about that?")
