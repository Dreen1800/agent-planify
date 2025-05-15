import os
import datetime
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def alltransactions(user_email):
    try:
        response = supabase.table('transactions') \
            .select('*') \
            .eq('email', user_email) \
            .execute()
                
        return {"success": True, "data": response.data}
    except Exception as e:
        return {"success": False, "message": str(e)}
      
def addtransactions(arguments):
    try:
        phone_number = arguments.get("phone_number", "")
        print(f"DEBUG - addtransactions - Telefone recebido: '{phone_number}'")
        
        # Garantindo que o telefone não seja None
        if phone_number is None:
            phone_number = ""
        
        payload = {
            "amount": arguments.get("amount"),
            "description": arguments.get("description"),
            "category": arguments.get("category"),
            "type": arguments.get("type"),
            "payment_method": arguments.get("payment_method"),
            "status": "paid",
            "telefone": phone_number  # Adicionando o telefone ao payload
        }
        
        print(f"DEBUG - Payload para inserção: {payload}")
        
        # Verificação adicional
        if "telefone" not in payload or not payload["telefone"]:
            print("DEBUG - ALERTA: telefone está vazio no payload!")
        
        response = supabase.table('transactions').insert(payload).execute()
        print(f"DEBUG - Resposta do Supabase: {response}")
        
        return {
            "success": True,
            "message": "Transação adicionada com sucesso!",
            "data": response.data
        }
    except Exception as e:
        print(f"DEBUG - Erro ao adicionar transação: {e}")
        return {
            "success": False,
            "message": "Erro ao adicionar transação",
            "error": str(e)
        }
    
def get_user(user_email):
    try:
        response = supabase.table('users_control').select('*').eq('email', user_email).execute()
        
        return {
            "success": bool(response.data),
            "data": response.data[0] if response.data else None,
            "message": None if response.data else "Usuário não encontrado"
        }
    except Exception as e:
        return {"success": False, "data": None, "message": str(e)}
    
# Busca o response_id para um número de telefone específico
def get_conversation_id(phone_number):
    try:
        response = supabase.table('conversation_history').select('response_id').eq('phone_number', phone_number).execute()
        
        if response.data and len(response.data) > 0:
            return response.data[0]['response_id']
        
        return None
    except Exception as e:
        print(f"Erro ao obter conversation_id: {e}")
        return None
    
# Atualiza ou cria um registro de conversa para um número de telefone
def update_conversation_id(phone_number, response_id, user_name=None):
    try:
        existing = supabase.table('conversation_history').select('*').eq('phone_number', phone_number).execute()
        
        if existing.data and len(existing.data) > 0:
            # Atualizar registro existente
            update_data = {
                'response_id': response_id,
                'last_interaction': datetime.datetime.now().isoformat(),
                'conversation_count': existing.data[0]['conversation_count'] + 1
            }
            
            if user_name:
                update_data['user_name'] = user_name
                
            supabase.table('conversation_history').update(update_data).eq('phone_number', phone_number).execute()
        else:
            # Criar novo registro
            supabase.table('conversation_history').insert({
                'phone_number': phone_number,
                'response_id': response_id,
                'user_name': user_name
            }).execute()
        
        return True
    except Exception as e:
        print(f"Erro ao atualizar conversation_id: {e}")
        return False