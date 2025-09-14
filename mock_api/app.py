from flask import Flask, request, jsonify
from dateutil import parser
import os, time, random, uuid, threading
from generator import DataStore

API_KEY = os.environ["API_KEY"]
RATE = int(os.environ.get("API_RATE_LIMIT_PER_MIN", "60"))
WINDOW = 60

app = Flask(__name__)
store = DataStore()

# thread-safe in-memory rate limiter
lock = threading.Lock()
last_reset = time.time()
count = 0

def check_rate_limit():
    global last_reset, count
    now = time.time()
    with lock:
        if now - last_reset > WINDOW:
            last_reset = now
            count = 0
        count += 1
        if count > RATE:
            return False
        return True


def require_auth():
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer ") or auth.split(" ",1)[1] != API_KEY:
        return False
    return True


def maybe_chaos():
    # ~2% internal errors
    if random.random() < 0.02:
        resp = jsonify({"error":"internal_error","id":str(uuid.uuid4())})
        resp.status_code = 500
        return resp
    return None


def paginate(items, page, page_size):
    total = len(items)
    total_pages = (total + page_size - 1) // page_size
    start = (page-1)*page_size
    end = start + page_size
    data = items[start:end]
    next_page = page+1 if page < total_pages else None
    return {
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "next_page": next_page,
        "count": len(data),
        "data": data,
    }

@app.get("/health")
def health():
    return {"status":"ok"}

@app.get("/customers")
@app.get("/payments")
@app.get("/sessions")
def list_resources():
    if not require_auth():
        return jsonify({"error":"unauthorized"}), 401
    if not check_rate_limit():
        return jsonify({"error":"rate_limited","retry_after":30}), 429
    chaos = maybe_chaos()
    if chaos:
        return chaos

    path = request.path.strip("/")
    if path == "customers":
        items = store.customers
    elif path == "payments":
        items = store.payments
    else:
        items = store.sessions

    # filtering (minimal examples)
    qs = request.args
    updated_since = qs.get("updated_since")
    if updated_since:
        ts = parser.isoparse(updated_since)
        items = [i for i in items if parser.isoparse(i.get("updated_at") or i.get("created_at") or i.get("session_start")) >= ts]

    # example filters
    status = qs.get("status")
    if status and path == "payments":
        items = [i for i in items if i["status"] == status]
    country = qs.get("country")
    if country:
        items = [i for i in items if i.get("country") == country]

    source = qs.get("source")
    if source and path == "sessions":
        items = [i for i in items if i.get("source") == source]

    page = int(qs.get("page", 1))
    page_size = min(int(qs.get("page_size", 500)), 1000)
    return jsonify(paginate(items, page, page_size))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
