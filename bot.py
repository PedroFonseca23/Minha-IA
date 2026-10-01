import os
import sqlite3
import requests
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)
DB_HISTORICO = "chat_history.db"

# Modelo Open Source gratuito hospedado no Hugging Face (Qwen 2.5 7B Instruct)
HF_API_URL = "https://api-inference.huggingface.co/models/Qwen/Qwen2.5-7B-Instruct"

# Pode criar um token gratuito em https://huggingface.co/settings/tokens (Opcional, mas aumenta o limite)
HF_TOKEN = os.environ.get("HF_TOKEN", "")

SYSTEM_PROMPT = """
Tu és uma Inteligência Artificial própria, viva, inteligente e bem-humorada.
- Conversa de forma natural, descontraída e amiga.
- Responde a saudações com energia e personalidade.
- Escreve programas e códigos limpos quando solicitado.
- Responde sempre em português.
"""

def init_db():
    conn = sqlite3.connect(DB_HISTORICO)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            title TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            role TEXT,
            content TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@app.route("/")
def index():
    return "<h1>Servidor a rodar com sucesso!</h1>"

@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.json
    session_id = data.get("session_id")
    user_text = data.get("text", "")

    if not user_text:
        return jsonify({"error": "Escreva algo..."}), 400

    headers = {"Content-Type": "application/json"}
    if HF_TOKEN:
        headers["Authorization"] = f"Bearer {HF_TOKEN}"

    prompt = f"<|im_start|>system\n{SYSTEM_PROMPT}<|im_end|>\n<|im_start|>user\n{user_text}<|im_end|>\n<|im_start|>assistant\n"

    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": 512,
            "temperature": 0.7,
            "return_full_text": False
        }
    }

    try:
        response = requests.post(HF_API_URL, headers=headers, json=payload, timeout=30)
        res_data = response.json()

        if isinstance(res_data, list) and len(res_data) > 0:
            ai_response = res_data[0].get("generated_text", "").strip()
        else:
            ai_response = "O modelo está a arrancar no Hugging Face, tente novamente em 15 segundos."

        return jsonify({"response": ai_response})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
