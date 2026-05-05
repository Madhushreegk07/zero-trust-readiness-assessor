from flask import Flask, request, jsonify
import requests
import os
from dotenv import load_dotenv
import time
import redis
import hashlib
import json

# Load environment variables
load_dotenv(override=True)

app = Flask(__name__)

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

@app.after_request
def after_request(response):
    elapsed = time.time() - request.start_time
    request_times.append(elapsed)

    # keep only last 100 requests (avoid memory leak)
    if len(request_times) > 100:
        request_times.pop(0)

    return response

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

    cache_key = make_cache_key(data)

    # CHECK CACHE
    if CACHE_ENABLED:
        cached = redis_client.get(cache_key)
        if cached:
            return jsonify({
                "result": json.loads(cached),
                "cached": True
            })

    user_input = data.get("input", "")

    url = "https://api.groq.com/openai/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "llama3-70b-8192",
        "messages": [
            {
                "role": "system",
                "content": "You are a Zero Trust security expert."
            },
            {
                "role": "user",
                "content": user_input
            }
        ]
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response_json = response.json()
    except Exception as e:
        return jsonify({
            "error": "API request failed",
            "details": str(e)
        }), 500

    # SAFE RESPONSE PARSING
    if "choices" in response_json:
        ai_message = response_json["choices"][0]["message"]["content"]
    else:
        ai_message = str(response_json)

    result = {
        "message": ai_message
    }

    # STORE IN CACHE
    if CACHE_ENABLED:
        redis_client.setex(cache_key, CACHE_TTL, json.dumps(result))

    return jsonify({
        "result": result,
        "cached": False
    })

# =========================
# RUN SERVER
# =========================
if __name__ == '__main__':
    app.run(debug=True)