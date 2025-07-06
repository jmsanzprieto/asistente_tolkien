# Elendur: Asistente Académico de J.R.R. Tolkien

## Descripción del Proyecto

**Elendur** es un asistente de inteligencia artificial especializado en la obra completa de **J.R.R. Tolkien** y la mitología de **Arda**. Este proyecto proporciona una **API RESTful** para interactuar con Elendur, obtener información precisa basada estrictamente en el canon primario y secundario de Tolkien, y una **interfaz web intuitiva** para facilitar la conversación. Además, permite enviar las respuestas del asistente por **correo electrónico** (si las credenciales están configuradas).

## Características

- **Asistente de IA Especializado**: Responde preguntas sobre J.R.R. Tolkien con un tono formal, objetivo y académico, basado en el canon primario y secundario.
- **Interfaz Web Intuitiva**: Una aplicación web construida con HTML, CSS y Bootstrap que permite a los usuarios interactuar fácilmente con el asistente.
- **Funcionalidad de Correo Electrónico**: Posibilidad de enviar la última respuesta generada por el asistente a una dirección de correo electrónico específica.
- **Privacidad**: Por diseño, el asistente no guarda ningún registro de las conversaciones para proteger la privacidad del usuario.
- **Desarrollado con FastAPI**: Un framework web moderno y rápido para construir APIs con Python.
- **Integración con Google Gemini API**: Utiliza un modelo generativo de Google para las capacidades de IA.

## Tecnologías Utilizadas

### Backend:

- Python 3.x
- FastAPI
- google-generativeai
- python-dotenv
- uvicorn
- smtplib (para envío de correo)
- Jinja2Templates (para servir la interfaz web)

### Frontend:

- HTML5
- CSS3 (Estilos personalizados y Bootstrap)
- JavaScript (ES6+)
- Bootstrap 5.3
- Font Awesome 6.5 (para iconos)

## Configuración del Entorno

Antes de ejecutar el proyecto, necesitas configurar tus variables de entorno.

### Crea un archivo `.env`:

En la raíz de tu proyecto, crea un archivo llamado `.env` y añade las siguientes variables:

```env
GEMINI_API_KEY="TU_CLAVE_API_DE_GEMINI"
IA_GENERATIVE_MODEL="gemini-pro" # O el nombre del modelo que prefieras (ej. gemini-1.5-flash)

# Opcional: Configuración para el envío de correo
# Si no se configuran, la funcionalidad de envío de correo no estará disponible.
EMAIL_ADDRESS="tu_correo@ejemplo.com"
EMAIL_PASSWORD="TU_CONTRASEÑA_DE_APLICACION_O_ACCESO" # Para Gmail, usa una contraseña de aplicación
SMTP_SERVER="smtp.gmail.com" # O el servidor SMTP de tu proveedor (ej. smtp.office365.com)
SMTP_PORT=587 # Puerto SMTP (normalmente 587 para TLS)
```

> **GEMINI_API_KEY**: Obtén tu clave API de Google AI Studio.
>
> **EMAIL_PASSWORD**: Si usas Gmail, NO uses tu contraseña principal. Debes generar una "contraseña de aplicación" desde la configuración de seguridad de tu cuenta de Google.

### Instala las dependencias:

Navega hasta el directorio raíz de tu proyecto en la terminal y ejecuta:

```bash
pip install fastapi uvicorn google-generativeai python-dotenv "python-multipart[standard]" jinja2
```

## Estructura del Proyecto

```
tu_proyecto/
├── .env
├── main.py
└── templates/
    └── index.html
```

- `main.py`: Contiene la lógica del backend de FastAPI, la configuración de la IA, los endpoints de la API y el manejo del envío de correos.
- `templates/index.html`: Es la interfaz de usuario web que interactúa con la API de FastAPI.

## Cómo Ejecutar el Proyecto

Asegúrate de que estás en la raíz de tu proyecto donde se encuentran `main.py` y la carpeta `templates`.

Inicia la aplicación FastAPI usando Uvicorn:

```bash
uvicorn main:app --reload
```

El flag `--reload` es útil para el desarrollo, ya que reiniciará el servidor automáticamente al detectar cambios en el código.

### Accede a la interfaz web:

Abre tu navegador y ve a: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)

### Accede a la documentación de la API (Swagger UI):

Visita: [http://127.0.0.1:8000/api/docs](http://127.0.0.1:8000/api/docs)

## Uso

### Interfaz Web

- **Preguntar a Elendur**: Escribe tu pregunta relacionada con la obra de J.R.R. Tolkien en el campo de texto y haz clic en "Preguntar a Elendur". La respuesta aparecerá debajo.
- **Enviar por Correo**: Si la funcionalidad está disponible (configurada en `.env`), puedes introducir una dirección de correo electrónico y hacer clic en "Enviar por correo" para enviar la última respuesta generada.

### Endpoints de la API (para desarrolladores)

#### POST `/api/ask_elendur/`

**Descripción**: Envía una pregunta a Elendur y recibe una respuesta.

**Cuerpo de la Solicitud (JSON)**:

```json
{
  "question": "¿Quién es Galadriel?"
}
```

**Respuesta Exitosa (JSON)**:

```json
{
  "answer": "Galadriel es una elfa Noldor de gran poder...",
  "assistant_name": "Elendur (Asistente Académico)",
  "email_available": true
}
```

#### POST `/api/send_email/`

**Descripción**: Envía un correo electrónico con una respuesta generada. Requiere que la configuración de correo esté activa.

**Cuerpo de la Solicitud (JSON)**:

```json
{
  "recipient_email": "destino@ejemplo.com",
  "subject": "Información de Tolkien solicitada",
  "body": "Aquí va la respuesta de Elendur..."
}
```

**Respuesta Exitosa (JSON)**:

```json
{
  "message": "La información ha sido enviada con éxito a destino@ejemplo.com.",
  "success": true
}
```

## Consideraciones de Privacidad

Este proyecto ha sido diseñado pensando en la privacidad. Elendur no almacena ni registra ninguna de tus conversaciones. Cada interacción es efímera, lo que significa que tus preguntas y las respuestas generadas no se guardan en el servidor una vez que la interacción ha terminado.
