from flask import Flask, request, jsonify
import requests
import os
from dotenv import load_dotenv
import time
import redis
import hashlib
import json

# ✅ NEW: Sentence Transformer
from sentence_transformers import SentenceTransformer

# Hide server version completely
from werkzeug.serving import WSGIRequestHandler
WSGIRequestHandler.server_version = ""
WSGIRequestHandler.sys_version = ""

# Load environment variables
load_dotenv(override=True)

app = Flask(__name__)

# ✅ OPTIONAL SECURITY: Limit request size (1MB)
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024

# =========================
# LOAD MODEL AT STARTUP
# =========================
print("Loading SentenceTransformer model...")
model = SentenceTransformer("all-MiniLM-L6-v2")
print("Model loaded successfully!")

# =========================
# API KEY
# =========================
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY is missing in .env file")

# =========================
# REDIS CACHE SETUP
# =========================
try:
    redis_client = redis.Redis(host='localhost', port=6379, db=0)
    redis_client.ping()
    CACHE_ENABLED = True
except:
    print("Redis not available. Running without cache.")
    redis_client = None
    CACHE_ENABLED = False

CACHE_TTL = 900  # 15 minutes

# =========================
# METRICS
# =========================
start_time = time.time()
request_times = []

@app.before_request
def before_request():
    request.start_time = time.time()

# =========================
# SECURITY + METRICS
# =========================
@app.after_request
def apply_security_and_metrics(response):
    # -------- SECURITY HEADERS --------
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self'; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "font-src 'self'; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "frame-ancestors 'none'; "
        "form-action 'self';"
    )

    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=()"

    # Remove server header
    response.headers.pop("Server", None)

    # -------- METRICS --------
    elapsed = time.time() - request.start_time
    request_times.append(elapsed)

    if len(request_times) > 100:
        request_times.pop(0)

    return response

# =========================
# ROBOTS.TXT
# =========================
@app.route('/robots.txt')
def robots():
    return "User-agent: *\nDisallow:", 200, {"Content-Type": "text/plain"}

# =========================
# HEALTH CHECK
# =========================
@app.route('/health', methods=['GET'])
def health():
    uptime = time.time() - start_time

    avg_response = (
        sum(request_times) / len(request_times)
        if request_times else 0
    )

    return jsonify({
        "status": "ok",
        "model": "zero-trust-ai-v1",
        "uptime_seconds": round(uptime, 2),
        "avg_response_time_sec": round(avg_response, 4),
        "total_requests_tracked": len(request_times),
        "cache_enabled": CACHE_ENABLED
    })

# =========================
# ROOT ROUTE
# =========================
@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "message": "Zero Trust API is running"
    })

# =========================
# CACHE KEY FUNCTION
# =========================
def make_cache_key(data: dict):
    key_string = json.dumps(data, sort_keys=True)
    return hashlib.sha256(key_string.encode()).hexdigest()

# =========================
# MAIN AI ROUTE
# =========================
@app.route('/recommend', methods=['POST'])
def recommend():
    data = request.get_json(silent=True) or {}

    if not isinstance(data, dict):
        return jsonify({"error": "Invalid input"}), 400

    user_input = data.get("input", "")

    # -------- INPUT VALIDATION --------
    if not isinstance(user_input, str) or len(user_input) > 1000:
        return jsonify({"error": "Invalid input"}), 400

    # ✅ NEW: Generate embedding
    embedding = model.encode(user_input).tolist()

    cache_key = make_cache_key(data)

    # -------- CACHE CHECK --------
    if CACHE_ENABLED:
        cached = redis_client.get(cache_key)
        if cached:
            return jsonify({
                "result": json.loads(cached),
                "cached": True,
                "is_fallback": False
            })

    url = "https://api.groq.com/openai/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": "You are a Zero Trust security expert."},
            {"role": "user", "content": user_input}
        ]
    }

    fallback_response = {
        "message": "AI service temporarily unavailable. Showing default recommendation."
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)

        try:
            response_json = response.json()
        except:
            return jsonify({
                "result": fallback_response,
                "is_fallback": True
            })

    except Exception:
        return jsonify({
            "result": fallback_response,
            "is_fallback": True
        })

    # -------- HANDLE API ERROR --------
    if "error" in response_json:
        return jsonify({
            "result": fallback_response,
            "is_fallback": True
        })

    # -------- SAFE PARSING --------
    if "choices" in response_json:
        ai_message = response_json["choices"][0]["message"]["content"]
    else:
        ai_message = str(response_json)

    result = {
        "message": ai_message
    }

    # -------- CACHE STORE --------
    if CACHE_ENABLED:
        redis_client.setex(cache_key, CACHE_TTL, json.dumps(result))

    return jsonify({
        "result": result,
        "cached": False,
        "is_fallback": False
    })

# =========================
# RUN SERVER
# =========================
if __name__ == '__main__':
    app.run(debug=False)