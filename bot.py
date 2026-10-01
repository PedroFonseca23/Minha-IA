import os
import sqlite3
from neonize.client import NewClient
from neonize.events import MessageEv, ConnectedEv

# ==============================================================================
# 1. BANCO DE DADOS LOCAL DA IA (SQLite)
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
    # Mensagens iniciais de exemplo
    cursor.execute("INSERT OR IGNORE INTO conhecimento (pergunta, resposta) VALUES ('olá', 'Olá! Sou a sua IA própria em Python. Como posso ajudar?')")
    cursor.execute("INSERT OR IGNORE INTO conhecimento (pergunta, resposta) VALUES ('quais são os serviços', 'Oferecemos soluções de automação e desenvolvimento sob medida.')")
    conn.commit()
    conn.close()

def consultar_ou_ensinar_ia(texto_usuario: str) -> str:
    texto_limpo = texto_usuario.strip()

    # Comando para ensinar a IA diretamente pelo WhatsApp
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

    # Buscar resposta no banco de dados
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

# Inicializa o banco de memória
inicializar_banco()

# ==============================================================================
# 2. CONEXÃO COM O WHATSAPP E QR CODE (Neonize)
# ==============================================================================
client = NewClient("sessao_whatsapp.db")

@client.event(ConnectedEv)
def on_connected(client: NewClient, __):
    print("\n✅ Conectado com sucesso ao WhatsApp! A IA em Python está pronta.\n")

@client.event(MessageEv)
def on_message(client: NewClient, message: MessageEv):
    # Ignora mensagens enviadas pelo próprio número
    if message.Info.MessageSource.IsFromMe:
        return

    # Extrai o texto recebido
    user_text = message.Message.conversation or message.Message.extendedTextMessage.text
    chat_jid = message.Info.MessageSource.Chat

    if user_text and chat_jid:
        print(f"Mensagem recebida: {user_text}")
        resposta_ia = consultar_ou_ensinar_ia(user_text)
        client.send_message(chat_jid, resposta_ia)

print("\n--- INICIANDO CONEXÃO COM O WHATSAPP ---")
client.connect()
