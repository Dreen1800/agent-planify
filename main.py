import os
import requests
import base64
import json
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
from flask import Flask, request, jsonify
from utils.supabase_tools import alltransactions, addtransactions, get_conversation_id, update_conversation_id, get_user
from utils.prompt import INSTRUCTIONS
from utils.pdf_processor import process_pdf_document
from utils.audio_processor import process_audio_message

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

Z_API_URL = os.getenv("Z_API_URL")
Z_API_TOKEN = os.getenv("Z_API_TOKEN")
Z_API_INSTANCE = os.getenv("Z_API_INSTANCE")
Z_API_KEY = os.getenv("Z_API_KEY")
NUMBER_BOT = os.getenv("NUMBER_BOT")  # Certifique-se de adicionar no .env

app = Flask(__name__)

def send_whatsapp_message(destination, message, is_group=False):
    url = f"{Z_API_URL}/instances/{Z_API_INSTANCE}/token/{Z_API_TOKEN}/send-text"
    
    headers = {
        "Content-Type": "application/json",
        "Client-Token": Z_API_KEY
    }
    payload = {
        "phone": destination,
        "message": message
    }  
    print(f"DEBUG - Enviando mensagem para: {destination}, É grupo: {is_group}")
    
    response = requests.post(url, json=payload, headers=headers)
    
    try:
        return response.json()
    except:
        return {"error": "Não foi possível analisar a resposta como JSON", "text": response.text}

def execute_tool_function(function_name, arguments, sender=None):
    print(f"DEBUG - Execute tool function chamada: {function_name}, Sender: '{sender}'")
    
    if function_name == 'alltransactions':
        return alltransactions(arguments['user_email'])
    elif function_name == 'addtransactions':
        if sender:
            cleaned_number = ''.join(filter(str.isdigit, sender))
            if cleaned_number.startswith('55'):
                if len(cleaned_number) == 12: 
                    ddd = cleaned_number[2:4]
                    rest = cleaned_number[4:]
                    formatted_sender = f"+55{ddd}9{rest}"
                elif len(cleaned_number) == 13:
                    formatted_sender = f"+{cleaned_number}"
                else:
                    formatted_sender = f"+{cleaned_number}"
            else:
                if len(cleaned_number) == 10:
                    ddd = cleaned_number[0:2]
                    rest = cleaned_number[2:]
                    formatted_sender = f"+55{ddd}9{rest}"
                elif len(cleaned_number) == 11:
                    formatted_sender = f"+55{cleaned_number}"
                else:
                    formatted_sender = f"+55{cleaned_number}"
            arguments['phone_number'] = formatted_sender
        else:
            print("DEBUG - Sender está vazio ou nulo!")
            
        return addtransactions(arguments)
    elif function_name == 'get_user':
        return get_user(arguments['user_email'])
    return {"error": f"Função '{function_name}' não encontrada"}

@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint de health check para monitoramento"""
    return jsonify({
        "status": "healthy",
        "service": "Planify Agent",
        "timestamp": str(datetime.now())
    })

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    if isinstance(data, list) and len(data) > 0:
        data = data[0]

    print("\n*** WEBHOOK RECEBIDO ***")
    print(f"DEBUG - Dados recebidos: {json.dumps(data, indent=2)}")
    
    if data.get('type') == 'ReceivedCallback' and not data.get('fromMe', True):
        is_group = data.get('isGroup', False)
        sender = data.get('phone') 
        chat_name = data.get('chatName', 'Usuário')
        connected_phone = data.get('connectedPhone', '') 
        participant_phone = data.get('participantPhone', '') 

        should_process = True

        if is_group:
            text_message = ''
            if 'text' in data and data.get('text', {}).get('message', ''):
                text_message = data.get('text', {}).get('message', '')
            elif 'image' in data and data.get('image', {}).get('caption', ''):
                text_message = data.get('image', {}).get('caption', '')
            
            print(f"DEBUG - Texto completo da mensagem/legenda: '{text_message}'")
            bot_number_variations = [
                f"@{connected_phone}", 
                connected_phone,        
                f"+{connected_phone}", 
                f"@+{connected_phone}" 
            ]
            
            bot_mention = False
            for variation in bot_number_variations:
                if variation in text_message:
                    bot_mention = True
                    print(f"DEBUG - Bot mencionado usando variação: '{variation}'")
                    break
            
            should_process = bot_mention

            print(f"DEBUG - Bot mencionado: {bot_mention}")
        else:
            print(f"DEBUG - Mensagem direta detectada de: {sender}")

        if should_process:
            print(f"DEBUG - Processando mensagem, sender: {sender}")

            if is_group and participant_phone:
                conversation_id = participant_phone
                print(f"DEBUG - ID de conversa para grupo: {conversation_id}")
            else:
                conversation_id = sender
            previous_response_id = get_conversation_id(conversation_id)
            print(f"DEBUG - conversation_id usado: {conversation_id}")
            print(f"DEBUG - previous_response_id obtido: {previous_response_id}")
            
            content = []

            if 'text' in data:
                message_text = data.get('text', {}).get('message', '')

                if is_group:
                    for prefix in [f"@{connected_phone} ", f"{connected_phone} ", 
                                  f"@+{connected_phone} ", f"+{connected_phone} "]:
                        if message_text.startswith(prefix):
                            message_text = message_text[len(prefix):]
                            break
                    
                    print(f"DEBUG - Texto após remover menção: '{message_text}'")
                
                content.append({"type": "input_text", "text": message_text})
            else:
                if 'image' in data:
                    content.append({"type": "input_text", "text": "O que você vê nesta imagem?"})

            if 'image' in data:
                try:
                    image_url = data.get('image', {}).get('imageUrl', '')
                    caption = data.get('image', {}).get('caption', '')

                    if image_url:
                        content.append({
                            "type": "input_image",
                            "image_url": image_url,
                            "detail": "auto"
                        })

                    if caption and caption.strip():
                        if not any(item.get('type') == 'input_text' for item in content):
                           content.append({"type": "input_text", "text": caption})
                        
                except Exception as e:
                    print(f"DEBUG - Erro ao processar imagem: {str(e)}")

                    destination = sender
                    if is_group:
                        destination = sender 
                    
                    send_whatsapp_message(destination, "Desculpe, tive um problema ao processar sua imagem.", is_group=is_group)

            # Processar documento PDF se presente
            if 'document' in data:
                try:
                    document_data = data.get('document', {})
                    document_url = document_data.get('documentUrl', '')
                    mime_type = document_data.get('mimeType', '')
                    file_name = document_data.get('fileName', '')
                    caption = document_data.get('caption', '')

                    print(f"DEBUG - Documento recebido: {file_name}, Tipo: {mime_type}")

                    if mime_type == 'application/pdf' and document_url:
                        print(f"DEBUG - Processando PDF: {document_url}")
                        
                        # Processar o PDF
                        pdf_result = process_pdf_document(document_url)
                        
                        if pdf_result["success"]:
                            pdf_text = pdf_result["text"]
                            pdf_analysis = pdf_result["analysis"]
                            
                            # Criar conteúdo para o AI com informações do PDF
                            pdf_content = f"DOCUMENTO PDF ANALISADO:\n"
                            pdf_content += f"Nome do arquivo: {file_name}\n"
                            if caption and caption.strip():
                                pdf_content += f"Legenda: {caption}\n"
                            pdf_content += f"Tipo de documento identificado: {pdf_analysis.get('document_type', 'desconhecido')}\n"
                            pdf_content += f"Nível de confiança: {pdf_analysis.get('confidence', 'baixo')}\n\n"
                            
                            # Adicionar informações-chave
                            if pdf_analysis.get('key_information'):
                                pdf_content += "INFORMAÇÕES PRINCIPAIS:\n"
                                for info in pdf_analysis['key_information']:
                                    pdf_content += f"- {info}\n"
                                pdf_content += "\n"
                            
                            # Adicionar texto extraído (limitado para não sobrecarregar)
                            if len(pdf_text) > 2000:
                                pdf_content += f"CONTEÚDO DO DOCUMENTO (primeiros 2000 caracteres):\n{pdf_text[:2000]}..."
                            else:
                                pdf_content += f"CONTEÚDO DO DOCUMENTO:\n{pdf_text}"
                            
                            # Se há uma transação potencial identificada, incluir na mensagem
                            if pdf_analysis.get('potential_transaction'):
                                transaction = pdf_analysis['potential_transaction']
                                pdf_content += f"\n\nTRANSAÇÃO SUGERIDA AUTOMATICAMENTE:\n"
                                pdf_content += f"- Valor: R$ {transaction['amount']:.2f}\n"
                                pdf_content += f"- Descrição: {transaction['description']}\n"
                                pdf_content += f"- Categoria: {transaction['category']}\n"
                                pdf_content += f"- Tipo: {transaction['type']}\n"
                                pdf_content += f"- Método de pagamento: {transaction['payment_method']}\n"
                                pdf_content += "\nPor favor, analise estas informações e confirme se devo registrar esta transação."
                            
                            # Adicionar ao conteúdo que será enviado para o AI
                            content.append({"type": "input_text", "text": pdf_content})
                            
                        else:
                            error_msg = pdf_result.get("error", "Erro desconhecido")
                            print(f"DEBUG - Erro ao processar PDF: {error_msg}")
                            
                            # Informar erro ao usuário
                            destination = sender
                            if is_group:
                                destination = sender
                            
                            send_whatsapp_message(destination, 
                                f"Recebi seu documento PDF '{file_name}', mas tive dificuldades para analisá-lo: {error_msg}", 
                                is_group=is_group)
                    else:
                        print(f"DEBUG - Documento não é PDF ou URL inválida. Tipo: {mime_type}")
                        
                except Exception as e:
                    print(f"DEBUG - Erro ao processar documento PDF: {str(e)}")

                    destination = sender
                    if is_group:
                        destination = sender 
                    
                    send_whatsapp_message(destination, "Desculpe, tive um problema ao processar seu documento PDF.", is_group=is_group)

            # Processar mensagem de áudio se presente
            if 'audio' in data:
                try:
                    audio_data = data.get('audio', {})
                    audio_url = audio_data.get('audioUrl', '')
                    mime_type = audio_data.get('mimeType', '')
                    
                    print(f"DEBUG - Áudio recebido: URL={audio_url}, Tipo: {mime_type}")

                    if audio_url:
                        print(f"DEBUG - Processando áudio: {audio_url}")
                        
                        # Processar o áudio com Whisper
                        audio_result = process_audio_message(audio_url, api_key)
                        
                        if audio_result["success"]:
                            transcription = audio_result["transcription"]
                            
                            print(f"DEBUG - Transcrição obtida: {transcription}")
                            
                            # Adicionar transcrição ao conteúdo para processamento pelo AI
                            audio_content = f"MENSAGEM DE ÁUDIO TRANSCRITA:\n{transcription}"
                            content.append({"type": "input_text", "text": audio_content})
                            
                        else:
                            error_msg = audio_result.get("error", "Erro desconhecido")
                            print(f"DEBUG - Erro ao processar áudio: {error_msg}")
                            
                            # Informar erro ao usuário de forma amigável
                            destination = sender
                            if is_group:
                                destination = sender
                            
                            # Simplificar mensagem de erro para o usuário
                            user_error_msg = "Recebi seu áudio, mas não consegui processá-lo. Pode tentar enviar novamente ou digitar a mensagem?"
                            if "Invalid file format" in error_msg:
                                user_error_msg = "Formato de áudio não suportado. Tente gravar novamente ou envie como mensagem de texto."
                            elif "muito grande" in error_msg.lower():
                                user_error_msg = "Áudio muito longo. Envie um áudio mais curto ou divida em partes menores."
                            
                            send_whatsapp_message(destination, user_error_msg, is_group=is_group)
                    else:
                        print(f"DEBUG - URL de áudio inválida")
                        
                except Exception as e:
                    print(f"DEBUG - Erro ao processar mensagem de áudio: {str(e)}")

                    destination = sender
                    if is_group:
                        destination = sender 
                    
                    send_whatsapp_message(destination, "Desculpe, tive um problema ao processar seu áudio.", is_group=is_group)

            if content:
                try:
                    tools = [
                        {"type": "function", "name": "alltransactions", "description": "Consulta transações por email",
                         "parameters": {"type": "object", "properties": {"user_email": {"type": "string", 
                         "description": "Email do usuário"}}, "required": ["user_email"], 
                         "additionalProperties": False}, "strict": True},
                        {"type": "function", "name": "addtransactions", "description": "Adiciona uma nova transação",
                        "parameters": {"type": "object", "properties": {
                            "amount": {"type": "number", "description": "Valor da transação"},
                            "description": {"type": "string", "description": "Descrição da transação"},
                            "category": {"type": "string", "description": "Categoria (ex: alimentação, transporte)"},
                            "type": {"type": "string", "description": "Tipo da transação (entrada ou saída)"},
                            "payment_method": {"type": "string", "description": "Método de pagamento (ex: cartão, pix)"},
                            "phone_number": {"type": "string", "description": "Número de telefone do usuário"}
                        }, "required": ["amount", "description", "category", "type", "payment_method", "phone_number"], 
                        "additionalProperties": False}, "strict": True},
                        {"type": "function", "name": "get_user", "description": "Consulta informações de um usuário pelo email",
                        "parameters": {"type": "object", "properties": {"user_email": {"type": "string", 
                        "description": "Email do usuário a ser consultado"}}, "required": ["user_email"], 
                        "additionalProperties": False}, "strict": True}
                    ]
                    
                    input_messages = [{"role": "user", "content": content}]
                    
                    while True:
                        response = client.responses.create(
                            model="gpt-4o-mini",
                            instructions=INSTRUCTIONS,
                            input=input_messages,
                            tools=tools,
                            previous_response_id=previous_response_id
                        )
                        
                        if (hasattr(response, 'output') and 
                            isinstance(response.output, list) and 
                            len(response.output) > 0 and 
                            getattr(response.output[0], 'type', None) == 'function_call'):
                            
                            output_item = response.output[0]
                            function_name = output_item.name
                            arguments = json.loads(output_item.arguments)
                            call_id = output_item.call_id

                            sender_to_use = participant_phone if (is_group and participant_phone) else sender
                            
                            result = execute_tool_function(function_name, arguments, sender_to_use)
                            
                            input_messages.append(output_item)
                            input_messages.append({
                                "type": "function_call_output", 
                                "call_id": call_id,
                                "output": json.dumps(result)
                            })
                        else:
                            break

                    user_name = data.get('senderName', '') if is_group else chat_name
                    update_conversation_id(conversation_id, response.id, user_name=user_name)

                    destination = sender

                    response_text = response.output_text
                    if is_group and participant_phone:
                        pass

                    print(f"DEBUG - Resposta do AI: '{response_text}'")
                    print(f"DEBUG - Preparando para enviar resposta: '{response_text}'")

                    result = send_whatsapp_message(destination, response_text, is_group=is_group)
                    print(f"DEBUG - Mensagem enviada para {'grupo' if is_group else 'usuário'}: {result}")

                    # Verificar se foi um registro bem-sucedido
                    if "✅ Registrado" in response_text or "registrado como" in response_text.lower():
                        print("DEBUG - ✅ TRANSAÇÃO REGISTRADA COM SUCESSO!")
                    elif "Registrando" in response_text:
                        print("DEBUG - 🔄 PROCESSANDO REGISTRO DE TRANSAÇÃO...")
                    elif "confirma" in response_text.lower() or "devo prosseguir" in response_text.lower():
                        print("DEBUG - ❓ SISTEMA PEDINDO CONFIRMAÇÃO")
                    
                except Exception as e:
                    print(f"DEBUG - Erro ao processar mensagem: {str(e)}")
                    send_whatsapp_message(sender, "Poxa, encontrei um problema ao processar sua mensagem.", is_group=is_group)
    
    return jsonify({"status": "success"})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5001, debug=True)