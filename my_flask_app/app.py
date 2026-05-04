from flask import Flask, request, jsonify
import requests
import os
from datetime import datetime
from dotenv import load_dotenv

# Load .env file
load_dotenv(override=True)
print("API KEY LOADED:", os.getenv("GROQ_API_KEY")) 

app = Flask(__name__)

# Get API key
GROQ_API_KEY = os.getenv("GROQ_API_KEY","").strip()


# Function to load prompt
def load_prompt(user_input):
    with open("prompt.txt", "r") as f:
        template = f.read()
    return template.replace("{input}", user_input)


# POST API - Describe
@app.route('/')
def home():
    return "Server is running successfully"
@app.route("/describe", methods=["POST"])
def describe():

    # 1. Get input from request
    data = request.get_json()

    # 2. Validate input
    if not data or "input" not in data:
        return jsonify({"error": "Missing 'input' field"}), 400

    user_input = data["input"]

    # 3. Load prompt
    prompt = load_prompt(user_input)

    # 4. Call Groq API
    print("USING KEY:", GROQ_API_KEY[:10])
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

    # 5. Extract output safely
    try:
        output = result["choices"][0]["message"]["content"]
    except:
        return jsonify({
            "error": "Groq API failed",
            "details": result
        }), 500

    # 6. Return final response
    return jsonify({
        "input": user_input,
        "output": output,
        "generated_at": datetime.utcnow().isoformat()
    })


# POST API - Recommend
@app.route('/recommend', methods=['GET','POST'])
def recommend():
    print("RECOMMEND API CALLED") 
    data = request.get_json(silent=True)

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
# Run app
if __name__ == "__main__":
    app.run(debug=True)