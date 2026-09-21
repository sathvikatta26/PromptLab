from transformers import pipeline

generator = pipeline(
    "text-generation",
    model="gpt2"
)

result = generator(
    "Prompt engineering is",
    max_new_tokens=50
)

print(result[0]["generated_text"])