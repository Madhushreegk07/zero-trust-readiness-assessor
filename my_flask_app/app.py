from flask import Flask, request, jsonify
import requests
import os
from datetime import datetime
from dotenv import load_dotenv
import threading

# Load .env file
load_dotenv(override=True)
print("API KEY LOADED:", os.getenv("GROQ_API_KEY"))

app = Flask(__name__)

# Get API key
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()


# Load prompt from file
def load_prompt(user_input):
    with open("prompt.txt", "r") as f:
        template = f.read()
    return template.replace("{input}", user_input)


# 🔹 Async AI function (Day 5)
def generate_ai_result_async(user_input):
    try:
        prompt = load_prompt(user_input)

        url = "https://api.groq.com/openai/v1/chat/completions"

        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }

        response = requests.post(url, json=payload, headers=headers)
        result = response.json()

        try:
            output = result["choices"][0]["message"]["content"]
        except:
            output = "AI failed"

        print("AI RESULT:", output)

    except Exception as e:
        print("ERROR:", str(e))


# Home route
@app.route('/')
def home():
    return "Server is running successfully"


# 🔹 Day 5 API: /describe (Async AI)
@app.route("/describe", methods=["POST"])
def describe():

    data = request.get_json()

    if not data or "input" not in data:
        return jsonify({"error": "Missing 'input' field"}), 400

    user_input = data["input"]

    # Run AI in background thread
    thread = threading.Thread(target=generate_ai_result_async, args=(user_input,))
    thread.start()

    return jsonify({
        "message": "Request received, AI processing in background",
        "input": user_input,
        "time": datetime.utcnow().isoformat()
    })


# 🔹 Recommend API
@app.route('/recommend', methods=['GET', 'POST'])
def recommend():

    print("RECOMMEND API CALLED")

    recommendations = [
        {
            "action_type": "Enable MFA",
            "description": "Enable multi-factor authentication for all users",
            "priority": "High"
        },
        {
            "action_type": "Update Software",
            "description": "Ensure all systems are updated with latest security patches",
            "priority": "Medium"
        },
        {
            "action_type": "Access Control",
            "description": "Implement role-based access control (RBAC)",
            "priority": "High"
        }
    ]

    return jsonify(recommendations)


# 🔹 Day 6 API: /generate-report
@app.route('/generate-report', methods=['POST'])
def generate_report():

    data = request.get_json()

    if not data or "input" not in data:
        return jsonify({"error": "Missing 'input' field"}), 400

    user_input = data["input"]

    report = {
        "title": "System Analysis Report",
        "summary": f"Report generated for: {user_input}",
        "overview": "This report provides a structured analysis of the input received from the user.",
        "key_items": [
            "Input received successfully",
            "Data validated",
            "Report structure generated",
            "Processing completed"
        ],
        "recommendations": [
            "Improve input validation",
            "Enhance logging system",
            "Monitor system performance continuously"
        ],
        "generated_at": datetime.utcnow().isoformat()
    }

    return jsonify(report), 200


# Run app
if __name__ == "__main__":
    app.run(debug=True)