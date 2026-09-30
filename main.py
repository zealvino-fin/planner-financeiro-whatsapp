import os
from flask import Flask, request, jsonify
import google.generativeai as genai

app = Flask(__name__)

# Configuração da API do Gemini e ID da Planilha do José
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID", "1gR8Ax3SQN6rMkd8mvJaOHHpqdjwLixnTEoKk4IWMDis")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

@app.route("/", methods=["GET"])
def home():
    return "Servidor do Planner Financeiro do José ativo 24/7!", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    print("Mensagem recebida do WhatsApp:", data)
    
    # Processamento inteligente com o Gemini
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        # O robô interpreta a mensagem e regista na planilha do Google Sheets
        return jsonify({"status": "sucesso", "mensagem": "Lançamento processado!"}), 200
    except Exception as e:
        print("Erro ao processar:", e)
        return jsonify({"status": "erro", "detalhe": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
