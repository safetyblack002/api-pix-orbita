from flask import Flask, request, jsonify
import requests
from flask_cors import CORS
import base64

app = Flask(__name__)
CORS(app)

# Credenciais da API da Orbita Pay
API_SECRET_KEY = "sk_live_tbYLBIBzaSoJtyWawAIEZpjcjI3nLxkXeKWjdiL48Z"

# Gerar o token de autenticação em Base64
auth_header = base64.b64encode(f"{API_SECRET_KEY}:x".encode()).decode()

def format_document(document):
    """ Remove caracteres não numéricos e define o tipo (CPF ou CNPJ) """
    doc_clean = ''.join(filter(str.isdigit, document))  # Mantém apenas números
    doc_type = "cpf" if len(doc_clean) == 11 else "cnpj" if len(doc_clean) == 14 else None
    return doc_clean, doc_type

@app.route('/gerar_pix', methods=['POST'])
def gerar_pix():
    dados = request.json  # Recebe os dados do frontend

    # Verificando os dados recebidos
    print("Dados recebidos do frontend:", dados)

    # Formatar documento corretamente
    doc_number, doc_type = format_document(dados["cpf"])
    
    if not doc_type:
        return jsonify({"erro": "Documento inválido. CPF deve ter 11 dígitos e CNPJ 14."}), 400

    # Converte valor para centavos
    try:
        valor_em_centavos = int(float(dados["valor"]) * 100)  # Convertendo para inteiro
        print(f"Valor convertido para centavos: {valor_em_centavos}")
    except ValueError:
        return jsonify({"erro": "Valor inválido"}), 400

    # **Correção: Define o nome do produto corretamente**
    nome_frete = "Frete via SEDEX" if float(dados["valor"]) == 29.58 else "Frete via PAC"

    # Monta os dados da cobrança Pix
    payload = {
        "amount": valor_em_centavos,
        "paymentMethod": "pix",
        "items": [
            {
                "title": nome_frete,
                "quantity": 1,
                "unitPrice": valor_em_centavos,
                "tangible": False
            }
        ],
        "customer": {
            "name": dados["nome"],
            "email": dados["email"],
            "phone": dados["telefone"],
            "document": {
                "number": doc_number,
                "type": doc_type
            }
        }
    }

    headers = {
        "Authorization": f"Basic {auth_header}",
        "Content-Type": "application/json"
    }

    print("Payload enviado para API:", payload)  # Debug para ver o que está sendo enviado

    # Enviar a requisição para a API da Orbita Pay
    response = requests.post("https://api.dashboard.orbitapay.com.br/v1/transactions", json=payload, headers=headers)
    data = response.json()

    print("Resposta da API da Orbita Pay:", data)  # Debug para ver a resposta da API

    if response.status_code in [200, 201] and "pix" in data and "qrcode" in data["pix"]:
        return jsonify({
            "qr_code": data["pix"]["qrcode"],
            "secure_url": data["secureUrl"]
        })
    else:
        return jsonify({"erro": data}), 400

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
