import os
from dotenv import load_dotenv
import google.generativeai as genai
# Corregido: Importar la clase datetime directamente
from datetime import datetime
import sys # Para salir del script si hay errores

# Importaciones para enviar correo
import smtplib
from email.mime.text import MIMEText
from email.header import Header
from email.utils import formataddr

# --- 1. Cargar variables del archivo .env ---
load_dotenv()

gemini_api_key = os.getenv("GEMINI_API_KEY")
ia_generative_model_name = os.getenv("IA_GENERATIVE_MODEL")

# Credenciales de correo
sender_email = os.getenv("EMAIL_ADDRESS")
sender_password = os.getenv("EMAIL_PASSWORD")
smtp_server = os.getenv("SMTP_SERVER")
smtp_port = int(os.getenv("SMTP_PORT", 587)) # Puerto por defecto 587


# Verificar que las claves y credenciales necesarias están presentes
if not gemini_api_key:
    print("Error: La clave de API de Gemini (GEMINI_API_KEY) no se encontró en el archivo .env")
    sys.exit(1)
if not ia_generative_model_name:
     print("Error: El nombre del modelo generativo (IA_GENERATIVE_MODEL) no se encontró en el archivo .env. Debes especificar qué modelo usar (ej. gemini-pro).")
     sys.exit(1)
# Verificar credenciales de correo para la funcionalidad de envío
if not all([sender_email, sender_password, smtp_server]):
    print("Advertencia: Las credenciales de correo (EMAIL_ADDRESS, EMAIL_PASSWORD, SMTP_SERVER) no se encontraron en el archivo .env.")
    print("La funcionalidad de envío de correo NO estará disponible.")
    email_sending_available = False
else:
     email_sending_available = True
     print("Funcionalidad de envío de correo disponible.")


# --- 3. Definir la personalidad o instrucciones del sistema (TU PROMPT DE COMPORTAMIENTO) ---
persona_prompt = """
Eres un asistente de IA llamado Elendur.
Tu rol es el de un **académico y especialista riguroso** en la obra completa de J.R.R. Tolkien y toda la mitología de Arda (incluyendo libros, manuscritos, lenguajes y estudios relevantes).
Tu objetivo es **proporcionar información precisa y concreta** sobre estos temas, basada estrictamente en el **canon primario y secundario** de Tolkien.
El tono de tus respuestas debe ser **formal, objetivo y académico**. Evita cualquier expresión de familiaridad, entusiasmo o uso de emojis.
Responde a las preguntas **directamente y con concisión**, enfocándote en los hechos y detalles relevantes.
Si la información solicitada es especulativa, no confirmada en las obras de Tolkien, o si no tienes datos disponibles, **indícalo de manera clara y formal**, mencionando la limitación o la fuente (o falta de ella).
Siempre busca ofrecer la información más **relevante y verificable** dentro del ámbito académico de los estudios de Tolkien.
Mantén siempre tu identidad como Elendur, el especialista académico en Tolkien.
"""
# Nota: Eliminamos la instrucción explícita de preguntar por el correo, lo hará el script.


# --- 2. Configurar la API de Gemini e inicializar el MODELO CON la personalidad ---
try:
    genai.configure(api_key=gemini_api_key)
    # Pasa la personalidad (persona_prompt) al inicializar el modelo
    model = genai.GenerativeModel(ia_generative_model_name, system_instruction=persona_prompt)
    print(f"Modelo '{ia_generative_model_name}' configurado correctamente.")
except Exception as e:
    print(f"Error al configurar la API de Gemini o cargar el modelo '{ia_generative_model_name}': {e}")
    print("Verifica tu clave de API de Gemini o la disponibilidad del modelo especificado en .env para chat.")
    sys.exit(1)


# --- Función para enviar el correo electrónico ---
def send_email(to_email, subject, body):
    print(f"\nIntentando enviar correo a {to_email} con asunto: '{subject}'...")

    try:
        msg = MIMEText(body, 'plain', 'utf-8')
        msg['Subject'] = Header(subject, 'utf-8')
        msg['From'] = formataddr(("Gema, tu Asistente Tolkien", sender_email)) # Nombre opcional y correo
        msg['To'] = to_email

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls() # Iniciar encriptación TLS (para puerto 587)
            server.login(sender_email, sender_password) # Iniciar sesión
            server.sendmail(sender_email, to_email, msg.as_string()) # Enviar correo

        print("Correo enviado con éxito.")
        return True

    except Exception as e:
        print(f"Error al enviar el correo: {e}")
        print("Verifica la configuración SMTP, credenciales y dirección del destinatario.")
        print("Si usas Gmail, asegúrate de usar una contraseña de aplicación (altamente recomendado) y permitir acceso a aplicaciones menos seguras si aplica a tu configuración.")
        return False


# --- 4. Iniciar una sesión de chat ---
try:
    chat = model.start_chat(history=[]) # Empezamos una nueva conversación sin historial previo

    # Intenta sacar el nombre de la personalidad para el saludo
    try:
        # Busca la línea que contiene "llamado " y extrae lo que sigue
        name_line = next((line for line in persona_prompt.splitlines() if "llamado " in line), "")
        # Asegúrate de que la extracción del nombre es robusta si cambias el prompt
        if "llamado " in name_line:
             nombre_asistente = name_line.split('llamado ')[-1].split('.')[0].strip() # Extrae hasta el punto si existe
        else:
             nombre_asistente = "Elendur (Asistente Académico)" # Nombre por defecto o si el prompt no lo dice claro

    except Exception as e:
         print(f"Error al extraer nombre del prompt: {e}") # Debugging si falla la extracción
         nombre_asistente = "Elendur (Asistente Académico)" # Nombre genérico si falla


    print(f"\nSaludos. Soy {nombre_asistente}, su asistente académico especializado en la obra de J.R.R. Tolkien. Estoy a su disposición para consultas rigurosas.") # Saludo adaptado al tono formal
    if email_sending_available:
        print("Si desea recibir por correo la información que le proporcione, por favor, indíquelo tras recibir mi respuesta (ej. 'enviar por correo').")
    else:
         print("Nota: La funcionalidad de envío de correo no se encuentra disponible debido a la falta de configuración.")

    print("Para finalizar la sesión, escriba 'salir' o 'adios'.")
    print("-" * 30)

except Exception as e:
     print(f"Error al iniciar la sesión de chat después de configurar el modelo: {e}")
     sys.exit(1)

# --- 5. Bucle de conversación ---
last_ai_response_text = "" # Variable para guardar la última respuesta de la IA

while True:
    # --- Get primary user input ---
    user_input = input("Tú: ")

    # --- Detectar comandos de salida ---
    if user_input.lower() in ["salir", "adios", "quit", "exit"]:
        print(f"{nombre_asistente}: ¡Adiós! Que los caminos te sean leves. 😊")
        break

    # --- Si no es un comando de salida, enviar mensaje a Gemini ---
    try:
        # Enviamos la entrada del usuario al modelo de chat
        response = chat.send_message(user_input)

        # Procesar la respuesta del modelo
        if response.text:
             ai_response_text = response.text
             print(f"{nombre_asistente}: {ai_response_text}")
             # Guardar la respuesta válida por si el usuario pide enviarla por correo
             last_ai_response_text = ai_response_text
        else:
             # Manejar casos donde la respuesta no es texto (ej. seguridad bloqueada)
             print(f"{nombre_asistente}: (No pude generar una respuesta en este momento. ¿Podrías intentar de otra forma? 😊)")
             last_ai_response_text = "" # Limpiar la respuesta guardada si no fue texto


    except Exception as e:
        print(f"Ocurrió un error al comunicarse con Gemini: {e}")
        print("Por favor, intenta de nuevo.")
        last_ai_response_text = "" # Limpiar la respuesta guardada en caso de error de API
        # break # Opcional: rompe el bucle si hay un error persistente

    # --- DESPUÉS de obtener y imprimir la respuesta de la IA, preguntar sobre el correo ---
    # Solo preguntar si el envío de correo está configurado Y si hubo una respuesta válida de la IA para enviar
    if email_sending_available and last_ai_response_text:
        # Preguntamos directamente desde el script
        email_follow_up_input = input(f"{nombre_asistente}: ¿Te gustaría que te envíe esta información por correo? (sí/no) 😊 ")

        # --- Verificar la respuesta del seguimiento para detectar afirmación ---
        if email_follow_up_input.lower().strip() in ["sí", "si", "ok", "yes"]:
            print(f"{nombre_asistente}: ¡Claro! ¿A qué dirección de correo electrónico debo enviarte la información? 😊")
            recipient_input = input("Dirección de correo: ")

            if not recipient_input or "@" not in recipient_input or "." not in recipient_input: # Validación básica
                print(f"{nombre_asistente}: Hmm, parece que '{recipient_input}' no es una dirección de correo válida. No podré enviarlo. 😟")
                # No email sent, loop continues
            else:
                # Preparar asunto del correo
                subject = f"Información de Tolkien de {nombre_asistente}"
                print("Preparando para enviar correo...")
                # Llamar a la función de envío de correo con la última respuesta guardada
                success = send_email(recipient_input, subject, last_ai_response_text)

                if success:
                    print(f"{nombre_asistente}: ¡Listo! He enviado la información a {recipient_input}. 😊")
                    # Limpiar la última respuesta guardada después de enviarla
                    last_ai_response_text = ""
                else:
                    print(f"{nombre_asistente}: Lo siento, hubo un problema al enviar el correo. Verifica las credenciales o intenta de nuevo. 😟")
                    # Limpiar la última respuesta guardada si falla el envío
                    last_ai_response_text = ""

        # Si la respuesta al seguimiento NO fue una afirmación, o si el envío de correo no estaba disponible,
        # o no había respuesta que enviar, el bucle simplemente continúa a la siguiente iteración,
        # pidiendo la próxima entrada principal del usuario.


print("-" * 30)
print("Conversación terminada.")