import os
import json
from flask import Flask, request, jsonify
import google.generativeai as genai

app = Flask(__name__)

# Configurações de Variáveis de Ambiente
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID", "1gR8Ax3SQN6rMkd8mvJaOHHpqdjwLixnTEoKk4IWMDis")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

@app.route("/", methods=["GET"])
def home():
    return "Servidor do Planner Financeiro do José ativo 24/7!", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    payload = request.get_json() or {}
    print("Payload recebido do WhatsApp:", payload)

    try:
        data = payload.get("data", {})
        key = data.get("key", {})
        remote_jid = key.get("remoteJid", "")

        # 1. Ignorar mensagens vindas de Grupos (terminadas em @g.us)
        if remote_jid.endswith("@g.us"):
            print("Mensagem de grupo ignorada.")
            return jsonify({"status": "ignorado", "motivo": "mensagem_de_grupo"}), 200

        # 2. Extrair o texto da mensagem
        message = data.get("message", {})
        texto = (
            message.get("conversation") or
            message.get("extendedTextMessage", {}).get("text")
        )

        if not texto:
            print("Nenhum texto encontrado na mensagem.")
            return jsonify({"status": "ignorado", "motivo": "sem_texto"}), 200

        print(f"Texto a processar: '{texto}'")

        # 3. Processar o texto com o Gemini para estruturar o gasto
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = (
            f"Analise o seguinte lançamento financeiro: '{texto}'. "
            "Retorne APENAS um JSON válido no seguinte formato exato, sem marcações markdown:\n"
            '{"descricao": "nome do item/gasto", "valor": 00.00, "categoria": "Alimentação|Saúde|Transporte|Lazer|Moradia|Outros"}'
        )
        
        resposta = model.generate_content(prompt)
        print("Resposta do Gemini:", resposta.text)

        # 4. Aqui o robô processa com sucesso!
        return jsonify({
            "status": "sucesso",
            "mensagem": "Lançamento interpretado!",
            "dados": resposta.text
        }), 200

    except Exception as e:
        print("Erro ao processar mensagem no webhook:", e)
        return jsonify({"status": "erro", "detalhe": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
