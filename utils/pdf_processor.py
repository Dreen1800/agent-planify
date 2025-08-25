import requests
import PyPDF2
import pdfplumber
import io
import re
from typing import Dict, List, Optional, Any

def download_pdf_from_url(pdf_url: str) -> Optional[bytes]:
    """
    Baixa um PDF de uma URL e retorna os bytes do arquivo.
    
    Args:
        pdf_url (str): URL do arquivo PDF
        
    Returns:
        Optional[bytes]: Bytes do arquivo PDF ou None se houver erro
    """
    try:
        print(f"DEBUG - Baixando PDF da URL: {pdf_url}")
        response = requests.get(pdf_url, timeout=30)
        response.raise_for_status()
        
        # Verifica se o conteúdo é realmente um PDF
        if response.headers.get('content-type', '').lower() not in ['application/pdf', 'application/octet-stream']:
            print(f"DEBUG - Aviso: Content-Type não é PDF: {response.headers.get('content-type')}")
        
        print(f"DEBUG - PDF baixado com sucesso. Tamanho: {len(response.content)} bytes")
        return response.content
    
    except requests.exceptions.RequestException as e:
        print(f"DEBUG - Erro ao baixar PDF: {str(e)}")
        return None
    except Exception as e:
        print(f"DEBUG - Erro inesperado ao baixar PDF: {str(e)}")
        return None

def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """
    Extrai texto de um PDF usando múltiplas estratégias.
    
    Args:
        pdf_bytes (bytes): Bytes do arquivo PDF
        
    Returns:
        str: Texto extraído do PDF
    """
    text = ""
    
    try:
        # Estratégia 1: Usar pdfplumber (melhor para PDFs com formatação complexa)
        print("DEBUG - Tentando extrair texto com pdfplumber...")
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                page_text = page.extract_text()
                if page_text:
                    text += f"\n--- Página {page_num} ---\n{page_text}\n"
        
        if text.strip():
            print(f"DEBUG - Texto extraído com pdfplumber: {len(text)} caracteres")
            return text
    
    except Exception as e:
        print(f"DEBUG - Erro com pdfplumber: {str(e)}")
    
    try:
        # Estratégia 2: Usar PyPDF2 como fallback
        print("DEBUG - Tentando extrair texto com PyPDF2...")
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
        
        for page_num, page in enumerate(pdf_reader.pages, 1):
            page_text = page.extract_text()
            if page_text:
                text += f"\n--- Página {page_num} ---\n{page_text}\n"
        
        if text.strip():
            print(f"DEBUG - Texto extraído com PyPDF2: {len(text)} caracteres")
            return text
    
    except Exception as e:
        print(f"DEBUG - Erro com PyPDF2: {str(e)}")
    
    return text if text.strip() else "Não foi possível extrair texto do PDF."

def analyze_pdf_content(text: str) -> Dict[str, Any]:
    """
    Analisa o conteúdo extraído do PDF para identificar informações relevantes.
    
    Args:
        text (str): Texto extraído do PDF
        
    Returns:
        Dict[str, Any]: Dicionário com informações analisadas
    """
    analysis = {
        "document_type": "unknown",
        "financial_data": {},
        "key_information": [],
        "potential_transaction": None,
        "confidence": "low"
    }
    
    text_lower = text.lower()
    
    # Detectar tipos de documentos financeiros
    if any(keyword in text_lower for keyword in ["comprovante", "recibo", "nota fiscal", "cupom"]):
        analysis["document_type"] = "receipt"
        analysis["confidence"] = "high"
    elif any(keyword in text_lower for keyword in ["extrato", "statement", "banco"]):
        analysis["document_type"] = "bank_statement"
        analysis["confidence"] = "high"
    elif any(keyword in text_lower for keyword in ["pix", "transferência", "ted", "doc"]):
        analysis["document_type"] = "transfer_proof"
        analysis["confidence"] = "high"
    elif any(keyword in text_lower for keyword in ["fatura", "cartão", "card"]):
        analysis["document_type"] = "credit_card_bill"
        analysis["confidence"] = "medium"
    
    # Extrair valores monetários
    money_patterns = [
        r'R\$\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)',  # R$ 1.234,56
        r'(\d{1,3}(?:\.\d{3})*(?:,\d{2}))\s*(?:reais?)',  # 1.234,56 reais
        r'(?:total|valor|quantia)[:]\s*R?\$?\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)',  # Total: R$ 1.234,56
    ]
    
    amounts = []
    for pattern in money_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            # Converter formato brasileiro para float
            amount_str = match.replace('.', '').replace(',', '.')
            try:
                amount = float(amount_str)
                amounts.append(amount)
            except ValueError:
                continue
    
    if amounts:
        analysis["financial_data"]["amounts"] = amounts
        analysis["financial_data"]["max_amount"] = max(amounts)
        analysis["financial_data"]["total_amounts"] = sum(amounts)
    
    # Extrair datas
    date_patterns = [
        r'(\d{1,2}/\d{1,2}/\d{4})',  # DD/MM/YYYY
        r'(\d{1,2}-\d{1,2}-\d{4})',  # DD-MM-YYYY
        r'(\d{4}-\d{1,2}-\d{1,2})',  # YYYY-MM-DD
    ]
    
    dates = []
    for pattern in date_patterns:
        matches = re.findall(pattern, text)
        dates.extend(matches)
    
    if dates:
        analysis["financial_data"]["dates"] = dates
    
    # Identificar estabelecimentos/empresas
    establishment_keywords = ["ltda", "s.a.", "eireli", "me", "epp"]
    lines = text.split('\n')
    establishments = []
    
    for line in lines:
        line_clean = line.strip()
        if any(keyword in line_clean.lower() for keyword in establishment_keywords):
            establishments.append(line_clean)
        elif len(line_clean) > 10 and len(line_clean) < 100:  # Possível nome de estabelecimento
            if any(char.isupper() for char in line_clean):
                establishments.append(line_clean)
    
    if establishments:
        analysis["financial_data"]["establishments"] = establishments[:5]  # Limitar a 5
    
    # Identificar métodos de pagamento
    payment_methods = []
    payment_keywords = {
        "pix": "PIX",
        "cartão": "Cartão",
        "débito": "Débito",
        "crédito": "Crédito",
        "dinheiro": "Dinheiro",
        "transferência": "Transferência",
        "ted": "TED",
        "doc": "DOC"
    }
    
    for keyword, method in payment_keywords.items():
        if keyword in text_lower:
            payment_methods.append(method)
    
    if payment_methods:
        analysis["financial_data"]["payment_methods"] = list(set(payment_methods))
    
    # Criar sugestão de transação se houver dados suficientes
    if amounts and analysis["document_type"] != "unknown":
        main_amount = max(amounts) if len(amounts) > 1 else amounts[0]
        establishment = establishments[0] if establishments else "Estabelecimento não identificado"
        payment_method = payment_methods[0] if payment_methods else "Não identificado"
        
        # Determinar categoria baseada no tipo de documento e conteúdo
        category = determine_category(text_lower, establishment)
        
        analysis["potential_transaction"] = {
            "amount": main_amount,
            "description": establishment[:50],  # Limitar descrição
            "category": category,
            "type": "expense",  # Assumir despesa por padrão para recibos
            "payment_method": payment_method
        }
        analysis["confidence"] = "high" if amounts and establishments else "medium"
    
    # Adicionar informações-chave
    key_info = []
    if amounts:
        key_info.append(f"Valores encontrados: {', '.join([f'R$ {a:.2f}' for a in amounts])}")
    if dates:
        key_info.append(f"Datas encontradas: {', '.join(dates[:3])}")
    if establishments:
        key_info.append(f"Estabelecimentos: {', '.join(establishments[:2])}")
    
    analysis["key_information"] = key_info
    
    return analysis

def determine_category(text_lower: str, establishment: str = "") -> str:
    """
    Determina a categoria da transação baseada no conteúdo do texto.
    
    Args:
        text_lower (str): Texto em minúsculas
        establishment (str): Nome do estabelecimento
        
    Returns:
        str: Categoria determinada
    """
    # Categorias baseadas em palavras-chave
    category_keywords = {
        "Alimentação": ["mercado", "supermercado", "restaurante", "lanchonete", "padaria", "açougue", "food", "ifood", "uber eats"],
        "Transporte": ["posto", "combustível", "gasolina", "etanol", "uber", "taxi", "ônibus", "metrô", "estacionamento"],
        "Saúde": ["farmácia", "hospital", "clínica", "médico", "dentista", "laboratório", "exame"],
        "Lazer": ["cinema", "teatro", "bar", "pub", "entretenimento", "diversão", "parque"],
        "Vestuário": ["loja", "roupa", "calçado", "sapato", "moda", "boutique"],
        "Educação": ["escola", "faculdade", "curso", "livro", "material escolar"],
        "Contas": ["água", "luz", "energia", "telefone", "internet", "gás"],
        "Streaming": ["netflix", "spotify", "amazon prime", "disney", "youtube"],
        "Mercado": ["mercado", "supermercado", "hipermercado", "atacado"]
    }
    
    text_and_establishment = f"{text_lower} {establishment.lower()}"
    
    for category, keywords in category_keywords.items():
        if any(keyword in text_and_establishment for keyword in keywords):
            return category
    
    return "Outras Despesas"

def process_pdf_document(pdf_url: str) -> Dict[str, Any]:
    """
    Função principal para processar um documento PDF completo.
    
    Args:
        pdf_url (str): URL do documento PDF
        
    Returns:
        Dict[str, Any]: Resultado completo do processamento
    """
    result = {
        "success": False,
        "text": "",
        "analysis": {},
        "error": None
    }
    
    try:
        # Baixar PDF
        pdf_bytes = download_pdf_from_url(pdf_url)
        if not pdf_bytes:
            result["error"] = "Não foi possível baixar o PDF da URL fornecida"
            return result
        
        # Extrair texto
        text = extract_text_from_pdf(pdf_bytes)
        if not text or text.strip() == "Não foi possível extrair texto do PDF.":
            result["error"] = "Não foi possível extrair texto do PDF"
            return result
        
        result["text"] = text
        
        # Analisar conteúdo
        analysis = analyze_pdf_content(text)
        result["analysis"] = analysis
        result["success"] = True
        
        print(f"DEBUG - PDF processado com sucesso. Tipo: {analysis['document_type']}, Confiança: {analysis['confidence']}")
        
        return result
    
    except Exception as e:
        result["error"] = f"Erro ao processar PDF: {str(e)}"
        print(f"DEBUG - Erro no processamento do PDF: {str(e)}")
        return result
