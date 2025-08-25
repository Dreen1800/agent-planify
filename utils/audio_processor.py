import os
import requests
import tempfile
from openai import OpenAI
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def download_audio_file(audio_url):
    """
    Baixa o arquivo de áudio da URL fornecida e salva com extensão apropriada
    """
    try:
        logger.info(f"Baixando áudio de: {audio_url}")
        response = requests.get(audio_url, timeout=30)
        response.raise_for_status()
        
        # Determinar extensão baseada na URL ou content-type
        file_extension = '.ogg'  # padrão para WhatsApp
        if '.mp3' in audio_url.lower():
            file_extension = '.mp3'
        elif '.wav' in audio_url.lower():
            file_extension = '.wav'
        elif '.m4a' in audio_url.lower():
            file_extension = '.m4a'
        
        # Criar arquivo temporário com extensão correta
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
            temp_file.write(response.content)
            return temp_file.name
            
    except Exception as e:
        logger.error(f"Erro ao baixar áudio: {str(e)}")
        return None

def convert_audio_to_supported_format(input_path, output_format='mp3'):
    """
    Verifica se o áudio já está em formato suportado pelo Whisper
    Formatos suportados: mp3, mp4, mpeg, mpga, m4a, wav, webm
    """
    try:
        logger.info(f"Verificando formato do áudio: {input_path}")
        
        # Para simplificar, vamos assumir que o arquivo já está em formato suportado
        # Se houver problemas, o Whisper retornará um erro mais específico
        return input_path
        
    except Exception as e:
        logger.error(f"Erro ao verificar áudio: {str(e)}")
        return None

def transcribe_audio_with_whisper(audio_file_path, api_key):
    """
    Transcreve o áudio usando a API do Whisper da OpenAI
    """
    try:
        logger.info("Iniciando transcrição com Whisper API")
        
        client = OpenAI(api_key=api_key)
        
        # Verificar se o arquivo existe e tem tamanho válido
        if not os.path.exists(audio_file_path):
            raise FileNotFoundError(f"Arquivo de áudio não encontrado: {audio_file_path}")
        
        file_size = os.path.getsize(audio_file_path)
        if file_size == 0:
            raise ValueError("Arquivo de áudio está vazio")
        
        logger.info(f"Enviando áudio ({file_size / 1024 / 1024:.2f}MB) para Whisper API")
        
        # Tentar transcrição com o arquivo original
        try:
            with open(audio_file_path, 'rb') as audio_file:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="pt"  # Português
                )
            
            logger.info("Transcrição concluída com sucesso")
            return {
                "success": True,
                "transcription": transcript.text,
                "language": "pt"
            }
        
        except Exception as format_error:
            # Se erro de formato, tentar renomear para .wav
            if "Invalid file format" in str(format_error):
                logger.info("Tentando com extensão .wav...")
                wav_path = audio_file_path.replace('.ogg', '.wav').replace('.tmp', '.wav')
                
                # Copiar arquivo com nova extensão
                import shutil
                shutil.copy2(audio_file_path, wav_path)
                
                try:
                    with open(wav_path, 'rb') as audio_file:
                        transcript = client.audio.transcriptions.create(
                            model="whisper-1",
                            file=audio_file,
                            language="pt"
                        )
                    
                    logger.info("Transcrição concluída com sucesso usando .wav")
                    # Limpar arquivo wav temporário
                    try:
                        os.unlink(wav_path)
                    except:
                        pass
                    
                    return {
                        "success": True,
                        "transcription": transcript.text,
                        "language": "pt"
                    }
                
                except Exception as wav_error:
                    # Limpar arquivo wav temporário
                    try:
                        os.unlink(wav_path)
                    except:
                        pass
                    raise wav_error
            else:
                raise format_error
        
    except Exception as e:
        logger.error(f"Erro na transcrição: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

def compress_audio(input_path, target_bitrate="64k"):
    """
    Função simplificada - se o arquivo for muito grande, retorna erro
    Em produção, você pode usar FFmpeg ou outras ferramentas externas
    """
    try:
        logger.warning(f"Arquivo de áudio muito grande: {input_path}")
        logger.warning("Compressão automática não disponível. Peça ao usuário um arquivo menor.")
        return None
        
    except Exception as e:
        logger.error(f"Erro ao processar áudio: {str(e)}")
        return None

def cleanup_temp_files(*file_paths):
    """
    Remove arquivos temporários
    """
    for file_path in file_paths:
        if file_path and os.path.exists(file_path):
            try:
                os.unlink(file_path)
                logger.info(f"Arquivo temporário removido: {file_path}")
            except Exception as e:
                logger.warning(f"Erro ao remover arquivo temporário {file_path}: {str(e)}")

def process_audio_message(audio_url, api_key):
    """
    Função principal para processar mensagens de áudio
    Envia o áudio diretamente para a API do Whisper
    """
    temp_file = None
    
    try:
        logger.info("Iniciando processamento de mensagem de áudio")
        
        # 1. Baixar o arquivo de áudio
        temp_file = download_audio_file(audio_url)
        if not temp_file:
            return {
                "success": False,
                "error": "Falha ao baixar o arquivo de áudio"
            }
        
        # 2. Verificar tamanho do arquivo (limite de 25MB da API Whisper)
        file_size = os.path.getsize(temp_file)
        max_size_mb = 25
        
        if file_size > max_size_mb * 1024 * 1024:
            return {
                "success": False,
                "error": f"Arquivo muito grande ({file_size / 1024 / 1024:.2f}MB). Limite: {max_size_mb}MB. Envie um áudio menor."
            }
        
        logger.info(f"Arquivo de áudio: {file_size / 1024 / 1024:.2f}MB")
        
        # 3. Transcrever diretamente com Whisper
        transcription_result = transcribe_audio_with_whisper(temp_file, api_key)
        
        if not transcription_result["success"]:
            return transcription_result
        
        # 4. Preparar resposta
        result = {
            "success": True,
            "transcription": transcription_result["transcription"],
            "language": transcription_result["language"],
            "message": f"Áudio transcrito: {transcription_result['transcription']}"
        }
        
        logger.info(f"Transcrição concluída: {result['transcription'][:100]}...")
        return result
        
    except Exception as e:
        logger.error(f"Erro no processamento de áudio: {str(e)}")
        return {
            "success": False,
            "error": f"Erro no processamento: {str(e)}"
        }
    
    finally:
        # Limpar arquivo temporário
        if temp_file:
            cleanup_temp_files(temp_file)

def get_audio_info(audio_url):
    """
    Obtém informações básicas sobre o arquivo de áudio
    """
    try:
        response = requests.head(audio_url, timeout=10)
        content_type = response.headers.get('content-type', '')
        content_length = response.headers.get('content-length', '0')
        
        return {
            "content_type": content_type,
            "size_bytes": int(content_length) if content_length.isdigit() else 0,
            "size_mb": round(int(content_length) / 1024 / 1024, 2) if content_length.isdigit() else 0
        }
    except Exception as e:
        logger.warning(f"Não foi possível obter informações do áudio: {str(e)}")
        return {
            "content_type": "unknown",
            "size_bytes": 0,
            "size_mb": 0
        }
