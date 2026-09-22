"""
Pipeline complet d'Ataraxia.

Deux modes possibles :
- libre  : l'utilisateur décrit directement ce qu'il veut voir.
- seance : le psy guide une séance de 5 questions, puis toute la discussion
  est analysée pour construire la scène.
Dans les deux cas : génération Marble -> ouverture dans le navigateur/casque.

Usage : python -m orchestrator.pipeline
"""

from ai.conversation import (
    demarrer_seance,
    repondre_a_la_question,
    enrichir_description_libre,
    enrichir_description_depuis_historique,
    NB_QUESTIONS_SEANCE,
)
from ai.prompts import Theme, list_bundles
from voice.transcribe import ecouter_et_transcrire
from voice.tts import parler
from marble.client import generer_monde
from vr_display.launcher import ouvrir_dans_navigateur


def choisir_mode() -> str:
    """Demande à l'utilisateur le mode d'utilisation : libre ou séance guidée."""
    print("Modes disponibles :")
    print("  1. libre  — vous décrivez directement ce que vous voulez voir")
    print("  2. seance — le psy vous guide avec 5 questions avant de générer la scène")
    while True:
        choix = input("Choisissez un mode (libre/seance) : ").strip().lower()
        if choix in ("libre", "seance"):
            return choix
        print("Mode inconnu, tapez 'libre' ou 'seance'.")


def choisir_theme() -> Theme:
    """Demande le thème de la séance au clavier (à remplacer par un choix
    vocal plus tard si besoin)."""
    themes = list_bundles()
    print("Thèmes disponibles :", ", ".join(themes))
    while True:
        choix = input("Choisissez un thème pour la séance : ").strip().lower()
        if choix in themes:
            return choix
        print("Thème inconnu, réessayez.")


def executer_mode_libre() -> str | None:
    """Mode libre : une seule intention utilisateur, envoyée directement à l'enrichissement."""
    print("\nDécrivez ce que vous voulez voir, puis appuyez sur Entrée quand vous avez fini.\n")
    intention_utilisateur = ecouter_et_transcrire(mode="entree")
    print(f"Vous : {intention_utilisateur}\n")

    print("--- Analyse de votre demande en cours... ---\n")
    return enrichir_description_libre(intention_utilisateur)


def executer_mode_seance() -> str | None:
    """Mode séance guidée : 5 questions du psy, puis analyse de toute la discussion."""
    theme = choisir_theme()
    print(f"\n--- Séance '{theme}' démarrée ({NB_QUESTIONS_SEANCE} questions) ---\n")

    historique = demarrer_seance(theme)
    print("Psy :", historique[-1]["content"], "\n")
    parler(historique[-1]["content"])

    for _ in range(NB_QUESTIONS_SEANCE):
        reponse_utilisateur = ecouter_et_transcrire(mode="entree")
        print(f"Vous : {reponse_utilisateur}\n")

        historique = repondre_a_la_question(historique, reponse_utilisateur)
        print("Psy :", historique[-1]["content"], "\n")
        parler(historique[-1]["content"])

    print("--- Séance terminée, analyse de la discussion en cours... ---\n")
    return enrichir_description_depuis_historique(historique)


def lancer_pipeline():
    mode = choisir_mode()

    if mode == "libre":
        description_enrichie = executer_mode_libre()
    else:
        description_enrichie = executer_mode_seance()

    if not description_enrichie:
        print("⚠️  Échec de l'enrichissement, arrêt.")
        return

    print(f"Scène à générer : {description_enrichie}\n")
    parler("Laisse-moi te préparer un endroit, un instant...")

    url_monde = generer_monde(description_enrichie)
    if url_monde:
        print(f"✅ Monde généré : {url_monde}")
        ouvrir_dans_navigateur(url_monde)
    else:
        print("⚠️  Échec de la génération Marble. Vérifiez la clé API / les crédits.")


if __name__ == "__main__":
    try:
        lancer_pipeline()
    except KeyboardInterrupt:
        print("\n\n⏹️  Séance interrompue.")
    except Exception as e:
        # Filet de sécurité global : en cas d'imprévu pendant la démo, on
        # affiche un message clair plutôt qu'un traceback brut devant le jury.
        print(f"\n\n⚠️  Un problème inattendu est survenu : {e}")
        print("Basculez sur la vidéo de secours si besoin.")