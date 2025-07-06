import os
from dotenv import load_dotenv
import google.generativeai as genai
from datetime import datetime
import sys
import io # Importado para la generación de PDF

# Importaciones para FastAPI
from fastapi import FastAPI, HTTPException, status, Request
from fastapi.responses import JSONResponse, HTMLResponse, StreamingResponse # StreamingResponse para PDF
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr
from typing import Optional

# Importaciones para enviar correo
import smtplib
from email.mime.text import MIMEText
from email.header import Header
from email.utils import formataddr

# Importaciones para generar PDF
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT

# --- 1. Cargar variables del archivo .env ---
load_dotenv()

# --- Configuración global del asistente y correo ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
IA_GENERATIVE_MODEL_NAME = os.getenv("IA_GENERATIVE_MODEL")

# Credenciales de correo
SENDER_EMAIL = os.getenv("EMAIL_ADDRESS")
SENDER_PASSWORD = os.getenv("EMAIL_PASSWORD")
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))

# Verificar que las claves y credenciales necesarias están presentes
if not GEMINI_API_KEY:
    print("Error: La clave de API de Gemini (GEMINI_API_KEY) no se encontró en el archivo .env")
    sys.exit(1)
if not IA_GENERATIVE_MODEL_NAME:
     print("Error: El nombre del modelo generativo (IA_GENERATIVE_MODEL) no se encontró en el archivo .env. Debes especificar qué modelo usar (ej. gemini-pro).")
     sys.exit(1)

EMAIL_SENDING_AVAILABLE = False
if all([SENDER_EMAIL, SENDER_PASSWORD, SMTP_SERVER]):
    EMAIL_SENDING_AVAILABLE = True
    print("Funcionalidad de envío de correo disponible.")
else:
    print("Advertencia: Las credenciales de correo (EMAIL_ADDRESS, EMAIL_PASSWORD, SMTP_SERVER) no se encontraron en el archivo .env.")
    print("La funcionalidad de envío de correo NO estará disponible.")

# --- 2. Definir la personalidad o instrucciones del sistema (TU PROMPT DE COMPORTAMIENTO) ---
PERSONA_PROMPT = """
Eres un asistente de IA llamado Elendur.
Tu rol es el de un **académico y especialista riguroso** en la obra completa de J.R.R. Tolkien y toda la mitología de Arda (incluyendo libros, manuscritos, lenguajes y estudios relevantes).
Tu objetivo es **proporcionar información precisa y concreta** sobre estos temas, basada estrictamente en el **canon primario y secundario** de Tolkien.
El tono de tus respuestas debe ser **formal, objetivo y académico**. Evita cualquier expresión de familiaridad, entusiasmo o uso de emojis.
Responde a las preguntas **directamente y con concisión**, enfocándote en los hechos y detalles relevantes.
Si la información solicitada es especulativa, no confirmada en las obras de Tolkien, o si no tienes datos disponibles, **indícalo de manera clara y formal**, mencionando la limitación o la fuente (o falta de ella).
Siempre busca ofrecer la información más **relevante y verificable** dentro del ámbito académico de los estudios de Tolkien.
Mantén siempre tu identidad como Elendur, el especialista académico en Tolkien.
"""

# Extraer el nombre del asistente del prompt
try:
    name_line = next((line for line in PERSONA_PROMPT.splitlines() if "llamado " in line), "")
    if "llamado " in name_line:
         ASSISTANT_NAME = name_line.split('llamado ')[-1].split('.')[0].strip()
    else:
         ASSISTANT_NAME = "Elendur (Asistente Académico)"
except Exception as e:
     print(f"Error al extraer nombre del prompt: {e}")
     ASSISTANT_NAME = "Elendur (Asistente Académico)"


# --- 3. Configurar la API de Gemini e inicializar el MODELO CON la personalidad ---
try:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(IA_GENERATIVE_MODEL_NAME, system_instruction=PERSONA_PROMPT)
    print(f"Modelo '{IA_GENERATIVE_MODEL_NAME}' configurado correctamente.")
except Exception as e:
    print(f"Error al configurar la API de Gemini o cargar el modelo '{IA_GENERATIVE_MODEL_NAME}': {e}")
    print("Verifica tu clave de API de Gemini o la disponibilidad del modelo especificado en .env para chat.")
    sys.exit(1)


# --- 4. Inicialización de FastAPI ---
app = FastAPI(
    title=f"{ASSISTANT_NAME}: Asistente Académico de Tolkien",
    description="API para interactuar con un asistente especializado en la obra de J.R.R. Tolkien.",
    version="1.0.0",
)

# Configurar Jinja2Templates
templates = Jinja2Templates(directory="templates")

# Montar StaticFiles para servir CSS, JS y otros activos estáticos
app.mount("/static", StaticFiles(directory="static"), name="static")


# --- Esquemas Pydantic para validación de datos ---
class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str
    timestamp: str
    assistant_name: str
    ask_for_download: bool = False # Campo unificado para pedir opción de email/pdf
    email_available: bool = False # Nuevo campo para indicar si el correo está configurado

class EmailRequest(BaseModel):
    recipient_email: EmailStr
    subject: str
    body: str

class EmailResponse(BaseModel):
    message: str
    success: bool

class PdfRequest(BaseModel): # Reintroducido
    question: str
    answer: str


# --- Función auxiliar para enviar correo electrónico ---
def _send_email_internal(to_email: str, subject: str, body: str) -> bool:
    """Función interna para enviar un correo electrónico.
    Retorna True si el envío fue exitoso, False en caso contrario.
    """
    if not EMAIL_SENDING_AVAILABLE:
        print("Error: La funcionalidad de envío de correo no está disponible.")
        return False

    try:
        msg = MIMEText(body, 'plain', 'utf-8')
        msg['Subject'] = Header(subject, 'utf-8').encode()
        msg['From'] = formataddr((str(Header(f"{ASSISTANT_NAME} (Asistente)", 'utf-8')), SENDER_EMAIL))
        msg['To'] = to_email

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"Error al enviar correo: {e}")
        return False


# --- NUEVA FUNCIÓN: Clasificación de la pregunta por la IA ---
async def is_tolkien_related(query: str) -> bool:
    """
    Usa el modelo de IA para determinar si una consulta está directamente relacionada
    con la obra de J.R.R. Tolkien.
    """
    classification_prompt = f"""
    Dada la siguiente consulta de usuario, determina si está directamente relacionada
    con la historia, personajes, lugares, eventos o mitología de las obras de J.R.R. Tolkien
    (por ejemplo, El Hobbit, El Señor de los Anillos, El Silmarillion).

    Responde con 'YES' si la consulta es directamente relevante a Tolkien.
    Responde con 'NO' si es un saludo general, agradecimiento, una meta-pregunta sobre el asistente,
    una pregunta personal, o cualquier cosa no relacionada directamente con Tolkien.

    Ejemplos:
    - Consulta: ¿Quién es Gandalf? -> YES
    - Consulta: Háblame de los Elfos. -> YES
    - Consulta: ¿Dónde está Mordor? -> YES
    - Consulta: Gracias por tu respuesta. -> NO
    - Consulta: Hola. -> NO
    - Consulta: Tengo otra pregunta. -> NO
    - Consulta: ¿Cuál es la capital de Francia? -> NO
    - Consulta: ¿Puedes contarme un chiste? -> NO

    Consulta: {query}
    ¿Es esta consulta directamente relacionada con Tolkien? (YES/NO):
    """
    try:
        temp_chat_session = model.start_chat(history=[])
        response = await temp_chat_session.send_message_async(
            classification_prompt,
            generation_config={"temperature": 0.0, "max_output_tokens": 10}
        )
        classification_result = response.text.strip().upper()
        print(f"Clasificación para '{query}': {classification_result}")
        return classification_result == 'YES'
    except Exception as e:
        print(f"Error durante la clasificación de la pregunta: {e}")
        return False

# --- RUTAS DE LA API ---

# Ruta raíz para servir index.html usando Jinja2
@app.get("/", response_class=HTMLResponse, summary="Abre la interfaz web del asistente de Elendur")
async def read_root(request: Request):
    """
    Sirve la interfaz HTML principal del asistente de chat de Elendur utilizando Jinja2.
    """
    return templates.TemplateResponse("index.html", {"request": request, "assistant_name": ASSISTANT_NAME})


# Ruta para manejar las solicitudes de chat
@app.post("/chat", response_model=ChatResponse, summary="Envía un mensaje al asistente y recibe una respuesta")
async def chat(request: ChatRequest):
    """
    Procesa el mensaje del usuario con el modelo generativo de IA y devuelve la respuesta.
    Si la funcionalidad de correo está disponible y la pregunta es relevante a Tolkien,
    la respuesta incluirá una bandera para indicar al frontend que pregunte al usuario
    si desea recibir la respuesta por correo o descargar un PDF.
    """
    try:
        chat_session = model.start_chat(history=[])
        response = await chat_session.send_message_async(request.message)
        ai_response_text = response.text

        is_query_tolkien_related = await is_tolkien_related(request.message)

        # ask_for_download se activa si la pregunta es relevante a Tolkien.
        # Esto le dice al frontend que muestre la burbuja de opciones (email/pdf).
        should_ask_for_download_or_email = is_query_tolkien_related

        return ChatResponse(
            response=ai_response_text,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            assistant_name=ASSISTANT_NAME,
            ask_for_download=should_ask_for_download_or_email,
            email_available=EMAIL_SENDING_AVAILABLE # Envía el estado de disponibilidad del correo
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al procesar la solicitud: {e}"
        )

# Ruta para enviar correo electrónico
@app.post("/send-email", response_model=EmailResponse, summary="Envía información de la conversación por correo")
async def send_email_route(request: EmailRequest):
    """
    Endpoint para enviar un correo electrónico con la información de la conversación.
    Solo disponible si las credenciales de correo están configuradas en .env.

    Ejemplo de cuerpo de solicitud:
    ```json
    {
      "recipient_email": "destino@ejemplo.com",
      "subject": "Información de Tolkien solicitada",
      "body": "Aquí va la respuesta de Elendur sobre Gandalf..."
    }
    ```
    """
    if not EMAIL_SENDING_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="La funcionalidad de envío de correo no está configurada o disponible."
        )

    success = _send_email_internal(request.recipient_email, request.subject, request.body)

    if success:
        return EmailResponse(
            message=f"La información ha sido enviada con éxito a {request.recipient_email}.",
            success=True
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Lo siento, hubo un problema al enviar el correo. Verifica las credenciales o intenta de nuevo."
        )

# NUEVA RUTA PARA GENERAR PDF
@app.post("/generate-pdf", summary="Genera un PDF con la pregunta y respuesta de la conversación")
async def generate_pdf(request: PdfRequest):
    """
    Endpoint para generar un PDF que contenga la pregunta del usuario y la respuesta del asistente.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()

    # Estilos personalizados
    styles.add(ParagraphStyle(name='TitleStyle',
                              parent=styles['h1'],
                              fontSize=20,
                              leading=24,
                              alignment=TA_CENTER,
                              spaceAfter=20))
    # Se cambió el nombre de 'Heading2' a 'CustomHeading2' para evitar colisión con estilos existentes
    styles.add(ParagraphStyle(name='CustomHeading2',
                              parent=styles['h2'],
                              fontSize=14,
                              leading=18,
                              spaceAfter=10,
                              spaceBefore=20,
                              alignment=TA_LEFT))
    # Se cambió el nombre de 'BodyText' a 'CustomBodyText' para evitar colisión con estilos existentes
    styles.add(ParagraphStyle(name='CustomBodyText',
                              parent=styles['Normal'],
                              fontSize=12,
                              leading=14,
                              spaceAfter=10,
                              alignment=TA_LEFT))
    styles.add(ParagraphStyle(name='Footer',
                              parent=styles['Normal'],
                              fontSize=10,
                              leading=12,
                              alignment=TA_CENTER,
                              textColor='#888888'))

    story = []

    # Título
    story.append(Paragraph(f"Informe de Consulta con {ASSISTANT_NAME}", styles['TitleStyle']))
    story.append(Spacer(1, 0.2 * inch))

    # Información de la consulta
    story.append(Paragraph("<b>Fecha y Hora:</b> " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"), styles['CustomBodyText'])) # Usar el nuevo nombre del estilo aquí
    story.append(Spacer(1, 0.1 * inch))

    # Pregunta del Usuario
    story.append(Paragraph("<b>Pregunta del Usuario:</b>", styles['CustomHeading2']))
    story.append(Paragraph(request.question, styles['CustomBodyText'])) # Usar el nuevo nombre del estilo aquí
    story.append(Spacer(1, 0.3 * inch))

    # Respuesta de Elendur
    story.append(Paragraph("<b>Respuesta de Elendur:</b>", styles['CustomHeading2']))
    story.append(Paragraph(request.answer, styles['CustomBodyText'])) # Usar el nuevo nombre del estilo aquí
    story.append(Spacer(1, 0.5 * inch))

    # Pie de página
    story.append(Paragraph(f"Generado por {ASSISTANT_NAME}, tu especialista en la obra de J.R.R. Tolkien.", styles['Footer']))

    try:
        doc.build(story)
        buffer.seek(0)
        return StreamingResponse(buffer,
                                 media_type="application/pdf",
                                 headers={"Content-Disposition": "attachment; filename=consulta_Elendur.pdf"})
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al generar el PDF: {e}"
        )