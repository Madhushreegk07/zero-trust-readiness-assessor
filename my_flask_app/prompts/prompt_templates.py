def get_prompt(user_input):
    return f"Analyze this input: {user_input}"
def generate_prompt(user_input):
    return f"""
You are an AI assistant for environmental issue reporting.

Instructions:
- Classify into: Garbage, Water Pollution, Air Pollution, Plastic Waste, Drainage, Other
- Always give clear and practical actions
- Keep answers short (1 line each)

Output strictly:

Issue Type: <category>
Description: <short description>
Suggested Action: <clear action>

User Input:
{user_input}
"""