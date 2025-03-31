import openai
import os

openai.api_key = os.getenv("OPENAI_API_KEY")

def generate_summary(korean_text: str) -> str:
    prompt = f"""
You are a professional business assistant. Please summarize the following Korean sentence into clean, polite English suitable for a supplier email. Remove informal phrases and keep it clear:

"{korean_text}"

Return only the final English version without extra explanations.
"""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        return response['choices'][0]['message']['content'].strip()
    except Exception as e:
        return f"[GPT ERROR] {e}"

def generate_followup(inquiry_summary: str) -> str:
    prompt = f"""
Based on the following context, write a polite follow-up email in English asking the supplier to kindly check again and reply as soon as possible:

Context: {inquiry_summary}

Return only the body of the email.
"""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        return response['choices'][0]['message']['content'].strip()
    except Exception as e:
        return f"[GPT ERROR] {e}"
