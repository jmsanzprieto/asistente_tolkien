// Variables globales para elementos del DOM
const questionInput = document.getElementById('questionInput');
const askButton = document.getElementById('askButton');
const askButtonText = document.getElementById('askButtonText');
const askSpinner = document.getElementById('askSpinner');
const chatHistory = document.getElementById('chatHistory');

const messageModal = new bootstrap.Modal(document.getElementById('messageModal'));
const modalMessageText = document.getElementById('modalMessageText');

let lastAnswer = ""; // Variable para almacenar la última respuesta
let lastQuestion = ""; // Variable para almacenar la última pregunta del usuario
let currentInteractionDiv = null; // Para gestionar la burbuja de interacción (email/pdf)
let expectingEmailAddress = false; // Estado para saber si estamos esperando un correo
let isEmailSendingAvailable = false; // Variable para almacenar el estado del envío de correo del backend

// Función para mostrar mensajes en el modal
function showMessageModal(message, title = "Mensaje") {
    document.getElementById('messageModalLabel').textContent = title;
    modalMessageText.textContent = message;
    messageModal.show();
}

// Función para añadir un mensaje al historial del chat
function appendMessage(sender, text, classes = []) {
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('message-bubble', ...classes);

    if (sender === 'user') {
        messageDiv.classList.add('user-message');
    } else {
        messageDiv.classList.add('ai-message');
    }
    messageDiv.textContent = text;
    chatHistory.appendChild(messageDiv);

    // Hacer scroll al final del historial de chat
    chatHistory.scrollTop = chatHistory.scrollHeight;
    return messageDiv; // Devuelve el elemento creado
}

// Función para eliminar elementos de interacción (prompt de email/pdf o formulario)
function removeInteractionElements() {
    if (currentInteractionDiv) {
        currentInteractionDiv.remove();
        currentInteractionDiv = null;
    }
}

// Función para enviar el correo (nueva función separada)
async function sendEmailToUser(recipientEmail, emailBody, emailSubject) {
    // Deshabilitar input y botón mientras se envía
    askButton.disabled = true;
    askButtonText.classList.add('d-none');
    askSpinner.classList.remove('d-none'); // Usamos el spinner principal

    // Opcional: mostrar un mensaje en el chat de que se está enviando
    const sendingMessage = appendMessage('ai', `Intentando enviar el correo a ${recipientEmail}...`);

    try {
        const response = await fetch('/send-email', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                recipient_email: recipientEmail,
                subject: emailSubject || `Información de Tolkien de Elendur`, // Asunto por defecto
                body: emailBody
            }),
        });

        const data = await response.json();

        sendingMessage.remove(); // Eliminar el mensaje de "enviando..."

        if (response.ok) {
            appendMessage('ai', `¡Listo! He enviado la información a ${recipientEmail}.`);
            lastAnswer = ""; // Limpiar la última respuesta guardada después del éxito
            lastQuestion = ""; // Limpiar la última pregunta
        } else {
            appendMessage('ai', `Lo siento, no pude enviar el correo a ${recipientEmail}. Error: ${data.detail || 'Hubo un problema.'}`);
        }
    } catch (error) {
        console.error('Error al enviar el correo:', error);
        if (sendingMessage) sendingMessage.remove();
        appendMessage('ai', "Error de conexión. No se pudo enviar el correo.");
    } finally {
        // Habilitar botón y ocultar spinner
        askButton.disabled = false;
        askButtonText.classList.remove('d-none');
        askSpinner.classList.add('d-none');
        expectingEmailAddress = false; // Restablecer el estado
        questionInput.placeholder = "Escribe tu pregunta aquí..."; // Restaurar placeholder
    }
}

// Función para añadir la pregunta de correo/PDF al chat
function appendEmailPdfPrompt() {
    removeInteractionElements(); // Limpiar interacciones anteriores si las hay

    currentInteractionDiv = document.createElement('div');
    currentInteractionDiv.classList.add('ai-email-interaction'); // Mantener la misma clase para estilo
    currentInteractionDiv.id = 'interactionPromptContainer'; // Para fácil referencia

    let buttonsHtml = '';
    // Solo muestra el botón de Email si el backend indica que está disponible
    if (isEmailSendingAvailable) {
        buttonsHtml += `<button type="button" class="btn btn-success btn-sm me-2" id="yesEmail">Enviar por Email</button>`;
    }
    buttonsHtml += `<button type="button" class="btn btn-info btn-sm me-2" id="downloadPdf">Descargar PDF</button>`;
    buttonsHtml += `<button type="button" class="btn btn-secondary btn-sm" id="noThanks">No, gracias</button>`;


    currentInteractionDiv.innerHTML = `
        <h6 class="mb-3 text-muted text-center"><i class="fas fa-envelope-open-text"></i> ¿Te gustaría recibir esta información por correo electrónico o descargarla como PDF?</h6>
        <div class="text-center">
            ${buttonsHtml}
        </div>
    `;
    chatHistory.appendChild(currentInteractionDiv);
    chatHistory.scrollTop = chatHistory.scrollHeight;

    // Adjuntar event listeners a los botones dinámicamente
    if (isEmailSendingAvailable) { // Asegurarse de que el botón existe antes de adjuntar el listener
        document.getElementById('yesEmail').addEventListener('click', () => {
            removeInteractionElements(); // Quitar la burbuja de opciones
            appendMessage('ai', "Por favor, introduce la dirección de correo electrónico a la que quieres que envíe la respuesta.");
            expectingEmailAddress = true; // Establecer el estado para esperar correo
            questionInput.placeholder = "Introduce tu correo electrónico aquí..."; // Cambiar placeholder
            questionInput.focus(); // Poner el foco en el input
        });
    }


    document.getElementById('downloadPdf').addEventListener('click', async () => {
        removeInteractionElements(); // Quitar la burbuja de opciones
        appendMessage('ai', "Generando tu documento PDF, por favor espera...");

        try {
            const response = await fetch('/generate-pdf', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    question: lastQuestion,
                    answer: lastAnswer
                }),
            });

            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.style.display = 'none';
                a.href = url;
                a.download = 'consulta_Elendur.pdf'; // Nombre del archivo
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                appendMessage('ai', "¡Listo! Tu PDF ha sido generado y la descarga debería comenzar en breve.");
                lastAnswer = ""; // Limpiar después de la descarga
                lastQuestion = ""; // Limpiar la pregunta
            } else {
                const errorData = await response.json();
                appendMessage('ai', `Lo siento, no pude generar el PDF. Error: ${errorData.detail || 'Hubo un problema.'}`);
            }
        } catch (error) {
            console.error('Error al generar el PDF:', error);
            appendMessage('ai', "Error de conexión. No se pudo generar el PDF.");
        } finally {
            // Asegurarse de que el input y el botón estén listos para la siguiente pregunta
            askButton.disabled = false;
            askButtonText.classList.remove('d-none');
            askSpinner.classList.add('d-none');
            expectingEmailAddress = false;
            questionInput.placeholder = "Escribe tu pregunta aquí...";
        }
    });

    document.getElementById('noThanks').addEventListener('click', () => {
        appendMessage('ai', "De acuerdo, no se realizará ninguna acción adicional con esta respuesta.");
        removeInteractionElements(); // Quitar la burbuja de opciones
        expectingEmailAddress = false; // Restablecer el estado
        questionInput.placeholder = "Escribe tu pregunta aquí..."; // Restaurar placeholder
        lastAnswer = ""; // Limpiar la última respuesta
        lastQuestion = ""; // Limpiar la pregunta
    });
}


// Event listener para el botón principal de "Enviar"
askButton.addEventListener('click', async () => {
    const question = questionInput.value.trim();

    if (!question) {
        showMessageModal("Por favor, introduce texto antes de enviar.");
        return;
    }

    // --- Manejar la entrada de dirección de correo electrónico si se está esperando una ---
    if (expectingEmailAddress) {
        const recipientEmail = question; // La entrada del usuario es la dirección de correo
        appendMessage('user', recipientEmail); // Mostrar el correo del usuario en el chat
        questionInput.value = ''; // Limpiar el input inmediatamente

        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(recipientEmail)) {
            appendMessage('ai', "El formato del correo electrónico no es válido. Por favor, verifica e inténtalo de nuevo.");
            // No se cambia expectingEmailAddress para permitir reintentar
        } else {
            // Correo válido, proceder a enviar
            await sendEmailToUser(recipientEmail, lastAnswer, `Información sobre "${lastQuestion}" de Elendur`);
            // expectingEmailAddress se restablece dentro de sendEmailToUser
        }
        return; // Importante: Detener aquí el procesamiento si se manejó una entrada de correo
    }
    // --- Fin del manejo de entrada de correo ---

    // Lógica original para nuevas preguntas
    removeInteractionElements(); // Asegurarse de que no haya interacciones de correo/pdf pendientes

    appendMessage('user', question); // Añadir la pregunta del usuario al chat
    lastQuestion = question; // Guardar la última pregunta
    questionInput.value = ''; // Limpiar el input

    // Deshabilitar botón y mostrar spinner
    askButton.disabled = true;
    askButtonText.classList.add('d-none');
    askSpinner.classList.remove('d-none');

    // Mostrar mensaje de "pensando"
    const thinkingMessage = appendMessage('ai', "Elendur está pensando...");

    try {
        // Realizar la solicitud a la API de FastAPI para la pregunta
        const response = await fetch('/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ message: question }),
        });

        const data = await response.json();

        thinkingMessage.remove(); // Eliminar el mensaje de "pensando"

        if (response.ok) {
            appendMessage('ai', data.response); // Añadir la respuesta del asistente
            lastAnswer = data.response; // Guardar la última respuesta
            isEmailSendingAvailable = data.email_available; // Actualizar el estado del envío de correo

            // Usar ask_for_download para la lógica de email/pdf
            if (data.ask_for_download) {
                appendEmailPdfPrompt(); // Llamar a la función para mostrar la pregunta de correo/pdf
            }

        } else {
            appendMessage('ai', `Error: ${data.detail || 'No se pudo obtener una respuesta.'}`);
            lastAnswer = "";
            lastQuestion = "";
        }
    } catch (error) {
        console.error('Error al preguntar a Elendur:', error);
        if (thinkingMessage) thinkingMessage.remove();
        appendMessage('ai', "Error de conexión. No se pudo contactar al asistente.");
        lastAnswer = "";
        lastQuestion = "";
    } finally {
        // Habilitar botón y ocultar spinner
        askButton.disabled = false;
        askButtonText.classList.remove('d-none');
        askSpinner.classList.add('d-none');
    }
});