from prompts.prompt_templates import generate_prompt

# 5 test inputs
inputs = [
    "Garbage is piled up near my street",
    "Dirty water in the lake",
    "Too much smoke from factories",
    "Plastic waste everywhere",
    "Drainage is blocked"
]

for i, text in enumerate(inputs, 1):
    print(f"\nTest Case {i}:")
    print(generate_prompt(text))