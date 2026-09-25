# Ataraxia

**Compagnon d'écoute vocale + monde VR apaisant, généré à la demande.**

Ataraxia est une application de bien-être mental : la personne parle librement à un compagnon virtuel bienveillant pendant ~11 tours, puis décrit un lieu où elle aimerait se relaxer. Ce lieu est transformé en un environnement immersif 3D via [marble.worldlabs.ai](https://marble.worldlabs.ai), que la personne peut ensuite explorer avec un casque VR.

Le projet est pensé pour un usage en réalité virtuelle depuis un casque (Meta Quest, PICO, etc.), mais fonctionne aussi dans un navigateur classique.

---

## Table des matières

1. [Vision et scope](#vision-et-scope)
2. [Architecture](#architecture)
3. [Prérequis](#prérequis)
4. [Installation](#installation)
5. [Configuration (.env)](#configuration-env)
6. [Lancer l'application](#lancer-lapplication)
7. [Accès depuis un casque VR](#accès-depuis-un-casque-vr)
8. [Le flow utilisateur en détail](#le-flow-utilisateur-en-détail)
9. [Structure du dépôt](#structure-du-dépôt)
10. [Endpoints API](#endpoints-api)
11. [Intégration Marble](#intégration-marble)
12. [Prompts LLM](#prompts-llm)
13. [Sécurité et vie privée](#sécurité-et-vie-privée)
14. [Débogage](#débogage)
15. [Limites connues](#limites-connues)

---

## Vision et scope

Ataraxia n'est **pas** un outil médical. C'est un compagnon d'écoute conversationnel qui aide à mettre des mots sur des émotions, dans un cadre chaleureux, français, sans jugement. Le projet a trois piliers :

- **Un dialogue psy vocal** — la personne parle à haute voix, le compagnon écoute, reformule et pose la question suivante.
- **Une bascule vers l'imaginaire** — après ~10 tours d'écoute pure, le compagnon invite à décrire un lieu apaisant.
- **Un monde VR généré** — cette description est transformée en environnement immersif via Marble, prêt à être exploré au casque.

Le projet est explicitement défensif quant aux situations de détresse : si la personne exprime une idée suicidaire ou de danger imminent, le compagnon oriente immédiatement vers le **3114** (numéro national de prévention du suicide, gratuit, 24h/24 en France).

---

## Architecture

```
+------------------+      voix        +--------------------------+
|                  |----------------->| STT: Groq Whisper-v3-turbo|
|  Casque VR / Web |                  +--------------------------+
|  (front vanilla) |                              |
|                  |     texte transcrit           v
|                  |                  +-----------+-----------+
|                  |<-----------------|  PsySession (Groq)    |
|                  |  audio (Edge TTS)|  gpt-oss-120b         |
+------------------+                  +-----------+-----------+
                                                  |
                                                  | description enrichie
                                                  v
                                     +------------+-------------+
                                     |  MarbleClient (World Labs)|
                                     |  marble-1.0-draft (~40s) |
                                     |  ou marble-1.1 (~5 min)   |
                                     +------------+-------------+
                                                  |
                                       viewer_url + assets
                                                  v
                                        Casque VR : monde immersif
```

**Composants**

| Composant | Rôle | Techno |
|---|---|---|
| `orchestrator/server.py` | Backend HTTP + orchestration | FastAPI + uvicorn |
| `orchestrator/web/` | Frontend statique (thème, dialogue, monde) | HTML + JS vanilla |
| `ai/conversation.py` | Boucle de dialogue psy, sentiment | Groq |
| `ai/prompts.py` | Tous les system prompts + enrichissement JSON | — |
| `marble/client.py` | Client typé pour l'API World Labs | httpx |
| `marble/config.py` | Chargement config depuis `.env` | python-dotenv |
| `voice/tts.py` | Synthèse vocale française chaleureuse | Edge TTS |
| `voice/transcribe.py` | STT français via Groq Whisper | Groq |
| `voice/audio_device.py` | Capture micro / lecture (CLI uniquement) | sounddevice / pygame |

---

## Prérequis

- **Python 3.10+** (testé sur 3.12)
- Un compte **[Groq](https://console.groq.com)** avec une clé API (gratuit pour usage modéré)
- Un compte **[World Labs](https://platform.worldlabs.ai)** avec des crédits Marble (payant)
- Pour l'usage VR : un casque avec navigateur (Meta Quest, PICO 4, etc.) et un moyen d'exposer le serveur en HTTPS sur le réseau (voir [Accès depuis un casque VR](#accès-depuis-un-casque-vr))

---

## Installation

```bash
git clone <repo> ataraxia
cd ataraxia/workshop-b3-projet

python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

`requirements.txt` contient : `groq`, `python-dotenv`, `sounddevice`, `soundfile`, `numpy`, `edge-tts`, `pygame`, `fastapi`, `uvicorn[standard]`, `python-multipart`, `httpx`.

---

## Configuration (.env)

Crée un fichier `.env` à la racine de `workshop-b3-projet/` :

```env
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
MARBLE_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Optionnel — sinon les valeurs par défaut ci-dessous sont utilisées
MARBLE_BASE_URL=https://api.worldlabs.ai
MARBLE_MODEL=marble-1.0-draft
MARBLE_POLL_INTERVAL_S=12
MARBLE_TIMEOUT_S=480
```

**Points d'attention**

- **Ne mets pas d'espace** autour du `=` (`python-dotenv` accepte, mais certaines libs sont strictes)
- **Ne commite jamais** ton `.env` — vérifie qu'il est dans `.gitignore`
- **Redémarre uvicorn** après avoir modifié `.env` : la clé est lue au boot, pas à chaque requête

Choix du modèle Marble :

| Modèle | Temps | Qualité | Usage recommandé |
|---|---|---|---|
| `marble-1.0-draft` | **~40s** | correcte | **par défaut**, démo, itération rapide |
| `marble-1.1` | ~5 min | haute | rendu final |
| `marble-1.1-plus` | ~5-8 min | max, grands espaces | scènes ambitieuses |

Chaque génération consomme des crédits (compte via `remaining_credits` : voir la section [Intégration Marble](#intégration-marble)).

---

## Lancer l'application

Depuis `workshop-b3-projet/` :

```bash
python -m uvicorn orchestrator.server:app --host 127.0.0.1 --port 8000 --reload
```

Puis ouvre <http://127.0.0.1:8000> dans un navigateur (Chrome/Edge/Firefox — le micro doit être autorisé au premier appel).

Le flag `--reload` recharge le code Python à chaque sauvegarde, mais **pas le `.env`** — pour ça, tu dois Ctrl+C et relancer.

### En arrière-plan (dev)

```powershell
Start-Process -NoNewWindow python -ArgumentList '-m','uvicorn','orchestrator.server:app','--host','127.0.0.1','--port','8000'
```

Pour arrêter :

```powershell
Get-Process python | Where-Object { $_.StartInfo.Arguments -match 'uvicorn' } | Stop-Process
```

---

## Accès depuis un casque VR

Le casque doit atteindre le serveur du PC. Deux contraintes non négociables :

1. **Le serveur doit être joignable depuis le réseau** (pas seulement `127.0.0.1`).
2. **Le micro exige un contexte sécurisé** — `navigator.mediaDevices.getUserMedia()` refuse toute origine non-HTTPS (sauf `localhost`). Un simple `http://<ip-lan>:8000` sur le casque **échouera silencieusement** sur le micro : le VAD n'entendra jamais rien.

### Solution recommandée : tunnel HTTPS via cloudflared

Installation :

```powershell
scoop install cloudflared
# ou
winget install Cloudflare.cloudflared
```

Puis, dans un terminal séparé, tunnel gratuit sans compte :

```powershell
cloudflared tunnel --url http://localhost:8000 --no-autoupdate
```

Après quelques secondes, cloudflared affiche une URL du type :

```
https://xxxx-xxxx-xxxx-xxxx.trycloudflare.com
```

C'est cette URL que tu ouvres **dans le navigateur du casque VR**. Elle est publique le temps que le tunnel tourne — n'importe qui avec l'URL peut ouvrir l'app et consommer tes crédits Groq/Marble. **Ferme le tunnel (Ctrl+C) dès que tu as fini.**

### Alternative : LAN direct (uniquement pour tester la UI sans le micro)

```bash
python -m uvicorn orchestrator.server:app --host 0.0.0.0 --port 8000
```

Trouve l'IP LAN du PC : `ipconfig` (Windows) ou `ip a` (Linux). Sur le casque : `http://<ip-lan>:8000`. **Le micro sera refusé** — c'est utile pour un aperçu visuel uniquement.

Windows Firewall demandera l'autorisation au premier appel LAN. Ne l'accorde que sur des réseaux privés de confiance.

---

## Le flow utilisateur en détail

Le nombre exact de tours est défini par `TOURS_PAR_SEANCE` dans `ai/prompts.py` (actuellement **11**).

### 1. Choix du thème (écran d'accueil)

L'utilisateur choisit parmi : `anxiete`, `stress`, `humeur`, `sommeil`, `estime`. Chaque thème a une question d'ouverture dédiée (voir `OPENING_QUESTIONS` dans `prompts.py`).

### 2. Boucle dialogue vocal (tours 1 à 10)

Pour chaque tour :

- Le compagnon parle (audio Edge TTS). Une fois qu'il se tait, le **VAD** (Voice Activity Detection basé RMS, dans `app.js`) démarre automatiquement l'écoute micro.
- L'utilisateur parle. Le VAD coupe après **1.5s de silence continu** ou **60s max**.
- L'audio est envoyé à `/api/session/{sid}/turn` → transcription Groq Whisper → analyse sentiment (petit modèle Groq) → génération de la réponse (gros modèle Groq).
- Le compagnon reformule/accueille en 1 phrase, puis pose UNE question adaptée.
- **Les tours 1-10 sont de la pure écoute psy** : le prompt système interdit au LLM de parler de lieu apaisant, paysage, monde VR ou visualisation à ces tours-là, même si la personne y fait allusion.

Un bouton "reformuler" permet à tout moment de demander au compagnon de rephraser sa dernière question sans avancer le compteur.

### 3. Tour 11 : bascule vers le lieu apaisant

Le tour 11 est dédié : le compagnon accueille brièvement la réponse précédente, puis pose UNE question **concrète et directe** invitant à décrire un lieu (réel ou imaginaire) où la personne aimerait se relaxer, avec ce qu'elle y voit, entend, sent, touche.

### 4. Finish : enrichissement + génération Marble

Après le tour 11, le front appelle `POST /api/session/{sid}/finish` :

- La dernière réponse user est passée à un **prompt d'enrichissement** qui produit un JSON structuré (description immersive de 40-80 mots + détails : lieu_type, moment, météo, couleurs, sons, odeurs, ambiance, etc.).
- Cette description est envoyée à Marble pour générer un monde.
- Deux audios TTS sont produits en parallèle : la description à voix haute + l'invitation à fermer les yeux.

### 5. Génération en cours (écran "respire...")

Le front polle `/api/world/{world_id}/status` toutes les **12s** pendant maximum **8 min**. Pendant ce temps, la personne a les yeux fermés (voix : "ton monde se prépare doucement").

Avec `marble-1.0-draft`, la génération aboutit en **~40s** typiquement. Avec `marble-1.1`, compter ~5 min.

### 6. Ouverture (écran "yeux ouverts")

Quand le monde est `ready`, le front affiche la thumbnail (si dispo) et un bouton "Entrer dans mon monde" qui ouvre `viewer_url` (`https://marble.worldlabs.ai/world/{world_id}`). Le compagnon invite : "Tu peux ouvrir les yeux. Ton monde t'attend. Es-tu prêt à y entrer ?"

Depuis le casque, l'utilisateur passe alors dans le viewer VR immersif de World Labs.

---

## Structure du dépôt

```
workshop-b3-projet/
├── ai/
│   ├── conversation.py       # PsySession, boucle dialogue Groq, sentiment
│   └── prompts.py            # System prompts, OPENING_QUESTIONS, enrichissement JSON
├── marble/
│   ├── client.py             # MarbleClient, WorldRef, exceptions typées
│   └── config.py             # MarbleConfig lue depuis .env
├── orchestrator/
│   ├── server.py             # FastAPI : /api/themes, /session, /world/status
│   └── web/
│       ├── index.html        # 3 écrans : theme, session, world
│       ├── app.js            # VAD, TTS, poll monde
│       └── style.css         # phases reveal / closed / open
├── voice/
│   ├── tts.py                # Edge TTS async (voix française chaleureuse)
│   ├── transcribe.py         # STT via Groq Whisper (variante CLI)
│   └── audio_device.py       # micro/HP pour usage CLI
├── scripts/
│   └── record_and_transcribe.py
├── data/
│   └── marble_stub_log.jsonl # log des worlds simulés (mode stub)
├── tests/
├── docs/
├── vr_display/
├── requirements.txt
├── .env                       # secrets — NE JAMAIS COMMITER
└── README.md
```

---

## Endpoints API

| Méthode | Chemin | Rôle |
|---|---|---|
| GET | `/` | Sert `index.html` |
| GET | `/static/*` | Assets front (JS, CSS) |
| GET | `/api/themes` | `{themes: [...], total_turns: 11}` |
| POST | `/api/session/start` | Body `{theme}` → `{session_id, turn, total_turns, psy_text, psy_audio_b64}` |
| POST | `/api/session/{sid}/turn` | Body multipart `audio` → transcription + réponse psy + sentiment + audio |
| POST | `/api/session/{sid}/reformulate` | Reformule la dernière question sans avancer le compteur |
| POST | `/api/session/{sid}/finish` | Enrichit + lance génération Marble → `{world_id, operation_id, status, description, details, viewer_url, stub_mode, audio}` |
| GET | `/api/world/{world_id}/status` | Poll état génération → `{status, viewer_url, thumbnail_url, assets, audio, invite_open_text}` |

### Codes d'erreur métier

Le handler `/api/session/{sid}/finish` distingue :

- **HTTP 402** `{detail: {code: "marble_out_of_credits", message, upstream}}` — le compte World Labs n'a plus de crédits. Le front affiche un message clair avec un lien vers la page billing.
- **HTTP 502** `{detail: {code: "marble_api_error", message, upstream}}` — autre erreur remontée par Marble (auth, prompt refusé, quota, etc.).
- **HTTP 400** `{detail: "Séance non encore terminée."}` — appel prématuré, la personne n'a pas fait ses 11 tours.

---

## Intégration Marble

### Vérifier ses crédits

```bash
curl -H "WLT-Api-Key: $MARBLE_API_KEY" https://api.worldlabs.ai/marble/v1/credits
# {"remaining_credits": 3610.0}
```

Chaque génération consomme des crédits (facturés au POST, pas à la fin — un cancel ne rembourse pas). Le coût dépend du modèle.

### Modes de fonctionnement

Le `MarbleClient` bascule automatiquement en **mode stub** si `MARBLE_API_KEY` est absente :
- `generate_world()` retourne un `WorldRef` fictif immédiatement `ready`, sans URL viewer
- Chaque appel est loggé dans `data/marble_stub_log.jsonl`
- Utile pour tester tout le pipeline sans consommer de crédits

Le front reflète le mode stub dans la phase "closed" (message "mode démo — aucune génération réelle") et saute automatiquement au bout de 4s.

### Endpoints Marble utilisés

- `POST /marble/v1/worlds:generate` — lance la génération asynchrone
- `GET  /marble/v1/operations/{operation_id}` — poll le statut de l'opération
- `GET  /marble/v1/worlds/{world_id}` — récupère assets + viewer_url une fois `ready`
- `GET  /marble/v1/credits` — solde restant

Auth : header `WLT-Api-Key: <clé>` (**pas** `Bearer`).

### Temps de génération observés

| Modèle | POST (ack) | Génération complète |
|---|---|---|
| `marble-1.0-draft` | instantané | **~40s** |
| `marble-1.1` | instantané | ~5 min |
| `marble-1.1-plus` | instantané | 5-8 min |

Un monde qui reste `IN_PROGRESS` très longtemps avec `updated_at == created_at` (aucun tick) est probablement **bloqué côté Marble** — souvent le signe que les crédits sont tombés à zéro pendant la génération.

---

## Prompts LLM

Tous les prompts vivent dans `ai/prompts.py`. Les points clés :

- **`PSY_SYSTEM_PROMPT`** — définit la posture du compagnon (français, tutoiement, phrases courtes, jamais de diagnostic, escalade 3114 si détresse) et la structure de séance en 11 tours. Les tours 1-10 sont pure écoute, le tour 11 bascule sur la question du lieu.
- **`WORLD_DESCRIPTION_SYSTEM_PROMPT`** — directeur artistique qui transforme la réponse brute du tour 11 en JSON structuré prêt pour Marble (description immersive 40-80 mots + 10 champs de détails).
- **`SENTIMENT_INTONATION_SYSTEM_PROMPT`** — analyse d'émotion vocale, sortie JSON stricte, avec flag `alerte_detresse` pour détecter les signaux critiques.
- **`VOICE_TRANSCRIPTION_PROMPT`** — prompt d'orientation passé à Whisper pour bonifier la reconnaissance sur le vocabulaire émotionnel français.

### Changer le modèle Groq

Dans `ai/conversation.py` :

```python
DEFAULT_CHAT_MODEL = "openai/gpt-oss-120b"   # psy + enrichissement
DEFAULT_FAST_MODEL = "openai/gpt-oss-20b"    # sentiment (JSON strict)
```

Modifie ces constantes ou passe-les au constructeur `PsySession(model=..., sentiment_model=...)`.

---

## Sécurité et vie privée

- **Aucune persistance côté serveur** : les sessions vivent en RAM (`_sessions` dict dans `server.py`). Un redémarrage efface tout.
- **Aucune télémétrie** : l'app n'envoie rien à des services tiers autres que Groq (LLM+STT), Edge (TTS) et World Labs (Marble).
- **Enregistrements audio** : les blobs webm envoyés au STT ne sont pas stockés sur disque côté serveur. Groq peut les conserver selon sa politique — vérifier leurs CGU.
- **Prévention détresse** : le prompt système inclut une consigne explicite d'orientation vers le **3114** en cas de signal critique.
- **Exposition réseau** : en HTTPS via cloudflared, l'URL publique du tunnel est le seul contrôle d'accès (URL longue, non listée). Ne pas la partager, la fermer après usage.

---

## Débogage

### Le monde ne se génère jamais

Ordre à vérifier :

1. **Crédits** :
   ```bash
   curl -H "WLT-Api-Key: $MARBLE_API_KEY" https://api.worldlabs.ai/marble/v1/credits
   ```
   Si `remaining_credits: 0.0` → recharger sur <https://platform.worldlabs.ai/billing>.

2. **Clé chargée en mémoire = clé actuelle du `.env` ?** Après un changement de `.env`, uvicorn doit être **redémarré** pour recharger. `--reload` ne recharge pas les variables d'environnement.

3. **Statut de l'opération** :
   ```bash
   curl -H "WLT-Api-Key: $MARBLE_API_KEY" \
     https://api.worldlabs.ai/marble/v1/operations/<operation_id>
   ```
   Si `updated_at == created_at` après plusieurs minutes → l'opération est bloquée côté Marble (souvent lié à crédits épuisés en cours de route). Aucun endpoint public pour annuler.

4. **Modèle utilisé** : `marble-1.1` prend légitimement ~5 min. Pour du dev rapide, mets `MARBLE_MODEL=marble-1.0-draft` dans `.env` puis redémarre uvicorn.

### Le micro ne s'active pas sur le casque VR

- Vérifie que l'URL est en **`https://`** (pas `http://`) — le casque exige un contexte sécurisé sinon `getUserMedia` échoue silencieusement.
- Vérifie l'autorisation dans les paramètres du navigateur du casque (icône cadenas → autorisations).
- `localhost` fonctionne sans HTTPS, mais uniquement depuis le PC lui-même.

### Le VAD coupe trop tôt / trop tard

Dans `orchestrator/web/app.js`, ajuste :

- `SPEAK_THRESHOLD = 0.015` — seuil RMS de détection de parole
- `SILENCE_MS = 1500` — durée de silence continu qui déclenche l'envoi
- `MIN_SPEAK_MS = 400` — durée minimale de parole avant qu'un silence soit valide
- `MAX_MS = 60000` — sécurité, coupe à 60s max

### `ModuleNotFoundError` sur `dotenv`, `groq`, `fastapi`...

Ton PATH contient probablement plusieurs Python. Vérifie lequel est actif :

```powershell
(Get-Command python).Source
python --version
python -c "import dotenv, groq, fastapi, uvicorn; print('OK')"
```

Réinstalle dans le bon interpréteur : `python -m pip install -r requirements.txt`.

### Uvicorn "port already in use"

```powershell
netstat -ano | Select-String ":8000.*LISTENING"
Stop-Process -Id <PID> -Force
```

### Erreur 500 côté /finish

Si tu vois un traceback avec `httpx.HTTPStatusError` non attrapé, c'est probablement un cas Marble non couvert par les handlers `MarbleOutOfCreditsError` / `MarbleAPIError`. Ajoute une branche dans `MarbleClient._raise_for_status()` pour typer l'erreur, puis dans `server.py:/finish` pour la traduire en HTTP propre.

---

## Limites connues

- **Sessions en RAM** — pas de reprise après crash uvicorn.
- **Un seul utilisateur simultané est confortable** — chaque session tient un `PsySession` avec ses appels Groq en flight ; sous charge, ajouter un worker pool.
- **Le mode stub Marble n'a pas de viewer** — utile pour tester le pipeline mais pas pour valider le rendu VR.
- **Le VAD basé RMS est fragile en environnement bruyant** — un fond sonore constant au-dessus de `SPEAK_THRESHOLD` empêche la détection de silence et coupe à 60s.
- **Aucun test automatisé** dans `tests/` pour le moment.
- **Cloudflared quick-tunnel** — URL éphémère (change à chaque relance), pas d'auth. Pour du prod, passer sur un tunnel nommé avec compte Cloudflare.

---

## Contact / crédits

Projet **Ataraxia** — workshop B3.
Stack : Groq (LLM + STT) · Edge TTS · World Labs Marble (VR) · FastAPI · vanilla JS.
