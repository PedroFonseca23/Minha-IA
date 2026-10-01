import os
import sqlite3
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)
DB_MEMORIA = "ia_memoria.db"
DB_HISTORICO = "chat_history.db"

# ==============================================================================
# 1. INICIALIZAÇÃO DOS BANCOS DE DADOS LOCAIS
# ==============================================================================
def init_dbs():
    # Banco de Conhecimento e Memória da SUA IA
    conn = sqlite3.connect(DB_MEMORIA)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conhecimento (
            pergunta TEXT UNIQUE,
            resposta TEXT
        )
    ''')
    cursor.execute("INSERT OR IGNORE INTO conhecimento (pergunta, resposta) VALUES ('olá', 'Olá! Sou a sua própria IA em Python. Como posso ajudar?')")
    cursor.execute("INSERT OR IGNORE INTO conhecimento (pergunta, resposta) VALUES ('quais são os serviços', 'Oferecemos soluções de automação e desenvolvimento sob medida.')")
    conn.commit()
    conn.close()

    # Banco de Histórico e Sessões do Chat Web
    conn2 = sqlite3.connect(DB_HISTORICO)
    cursor2 = conn2.cursor()
    cursor2.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            title TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor2.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            role TEXT,
            content TEXT,
            image_base64 TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn2.commit()
    conn2.close()

init_dbs()

# ==============================================================================
# 2. LÓGICA DA SUA IA PRÓPRIA (SEM APIS EXTERNAS)
# ==============================================================================
def processar_com_sua_ia(texto_usuario: str, imagem_base64: str = None) -> str:
    texto_limpo = (texto_usuario or "").strip()

    # 1. Comando de Aprendizado da sua IA
    if texto_limpo.lower().startswith("!ensinar"):
        conteudo = texto_limpo[8:].strip()
        if "=" not in conteudo:
            return "❌ Formato incorreto!\nUse: !ensinar Pergunta = Resposta ou Código"
        
        pergunta, resposta = [x.strip() for x in conteudo.split("=", 1)]
        if not pergunta or not resposta:
            return "❌ Pergunta e resposta não podem estar vazias."

        conn = sqlite3.connect(DB_MEMORIA)
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO conhecimento (pergunta, resposta) VALUES (?, ?)", (pergunta, resposta))
        conn.commit()
        conn.close()

        return f"✅ **Aprendizado Concluído na sua IA!**\n\n• **Pergunta:** {pergunta}\n• **Resposta/Código:**\n{resposta}"

    # 2. Se enviou apenas imagem
    if imagem_base64 and not texto_limpo:
        return "📸 Imagem recebida com sucesso e armazenada no histórico da conversa!"

    # 3. Consulta no banco de conhecimento da sua IA
    conn = sqlite3.connect(DB_MEMORIA)
    cursor = conn.cursor()
    cursor.execute("SELECT resposta FROM conhecimento WHERE LOWER(pergunta) = LOWER(?)", (texto_limpo,))
    resultado = cursor.fetchone()
    conn.close()

    if resultado:
        resposta_ia = resultado[0]
        if imagem_base64:
            return f"📸 Imagem recebida!\n\n{resposta_ia}"
        return resposta_ia

    # 4. Resposta padrão quando a IA ainda não aprendeu o tópico
    msg_padrao = f"Ainda não aprendi a responder a '{texto_limpo}'.\n\n"
    msg_padrao += f"Para me ensinar esta resposta ou código, envie:\n"
    msg_padrao += f"`!ensinar {texto_limpo} = Sua resposta ou bloco de código aqui`"
    
    if imagem_base64:
        return f"📸 Imagem recebida!\n\n{msg_padrao}"
    return msg_padrao

# ==============================================================================
# 3. INTERFACE WEB COMPLETA (HTML / CSS / JS)
# ==============================================================================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Painel da Minha IA</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github-dark.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
        body { display: flex; height: 100vh; background-color: #1e1e2e; color: #cdd6f4; }
        
        #sidebar { width: 260px; background-color: #181825; padding: 15px; display: flex; flex-direction: column; border-right: 1px solid #313244; }
        .new-btn { background: #89b4fa; color: #11111b; border: none; padding: 12px; border-radius: 8px; font-weight: bold; cursor: pointer; margin-bottom: 15px; }
        .new-btn:hover { background: #b4befe; }
        #history-list { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 8px; }
        .history-item { padding: 10px; background: #313244; border-radius: 6px; cursor: pointer; font-size: 0.9em; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .history-item:hover, .history-item.active { background: #45475a; color: #89b4fa; }

        #main { flex: 1; display: flex; flex-direction: column; height: 100vh; }
        #chat-box { flex: 1; padding: 20px; overflow-y: auto; display: flex; flex-direction: column; gap: 15px; }
        
        .msg { max-width: 80%; padding: 14px 18px; border-radius: 12px; line-height: 1.5; font-size: 0.95em; word-wrap: break-word; }
        .msg.user { align-self: flex-end; background: #89b4fa; color: #11111b; border-bottom-right-radius: 2px; }
        .msg.model { align-self: flex-start; background: #313244; color: #cdd6f4; border-bottom-left-radius: 2px; }
        .msg img { max-width: 100%; max-height: 250px; border-radius: 8px; margin-top: 10px; display: block; }

        pre { background: #181825 !important; border-radius: 8px; padding: 12px; margin: 10px 0; overflow-x: auto; }
        code { font-family: 'Consolas', 'Courier New', monospace; font-size: 0.9em; }
        .code-header { display: flex; justify-content: space-between; align-items: center; background: #11111b; padding: 6px 12px; border-radius: 6px 6px 0 0; margin-top: 10px; font-size: 0.8em; color: #a6adc8; }
        .download-btn { background: #a6e3a1; color: #11111b; border: none; padding: 4px 10px; border-radius: 4px; font-weight: bold; cursor: pointer; font-size: 0.8em; }
        .download-btn:hover { background: #94e2d5; }

        #input-container { padding: 15px 20px; background: #181825; border-top: 1px solid #313244; display: flex; flex-direction: column; gap: 10px; }
        #preview-box { display: none; align-items: center; gap: 10px; }
        #preview-img { height: 60px; border-radius: 6px; border: 1px solid #89b4fa; }
        .remove-img { color: #f38ba8; cursor: pointer; font-weight: bold; }
        
        .input-row { display: flex; gap: 10px; align-items: center; }
        textarea { flex: 1; background: #313244; border: 1px solid #45475a; color: #cdd6f4; padding: 12px; border-radius: 8px; resize: none; height: 50px; font-size: 0.95em; outline: none; }
        textarea:focus { border-color: #89b4fa; }
        .file-label { background: #45475a; padding: 12px; border-radius: 8px; cursor: pointer; font-size: 1.2em; display: flex; align-items: center; justify-content: center; }
        .file-label:hover { background: #585b70; }
        input[type="file"] { display: none; }
        .send-btn { background: #89b4fa; color: #11111b; border: none; padding: 0 20px; height: 50px; border-radius: 8px; font-weight: bold; cursor: pointer; }
        .send-btn:hover { background: #b4befe; }
    </style>
</head>
<body>

    <div id="sidebar">
        <button class="new-btn" onclick="startNewChat()">+ Nova Conversa</button>
        <div id="history-list"></div>
    </div>

    <div id="main">
        <div id="chat-box"></div>

        <div id="input-container">
            <div id="preview-box">
                <img id="preview-img" src="" alt="Preview">
                <span class="remove-img" onclick="removeImage()">✕ Remover</span>
            </div>
            <div class="input-row">
                <label class="file-label" title="Anexar Imagem">
                    🖼️️
                    <input type="file" id="image-input" accept="image/*" onchange="handleImageSelect(event)">
                </label>
                <textarea id="user-input" placeholder="Escreva uma mensagem ou use !ensinar Pergunta = Resposta..." onkeydown="checkEnter(event)"></textarea>
                <button class="send-btn" onclick="sendMessage()">Enviar</button>
            </div>
        </div>
    </div>

    <script>
        let currentSessionId = localStorage.getItem('active_session') || Date.now().toString();
        let selectedBase64Image = null;

        document.addEventListener("DOMContentLoaded", () => {
            loadHistoryList();
            loadChatSession(currentSessionId);
        });

        function checkEnter(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        }

        function handleImageSelect(e) {
            const file = e.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function(evt) {
                    selectedBase64Image = evt.target.result;
                    document.getElementById('preview-img').src = selectedBase64Image;
                    document.getElementById('preview-box').style.display = 'flex';
                };
                reader.readAsDataURL(file);
            }
        }

        function removeImage() {
            selectedBase64Image = null;
            document.getElementById('image-input').value = '';
            document.getElementById('preview-box').style.display = 'none';
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

            messages.forEach(m => appendMessageToUI(m.role, m.content, m.image_base64));
            chatBox.scrollTop = chatBox.scrollHeight;
        }

        function startNewChat() {
            currentSessionId = Date.now().toString();
            localStorage.setItem('active_session', currentSessionId);
            document.getElementById('chat-box').innerHTML = '';
            loadHistoryList();
        }

        async function sendMessage() {
            const input = document.getElementById('user-input');
            const text = input.value.trim();
            if (!text && !selectedBase64Image) return;

            const userText = text;
            const userImg = selectedBase64Image;

            input.value = '';
            removeImage();

            appendMessageToUI('user', userText, userImg);

            const chatBox = document.getElementById('chat-box');
            chatBox.scrollTop = chatBox.scrollHeight;

            const res = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: currentSessionId,
                    text: userText,
                    image_base64: userImg
                })
            });

            const data = await res.json();
            appendMessageToUI('model', data.response);
            
            loadHistoryList();
            chatBox.scrollTop = chatBox.scrollHeight;
        }

        function appendMessageToUI(role, content, imgBase64 = null) {
            const chatBox = document.getElementById('chat-box');
            const msgDiv = document.createElement('div');
            msgDiv.className = `msg ${role}`;

            let html = '';
            if (imgBase64) {
                html += `<img src="${imgBase64}" alt="Imagem Enviada"><br>`;
            }

            if (role === 'model') {
                html += formatMarkdownWithDownloadButtons(content);
            } else {
                html += (content || '').replace(/\\n/g, '<br>');
            }

            msgDiv.innerHTML = html;
            chatBox.appendChild(msgDiv);
            
            msgDiv.querySelectorAll('pre code').forEach((block) => {
                hljs.highlightElement(block);
            });
        }

        function formatMarkdownWithDownloadButtons(markdownText) {
            const rawHtml = marked.parse(markdownText || '');
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = rawHtml;

            tempDiv.querySelectorAll('pre').forEach((pre) => {
                const codeElement = pre.querySelector('code');
                const langMatch = codeElement ? codeElement.className.match(/language-(\w+)/) : null;
                const lang = langMatch ? langMatch[1] : 'txt';

                const header = document.createElement('div');
                header.className = 'code-header';
                header.innerHTML = `<span>📄 Ficheiro (${lang.toUpperCase()})</span>
                    <button class="download-btn" onclick="downloadCode(this, '${lang}')">💾 Criar/Descarregar Ficheiro</button>`;
                
                pre.parentNode.insertBefore(header, pre);
            });

            return tempDiv.innerHTML;
        }

        function downloadCode(button, extension) {
            const header = button.parentNode;
            const pre = header.nextElementSibling;
            const code = pre.querySelector('code') ? pre.querySelector('code').innerText : pre.innerText;

            const blob = new Blob([code], { type: 'text/plain;charset=utf-8' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `ficheiro_ia_${Date.now()}.${extension}`;
            a.click();
            URL.revokeObjectURL(url);
        }
    </script>
</body>
</html>
"""

# ==============================================================================
# 4. ROTAS DA API DO CHAT
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
    cursor.execute("SELECT role, content, image_base64 FROM messages WHERE session_id = ? ORDER BY id ASC", (session_id,))
    rows = cursor.fetchall()
    conn.close()
    return jsonify([{"role": r[0], "content": r[1], "image_base64": r[2]} for r in rows])

@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.json
    session_id = data.get("session_id")
    user_text = data.get("text", "")
    image_base64 = data.get("image_base64")

    conn = sqlite3.connect(DB_HISTORICO)
    cursor = conn.cursor()

    # Cria sessão no histórico se for nova
    cursor.execute("SELECT id FROM sessions WHERE id = ?", (session_id,))
    if not cursor.fetchone():
        title = user_text[:30] if user_text else "Envio de Imagem"
        cursor.execute("INSERT INTO sessions (id, title) VALUES (?, ?)", (session_id, title))

    # Regista a mensagem do utilizador
    cursor.execute("INSERT INTO messages (session_id, role, content, image_base64) VALUES (?, ?, ?, ?)",
                   (session_id, "user", user_text, image_base64))
    conn.commit()

    # Processa a resposta usando APENAS a sua IA em Python
    resposta_ia = processar_com_sua_ia(user_text, image_base64)

    # Guarda a resposta da sua IA no histórico
    cursor.execute("INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
                   (session_id, "model", resposta_ia))
    conn.commit()
    conn.close()

    return jsonify({"response": resposta_ia})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
