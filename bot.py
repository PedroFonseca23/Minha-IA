import os
import io
import sqlite3
import threading
import base64
import qrcode
from flask import Flask, render_template_string
from neonize.client import NewClient
from neonize.events import MessageEv, ConnectedEv, QREv

# ==============================================================================
# 0. LIMPEZA DE SESSÃO ANTIGA (Garante geração de um novo QR Code)
# ==============================================================================
# Se existir uma sessão antiga pendente/corrompida, remove para não travar a conexão
if os.path.exists("sessao_whatsapp.db"):
    try:
        os.remove("sessao_whatsapp.db")
        print("Sessão antiga removida com sucesso. A gerar novo QR Code...")
    except Exception as e:
        print(f"Aviso ao remover sessão: {e}")

qr_code_base64 = None
status_conexao = "A iniciar o WhatsApp e a gerar o Código QR..."

# ==============================================================================
# 1. SERVIDOR WEB COM PAINEL E CÓDIGO QR
# ==============================================================================
app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="5">
    <title>Conectar IA WhatsApp</title>
    <style>
        body { font-family: Arial, sans-serif; background-color: #f0f2f5; margin: 0; padding: 20px; display: flex; justify-content: center; align-items: center; min-height: 90vh; }
        .card { background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); text-align: center; max-width: 400px; width: 100%; }
        h2 { color: #075e54; margin-bottom: 10px; }
        .qr-img { max-width: 100%; height: auto; border: 4px solid #25d366; border-radius: 8px; margin: 15px 0; }
        .status-online { color: #25d366; font-size: 1.2em; font-weight: bold; }
        .info { color: #666; font-size: 0.9em; margin-top: 15px; }
    </style>
</head>
<body>
    <div class="card">
        <h2>🤖 IA WhatsApp em Python</h2>
        {% if conectado %}
            <div class="status-online">✅ IA ONLINE e Conectada!</div>
            <p>O seu robô está ativo e a responder a mensagens no WhatsApp.</p>
        {% elif qr_img %}
            <p>Abra o WhatsApp no telemóvel > <b>Aparelhos conectados</b> > <b>Conectar um aparelho</b> e faça o scan do Código QR abaixo:</p>
            <img class="qr-img" src="data:image/png;base64,{{ qr_img }}" alt="Código QR do WhatsApp">
            <p class="info">🔄 A página atualiza automaticamente a cada 5 segundos.</p>
        {% else %}
            <p><b>Estado:</b> {{ status }}</p>
            <p class="info">🔄 A página atualiza automaticamente a cada 5 segundos. Aguarde...</p>
        {% endif %}
    </div>
</body>
</html>
"""

@app.route("/")
def home():
    conectado = (status_conexao == "ONLINE")
    return render_template_string(HTML_TEMPLATE, qr_img=qr_code_base64, status=status_conexao, conectado=conectado)

def iniciar_servidor_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=iniciar_servidor_web, daemon=True).start()

# ==============================================================================
# 2. BANCO DE DADOS LOCAL DA IA (SQLite)
# ==============================================================================
DB_PATH = "ia_memoria.db"

def inicializar_banco():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conhecimento (
            pergunta TEXT UNIQUE,
            resposta TEXT
        )
    ''')
    cursor.execute("INSERT OR IGNORE INTO conhecimento (pergunta, resposta) VALUES ('olá', 'Olá! Sou a sua IA própria em Python. Como posso ajudar?')")
    cursor.execute("INSERT OR IGNORE INTO conhecimento (pergunta, resposta) VALUES ('quais são os serviços', 'Oferecemos soluções de automação e desenvolvimento sob medida.')")
    conn.commit()
    conn.close()

def consultar_ou_ensinar_ia(texto_usuario: str) -> str:
    texto_limpo = texto_usuario.strip()

    if texto_limpo.lower().startswith("!ensinar"):
        conteudo = texto_limpo[8:].strip()
        if "=" not in conteudo:
            return "❌ Formato incorreto!\nUse: !ensinar Pergunta = Resposta"
        
        pergunta, resposta = [x.strip() for x in conteudo.split("=", 1)]
        if not pergunta or not resposta:
            return "❌ Pergunta e resposta não podem estar vazias."

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO conhecimento (pergunta, resposta) VALUES (?, ?)", (pergunta, resposta))
        conn.commit()
        conn.close()

        return f"✅ *Aprendizado Concluído em Python!*\n\n• *Pergunta:* {pergunta}\n• *Resposta:* {resposta}"

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT resposta FROM conhecimento WHERE LOWER(pergunta) = LOWER(?)", (texto_limpo,))
    resultado = cursor.fetchone()
    conn.close()

    if resultado:
        return resultado[0]
    
    return (
        f"Ainda não aprendi a responder a '{texto_limpo}'.\n\n"
        f"Para me ensinar, envie:\n"
        f"!ensinar {texto_limpo} = Sua resposta aqui"
    )

inicializar_banco()

# ==============================================================================
# 3. CONEXÃO WHATSAPP E GERADORD DE QR CODE (Neonize)
# ==============================================================================
client = NewClient("sessao_whatsapp.db")

@client.event(QREv)
def on_qr(client: NewClient, qr: QREv):
    global qr_code_base64, status_conexao
    try:
        qr_string = getattr(qr, 'code', None) or str(qr)
        img = qrcode.make(qr_string)
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        qr_code_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
        status_conexao = "Código QR pronto para leitura!"
        print("\n📱 Novo Código QR gerado com sucesso!\n")
    except Exception as e:
        status_conexao = f"Erro ao gerar QR: {e}"
        print(f"Erro ao converter Código QR em imagem: {e}")

@client.event(ConnectedEv)
def on_connected(client: NewClient, __):
    global qr_code_base64, status_conexao
    qr_code_base64 = None
    status_conexao = "ONLINE"
    print("\n✅ Conectado com sucesso ao WhatsApp! A IA em Python está pronta.\n")

@client.event(MessageEv)
def on_message(client: NewClient, message: MessageEv):
    if message.Info.MessageSource.IsFromMe:
        return

    user_text = message.Message.conversation or message.Message.extendedTextMessage.text
    chat_jid = message.Info.MessageSource.Chat

    if user_text and chat_jid:
        print(f"Mensagem recebida: {user_text}")
        resposta_ia = consultar_ou_ensinar_ia(user_text)
        client.send_message(chat_jid, resposta_ia)

print("\n--- INICIANDO CONEXÃO COM O WHATSAPP ---")
client.connect()
