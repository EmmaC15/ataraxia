"""
Brique IA conversationnelle pour Ataraxia.

Gère :
- Le déroulé de la séance guidée (psy virtuel, 5 questions max du thème choisi).
- L'enrichissement de toute la discussion en description de monde pour Marble.
- L'analyse d'intonation/sentiment (optionnelle, en complément).
"""

import os
import json
from dotenv import load_dotenv
from groq import Groq

from ai.prompts import (
    Theme,
    PSY_SYSTEM_PROMPT,
    get_bundle,
    build_world_description_messages,
    build_sentiment_messages,
)

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
# gpt-oss-20b/120b ont un bug connu sur Groq : ils tentent parfois d'appeler
# un outil inexistant même sans tools configurés, ce qui fait planter la
# requête ("Tool choice is none, but model called a tool"). Qwen n'a pas ce
# problème et est accessible sur ce compte (22/09/2026).
MODELE_CHAT = "qwen/qwen3.8-27b"

# Séance raccourcie à 5 questions max (au lieu des 10 du bundle complet),
# pour rester compatible avec le temps de démo.
NB_QUESTIONS_SEANCE = 5

MESSAGE_SECOURS = "Désolé, j'ai eu un petit souci technique. Peux-tu répéter ta réponse ?"


def _appeler_modele(messages: list[dict], tentatives: int = 2) -> str | None:
    """
    Appelle le modèle de chat avec une tentative de retry simple en cas
    d'échec réseau/API. Renvoie None si toutes les tentatives échouent (le
    pipeline doit alors utiliser un message de secours plutôt que planter).
    """
    for i in range(tentatives):
        try:
            reponse = client.chat.completions.create(model=MODELE_CHAT, messages=messages)
            return reponse.choices[0].message.content
        except Exception as e:
            print(f"[IA] Erreur d'appel API (tentative {i + 1}/{tentatives}) : {e}")
    return None


def construire_system_message(theme: Theme, nb_questions: int = NB_QUESTIONS_SEANCE) -> str:
    """
    Assemble le system prompt du psy avec seulement les `nb_questions`
    premières questions du bundle du thème choisi (au lieu des 10 complètes).
    """
    questions = get_bundle(theme)[:nb_questions]
    liste_questions = "\n".join(f"{i + 1}. {q}" for i, q in enumerate(questions))
    system_psy = PSY_SYSTEM_PROMPT.format(questions_par_seance=nb_questions, theme=theme)
    return (
        system_psy
        + f"\n\nVoici les {nb_questions} questions de la séance, dans l'ordre à respecter :\n"
        + liste_questions
    )


def demarrer_seance(theme: Theme) -> list[dict]:
    """
    Initialise une nouvelle séance pour le thème donné.
    Renvoie l'historique de conversation, la dernière entrée étant la
    première question posée par le psy (à lire/synthétiser à voix haute).
    """
    historique = [
        {"role": "system", "content": construire_system_message(theme)},
        {"role": "user", "content": "Je suis prêt(e) à commencer."},
    ]
    contenu = _appeler_modele(historique)
    if contenu is None:
        # Filet de sécurité : on utilise directement la première question
        # scriptée du bundle plutôt que de planter la démo.
        contenu = get_bundle(theme)[0]
    historique.append({"role": "assistant", "content": contenu})
    return historique


def repondre_a_la_question(historique: list[dict], reponse_utilisateur: str) -> list[dict]:
    """
    Ajoute la réponse (transcrite) de l'utilisateur à l'historique, obtient
    la réaction empathique du psy + la question suivante, renvoie
    l'historique mis à jour.
    """
    historique.append({"role": "user", "content": reponse_utilisateur})
    contenu = _appeler_modele(historique)
    if contenu is None:
        contenu = MESSAGE_SECOURS
    historique.append({"role": "assistant", "content": contenu})
    return historique


def enrichir_description_libre(intention_utilisateur: str) -> str | None:
    """
    Mode libre : l'utilisateur décrit directement ce qu'il veut voir, sans
    passer par la séance guidée. Transforme cette intention brève en
    description riche prête pour Marble.
    """
    messages = build_world_description_messages(intention_utilisateur)
    contenu = _appeler_modele(messages)
    return contenu.strip() if contenu else None


def enrichir_description_depuis_historique(historique: list[dict]) -> str | None:
    """
    Analyse l'ensemble de la séance (toutes les questions/réponses) pour en
    dégager une description de scène adaptée à Marble — plutôt que de se
    baser sur une seule réponse isolée.
    """
    transcript = "\n".join(
        f"{'Utilisateur' if m['role'] == 'user' else 'Psy'} : {m['content']}"
        for m in historique
        if m["role"] in ("user", "assistant")
    )

    messages = build_world_description_messages(transcript)
    contenu = _appeler_modele(messages)
    return contenu.strip() if contenu else None


def analyser_sentiment(transcript: str, voice_features: dict) -> dict | None:
    """
    Analyse optionnelle d'intonation/sentiment à partir du texte transcrit
    et d'indices vocaux (débit, hauteur, volume, pauses, tremblements).
    """
    try:
        messages = build_sentiment_messages(transcript, voice_features)
        reponse = client.chat.completions.create(
            model=MODELE_CHAT,
            messages=messages,
            response_format={"type": "json_object"},
        )
        return json.loads(reponse.choices[0].message.content)
    except Exception as e:
        print(f"[IA] Erreur analyse sentiment : {e}")
        return None


if __name__ == "__main__":
    # Test rapide en mode texte (thème "anxiete"), sans passer par la voix
    historique = demarrer_seance("anxiete")
    print("Psy :", historique[-1]["content"])

    reponse_test = "Je me sens un peu tendu, surtout le matin en me réveillant."
    historique = repondre_a_la_question(historique, reponse_test)
    print("\nPsy :", historique[-1]["content"])