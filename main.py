import os
import json
from datetime import datetime
from flask import Flask, request, jsonify
import google.generativeai as genai
import gspread
from google.oauth2.service_account import Credentials

app = Flask(__name__)

SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID", "1gR8Ax3SQN6rMkd8mvJaOHHpqdjwLixnTEoKk4IWMDis")

def salvar_no_google_sheets(descricao, valor, categoria):
    credentials_raw = os.environ.get("GOOGLE_CREDENTIALS")
    if not credentials_raw:
        raise ValueError("A variável 'GOOGLE_CREDENTIALS' não está configurada no Render.")

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds_dict = json.loads(credentials_raw)
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SPREADSHEET_ID).sheet1

    data_atual = datetime.now().strftime("%d/%m/%Y")
    valor_formatado = f"{valor:.2f}".replace('.', ',')

    sheet.append_row([data_atual, descricao, valor_formatado, categoria])
    print(f"Sucesso: Lançamento gravado na planilha -> {[data_atual, descricao, valor_formatado, categoria]}")
    return True

@app.route("/", methods=["GET"])
def home():
    return "Servidor do Planner Financeiro ativo 24/7!", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    payload = request.get_json() or {}

    try:
        data = payload.get("data", {})
        key = data.get("key", {})
        remote_jid = key.get("remoteJid", "")

        # Ignora mensagens de grupos
        if remote_jid.endswith("@g.us"):
            return jsonify({"status": "ignorado", "motivo": "mensagem_de_grupo"}), 200

        message = data.get("message", {})
        texto = (
            message.get("conversation") or
            message.get("extendedTextMessage", {}).get("text")
        )

        if not texto:
            return jsonify({"status": "ignorado", "motivo": "sem_texto"}), 200

        print(f"Texto recebido: '{texto}'")

        # Pega a sua chave (que começa com AQ) configurada no Render
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("Nenhuma chave Gemini encontrada no Render.")

        genai.configure(api_key=api_key)
        
        # AQUI ESTÁ A SOLUÇÃO: Usando o modelo exato que o Google exigiu no log
        model = genai.GenerativeModel('gemini-3.8-flash')
        
        prompt = (
            f"Analise o seguinte gasto financeiro: '{texto}'. "
            "Retorne EXCLUSIVAMENTE um JSON válido no seguinte formato, sem formatação markdown:\n"
            '{"descricao": "nome do item", "valor": 00.00, "categoria": "Alimentação|Saúde|Transporte|Lazer|Moradia|Outros"}'
        )

        resposta = model.generate_content(prompt)
        raw_text = resposta.text.replace("```json", "").replace("```", "").strip()
        dados_gasto = json.loads(raw_text)

        descricao = dados_gasto.get("descricao", "Outros")
        valor = float(dados_gasto.get("valor", 0.0))
        categoria = dados_gasto.get("categoria", "Outros")

        salvar_no_google_sheets(descricao, valor, categoria)

        return jsonify({
            "status": "sucesso",
            "mensagem": "Lançamento gravado na planilha!"
        }), 200

    except Exception as e:
        print("Erro ao processar:", e)
        return jsonify({"status": "erro", "detalhe": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
