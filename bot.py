import os
import sqlite3
from flask import Flask, render_template_string, request, jsonify
from huggingface_hub import hf_hub_download
from llama_cpp import Llama

app = Flask(__name__)
DB_HISTORICO = "chat_history.db"

# ==============================================================================
# 1. CARREGAR O CÉREBRO PRÓPRIO DENTRO DO PYTHON (SEM API)
# ==============================================================================
print("🧠 A carregar o teu cérebro próprio para a memória...")

# Descarrega o modelo leve de 350MB diretamente para o teu servidor na 1ª vez
MODEL_PATH = hf_hub_download(
    repo_id="Qwen/Qwen2.5-0.5B-Instruct-GGUF",
    filename="qwen2.5-0.5b-instruct-q4_k_m.gguf"
)

# Inicializa o motor local de linguagem dentro do próprio Python
llm = Llama(
    model_path=MODEL_PATH,
    n_ctx=2048,           # Contexto da conversa
    n_threads=2,          # Threads da CPU
    verbose=False
)

SYSTEM_PROMPT = """
Tu és uma Inteligência Artificial própria, viva, inteligente e bem-humorada.
- Pensa e conversa de forma natural, descontraída e amigável.
- Responde a saudações com energia e personalidade.
- És capaz de criar códigos limpos quando solicitado.
- Responde sempre em português.
"""

# ==============================================================================
# 2. BANCO DE DADOS DO HISTÓRICO
# ==============================================================================
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

# ==============================================================================
# 3. INTERFACE WEB INTERATIVA (MOBILE & PC)
# ==============================================================================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Meu Cérebro Próprio IA</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/tokyo-night-dark.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <style>
        :root {
            --bg-body: #0b0f19;
            --bg-sidebar: #111827;
            --bg-card: #1f2937;
            --accent: #6366f1;
            --accent-hover: #4f46e5;
            --text-primary: #f9fafb;
            --text-muted: #9ca3af;
            --user-bubble: #3730a3;
            --ai-bubble: #1f2937;
            --border: #374151;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }

        body {
            display: flex;
            height: 100dvh;
            background-color: var(--bg-body);
            color: var(--text-primary);
            overflow: hidden;
        }

        #overlay {
            display: none;
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.6);
            backdrop-filter: blur(4px);
            z-index: 90;
        }

        #sidebar {
            width: 280px;
            background: var(--bg-sidebar);
            padding: 16px;
            display: flex;
            flex-direction: column;
            border-right: 1px solid var(--border);
            z-index: 100;
            transition: transform 0.3s ease;
        }

        .new-btn {
            background: var(--accent);
            color: white;
            border: none;
            padding: 14px;
            border-radius: 12px;
            font-weight: 600;
            cursor: pointer;
            font-size: 0.95em;
            box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
        }

        .history-title {
            font-size: 0.75em;
            text-transform: uppercase;
            color: var(--text-muted);
            margin: 20px 0 10px 4px;
            font-weight: 700;
        }

        #history-list { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 8px; }

        .history-item {
            padding: 12px;
            background: rgba(31, 41, 55, 0.6);
            border-radius: 8px;
            cursor: pointer;
            font-size: 0.88em;
            color: var(--text-muted);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            border: 1px solid transparent;
        }
        .history-item.active, .history-item:hover {
            background: var(--bg-card);
            color: var(--text-primary);
            border-color: var(--accent);
        }

        #main { flex: 1; display: flex; flex-direction: column; height: 100dvh; position: relative; }

        .topbar {
            height: 60px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 16px;
            background: var(--bg-sidebar);
            border-bottom: 1px solid var(--border);
        }

        .menu-btn { background: none; border: none; color: var(--text-primary); font-size: 1.6em; cursor: pointer; }
        .topbar-title { font-weight: 700; font-size: 1.05em; display: flex; align-items: center; gap: 8px; }
        .badge-local { background: #059669; color: white; font-size: 0.65em; padding: 2px 8px; border-radius: 12px; font-weight: 600; }

        #chat-box {
            flex: 1;
            padding: 16px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 16px;
        }

        .msg { max-width: 88%; padding: 14px 16px; border-radius: 16px; line-height: 1.6; font-size: 0.95em; word-wrap: break-word; }
        .msg.user { align-self: flex-end; background: var(--user-bubble); color: #e0e7ff; border-bottom-right-radius: 4px; }
        .msg.model { align-self: flex-start; background: var(--ai-bubble); color: var(--text-primary); border: 1px solid var(--border); border-bottom-left-radius: 4px; }

        pre { background: #050811 !important; border-radius: 10px; padding: 12px; margin: 10px 0; overflow-x: auto; border: 1px solid var(--border); }
        code { font-family: monospace; font-size: 0.88em; }

        .code-header {
            display: flex; justify-content: space-between; align-items: center;
            background: #111827; padding: 8px 12px; border-radius: 8px 8px 0 0;
            font-size: 0.8em; color: var(--text-muted); border: 1px solid var(--border); border-bottom: none; margin-top: 10px;
        }
        .btn-code { background: #2563eb; color: white; border: none; padding: 4px 8px; border-radius: 6px; font-size: 0.75em; cursor: pointer; margin-left: 4px; }

        #input-container { padding: 12px 16px; background: var(--bg-sidebar); border-top: 1px solid var(--border); display: flex; gap: 10px; }
        textarea {
            flex: 1; background: var(--bg-card); border: 1px solid var(--border);
            color: var(--text-primary); padding: 12px; border-radius: 12px; resize: none;
            height: 48px; max-height: 120px; font-size: 0.95em; outline: none;
        }
        textarea:focus { border-color: var(--accent); }
        .send-btn { background: var(--accent); color: white; border: none; width: 48px; height: 48px; border-radius: 12px; font-size: 1.2em; cursor: pointer; flex-shrink: 0; }

        /* Animação a pensar */
        .thinking { display: flex; gap: 4px; padding: 12px; }
        .thinking div { width: 8px; height: 8px; background: var(--text-muted); border-radius: 50%; animation: pulse 1.2s infinite ease-in-out; }
        .thinking div:nth-child(2) { animation-delay: 0.2s; }
        .thinking div:nth-child(3) { animation-delay: 0.4s; }
        @keyframes pulse { 0%, 100% { opacity: 0.3; } 50% { opacity: 1; } }

        @media (max-width: 768px) {
            #sidebar { position: fixed; top: 0; bottom: 0; left: 0; transform: translateX(-100%); }
            #sidebar.open { transform: translateX(0); }
            .msg { max-width: 92%; }
        }
        @media (min-width: 769px) { .menu-btn { display: none; } }
    </style>
</head>
<body>

    <div id="overlay" onclick="closeSidebar()"></div>

    <div id="sidebar">
        <button class="new-btn" onclick="startNewChat()">✨ Nova Conversa</button>
        <div class="history-title">Conversas Anteriores</div>
        <div id="history-list"></div>
    </div>

    <div id="main">
        <div class="topbar">
            <button class="menu-btn" onclick="toggleSidebar()">☰</button>
            <div class="topbar-title">
                🧠 Cérebro Local <span class="badge-local">SEM API</span>
            </div>
            <div style="width:24px;"></div>
        </div>

        <div id="chat-box"></div>

        <div id="input-container">
            <textarea id="user-input" placeholder="Conversa com o teu cérebro local..." onkeydown="checkEnter(event)"></textarea>
            <button class="send-btn" onclick="sendMessage()">➔</button>
        </div>
    </div>

    <script>
        let currentSessionId = localStorage.getItem('active_session') || Date.now().toString();

        document.addEventListener("DOMContentLoaded", () => {
            loadHistoryList();
            loadChatSession(currentSessionId);
        });

        function toggleSidebar() {
            document.getElementById('sidebar').classList.toggle('open');
            const overlay = document.getElementById('overlay');
            overlay.style.display = overlay.style.display === 'block' ? 'none' : 'block';
        }

        function closeSidebar() {
            document.getElementById('sidebar').classList.remove('open');
            document.getElementById('overlay').style.display = 'none';
        }

        function checkEnter(e) {
            if (e.key === 'Enter' && !e.shiftKey && window.innerWidth > 768) {
                e.preventDefault();
                sendMessage();
            }
        }

        async function loadHistoryList() {
            const res = await fetch('/api/history');
            const sessions = await res.json();
            const list = document.getElementById('history-list');
            list.innerHTML = '';

            sessions.forEach(s => {
                const item = document.createElement('div');
                item.className = `history-item ${s.id === currentSessionId ? 'active' : ''}`;
                item.innerText = s.title || 'Conversa sem título';
                item.onclick = () => {
                    currentSessionId = s.id;
                    localStorage.setItem('active_session', currentSessionId);
                    closeSidebar();
                    loadHistoryList();
                    loadChatSession(s.id);
                };
                list.appendChild(item);
            });
        }

        async function loadChatSession(sessionId) {
            currentSessionId = sessionId;
            localStorage.setItem('active_session', sessionId);
            const res = await fetch(`/api/chat/${sessionId}`);
            const messages = await res.json();
            const chatBox = document.getElementById('chat-box');
            chatBox.innerHTML = '';

            if (messages.length === 0) {
                appendMsg('model', 'Olá! Sou o teu cérebro local próprio. Como estou a rodar diretamente no teu servidor (sem nenhuma API), podes conversar comigo à vontade!');
            } else {
                messages.forEach(m => appendMsg(m.role, m.content));
            }
            chatBox.scrollTop = chatBox.scrollHeight;
        }

        function startNewChat() {
            currentSessionId = Date.now().toString();
            localStorage.setItem('active_session', currentSessionId);
            closeSidebar();
            loadChatSession(currentSessionId);
            loadHistoryList();
        }

        async function sendMessage() {
            const input = document.getElementById('user-input');
            const text = input.value.trim();
            if (!text) return;

            input.value = '';
            appendMsg('user', text);
            showThinking();

            const chatBox = document.getElementById('chat-box');
            chatBox.scrollTop = chatBox.scrollHeight;

            try {
                const res = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ session_id: currentSessionId, text: text })
                });

                removeThinking();
                const data = await res.json();

                if (data.error) {
                    appendMsg('model', `❌ Erro: ${data.error}`);
                } else {
                    appendMsg('model', data.response);
                }
            } catch (e) {
                removeThinking();
                appendMsg('model', '❌ Erro de processamento no servidor local.');
            }

            loadHistoryList();
            chatBox.scrollTop = chatBox.scrollHeight;
        }

        function showThinking() {
            const chatBox = document.getElementById('chat-box');
            const div = document.createElement('div');
            div.id = 'thinking-msg';
            div.className = 'msg model';
            div.innerHTML = `<div class="thinking"><div></div><div></div><div></div></div>`;
            chatBox.appendChild(div);
        }

        function removeThinking() {
            const el = document.getElementById('thinking-msg');
            if (el) el.remove();
        }

        function appendMsg(role, content) {
            const chatBox = document.getElementById('chat-box');
            const msgDiv = document.createElement('div');
            msgDiv.className = `msg ${role}`;

            if (role === 'model') {
                msgDiv.innerHTML = formatMarkdown(content);
            } else {
                msgDiv.innerText = content;
            }

            chatBox.appendChild(msgDiv);
            msgDiv.querySelectorAll('pre code').forEach((block) => {
                hljs.highlightElement(block);
            });
        }

        function formatMarkdown(text) {
            const rawHtml = marked.parse(text || '');
            const temp = document.createElement('div');
            temp.innerHTML = rawHtml;

            temp.querySelectorAll('pre').forEach((pre) => {
                const code = pre.querySelector('code');
                const lang = code && code.className.match(/language-(\w+)/) ? code.className.match(/language-(\w+)/)[1] : 'code';

                const header = document.createElement('div');
                header.className = 'code-header';
                header.innerHTML = `<span>💻 ${lang.toUpperCase()}</span>
                    <div>
                        <button class="btn-code" onclick="copyCode(this)">📋 Copiar</button>
                        <button class="btn-code" onclick="downloadCode(this, '${lang}')">💾 Baixar</button>
                    </div>`;
                pre.parentNode.insertBefore(header, pre);
            });

            return temp.innerHTML;
        }

        function copyCode(btn) {
            const pre = btn.parentNode.parentNode.nextElementSibling;
            const code = pre.querySelector('code') ? pre.querySelector('code').innerText : pre.innerText;
            navigator.clipboard.writeText(code).then(() => {
                btn.innerText = '✅ Copiado!';
                setTimeout(() => btn.innerText = '📋 Copiar', 2000);
            });
        }

        function downloadCode(btn, ext) {
            const pre = btn.parentNode.parentNode.nextElementSibling;
            const code = pre.querySelector('code') ? pre.querySelector('code').innerText : pre.innerText;
            const blob = new Blob([code], { type: 'text/plain;charset=utf-8' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `codigo_${Date.now()}.${ext}`;
            a.click();
            URL.revokeObjectURL(url);
        }
    </script>
</body>
</html>
"""

# ==============================================================================
# 4. ROTAS DA APLICAÇÃO
# ==============================================================================
@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route("/api/history", methods=["GET"])
def get_history():
    conn = sqlite3.connect(DB_HISTORICO)
    cursor = conn.cursor()
    cursor.execute("SELECT id, title FROM sessions ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return jsonify([{"id": r[0], "title": r[1]} for r in rows])

@app.route("/api/chat/<session_id>", methods=["GET"])
def get_session_messages(session_id):
    conn = sqlite3.connect(DB_HISTORICO)
    cursor = conn.cursor()
    cursor.execute("SELECT role, content FROM messages WHERE session_id = ? ORDER BY id ASC", (session_id,))
    rows = cursor.fetchall()
    conn.close()
    return jsonify([{"role": r[0], "content": r[1]} for r in rows])

@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.json
    session_id = data.get("session_id")
    user_text = data.get("text", "")

    if not user_text:
        return jsonify({"error": "Escreva uma mensagem..."}), 400

    conn = sqlite3.connect(DB_HISTORICO)
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM sessions WHERE id = ?", (session_id,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO sessions (id, title) VALUES (?, ?)", (session_id, user_text[:30]))

    cursor.execute("INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
                   (session_id, "user", user_text))
    conn.commit()

    # Carregar contexto para o cérebro local
    cursor.execute("SELECT role, content FROM messages WHERE session_id = ? ORDER BY id ASC", (session_id,))
    history_rows = cursor.fetchall()

    # Formatação do prompt para o modelo Qwen/Llama
    full_prompt = f"<|im_start|>system\n{SYSTEM_PROMPT}<|im_end|>\n"
    for role, content in history_rows:
        sender = "user" if role == "user" else "assistant"
        full_prompt += f"<|im_start|>{sender}\n{content}<|im_end|>\n"
    full_prompt += "<|im_start|>assistant\n"

    try:
        # Inferência feita 100% no teu próprio código
        output = llm(
            full_prompt,
            max_tokens=512,
            temperature=0.7,
            stop=["<|im_end|>"]
        )

        ai_response = output["choices"][0]["text"].strip()

        cursor.execute("INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
                       (session_id, "model", ai_response))
        conn.commit()
        conn.close()

        return jsonify({"response": ai_response})

    except Exception as e:
        conn.close()
        return jsonify({"error": f"Erro no cérebro local: {str(e)}"}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
