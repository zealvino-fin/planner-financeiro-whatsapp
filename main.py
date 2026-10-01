import os
import json
from datetime import datetime
from flask import Flask, request, jsonify
import google.generativeai as genai
import gspread
from google.oauth2.service_account import Credentials

app = Flask(__name__)

# Configurações obtidas das Variáveis de Ambiente do Render
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID", "1gR8Ax3SQN6rMkd8mvJaOHHpqdjwLixnTEoKk4IWMDis")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)


def salvar_no_google_sheets(descricao, valor, categoria):
    """Conecta ao Google Sheets via Service Account e adiciona o gasto."""
    credentials_raw = os.environ.get("GOOGLE_CREDENTIALS")

    if not credentials_raw:
        raise ValueError("A variável 'GOOGLE_CREDENTIALS' não foi configurada no Render.")

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    # Converte o JSON das credenciais a partir da variável de ambiente
    creds_dict = json.loads(credentials_raw)
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)

    # Abre a planilha pelo ID
    sheet = client.open_by_key(SPREADSHEET_ID).sheet1

    # Formata a data (DD/MM/AAAA) e o valor com vírgula (padrão Brasil)
    data_atual = datetime.now().strftime("%d/%m/%Y")
    valor_formatado = f"{valor:.2f}".replace('.', ',')

    # Insere a nova linha: [Data, Descrição, Valor, Categoria]
    sheet.append_row([data_atual, descricao, valor_formatado, categoria])
    print(f"Sucesso: Lançamento gravado -> {[data_atual, descricao, valor_formatado, categoria]}")
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

        # 1. Ignorar mensagens recebidas em grupos (@g.us)
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

        print(f"Texto extraído para processamento: '{texto}'")

        # 3. Processar com o Gemini
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = (
            f"Analise o seguinte gasto financeiro: '{texto}'. "
            "Retorne APENAS um JSON válido exatamente neste formato, sem marcações markdown ou texto extra:\n"
            '{"descricao": "nome do item", "valor": 00.00, "categoria": "Alimentação|Saúde|Transporte|Lazer|Moradia|Outros"}'
        )

        resposta = model.generate_content(prompt)
        print("Resposta bruta do Gemini:", resposta.text)

        # Limpa eventuais marcações de código (```json ... ```)
        raw_text = resposta.text.replace("```json", "").replace("```", "").strip()
        dados_gasto = json.loads(raw_text)

        descricao = dados_gasto.get("descricao", "Outros")
        valor = float(dados_gasto.get("valor", 0.0))
        categoria = dados_gasto.get("categoria", "Outros")

        # 4. Gravar na planilha do Google Sheets
        salvar_no_google_sheets(descricao, valor, categoria)

        return jsonify({
            "status": "sucesso",
            "mensagem": "Lançamento gravado na planilha!",
            "dados": {"descricao": descricao, "valor": valor, "categoria": categoria}
        }), 200

    except Exception as e:
        print("Erro ao processar mensagem no webhook:", e)
        return jsonify({"status": "erro", "detalhe": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
