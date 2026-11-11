/**
 * J.A.R.V.I.S. // Agente 9 — Lógica del Cliente
 * Sector: Seguridad y Gestión del Riesgo (UniPutumayo - Mocoa, Putumayo)
 *
 * Características:
 *  - Captura de voz (MediaRecorder API) y envío al backend STT (Whisper)
 *  - Comunicación con FastAPI (texto y audio)
 *  - Reproducción TTS: audio del servidor (edge-tts) con fallback chunked (Web Speech API)
 *  - Fix Chrome Speech Synthesis: cola de frases + keepalive para evitar pausas
 *  - Sonidos HUD: boot, activación de voz, respuesta del agente (AudioContext)
 *  - Monitor de incidentes en tiempo real
 */

// =====================================================================
// Estado de la sesión
// =====================================================================
let sessionId = 'sess_' + Math.random().toString(36).substring(2, 10);
let currentIncidenteId = null;
let speechAudioEnabled = true;

// Control TTS browser (keepalive Chrome bug)
let ttsKeepAlive = null;
let ttsChunkTimeout = null;

// Elementos del DOM
const chatMessages = document.getElementById('chatMessages');
const textInput = document.getElementById('textInput');
const btnSend = document.getElementById('btnSend');
const btnVoice = document.getElementById('btnVoice');
const btnVoiceLabel = document.getElementById('btnVoiceLabel');
const recordingBar = document.getElementById('recordingBar');
const recordingStatusText = document.getElementById('recordingStatusText');
const recordTimer = document.getElementById('recordTimer');

// Monitor de incidente
const badgeEstado = document.getElementById('badgeEstado');
const incCodigo = document.getElementById('incCodigo');
const priorityPill = document.getElementById('priorityPill');
const incTipoEvento = document.getElementById('incTipoEvento');
const incUbicacion = document.getElementById('incUbicacion');
const incAcciones = document.getElementById('incAcciones');
const escalationAlert = document.getElementById('escalationAlert');
const historyList = document.getElementById('historyList');

// Variables MediaRecorder y Reconocimiento de Voz en Vivo (STT)
let mediaRecorder = null;
let activeMicStream = null;
let audioChunks = [];
let isRecording = false;
let recordInterval = null;
let recordSeconds = 0;
let speechRecognition = null;
let liveFinalText = '';
let liveInterimText = '';

// =====================================================================
// AudioContext — Sonidos HUD generados por código (sin archivos externos)
// =====================================================================
let audioCtx = null;

function getAudioCtx() {
  if (!audioCtx || audioCtx.state === 'closed') {
    audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  }
  if (audioCtx.state === 'suspended') {
    audioCtx.resume();
  }
  return audioCtx;
}

/**
 * Genera un tono electrónico corto.
 * @param {number} freq1 - Frecuencia inicial (Hz)
 * @param {number} freq2 - Frecuencia final (Hz)
 * @param {number} duration - Duración en segundos
 * @param {number} volume - Volumen 0-1
 */
function playTone(freq1, freq2 = freq1, duration = 0.12, volume = 0.18) {
  try {
    const ctx = getAudioCtx();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.type = 'sine';
    osc.frequency.setValueAtTime(freq1, ctx.currentTime);
    osc.frequency.linearRampToValueAtTime(freq2, ctx.currentTime + duration);
    gain.gain.setValueAtTime(volume, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + duration);
    osc.start(ctx.currentTime);
    osc.stop(ctx.currentTime + duration);
  } catch (e) { /* AudioContext puede estar bloqueado hasta interacción del usuario */ }
}

/** Sonido de arranque del sistema J.A.R.V.I.S. (secuencia 3 tonos) */
function playBootSound() {
  setTimeout(() => playTone(320, 480, 0.18, 0.12), 0);
  setTimeout(() => playTone(480, 640, 0.18, 0.14), 220);
  setTimeout(() => playTone(800, 960, 0.22, 0.16), 450);
}

/** Sonido de activación de micrófono */
function playMicOnSound() {
  playTone(600, 900, 0.15, 0.2);
  setTimeout(() => playTone(900, 1100, 0.1, 0.15), 160);
}

/** Sonido de desactivación del micrófono */
function playMicOffSound() {
  playTone(900, 500, 0.2, 0.15);
}

/** Sonido de respuesta del agente (notificación suave) */
function playAgentResponseSound() {
  playTone(700, 850, 0.12, 0.12);
  setTimeout(() => playTone(850, 700, 0.12, 0.1), 140);
}

// =====================================================================
// Inicialización
// =====================================================================
document.addEventListener('DOMContentLoaded', () => {
  setupEventListeners();
  loadIncidentsHistory();
  restoreAdvisorSessionIfActive();
  // Refrescar historial periódicamente
  setInterval(loadIncidentsHistory, 15000);
  // Boot sound tras primera interacción (política de autoplay)
  document.addEventListener('click', () => {
    playBootSound();
  }, { once: true });
});

function setupEventListeners() {
  btnSend.addEventListener('click', handleSendTextMessage);
  textInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') handleSendTextMessage();
  });
  // Si el usuario empieza a escribir, callar al agente
  textInput.addEventListener('input', () => {
    stopAllAgentAudio();
  });
  btnVoice.addEventListener('click', toggleVoiceRecording);
}

/**
 * Silencia inmediatamente toda voz del agente (reproductores <audio> y Web Speech API)
 * para que el agente se calle en cuanto el usuario hable o envíe un mensaje.
 */
function stopAllAgentAudio() {
  try {
    // 1. Detener todos los elementos <audio> del chat
    const allAudios = document.querySelectorAll('audio');
    allAudios.forEach(audioEl => {
      try {
        audioEl.pause();
        audioEl.currentTime = 0;
      } catch (e) { }
    });

    // 2. Cancelar síntesis de voz del navegador y timers
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
    }
    if (ttsKeepAlive) {
      clearInterval(ttsKeepAlive);
      ttsKeepAlive = null;
    }
    if (ttsChunkTimeout) {
      clearTimeout(ttsChunkTimeout);
      ttsChunkTimeout = null;
    }
  } catch (e) {
    console.warn('Error al detener audio del agente:', e);
  }
}

// =====================================================================
// Envío de Reporte por Texto
// =====================================================================
async function handleSendTextMessage() {
  // Si el micrófono estaba grabando cuando el usuario presionó Enviar,
  // detener el micrófono de inmediato y enviar ese reporte sin seguir escuchando
  if (isRecording) {
    await stopRecordingAndSend();
    return;
  }

  // Asegurar que cualquier instancia residual de micrófono quede apagada
  shutdownMicrophoneResources();

  const text = textInput.value.trim();
  if (!text) return;

  // Callar al agente de inmediato
  stopAllAgentAudio();

  textInput.value = '';
  appendMessage('usuario', text);

  const loadingId = appendLoadingIndicator('Consultando sistemas tácticos y protocolos RAG...');

  try {
    const response = await fetch('/api/chat/text', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        mensaje: text,
        incidente_id: currentIncidenteId
      })
    });

    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      throw new Error(errData.detail || `Error en el servidor (${response.status})`);
    }

    const data = await response.json();
    removeLoadingIndicator(loadingId);
    handleAgentResponse(data);

  } catch (error) {
    removeLoadingIndicator(loadingId);
    appendMessage('agente', `⚠️ ${error.message}`);
  }
}

// =====================================================================
// Captura y Envío de Audio (STT → LLM → TTS)
// =====================================================================
async function toggleVoiceRecording() {
  if (!isRecording) {
    await startRecording();
  } else {
    await stopRecordingAndSend();
  }
}

/**
 * Apaga por completo el reconocimiento de voz y libera el hardware del micrófono
 * para garantizar que SOLO escuche cuando el usuario presione el botón VOZ.
 */
function shutdownMicrophoneResources() {
  isRecording = false;
  if (recordInterval) {
    clearInterval(recordInterval);
    recordInterval = null;
  }
  if (speechRecognition) {
    try {
      speechRecognition.onresult = null;
      speechRecognition.onend = null;
      speechRecognition.onerror = null;
      speechRecognition.abort();
    } catch (e) { }
    speechRecognition = null;
  }
  if (activeMicStream) {
    try {
      activeMicStream.getTracks().forEach(track => track.stop());
    } catch (e) { }
    activeMicStream = null;
  }
  btnVoice.classList.remove('recording');
  btnVoiceLabel.textContent = 'VOZ';
}

async function startRecording() {
  try {
    // 1. Callar al agente y limpiar cualquier sesión previa de micrófono
    stopAllAgentAudio();
    shutdownMicrophoneResources();

    // 2. Abrir micrófono con filtros de cancelación de eco y supresión de ruido
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
        channelCount: 1
      }
    });
    activeMicStream = stream;

    // Seleccionar formato de audio soportado
    let mimeType = 'audio/webm';
    if (!MediaRecorder.isTypeSupported('audio/webm')) {
      if (MediaRecorder.isTypeSupported('audio/mp4')) mimeType = 'audio/mp4';
      else if (MediaRecorder.isTypeSupported('audio/ogg')) mimeType = 'audio/ogg';
      else mimeType = '';
    }

    mediaRecorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream);
    audioChunks = [];
    liveFinalText = '';
    liveInterimText = '';
    isRecording = true;

    // 3. Iniciar reconocimiento de voz en tiempo real SOLO mientras isRecording === true
    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRec) {
      try {
        speechRecognition = new SpeechRec();
        speechRecognition.lang = 'es-CO';
        speechRecognition.continuous = true;
        speechRecognition.interimResults = true;
        speechRecognition.maxAlternatives = 1;

        speechRecognition.onresult = (event) => {
          if (!isRecording) return;
          let interim = '';
          for (let i = event.resultIndex; i < event.results.length; i++) {
            const transcript = event.results[i][0].transcript;
            if (event.results[i].isFinal) {
              liveFinalText = (liveFinalText + ' ' + transcript).trim();
            } else {
              interim += transcript;
            }
          }
          liveInterimText = interim.trim();
          const currentSpoken = (liveFinalText + ' ' + liveInterimText).trim();
          if (currentSpoken && isRecording) {
            textInput.value = currentSpoken;
            recordingStatusText.textContent = `🎤 Escuchando: "${currentSpoken}"`;
          }
        };

        // Solo reiniciar si el usuario NO ha presionado detener ni enviar
        speechRecognition.onend = () => {
          if (isRecording && speechRecognition) {
            try { speechRecognition.start(); } catch (e) { }
          }
        };

        speechRecognition.onerror = (e) => {
          console.info('Aviso SpeechRecognition:', e.error);
        };

        speechRecognition.start();
      } catch (e) {
        console.warn('No se pudo iniciar SpeechRecognition en vivo:', e);
      }
    }

    mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) audioChunks.push(event.data);
    };

    mediaRecorder.onstop = async () => {
      const blobType = mediaRecorder ? (mediaRecorder.mimeType || 'audio/webm') : 'audio/webm';
      const audioBlob = new Blob(audioChunks, { type: blobType });

      // Capturar el texto reconocido antes de limpiar el input
      const recognizedText = ([liveFinalText, liveInterimText].filter(Boolean).join(' ') || textInput.value || '').trim();

      // Apagar completamente micrófono y reconocimiento en vivo
      shutdownMicrophoneResources();
      textInput.value = '';

      await sendAudioToServer(audioBlob, blobType, recognizedText);
    };

    mediaRecorder.start(200);
    playMicOnSound();

    // UI Updates
    btnVoice.classList.add('recording');
    btnVoiceLabel.textContent = 'STOP';
    recordingBar.style.display = 'flex';
    recordingStatusText.textContent = '🎤 Escuchando... Hable ahora (presione STOP o Enviar al terminar).';
    recordSeconds = 0;
    recordTimer.textContent = '00:00';
    recordInterval = setInterval(() => {
      recordSeconds++;
      const mins = String(Math.floor(recordSeconds / 60)).padStart(2, '0');
      const secs = String(recordSeconds % 60).padStart(2, '0');
      recordTimer.textContent = `${mins}:${secs}`;
    }, 1000);

  } catch (err) {
    shutdownMicrophoneResources();
    console.error('Error al acceder al micrófono:', err);
    alert('Permiso de micrófono no otorgado o dispositivo no disponible.');
  }
}

async function stopRecordingAndSend() {
  if (!mediaRecorder || !isRecording) {
    shutdownMicrophoneResources();
    recordingBar.style.display = 'none';
    return;
  }

  // Marcar isRecording = false ANTES de detener para que onend NO reinicie el micrófono
  isRecording = false;
  clearInterval(recordInterval);
  recordInterval = null;
  playMicOffSound();
  btnVoice.classList.remove('recording');
  btnVoiceLabel.textContent = 'VOZ';
  recordingStatusText.textContent = 'Procesando su mensaje de voz...';

  if (speechRecognition) {
    try {
      speechRecognition.onend = null;
      speechRecognition.stop();
    } catch (e) { }
  }

  try {
    if (mediaRecorder.state !== 'inactive') {
      mediaRecorder.stop();
    } else {
      shutdownMicrophoneResources();
      recordingBar.style.display = 'none';
    }
  } catch (e) {
    shutdownMicrophoneResources();
    recordingBar.style.display = 'none';
  }
}

async function sendAudioToServer(audioBlob, mimeType, clientTranscript = '') {
  // Mostrar la burbuja del mensaje del usuario inmediatamente antes de la respuesta del agente
  const initialUserText = clientTranscript || '🎤 *Transcribiendo lo que dijiste...*';
  const userMsgEl = appendMessage('usuario', initialUserText);

  const loadingId = appendLoadingIndicator('Analizando lo que dijiste y consultando el inventario de Cel Red...');

  const ext = mimeType.includes('mp4') ? '.m4a' : mimeType.includes('ogg') ? '.ogg' : '.webm';
  const formData = new FormData();
  formData.append('audio', audioBlob, `consulta_voz${ext}`);
  formData.append('session_id', sessionId);
  if (clientTranscript) {
    formData.append('transcripcion_cliente', clientTranscript);
  }
  if (currentIncidenteId) formData.append('incidente_id', currentIncidenteId);

  try {
    const response = await fetch('/api/chat/audio', {
      method: 'POST',
      body: formData
    });

    recordingBar.style.display = 'none';

    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      throw new Error(errData.detail || `Error al procesar el audio (${response.status})`);
    }

    const data = await response.json();
    removeLoadingIndicator(loadingId);

    // Respetar el texto exacto que apareció cuando habló el usuario; solo actualizar si no hubo texto en vivo
    if (!clientTranscript && userMsgEl) {
      const finalTranscript = (data.texto_transcrito || 'Consulta de voz enviada').trim();
      const bodyEl = userMsgEl.querySelector('.message-body');
      if (bodyEl) {
        bodyEl.innerHTML = formatMarkdown(finalTranscript);
      }
    }

    handleAgentResponse(data);

  } catch (err) {
    recordingBar.style.display = 'none';
    removeLoadingIndicator(loadingId);
    appendMessage('agente', `⚠️ Error al procesar audio STT: ${err.message}`);
  }
}

// =====================================================================
// Procesamiento de Respuesta del Agente
// =====================================================================
function handleAgentResponse(data) {
  // Detener cualquier audio previo antes de reproducir la nueva respuesta
  stopAllAgentAudio();

  // Reproducir notificación de respuesta
  playAgentResponseSound();

  // Renderizar mensaje con reproductor de audio si el backend generó TTS
  appendMessage('agente', data.respuesta_texto, data.audio_url);

  // Si NO hay audio del servidor, usar síntesis del navegador (con fix de pausa)
  if (!data.audio_url && speechAudioEnabled && 'speechSynthesis' in window) {
    playBrowserSpeechFallback(data.respuesta_texto);
  }

  // Actualizar monitor del incidente
  if (data.incidente) {
    currentIncidenteId = data.incidente.id;
    updateIncidentCard(data.incidente, data.alerta_escalamiento);
  }

  loadIncidentsHistory();
}

function mapPriorityCssClass(prioridad) {
  const p = (prioridad || '').toLowerCase();
  if (p.includes('compra') || p.includes('critica') || p.includes('crítica')) return 'critica';
  if (p.includes('separado') || p.includes('alta')) return 'alta';
  if (p.includes('cotiz') || p.includes('media')) return 'media';
  return 'baja';
}

function mapStatusCssClass(estado) {
  const s = (estado || '').toLowerCase();
  if (s.includes('confirmad') || s.includes('escalado')) return 'escalado';
  if (s.includes('candado') || s.includes('revision') || s.includes('revisión')) return 'en-revision';
  return 'registrado';
}

function updateIncidentCard(inc, esEscalado) {
  incCodigo.textContent = inc.codigo || '---';
  incTipoEvento.textContent = inc.tipo_evento || 'En selección';
  incUbicacion.textContent = inc.ubicacion || 'Contado / Separado / Crédito';
  incAcciones.textContent = inc.acciones_recomendadas || 'Consultar catálogo y confirmar modalidad de pago.';

  // Actualizar barra compacta superior en la vista limpia de chat
  const compactCodigo = document.getElementById('compactCodigo');
  const compactEquipo = document.getElementById('compactEquipo');
  if (compactCodigo) compactCodigo.textContent = inc.codigo || '---';
  if (compactEquipo) compactEquipo.textContent = inc.tipo_evento || 'En selección';

  badgeEstado.textContent = inc.estado;
  badgeEstado.className = 'badge-status ' + mapStatusCssClass(inc.estado);

  priorityPill.textContent = inc.prioridad;
  priorityPill.className = 'priority-pill ' + mapPriorityCssClass(inc.prioridad);

  escalationAlert.style.display = (
    esEscalado ||
    inc.prioridad === 'Compra Inmediata' ||
    inc.prioridad === 'Separado' ||
    (inc.estado || '').includes('Confirmado')
  ) ? 'block' : 'none';
}

// =====================================================================
// Renderizado de Mensajes en el Chat
// =====================================================================
function appendMessage(sender, text, audioUrl = null) {
  const msgDiv = document.createElement('div');
  msgDiv.className = `message ${sender === 'usuario' ? 'user-message' : 'agent-message'}`;

  const senderName = sender === 'usuario' ? 'CLIENTE' : 'ASESOR CEL RED IA';

  let html = `
    <div class="message-sender">${senderName}</div>
    <div class="message-body">${formatMarkdown(text)}</div>
  `;

  if (audioUrl) {
    html += `
      <div class="audio-player-container">
        <audio id="tts_audio_${Date.now()}" controls src="${audioUrl}"></audio>
      </div>
    `;
  }

  html += `<div class="message-time">${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</div>`;
  msgDiv.innerHTML = html;

  // Reproducir audio del servidor con política correcta (sin autoplay attr)
  if (audioUrl) {
    const audioEl = msgDiv.querySelector('audio');
    if (audioEl) {
      audioEl.play().catch(() => {
        // Si autoplay está bloqueado, el usuario puede presionar play manualmente
        console.info('Autoplay bloqueado por el navegador; el usuario puede presionar ▶');
      });
    }
  }

  chatMessages.appendChild(msgDiv);
  chatMessages.scrollTop = chatMessages.scrollHeight;
  return msgDiv;
}

// =====================================================================
// TTS Fallback — Web Speech API con fix de pausa (Chrome bug)
// FIX: Cola de frases individual + keepalive cada 10s para evitar stall
// =====================================================================
function playBrowserSpeechFallback(text) {
  try {
    // Cancelar síntesis anterior y limpiar timers
    window.speechSynthesis.cancel();
    if (ttsKeepAlive) { clearInterval(ttsKeepAlive); ttsKeepAlive = null; }
    if (ttsChunkTimeout) { clearTimeout(ttsChunkTimeout); ttsChunkTimeout = null; }

    // Normalizador fonético para lectura natural (sin decir 'barra inclinada', 'guion' o 'paréntesis')
    const clean = text
      .replace(/\*\*([^*]+)\*\*/g, '$1')   // **negrita**
      .replace(/\*([^*]+)\*/g, '$1')        // *cursiva*
      .replace(/^\s*#{1,6}\s+/gm, '')       // # encabezados de línea
      .replace(/J\.A\.R\.V\.I\.S\.?/gi, 'Jarvis')
      .replace(/\bCRUE\b/g, 'Centro de Urgencias CRUE')
      .replace(/\bUNGRD\b/g, 'Unidad de Gestión del Riesgo')
      .replace(/\bmsnm\b/gi, 'metros sobre el nivel del mar')
      .replace(/\bej\.\s*/gi, 'por ejemplo, ')
      .replace(/\bINC-\d{8}-([A-Z0-9]{4})\b/g, (_, code) => 'código ' + code.split('').join(' '))
      .replace(/\(\s*Nivel de Urgencia:\s*([^-]+?)\s*-\s*Evento:\s*([^\)]+?)\s*\)/gi, ', con nivel de urgencia $1, por $2')
      .replace(/\|\s*\((\d{3})\)\s*(\d{3})[\-\s](\d{2})(\d{2})/g, ', o al celular $1 $2 $3 $4')
      .replace(/\((\d{3})\)\s*(\d{3})[\-\s](\d{2})(\d{2})/g, '$1 $2 $3 $4')
      .replace(/\s*\/\/\s*/g, ', ')
      .replace(/\s*\/\s*/g, ' o ')          // '/' -> 'o' en lugar de 'barra inclinada'
      .replace(/\s*\|\s*/g, ', ')
      .replace(/#(\d+)/g, (_, d) => 'numeral ' + d.split('').join(' '))
      .replace(/\n\s*[\-•]\s*/g, '. ')
      .replace(/\n+/g, '. ')
      .replace(/\s*;\s*/g, '. ')
      .replace(/\s+[\-—–]\s+/g, ', ')
      .replace(/\s*\(([^\)]+)\)/g, ', $1,')
      .replace(/[\(\)\[\]\{\}<>_~`*]/g, ' ')
      .replace(/[🚨⚠️ℹ️📍🔥🚗🌊⚡•⟳]/g, '')
      .replace(/[\u{1F000}-\u{1FFFF}]/gu, '')
      .replace(/,\s*:/g, ':')
      .replace(/:\s*\./g, ':')
      .replace(/([,\.])\s*[,\.]+/g, '$1')
      .replace(/\s+([,\.\?!:])/g, '$1')
      .replace(/\s+/g, ' ')
      .trim();

    if (!clean) return;

    // Dividir el texto completo en frases manejables por el motor TTS
    const sentences = clean.match(/[^.!?]+[.!?]+/g) || [clean];
    let i = 0;

    // Intentar seleccionar la voz más parecida a J.A.R.V.I.S. disponible en el navegador
    const availableVoices = window.speechSynthesis.getVoices();
    // Preferencia: voz española masculina con tono grave (Microsoft Alvaro, Google Español, etc.)
    const preferredVoice = availableVoices.find(v =>
      (v.name.toLowerCase().includes('alvaro') || v.name.toLowerCase().includes('diego') ||
        v.name.toLowerCase().includes('pablo') || v.name.toLowerCase().includes('jorge')) &&
      v.lang.startsWith('es')
    ) || availableVoices.find(v => v.lang.startsWith('es') && v.name.toLowerCase().includes('male'))
      || availableVoices.find(v => v.lang.startsWith('es'))
      || null;

    const speakNext = () => {
      if (i >= sentences.length) {
        if (ttsKeepAlive) { clearInterval(ttsKeepAlive); ttsKeepAlive = null; }
        return;
      }

      const fragment = sentences[i++].trim();
      if (!fragment) { speakNext(); return; }

      const utterance = new SpeechSynthesisUtterance(fragment);
      utterance.lang = 'es-ES';   // Español de España — Álvaro es voz peninsular
      utterance.rate = 0.88;       // Más pausado, solemne — como J.A.R.V.I.S.
      utterance.pitch = 0.85;       // Tono más grave

      // Usar la voz preferida si se encontró en la lista del navegador
      if (preferredVoice) utterance.voice = preferredVoice;

      utterance.onend = speakNext;
      utterance.onerror = (e) => {
        console.warn('SpeechSynthesis error:', e.error);
        speakNext();  // continuar con la siguiente frase aunque falle
      };

      window.speechSynthesis.speak(utterance);
    };

    // Iniciar lectura de la primera frase
    speakNext();

    // WORKAROUND Chrome: keepalive cada 10 segundos para evitar que el motor
    // se pause silenciosamente en textos largos (bug conocido de Chrome/Edge)
    ttsKeepAlive = setInterval(() => {
      if (!window.speechSynthesis.speaking) {
        clearInterval(ttsKeepAlive);
        ttsKeepAlive = null;
        return;
      }
      window.speechSynthesis.pause();
      window.speechSynthesis.resume();
    }, 10000);

  } catch (e) {
    console.warn('Error en síntesis nativa del navegador:', e);
  }
}

// =====================================================================
// Loading / Processing Indicator
// =====================================================================
function appendLoadingIndicator(label = 'Consultando inventario y precios en Cel Red...') {
  const id = 'loading_' + Date.now();
  const div = document.createElement('div');
  div.id = id;
  div.className = 'message agent-message';
  div.innerHTML = `
    <div class="message-sender">ASESOR CEL RED IA</div>
    <div class="message-body" style="color: var(--text-muted); font-style: italic;">
      ⟳ ${label}
    </div>
  `;
  chatMessages.appendChild(div);
  chatMessages.scrollTop = chatMessages.scrollHeight;
  return id;
}

function removeLoadingIndicator(id) {
  const el = document.getElementById(id);
  if (el) el.remove();
}

// =====================================================================
// Formateo de Markdown simple
// =====================================================================
function formatMarkdown(text) {
  if (!text) return '';
  return text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/\n/g, '<br/>');
}

// =====================================================================
// Escenarios Rápidos
// =====================================================================
function sendQuickPrompt(promptText) {
  textInput.value = promptText;
  handleSendTextMessage();
}

// =====================================================================
// Historial de Órdenes y Cotizaciones desde PostgreSQL (`celred_db`)
// =====================================================================
async function loadIncidentsHistory() {
  try {
    const res = await fetch('/api/incidentes?limit=8');
    if (!res.ok) return;
    const incidents = await res.json();

    if (!incidents || incidents.length === 0) {
      historyList.innerHTML = '<div class="history-empty">Sin órdenes o cotizaciones aún en Cel Red.</div>';
      return;
    }

    historyList.innerHTML = incidents.map(inc => {
      const priorClass = mapPriorityCssClass(inc.prioridad);
      return `
        <div class="history-item" onclick="inspectIncident(${inc.id})">
          <div class="history-header">
            <span class="history-code">${inc.codigo}</span>
            <span class="priority-pill ${priorClass}" style="font-size:0.6rem; padding: 2px 6px;">${inc.prioridad}</span>
          </div>
          <div class="history-desc">${inc.tipo_evento} — ${inc.ubicacion}</div>
        </div>
      `;
    }).join('');

  } catch (e) {
    // Base de datos puede estar iniciando, ignorar error silenciosamente
  }
}

async function inspectIncident(id) {
  try {
    const res = await fetch(`/api/incidentes/${id}`);
    if (res.ok) {
      const inc = await res.json();
      currentIncidenteId = inc.id;
      updateIncidentCard(inc, (inc.estado || '').includes('Confirmado'));
    }
  } catch (e) {
    console.error(e);
  }
}

// =====================================================================
// Navegación por Apartados Independientes (Una sola vista activa)
// =====================================================================
function switchMobileView(view) {
  const tabs = {
    chat: document.getElementById('tabBtnChat'),
    sidebar: document.getElementById('tabBtnSidebar'),
    advisor: document.getElementById('tabBtnAdvisor'),
    arch: document.getElementById('tabBtnArch')
  };
  const views = {
    chat: document.getElementById('viewChat'),
    sidebar: document.getElementById('viewSidebar'),
    advisor: document.getElementById('entrenamientoJhon'),
    arch: document.getElementById('arquitecturaSistema')
  };

  Object.values(tabs).forEach(btn => {
    if (btn) btn.classList.remove('active');
  });
  Object.values(views).forEach(sec => {
    if (sec) sec.style.display = 'none';
  });

  if (tabs[view]) tabs[view].classList.add('active');
  if (views[view]) views[view].style.display = 'block';
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function scrollToAdvisorPanel() {
  switchMobileView('advisor');
}

function quoteFromCatalog(promptText) {
  switchMobileView('chat');
  sendQuickPrompt(promptText);
}

// =====================================================================
// Apartado Exclusivo de Entrenamiento del Agente — Asesor Jhon
// =====================================================================
let advisorToken = sessionStorage.getItem('celred_advisor_token') || null;

function toggleAdvisorPassword() {
  const passInput = document.getElementById('advisorPass');
  if (!passInput) return;
  passInput.type = passInput.type === 'password' ? 'text' : 'password';
}

function setAdvisorUnlockedUI(unlocked) {
  const loginBox = document.getElementById('advisorLoginBox');
  const workspace = document.getElementById('advisorWorkspace');
  const badge = document.getElementById('advisorAuthBadge');

  if (unlocked) {
    if (loginBox) loginBox.style.display = 'none';
    if (workspace) workspace.style.display = 'grid';
    if (badge) {
      badge.textContent = '🔓 Sesión Activa: Asesor Jhon';
      badge.classList.add('unlocked');
    }
    loadAdvisorTips();
  } else {
    if (loginBox) loginBox.style.display = 'block';
    if (workspace) workspace.style.display = 'none';
    if (badge) {
      badge.textContent = '🔒 Sesión Bloqueada (Solo Jhon)';
      badge.classList.remove('unlocked');
    }
  }
}

async function restoreAdvisorSessionIfActive() {
  if (!advisorToken) {
    setAdvisorUnlockedUI(false);
    return;
  }
  try {
    const res = await fetch('/api/advisor/tips', {
      headers: { 'X-Advisor-Token': advisorToken }
    });
    if (res.ok) {
      setAdvisorUnlockedUI(true);
    } else {
      advisorToken = null;
      sessionStorage.removeItem('celred_advisor_token');
      setAdvisorUnlockedUI(false);
    }
  } catch (e) {
    setAdvisorUnlockedUI(false);
  }
}

async function handleAdvisorLogin(event) {
  event.preventDefault();
  const userEl = document.getElementById('advisorUser');
  const passEl = document.getElementById('advisorPass');
  const errEl = document.getElementById('advisorLoginError');
  if (errEl) errEl.style.display = 'none';

  const username = (userEl ? userEl.value : '').trim();
  const password = passEl ? passEl.value : '';

  try {
    const res = await fetch('/api/advisor/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(data.detail || 'Usuario o contraseña inválidos.');
    }

    advisorToken = data.token;
    sessionStorage.setItem('celred_advisor_token', advisorToken);
    if (passEl) passEl.value = '';
    playAgentResponseSound();
    setAdvisorUnlockedUI(true);
  } catch (err) {
    if (errEl) {
      errEl.textContent = `⚠️ ${err.message}`;
      errEl.style.display = 'block';
    }
  }
}

function handleAdvisorLogout() {
  advisorToken = null;
  sessionStorage.removeItem('celred_advisor_token');
  setAdvisorUnlockedUI(false);
}

function fillAdvisorTemplate(titulo, categoria, contenido) {
  const tEl = document.getElementById('tipTitulo');
  const cEl = document.getElementById('tipCategoria');
  const bEl = document.getElementById('tipContenido');
  if (tEl) tEl.value = titulo;
  if (cEl) cEl.value = categoria;
  if (bEl) bEl.value = contenido;
}

async function handleCreateAdvisorTip(event) {
  event.preventDefault();
  if (!advisorToken) {
    setAdvisorUnlockedUI(false);
    return;
  }

  const tEl = document.getElementById('tipTitulo');
  const cEl = document.getElementById('tipCategoria');
  const bEl = document.getElementById('tipContenido');
  const fbEl = document.getElementById('advisorFeedback');
  const btnEl = document.getElementById('btnSaveTip');

  const titulo = (tEl ? tEl.value : '').trim();
  const categoria = (cEl ? cEl.value : 'Tip de Cierre de Ventas').trim();
  const contenido = (bEl ? bEl.value : '').trim();

  if (!titulo || !contenido) return;

  if (btnEl) {
    btnEl.disabled = true;
    btnEl.textContent = '⏳ Guardando y vectorizando en PostgreSQL...';
  }

  try {
    const res = await fetch('/api/advisor/tips', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Advisor-Token': advisorToken
      },
      body: JSON.stringify({ titulo, categoria, contenido })
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(data.detail || 'No se pudo guardar el tip.');
    }

    if (tEl) tEl.value = '';
    if (bEl) bEl.value = '';
    if (fbEl) {
      fbEl.textContent = `✅ ${data.mensaje || 'Tip guardado exitosamente en el agente.'}`;
      fbEl.style.display = 'block';
      setTimeout(() => { fbEl.style.display = 'none'; }, 5000);
    }

    playAgentResponseSound();
    await loadAdvisorTips();
  } catch (err) {
    alert(`Error: ${err.message}`);
  } finally {
    if (btnEl) {
      btnEl.disabled = false;
      btnEl.textContent = '🧠 Enseñar y Guardar en la Memoria del Agente (pgvector)';
    }
  }
}

async function loadAdvisorTips() {
  if (!advisorToken) return;
  const listEl = document.getElementById('advisorTipsList');
  const countEl = document.getElementById('advisorTipsCount');
  if (!listEl) return;

  try {
    const res = await fetch('/api/advisor/tips', {
      headers: { 'X-Advisor-Token': advisorToken }
    });
    if (!res.ok) return;
    const tips = await res.json();
    if (countEl) countEl.textContent = String(tips.length || 0);

    if (!tips || tips.length === 0) {
      listEl.innerHTML = '<div class="history-empty">Aún no has registrado tips personalizados. ¡Usa el formulario para enseñarle el primero al agente!</div>';
      return;
    }

    listEl.innerHTML = tips.map(tip => {
      const safeTitle = (tip.titulo || '').replace(/'/g, "\\'");
      return `
        <div class="advisor-tip-item">
          <div class="tip-item-header">
            <span class="tip-item-title">💡 ${tip.titulo}</span>
            <span class="tip-item-cat">${tip.categoria}</span>
          </div>
          <div class="tip-item-body">${formatMarkdown(tip.contenido)}</div>
          <div class="tip-item-actions">
            <button type="button" class="btn-tip-test" onclick="testAdvisorTipInChat('${safeTitle}')">
              ⚡ Probar en el Chat
            </button>
            <button type="button" class="btn-tip-delete" onclick="deleteAdvisorTip(${tip.id})">
              🗑️ Eliminar
            </button>
          </div>
        </div>
      `;
    }).join('');
  } catch (e) {
    console.warn('Error cargando tips de Jhon:', e);
  }
}

function testAdvisorTipInChat(tituloTip) {
  switchMobileView('chat');
  window.scrollTo({ top: 0, behavior: 'smooth' });
  sendQuickPrompt(`Hola asesor, dame información y recomendaciones sobre: ${tituloTip}`);
}

async function deleteAdvisorTip(tipId) {
  if (!advisorToken) return;
  try {
    const res = await fetch(`/api/advisor/tips/${tipId}`, {
      method: 'DELETE',
      headers: { 'X-Advisor-Token': advisorToken }
    });
    if (res.ok) {
      await loadAdvisorTips();
    }
  } catch (e) {
    console.error('Error eliminando tip:', e);
  }
}
