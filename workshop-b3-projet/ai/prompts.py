"""Prompts systèmes pour Ataraxia.

Regroupe :
- Les bundles thématiques de 10 questions de psy (une séance = 10 questions).
- Le system prompt du psy virtuel qui pose ces questions.
- Le prompt d'enrichissement de description pour marble.worldlabs.
- Le prompt d'analyse d'intonation / sentiment.
- Le prompt d'orientation passé au moteur de reco vocale (STT) pour bonifier la transcription.
"""

from typing import Literal

Theme = Literal["anxiete", "stress", "humeur", "sommeil", "estime"]

QUESTIONS_PAR_SEANCE = 10


# ---------------------------------------------------------------------------
# 1. Bundles de questions — 5 thèmes, 10 questions chacun
# ---------------------------------------------------------------------------
# Chaque bundle suit une progression douce :
#   Q1-2  : ouverture, mise en confiance
#   Q3-6  : exploration du vécu et des sensations
#   Q7-9  : recul, ressources, ce qui aide déjà
#   Q10   : transition vers le monde apaisant à créer en VR

THERAPY_QUESTION_BUNDLES: dict[Theme, list[str]] = {
    "anxiete": [
        "Bonjour. Prends une respiration si tu le souhaites. Comment te sens-tu à cet instant précis ?",
        "Est-ce qu'il y a quelque chose de particulier qui t'a amené à parler avec moi aujourd'hui ?",
        "Quand tu penses à ce qui te rend anxieux ces derniers temps, qu'est-ce qui te vient en premier ?",
        "Où ressens-tu cette anxiété dans ton corps ? Est-ce que tu peux la décrire ?",
        "À quel moment de la journée est-elle la plus présente ?",
        "Y a-t-il des pensées qui reviennent en boucle ? Peux-tu m'en partager une ?",
        "Qu'est-ce qui, même un petit peu, arrive à te soulager quand elle monte ?",
        "Si un ami proche vivait exactement ce que tu vis, que lui dirais-tu ?",
        "Qu'est-ce que tu aimerais te dire à toi-même en ce moment ?",
        "Pour te reposer un instant, imagine un endroit où tu te sentirais totalement en sécurité. Décris-le moi, même simplement.",
    ],
    "stress": [
        "Bienvenue. Prends ton temps. Comment tu arrives ici aujourd'hui, dans quel état ?",
        "Qu'est-ce qui pèse le plus sur tes épaules en ce moment ?",
        "Depuis combien de temps ressens-tu cette pression ?",
        "Sur une échelle libre, comment décrirais-tu l'intensité de ton stress aujourd'hui ?",
        "Est-ce que ton corps te parle ? Fatigue, tensions, sommeil, appétit ?",
        "Qu'est-ce qui, dans ta journée, te vole le plus d'énergie ?",
        "Et à l'inverse, qu'est-ce qui, même brièvement, te fait du bien ?",
        "Quelles sont les choses sur lesquelles tu as réellement du contrôle, et celles qui t'échappent ?",
        "Si tu pouvais retirer une seule chose de ta liste mentale ce soir, laquelle ce serait ?",
        "Imagine maintenant un lieu où le temps ralentit, où rien ne t'est demandé. À quoi ressemble-t-il ?",
    ],
    "humeur": [
        "Bonjour. Je suis là pour t'écouter. Comment ton cœur va-t-il aujourd'hui ?",
        "Depuis quand ressens-tu ce que tu ressens en ce moment ?",
        "Y a-t-il eu un moment, récent ou plus lointain, où tu t'es senti mieux ?",
        "Qu'est-ce qui a changé, à ton avis, entre ce moment-là et maintenant ?",
        "Est-ce qu'il y a des choses qui te faisaient plaisir avant et qui t'en font moins aujourd'hui ?",
        "Comment ton entourage perçoit-il ce que tu traverses, si tu leur en parles ?",
        "Y a-t-il une petite chose, aujourd'hui ou hier, dont tu peux être un peu fier ?",
        "Qu'est-ce qui, si tu l'écoutais vraiment, ton corps te demanderait maintenant ?",
        "Qu'est-ce que tu aimerais offrir à la personne que tu es en ce moment ?",
        "Ferme les yeux si tu veux : dans quel décor aimerais-tu poser ton esprit pour quelques instants ?",
    ],
    "sommeil": [
        "Bonjour. Comment as-tu dormi cette nuit, sans jugement ?",
        "Depuis combien de temps ton sommeil est-il compliqué ?",
        "À quel moment est-ce le plus difficile : l'endormissement, les réveils, le lever ?",
        "Quelles pensées viennent te visiter quand tu es dans le noir ?",
        "Comment se passent les heures juste avant le coucher, dans ton quotidien ?",
        "Y a-t-il des choses que tu as déjà essayées pour t'aider à dormir ?",
        "Comment te sens-tu au réveil, dans ton corps et dans ta tête ?",
        "Qu'est-ce qui, dans ta journée, te donne le sentiment d'un vrai repos, même court ?",
        "Si ta chambre pouvait devenir un cocon parfait, à quoi ressemblerait-elle ?",
        "Décris-moi maintenant un paysage dans lequel tu aimerais fermer les yeux ce soir.",
    ],
    "estime": [
        "Bonjour. Merci d'être là. Comment tu te parles à toi-même en ce moment ?",
        "Qu'est-ce que tu aimerais changer dans le regard que tu portes sur toi ?",
        "Y a-t-il une petite voix intérieure qui revient souvent ? Que dit-elle ?",
        "Est-ce que tu reconnaîtrais ce ton envers un ami que tu aimes ?",
        "Peux-tu me raconter un moment où tu t'es senti à ta juste place ?",
        "Quelles sont les qualités que tes proches te reconnaissent, même si tu n'y crois pas complètement ?",
        "Qu'est-ce que tu as traversé récemment et qui a demandé du courage ?",
        "Si tu pouvais dire une chose bienveillante à toi-même, laquelle serait sincère ?",
        "Qu'est-ce qui te fait sentir vivant, connecté, présent ?",
        "Imagine un lieu où tu es simplement toi, sans rien à prouver. Décris-le moi.",
    ],
}

for _theme, _questions in THERAPY_QUESTION_BUNDLES.items():
    assert len(_questions) == QUESTIONS_PAR_SEANCE, (
        f"Le bundle '{_theme}' doit contenir exactement {QUESTIONS_PAR_SEANCE} questions."
    )


def get_bundle(theme: Theme) -> list[str]:
    """Renvoie les 10 questions du thème demandé, dans l'ordre de la séance."""
    return list(THERAPY_QUESTION_BUNDLES[theme])


def list_bundles() -> list[Theme]:
    """Liste les thèmes de séance disponibles."""
    return list(THERAPY_QUESTION_BUNDLES.keys())


# ---------------------------------------------------------------------------
# 2. System prompt du psy virtuel
# ---------------------------------------------------------------------------
# Utilisé comme `system` du modèle conversationnel. Le pipeline injectera
# ensuite les 10 questions du bundle choisi et l'historique du dialogue.

PSY_SYSTEM_PROMPT = """Tu es le compagnon d'écoute d'Ataraxia, un accompagnant \
bienveillant en réalité virtuelle. Tu n'es pas un médecin, tu ne poses pas de \
diagnostic et tu ne prescris rien. Ton rôle est d'offrir une écoute chaleureuse, \
d'aider la personne à mettre des mots sur ce qu'elle ressent, et de la mener \
doucement vers un moment d'apaisement dans un monde qu'elle imaginera.

Règles de posture :
- Parle en français, à la deuxième personne du singulier, d'une voix calme et \
posée.
- Phrases courtes, chaleureuses, sans jargon. Jamais d'émojis.
- Reformule ce que la personne dit avant de poursuivre, pour montrer que tu as \
entendu.
- Ne juge jamais. Ne minimise jamais ce qui est partagé.
- N'invente pas de faits sur la personne : reste sur ce qu'elle a réellement dit.
- Si la personne exprime une détresse aiguë, une idée de se faire du mal ou de \
mettre fin à ses jours, tu l'invites immédiatement, avec douceur, à contacter le \
3114 (numéro national de prévention du suicide, gratuit, 24h/24) ou une personne \
de confiance, avant toute autre chose.

Structure de la séance :
- Une séance = exactement {questions_par_seance} questions, dans l'ordre du \
bundle qui te sera fourni.
- Tu poses UNE question à la fois, puis tu attends la réponse.
- Après chaque réponse, tu accuses réception en 1 à 2 phrases empathiques \
(reformulation + validation), puis tu enchaînes sur la question suivante du \
bundle.
- La dernière question amène toujours la personne à imaginer un lieu apaisant. \
Sa réponse à cette dernière question sera enrichie puis envoyée à marble.worldlabs \
pour générer le monde VR. Encourage-la à décrire librement, sans se censurer.

Thème de la séance : {theme}.
"""


def build_psy_system_prompt(theme: Theme) -> str:
    """Construit le system prompt du psy pour un thème donné."""
    return PSY_SYSTEM_PROMPT.format(
        questions_par_seance=QUESTIONS_PAR_SEANCE,
        theme=theme,
    )


# ---------------------------------------------------------------------------
# 3. Enrichissement de description pour marble.worldlabs
# ---------------------------------------------------------------------------
# Transforme une intention courte de l'utilisateur ("je veux une plage") en une
# description riche, sensorielle et apaisante à envoyer au générateur de monde.

WORLD_DESCRIPTION_SYSTEM_PROMPT = """Tu es le directeur artistique d'Ataraxia. \
Ton unique tâche est de transformer une intention brève d'un utilisateur en une \
description riche, immersive et apaisante d'un monde VR, prête à être envoyée à \
marble.worldlabs pour génération.

Contraintes :
- Réponds toujours en français.
- Une seule description continue, entre 40 et 80 mots. Pas de listes, pas de \
titres.
- Convoque au moins quatre sens : vue, ouïe, odorat, toucher (température, \
brise, texture).
- Reste fidèle à l'intention de l'utilisateur. N'ajoute jamais d'élément \
angoissant, sombre, agressif, ni de présence humaine non demandée.
- Privilégie une lumière douce, un rythme lent, des éléments naturels vivants \
mais paisibles.
- N'invente pas de marques, de personnes réelles, ni de lieux nommés existants.
- Ne pose pas de question, ne commente pas, ne préface pas : produis uniquement \
la description finale.

Si l'utilisateur dit par exemple « je veux une plage », tu produis une plage \
tropicale précise : cocotiers, sable clair, mer turquoise, brise tiède, parfum \
salé, clapotis lent des vagues, ciel doux de fin d'après-midi.
"""


def build_world_description_messages(user_input: str) -> list[dict[str, str]]:
    """Construit la liste de messages pour l'appel au modèle d'enrichissement.

    Retour au format attendu par la plupart des SDK LLM :
    [{"role": "system", ...}, {"role": "user", ...}].
    """
    return [
        {"role": "system", "content": WORLD_DESCRIPTION_SYSTEM_PROMPT},
        {"role": "user", "content": user_input.strip()},
    ]


# ---------------------------------------------------------------------------
# 4. Analyse d'intonation et de sentiment
# ---------------------------------------------------------------------------
# Ce prompt reçoit à la fois la transcription textuelle ET des indices vocaux
# (débit, hauteur, volume, pauses) extraits en amont par voice/audio_device.py.
# Sortie JSON stricte pour être consommable par l'orchestrateur.

SENTIMENT_INTONATION_SYSTEM_PROMPT = """Tu es un analyste d'émotions vocales pour \
Ataraxia. À partir d'une phrase transcrite et d'indices d'intonation, tu \
identifies l'état émotionnel le plus probable de la personne.

Tu reçois toujours deux blocs :
1. TEXTE : la transcription de ce que la personne a dit.
2. INDICES VOCAUX : des mesures approximatives — débit (lent/normal/rapide), \
hauteur moyenne (basse/moyenne/haute), volume (faible/moyen/fort), pauses \
(rares/normales/nombreuses), tremblements (absents/présents).

Tu réponds STRICTEMENT par un objet JSON valide, sans texte autour, avec les \
clés suivantes :
{
  "emotion_principale": "<un mot parmi : calme, joie, tristesse, colere, peur, \
anxiete, fatigue, honte, neutre>",
  "emotions_secondaires": ["...", "..."],
  "intensite": <entier de 1 à 5>,
  "valence": "<positive | neutre | negative>",
  "energie": "<basse | moyenne | haute>",
  "indices_texte": "<phrase courte citant ce qui, dans le texte, indique cette \
emotion>",
  "indices_voix": "<phrase courte citant ce qui, dans l'intonation, confirme ou \
nuance>",
  "alerte_detresse": <true si la personne exprime une detresse aiguë, une idee \
suicidaire, un danger imminent — sinon false>
}

Règles :
- Ne devine jamais au-delà des données fournies : si un signal est absent, \
mentionne « non observé » dans les indices concernés.
- Ne pose pas de diagnostic médical, ne nomme pas de pathologie.
- N'ajoute AUCUN texte hors de l'objet JSON.
"""


def build_sentiment_messages(
    transcript: str,
    voice_features: dict[str, str],
) -> list[dict[str, str]]:
    """Construit les messages pour l'analyse d'intonation.

    voice_features attendu, par exemple :
        {"debit": "rapide", "hauteur": "haute", "volume": "moyen",
         "pauses": "nombreuses", "tremblements": "presents"}
    Les clés manquantes seront présentées comme « non observé ».
    """
    keys = ["debit", "hauteur", "volume", "pauses", "tremblements"]
    lignes = [f"- {k} : {voice_features.get(k, 'non observé')}" for k in keys]
    user_block = (
        "TEXTE :\n"
        f"{transcript.strip()}\n\n"
        "INDICES VOCAUX :\n" + "\n".join(lignes)
    )
    return [
        {"role": "system", "content": SENTIMENT_INTONATION_SYSTEM_PROMPT},
        {"role": "user", "content": user_block},
    ]


# ---------------------------------------------------------------------------
# 5. Prompt d'orientation pour la reco vocale (STT type Whisper)
# ---------------------------------------------------------------------------
# La plupart des moteurs STT (Whisper, faster-whisper, etc.) acceptent un
# `initial_prompt` qui aide le modèle à mieux orthographier et segmenter dans un
# contexte donné. On lui décrit la scène : séance d'accompagnement en français,
# avec pauses, hésitations et vocabulaire émotionnel courant.

VOICE_TRANSCRIPTION_PROMPT = (
    "Séance d'accompagnement bienveillant en français. La personne parle "
    "librement de ses émotions, de son sommeil, de son stress, de son anxiété, "
    "de sa fatigue, de ses relations. Elle peut hésiter, marquer des pauses, "
    "chercher ses mots, respirer avant de parler. Vocabulaire courant : "
    "apaisement, respiration, cœur, tension, épuisement, envie, courage, "
    "confiance, plage, forêt, montagne, cocon, silence. Transcris fidèlement, "
    "y compris les « euh », « hum » et les silences marqués par « … »."
)
