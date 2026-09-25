// Ataraxia — frontend web (vanilla JS)
// - Écoute automatique (VAD) : après la voix du psy, on capte tout de suite.
// - Bouton "reformule" pour demander au psy de rephraser sa dernière question.
// - Position "assis / couché" en haut à droite.
// - Trois phases sur l'écran monde : révélation → yeux fermés (respiration) → yeux ouverts.

const THEME_LABELS = {
  anxiete: "Anxiété",
  stress:  "Stress",
  humeur:  "Humeur",
  sommeil: "Sommeil",
  estime:  "Estime de soi",
  autre:   "Autre — j'en parle librement",
};

const state = {
  sessionId: null,
  worldId: null,
  totalTurns: 5,
  recorder: null,
  chunks: [],
  recording: false,
  currentAudio: null,
  vad: null,             // objet {cleanup, stopRecorder} pendant l'écoute auto
  pollingStarted: false,
  posture: "assis",      // "assis" | "couche"
  pendingRevealSkip: null, // closure : que faire si on skip la phase "reveal"
  mode: "psy",           // "psy" (dialogue en 5 tours) | "quick" (fast path direct)
};

const screens = {
  theme:   document.getElementById("screen-theme"),
  session: document.getElementById("screen-session"),
  world:   document.getElementById("screen-world"),
};

function showScreen(name) {
  for (const s of Object.values(screens)) s.classList.remove("active");
  screens[name].classList.add("active");
}

function setPhase(phase) {
  document.getElementById("stage").setAttribute("data-phase", phase);
  document.body.classList.toggle("eyes-closed", phase === "closed");
}

// ---------- Posture (assis / couché) ----------

function setPosture(pos) {
  state.posture = pos;
  document.body.classList.remove("pos-assis", "pos-couche");
  document.body.classList.add(pos === "couche" ? "pos-couche" : "pos-assis");
  document.querySelectorAll(".posture-btn").forEach(b => {
    b.classList.toggle("active", b.dataset.pos === pos);
  });
}

document.querySelectorAll(".posture-btn").forEach(btn => {
  btn.addEventListener("click", () => setPosture(btn.dataset.pos));
});

// ---------- Écran 1 : thèmes ----------

async function initThemes() {
  const r = await fetch("/api/themes");
  const data = await r.json();
  state.totalTurns = data.total_turns;
  buildProgress(state.totalTurns);

  const list = document.getElementById("themes-list");
  list.innerHTML = "";
  for (const t of data.themes) {
    const li = document.createElement("li");
    const btn = document.createElement("button");
    btn.className = "theme-btn";
    btn.type = "button";
    btn.innerHTML = `<span>${THEME_LABELS[t] || t}</span><span class="arrow">→</span>`;
    btn.addEventListener("click", () => startSession(t));
    li.appendChild(btn);
    list.appendChild(li);
  }
}

async function startSession(theme) {
  const r = await fetch("/api/session/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ theme }),
  });
  if (!r.ok) { alert("Impossible de démarrer la séance."); return; }
  const data = await r.json();
  state.sessionId = data.session_id;
  state.mode = "psy";
  showScreen("session");
  document.getElementById("progress").hidden = false;
  updateProgress(0);
  displayPsy(data.psy_text, data.psy_audio_b64);
}

// ---------- Fast path : décrire directement son lieu ----------

async function startQuickMode() {
  let r;
  try {
    r = await fetch("/api/session/quick_start", { method: "POST" });
  } catch (e) { alert("Impossible de démarrer le mode rapide."); return; }
  if (!r.ok) { alert("Impossible de démarrer le mode rapide."); return; }
  const data = await r.json();
  state.sessionId = data.session_id;
  state.mode = "quick";
  showScreen("session");
  // Pas de progress bar en mode rapide (pas de tours)
  document.getElementById("progress").hidden = true;
  // Bouton reformuler du dialogue psy n'a pas de sens ici
  document.getElementById("reformulate-btn").hidden = true;
  displayPsy(data.welcome_text, data.welcome_audio_b64);
}

document.getElementById("quick-mode-btn").addEventListener("click", startQuickMode);

async function sendSetPlace(blob) {
  const fd = new FormData();
  fd.append("audio", blob, "place.webm");

  let r;
  try {
    r = await fetch(`/api/session/${state.sessionId}/set_place`, { method: "POST", body: fd });
  } catch (e) { setHint("problème réseau — clique le micro pour réessayer"); return; }
  if (!r.ok) {
    let payload = null;
    try { payload = await r.json(); } catch (_) {}
    const msg = (payload && payload.detail) || "le serveur n'a pas pu traiter — clique le micro";
    setHint(typeof msg === "string" ? msg : "le serveur n'a pas pu traiter");
    return;
  }
  const data = await r.json();
  document.getElementById("user-text").textContent = data.user_text || "…";
  // On enchaîne sur la boucle recap → confirmation vocale
  showRecapAndListen(data);
}

// ---------- Progress dots ----------

function buildProgress(n) {
  const wrap = document.getElementById("progress");
  wrap.innerHTML = "";
  for (let i = 0; i < n; i++) {
    const d = document.createElement("span");
    d.className = "dot";
    wrap.appendChild(d);
  }
}

function updateProgress(current) {
  const dots = document.querySelectorAll("#progress .dot");
  dots.forEach((d, i) => {
    d.classList.remove("done", "current");
    if (i < current) d.classList.add("done");
    else if (i === current) d.classList.add("current");
  });
}

// ---------- Voix : lecture audio en base64, chaînable via callback ----------

function setCompagnonSpeaking(on) {
  document.body.classList.toggle("compagnon-speaking", !!on);
}

function playAudioB64(b64, onEnded) {
  if (state.currentAudio) {
    try { state.currentAudio.pause(); } catch (_) {}
    state.currentAudio = null;
  }
  setCompagnonSpeaking(false);
  if (!b64) { if (onEnded) onEnded(); return; }
  const audio = new Audio("data:audio/mp3;base64," + b64);
  state.currentAudio = audio;
  const finish = () => {
    setCompagnonSpeaking(false);
    if (onEnded) onEnded();
  };
  audio.onended = finish;
  audio.onerror = finish;
  audio.onplay = () => setCompagnonSpeaking(true);
  audio.play().catch(err => {
    console.warn("Lecture bloquée :", err);
    finish();
  });
}

function displayPsy(text, audioB64, onAudioEnded) {
  const cap = document.getElementById("psy-text");
  if (cap) cap.textContent = text || "";
  document.getElementById("reformulate-btn").hidden = false;
  setHint("le compagnon parle…");
  playAudioB64(audioB64, () => {
    if (onAudioEnded) onAudioEnded();
    else if (screens.session.classList.contains("active")) {
      // Défaut : après que le psy a fini, écoute auto.
      startAutoListen();
    }
  });
}

function setHint(text) { document.getElementById("mic-hint").textContent = text; }

function displaySentiment(sentiment) {
  const el = document.getElementById("sentiment");
  if (!sentiment) { el.hidden = true; return; }
  const emo = sentiment.emotion_principale || "";
  const alert = sentiment.alerte_detresse === true;
  el.hidden = !emo;
  el.textContent = alert
    ? "signal de détresse détecté — pense au 3114"
    : `perçu : ${emo}`;
  el.classList.toggle("alert", alert);
}

// ---------- Écoute automatique (VAD par RMS) ----------

const SPEAK_THRESHOLD = 0.015;   // RMS au-dessus duquel on considère "parole"
const SILENCE_MS      = 1500;    // silence continu qui déclenche l'envoi
const MIN_SPEAK_MS    = 400;     // durée minimale de parole avant de pouvoir couper
const MAX_MS          = 60000;   // sécurité : coupe à 60 s max
const CHECK_MS        = 100;

const micBtn = document.getElementById("mic-btn");
micBtn.addEventListener("click", () => {
  // Le bouton mic sert d'interrupteur manuel (rare : override du VAD).
  if (state.recording) {
    stopRecording();
  } else {
    startAutoListen();
  }
});

async function startAutoListen() {
  if (state.recording) return;
  let stream;
  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  } catch (e) {
    setHint("accès au micro refusé — clique le micro pour réessayer");
    return;
  }

  const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  const source = audioCtx.createMediaStreamSource(stream);
  const analyser = audioCtx.createAnalyser();
  analyser.fftSize = 512;
  source.connect(analyser);

  const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
    ? "audio/webm;codecs=opus"
    : "audio/webm";
  const recorder = new MediaRecorder(stream, { mimeType });
  const chunks = [];
  recorder.ondataavailable = e => { if (e.data.size > 0) chunks.push(e.data); };

  state.recorder = recorder;
  state.chunks = chunks;
  state.recording = true;
  micBtn.classList.add("recording");
  setHint("je t'écoute…");

  const dataArray = new Float32Array(analyser.fftSize);
  let hasSpoken = false;
  let speakStart = null;
  let silentSince = null;
  const startTime = Date.now();

  const cleanup = () => {
    try { clearInterval(interval); } catch (_) {}
    try { stream.getTracks().forEach(t => t.stop()); } catch (_) {}
    try { audioCtx.close(); } catch (_) {}
    state.vad = null;
  };

  const interval = setInterval(() => {
    analyser.getFloatTimeDomainData(dataArray);
    let sum = 0;
    for (let i = 0; i < dataArray.length; i++) sum += dataArray[i] * dataArray[i];
    const rms = Math.sqrt(sum / dataArray.length);

    const now = Date.now();
    if (rms > SPEAK_THRESHOLD) {
      if (!hasSpoken) { hasSpoken = true; speakStart = now; }
      silentSince = null;
    } else if (hasSpoken) {
      if (!silentSince) silentSince = now;
      else if (now - silentSince > SILENCE_MS && now - speakStart > MIN_SPEAK_MS) {
        cleanup();
        try { recorder.stop(); } catch (_) {}
      }
    }
    if (now - startTime > MAX_MS) {
      cleanup();
      try { recorder.stop(); } catch (_) {}
    }
  }, CHECK_MS);

  recorder.onstop = async () => {
    cleanup();
    micBtn.classList.remove("recording");
    micBtn.classList.add("pending");
    state.recording = false;
    if (!hasSpoken) {
      setHint("je n'ai rien entendu, clique le micro pour réessayer");
      micBtn.classList.remove("pending");
      return;
    }
    setHint("un instant…");
    const blob = new Blob(chunks, { type: mimeType });
    await sendTurn(blob);
    micBtn.classList.remove("pending");
  };

  state.vad = { cleanup, stopRecorder: () => { try { recorder.stop(); } catch (_) {} } };

  recorder.start(200);
}

function stopRecording() {
  if (state.vad) {
    state.vad.cleanup();
    state.vad.stopRecorder();
  } else if (state.recorder) {
    try { state.recorder.stop(); } catch (_) {}
  }
}

// ---------- Envoi du tour ----------

async function sendTurn(blob) {
  // En mode rapide, on n'a pas de tours psy : on envoie directement à /set_place
  // qui fait transcription + enrichissement, puis on rentre dans la boucle recap.
  if (state.mode === "quick") {
    return sendSetPlace(blob);
  }

  const fd = new FormData();
  fd.append("audio", blob, "user.webm");

  let r;
  try {
    r = await fetch(`/api/session/${state.sessionId}/turn`, { method: "POST", body: fd });
  } catch (e) { setHint("problème réseau — clique le micro pour réessayer"); return; }
  if (!r.ok) { setHint("le serveur n'a pas pu traiter — clique le micro"); return; }
  const data = await r.json();

  document.getElementById("user-text").textContent = data.user_text || "…";
  displaySentiment(data.sentiment);
  updateProgress(data.turn);

  if (data.empty) {
    setHint("je ne t'ai pas entendu, clique le micro pour reparler");
    return;
  }

  if (data.is_finished) {
    document.getElementById("reformulate-btn").hidden = true;
    setHint("merci. ton monde apaisant se dessine…");
    await startPreview();
    return;
  }

  displayPsy(data.psy_text, data.psy_audio_b64);
}

// ---------- Reformulation ----------

document.getElementById("reformulate-btn").addEventListener("click", async () => {
  // Coupe une écoute en cours pour ne pas envoyer un tour vide.
  if (state.recording) stopRecording();
  document.getElementById("reformulate-btn").disabled = true;
  setHint("le compagnon cherche d'autres mots…");
  try {
    const r = await fetch(`/api/session/${state.sessionId}/reformulate`, { method: "POST" });
    if (!r.ok) throw new Error("http " + r.status);
    const data = await r.json();
    displayPsy(data.psy_text, data.psy_audio_b64);
  } catch (e) {
    setHint("je n'ai pas pu reformuler — clique le micro pour continuer");
  } finally {
    document.getElementById("reformulate-btn").disabled = false;
  }
});

// ---------- Fin de séance : révélation → yeux fermés → yeux ouverts ----------

// ---------- Preview + Confirmation vocale ----------
// Flow C (recap éloquent) : /preview renvoie une description + audio de recap,
// puis on écoute la réponse user, /confirm classifie oui/non et soit lance Marble
// soit re-enrichit et boucle. Le skip vocal (D) coupe le recap dès que l'user
// commence à parler et enchaîne directement sur la capture de la réponse.

async function startPreview() {
  let r;
  try {
    r = await fetch(`/api/session/${state.sessionId}/preview`, { method: "POST" });
  } catch (e) { alert("Erreur pendant la préparation du lieu."); return; }
  if (!r.ok) { alert("Le serveur n'a pas pu préparer le lieu."); return; }
  const data = await r.json();
  showRecapAndListen(data);
}

function showRecapAndListen(data) {
  showScreen("world");
  setPhase("reveal");
  document.getElementById("world-desc").textContent = data.description || "";
  renderDetails(data.details || {});
  const hint = document.getElementById("reveal-hint");
  if (hint) hint.textContent = "écoute — tu choisis ensuite si tu confirmes ou si tu redécris.";

  // Masque les boutons de choix pendant la lecture du recap
  hideRevealActions();

  playRecapAudio(data.recap_audio_b64, () => {
    // Fin naturelle OU skip : on montre les 2 boutons de choix,
    // sans ouvrir le micro automatiquement (le chat vocal est opt-in).
    showRevealActions();
  });
}

function showRevealActions() {
  const actions = document.getElementById("reveal-actions");
  if (actions) actions.hidden = false;
  const skip = document.getElementById("reveal-skip-btn");
  if (skip) skip.hidden = true; // plus utile une fois les actions visibles
  const hint = document.getElementById("reveal-hint");
  if (hint) hint.textContent = "à toi : oui pour lancer, ou redécris à la voix.";
  // Réactive les boutons si désactivés au tour précédent
  const yes = document.getElementById("confirm-yes-btn");
  const vocal = document.getElementById("confirm-vocal-btn");
  if (yes) yes.disabled = false;
  if (vocal) vocal.disabled = false;
}

function hideRevealActions() {
  const actions = document.getElementById("reveal-actions");
  if (actions) actions.hidden = true;
  const skip = document.getElementById("reveal-skip-btn");
  if (skip) skip.hidden = false;
}

// Joue l'audio du recap. Un "fire" nettoie tout (audio + VAD passif éventuel)
// et enchaîne sur onDone. Cette closure est exposée dans state.pendingRevealSkip
// pour que le bouton "passer cette étape" puisse la déclencher.
async function playRecapAudio(recapB64, onDone) {
  let vadStream = null, vadCtx = null, vadInterval = null, fired = false;
  const cleanup = () => {
    try { if (vadInterval) clearInterval(vadInterval); } catch (_) {}
    try { vadStream && vadStream.getTracks().forEach(t => t.stop()); } catch (_) {}
    try { vadCtx && vadCtx.close(); } catch (_) {}
    vadStream = null; vadCtx = null; vadInterval = null;
  };
  const fire = () => {
    if (fired) return;
    fired = true;
    state.pendingRevealSkip = null;
    cleanup();
    if (state.currentAudio) {
      try { state.currentAudio.pause(); } catch (_) {}
      state.currentAudio = null;
    }
    setCompagnonSpeaking(false);
    onDone();
  };
  state.pendingRevealSkip = fire;

  // Skip vocal léger : si l'user parle pendant l'audio, on coupe (mais on
  // n'ouvre plus le micro automatiquement — il choisira son bouton).
  try {
    vadStream = await navigator.mediaDevices.getUserMedia({
      audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
    });
    vadCtx = new (window.AudioContext || window.webkitAudioContext)();
    const src = vadCtx.createMediaStreamSource(vadStream);
    const analyser = vadCtx.createAnalyser();
    analyser.fftSize = 512;
    src.connect(analyser);
    const buf = new Float32Array(analyser.fftSize);

    const SKIP_THRESHOLD = 0.03;
    const NEEDED_MS = 250;
    const IGNORE_MS = 600;
    const startAt = Date.now();
    let speakSince = null;

    vadInterval = setInterval(() => {
      if (Date.now() - startAt < IGNORE_MS) return;
      analyser.getFloatTimeDomainData(buf);
      let sum = 0;
      for (let i = 0; i < buf.length; i++) sum += buf[i] * buf[i];
      const rms = Math.sqrt(sum / buf.length);
      if (rms > SKIP_THRESHOLD) {
        if (!speakSince) speakSince = Date.now();
        else if (Date.now() - speakSince > NEEDED_MS) {
          fire();
        }
      } else {
        speakSince = null;
      }
    }, 80);
  } catch (e) {
    console.warn("skip vocal non disponible :", e);
  }

  playAudioB64(recapB64, () => fire());
}

// Bouton "oui, lance mon monde" : confirmation explicite, pas d'audio
document.getElementById("confirm-yes-btn").addEventListener("click", async () => {
  const yes = document.getElementById("confirm-yes-btn");
  const vocal = document.getElementById("confirm-vocal-btn");
  if (yes) yes.disabled = true;
  if (vocal) vocal.disabled = true;
  const hint = document.getElementById("reveal-hint");
  if (hint) hint.textContent = "ton monde se prépare…";
  let r;
  try {
    r = await fetch(`/api/session/${state.sessionId}/confirm_yes`, { method: "POST" });
  } catch (e) { alert("problème réseau"); if (yes) yes.disabled = false; if (vocal) vocal.disabled = false; return; }
  if (!r.ok) {
    let payload = null;
    try { payload = await r.json(); } catch (_) {}
    const detail = payload && payload.detail;
    const code = detail && typeof detail === "object" ? detail.code : null;
    const msg = (detail && typeof detail === "object" && detail.message) ||
                (typeof detail === "string" ? detail : null) ||
                "Le serveur n'a pas pu confirmer.";
    if (code === "marble_out_of_credits") {
      showWorldError("Crédits Marble épuisés", msg, "https://platform.worldlabs.ai/billing");
    } else if (code === "marble_api_error") {
      showWorldError("Marble a refusé la génération", msg, null);
    } else {
      alert(msg);
    }
    if (yes) yes.disabled = false;
    if (vocal) vocal.disabled = false;
    return;
  }
  const data = await r.json();
  state.worldId = data.world_id;
  const closeB64 = data.audio && data.audio.close_b64;
  goToClosedPhase(closeB64, data.stub_mode, data.status, data.viewer_url, null);
});

// Bouton "je redécris à la voix" : opt-in du micro pour reformulation
document.getElementById("confirm-vocal-btn").addEventListener("click", () => {
  hideRevealActions();
  listenForConfirmation();
});

async function listenForConfirmation() {
  const hint = document.getElementById("reveal-hint");
  if (hint) hint.textContent = "je t'écoute…";
  let stream;
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
    });
  } catch (e) {
    if (hint) hint.textContent = "micro refusé — recharge la page pour réautoriser";
    return;
  }
  const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  const source = audioCtx.createMediaStreamSource(stream);
  const analyser = audioCtx.createAnalyser();
  analyser.fftSize = 512;
  source.connect(analyser);

  const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
    ? "audio/webm;codecs=opus" : "audio/webm";
  const recorder = new MediaRecorder(stream, { mimeType });
  const chunks = [];
  recorder.ondataavailable = e => { if (e.data.size > 0) chunks.push(e.data); };

  const dataArray = new Float32Array(analyser.fftSize);
  let hasSpoken = false, speakStart = null, silentSince = null;
  const startTime = Date.now();

  const cleanup = () => {
    try { clearInterval(interval); } catch (_) {}
    try { stream.getTracks().forEach(t => t.stop()); } catch (_) {}
    try { audioCtx.close(); } catch (_) {}
  };

  const interval = setInterval(() => {
    analyser.getFloatTimeDomainData(dataArray);
    let sum = 0;
    for (let i = 0; i < dataArray.length; i++) sum += dataArray[i] * dataArray[i];
    const rms = Math.sqrt(sum / dataArray.length);
    const now = Date.now();
    if (rms > SPEAK_THRESHOLD) {
      if (!hasSpoken) { hasSpoken = true; speakStart = now; }
      silentSince = null;
    } else if (hasSpoken) {
      if (!silentSince) silentSince = now;
      else if (now - silentSince > SILENCE_MS && now - speakStart > MIN_SPEAK_MS) {
        cleanup();
        try { recorder.stop(); } catch (_) {}
      }
    }
    if (now - startTime > MAX_MS) {
      cleanup();
      try { recorder.stop(); } catch (_) {}
    }
  }, CHECK_MS);

  recorder.onstop = async () => {
    cleanup();
    if (!hasSpoken) {
      if (hint) hint.textContent = "je n'ai rien entendu — dis oui, ou redécris ton lieu";
      // Laisse le user retenter via le bouton visuel
      return;
    }
    if (hint) hint.textContent = "un instant…";
    const blob = new Blob(chunks, { type: mimeType });
    await sendConfirmation(blob);
  };

  recorder.start(200);
}

async function sendConfirmation(blob) {
  const fd = new FormData();
  fd.append("audio", blob, "confirm.webm");
  let r;
  try {
    r = await fetch(`/api/session/${state.sessionId}/confirm`, { method: "POST", body: fd });
  } catch (e) {
    alert("problème réseau pendant la confirmation");
    return;
  }
  if (!r.ok) {
    let payload = null;
    try { payload = await r.json(); } catch (_) {}
    const detail = payload && payload.detail;
    const code = detail && typeof detail === "object" ? detail.code : null;
    const msg =
      (detail && typeof detail === "object" && detail.message) ||
      (typeof detail === "string" ? detail : null) ||
      "Le serveur n'a pas pu confirmer le lieu.";
    if (code === "marble_out_of_credits") {
      showWorldError("Crédits Marble épuisés", msg, "https://platform.worldlabs.ai/billing");
    } else if (code === "marble_api_error") {
      showWorldError("Marble a refusé la génération", msg, null);
    } else {
      alert(msg);
    }
    return;
  }
  const data = await r.json();

  if (data.confirmed) {
    // Lieu validé → Marble a été appelé, on passe à la phase closed / polling
    state.worldId = data.world_id;
    const closeB64 = data.audio && data.audio.close_b64;
    goToClosedPhase(closeB64, data.stub_mode, data.status, data.viewer_url, null);
    return;
  }

  // Sinon : reformulation. La réponse de l'user devient la nouvelle description
  // → on affiche le nouveau recap et on ré-écoute.
  showRecapAndListen(data);
}

document.getElementById("reveal-skip-btn").addEventListener("click", () => {
  // fire() gère audio.pause + cleanup VAD + onDone (qui affiche les 2 boutons).
  if (state.pendingRevealSkip) state.pendingRevealSkip();
});

// ---------- Plein écran (utile sur casque VR) ----------

function toggleFullscreen() {
  const el = document.documentElement;
  const isFs = document.fullscreenElement || document.webkitFullscreenElement;
  if (isFs) {
    const exit = document.exitFullscreen || document.webkitExitFullscreen;
    if (exit) exit.call(document);
  } else {
    const req = el.requestFullscreen || el.webkitRequestFullscreen;
    if (req) req.call(el).catch(err => console.warn("fullscreen refusé :", err));
  }
}

document.getElementById("fullscreen-btn").addEventListener("click", toggleFullscreen);

function updateFullscreenLabel() {
  const btn = document.getElementById("fullscreen-btn");
  if (!btn) return;
  const isFs = document.fullscreenElement || document.webkitFullscreenElement;
  btn.textContent = isFs ? "quitter le plein écran" : "plein écran";
}
document.addEventListener("fullscreenchange", updateFullscreenLabel);
document.addEventListener("webkitfullscreenchange", updateFullscreenLabel);

function goToClosedPhase(closeAudioB64, stubMode, initialStatus, initialViewerUrl, initialThumb) {
  setPhase("closed");
  document.getElementById("close-status").textContent = "génération en cours…";
  playAudioB64(closeAudioB64);

  if (stubMode) {
    document.getElementById("close-status").textContent = "mode démo — aucune génération réelle";
    setTimeout(() => goToOpenPhase(null, null, null), 4000);
    return;
  }
  if (initialStatus === "ready" && initialViewerUrl) {
    setTimeout(() => goToOpenPhase(initialViewerUrl, initialThumb, null), 6000);
    return;
  }
  pollWorld();
}

const POLL_INTERVAL_MS = 12000;
const POLL_MAX_MS = 8 * 60 * 1000;

async function pollWorld() {
  if (state.pollingStarted) return;
  state.pollingStarted = true;
  const start = Date.now();

  while (Date.now() - start < POLL_MAX_MS) {
    await new Promise(res => setTimeout(res, POLL_INTERVAL_MS));
    let r;
    try { r = await fetch(`/api/world/${state.worldId}/status`); } catch (e) { continue; }
    if (!r.ok) continue;
    const s = await r.json();

    const elapsed = Math.round((Date.now() - start) / 1000);
    document.getElementById("close-status").textContent = `respire… ${elapsed}s`;

    if (s.status === "ready" && s.viewer_url) {
      const openB64 = s.audio && s.audio.open_b64;
      goToOpenPhase(s.viewer_url, s.thumbnail_url, openB64);
      state.pollingStarted = false;
      return;
    }
    if (s.status === "failed") {
      document.getElementById("close-status").textContent =
        "quelque chose s'est mis en travers — réessaie plus tard";
      state.pollingStarted = false;
      return;
    }
  }
  document.getElementById("close-status").textContent =
    "l'attente dépasse 8 min — vérifie ton compte Marble";
  state.pollingStarted = false;
}

function showWorldError(title, message, refillUrl) {
  showScreen("world");
  setPhase("closed");
  const el = document.getElementById("close-status");
  if (el) {
    el.innerHTML = "";
    const strong = document.createElement("strong");
    strong.textContent = title;
    const p = document.createElement("p");
    p.textContent = message;
    el.appendChild(strong);
    el.appendChild(p);
    if (refillUrl) {
      const a = document.createElement("a");
      a.href = refillUrl;
      a.target = "_blank";
      a.rel = "noopener noreferrer";
      a.textContent = "Recharger le compte World Labs";
      el.appendChild(a);
    }
  }
}

function goToOpenPhase(viewerUrl, thumbnailUrl, openAudioB64) {
  setPhase("open");
  const thumb = document.getElementById("world-thumb");
  if (thumbnailUrl) { thumb.src = thumbnailUrl; thumb.hidden = false; }
  else { thumb.hidden = true; }
  const enter = document.getElementById("world-enter");
  if (viewerUrl) { enter.href = viewerUrl; enter.hidden = false; }
  else { enter.hidden = true; }
  playAudioB64(openAudioB64);
}

function renderDetails(details) {
  const dl = document.getElementById("world-details");
  dl.innerHTML = "";
  const order = [
    "lieu_type", "moment", "meteo",
    "temperature_ressentie", "ambiance_emotionnelle",
    "couleurs_dominantes", "elements_visuels",
    "sons_ambiants", "odeurs", "mots_cles_marble",
  ];
  const seen = new Set();
  const push = (k, v) => {
    seen.add(k);
    const dt = document.createElement("dt");
    dt.textContent = k.replace(/_/g, " ");
    const dd = document.createElement("dd");
    dd.textContent = Array.isArray(v) ? v.join(", ") : String(v);
    dl.appendChild(dt); dl.appendChild(dd);
  };
  for (const k of order) if (k in details) push(k, details[k]);
  for (const k of Object.keys(details)) if (!seen.has(k)) push(k, details[k]);
}

// ---------- Restart ----------

document.getElementById("restart-btn").addEventListener("click", () => {
  state.sessionId = null;
  state.worldId = null;
  state.pollingStarted = false;
  state.mode = "psy";
  state.pendingRevealSkip = null;
  document.body.classList.remove("eyes-closed");
  document.getElementById("user-text").textContent = "—";
  document.getElementById("sentiment").hidden = true;
  document.getElementById("reformulate-btn").hidden = true;
  document.getElementById("progress").hidden = false;
  // reset des boutons du recap
  document.getElementById("reveal-actions").hidden = true;
  document.getElementById("reveal-skip-btn").hidden = false;
  showScreen("theme");
});

// ---------- Boot ----------

initThemes();
