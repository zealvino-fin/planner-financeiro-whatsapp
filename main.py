import os
import json
from flask import Flask, request, jsonify
import google.generativeai as genai
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

app = Flask(__name__)

# Configurações de Variáveis de Ambiente
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID", "1gR8Ax3SQN6rMkd8mvJaOHHpqdjwLixnTEoKk4IWMDis")
GOOGLE_CREDENTIALS_JSON = os.environ.get("GOOGLE_CREDENTIALS")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

def salvar_no_google_sheets(descricao, valor, categoria):
    """Conecta no Google Sheets e adiciona uma linha com o gasto"""
    if not GOOGLE_CREDENTIALS_JSON:
        print("Erro: A variável GOOGLE_CREDENTIALS não foi configurada no Render.")
        return False

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    # Carrega as credenciais a partir do JSON da variável de ambiente
    creds_dict = json.loads(GOOGLE_CREDENTIALS_JSON)
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)

    # Abre a planilha pelo ID
    sheet = client.open_by_key(SPREADSHEET_ID).sheet1
    
    # Data atual no formato DD/MM/AAAA
    data_atual = datetime.now().strftime("%d/%m/%Y")
    
    # Adiciona a linha na planilha: [Data, Descrição, Valor, Categoria]
    sheet.append_row([data_atual, descricao, valor, categoria])
    print(f"Sucesso: Lançamento adicionado à planilha -> {[data_atual, descricao, valor, categoria]}")
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

        # Ignora mensagens de grupos (@g.us)
        if remote_jid.endswith("@g.us"):
            return jsonify({"status": "ignorado", "motivo": "mensagem_de_grupo"}), 200

        message = data.get("message", {})
        texto = (
            message.get("conversation") or
            message.get("extendedTextMessage", {}).get("text")
        )

        if not texto:
            return jsonify({"status": "ignorado", "motivo": "sem_texto"}), 200

        print(f"Texto a processar: '{texto}'")

        # Chama o Gemini para extrair os dados do gasto
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = (
            f"Analise o seguinte gasto: '{texto}'. "
            "Retorne APENAS um JSON válido exatamente no seguinte formato, sem formatação markdown:\n"
            '{"descricao": "nome do item", "valor": 00.00, "categoria": "Alimentação|Saúde|Transporte|Lazer|Moradia|Outros"}'
        )
        
        resposta = model.generate_content(prompt)
        print("Resposta do Gemini:", resposta.text)

        # Trata o retorno do Gemini e converte para dicionário
        texto_resposta = resposta.text.replace("```json", "").replace("```", "").strip()
        dados_gasto = json.loads(texto_resposta)

        # Grava no Google Sheets
        salvar_no_google_sheets(
            descricao=dados_gasto.get("descricao", "Outros"),
            valor=dados_gasto.get("valor", 0.0),
            categoria=dados_gasto.get("categoria", "Outros")
        )

        return jsonify({"status": "sucesso", "dados": dados_gasto}), 200

    except Exception as e:
        print("Erro ao processar mensagem no webhook:", e)
        return jsonify({"status": "erro", "detalhe": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
