"""
Script de test manuel — à lancer en premier pour valider que la clé API
fonctionne et voir la vraie structure de réponse de l'API.

Usage : python scripts/test_marble.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from marble.client import lancer_generation, attendre_operation

DESCRIPTION_TEST = "Une forêt mystique avec des champignons lumineux"


def main():
    print("Lancement de la génération de test...")
    operation_id = lancer_generation(DESCRIPTION_TEST)
    print(f"Opération lancée : {operation_id}")

    print("Attente du résultat (peut prendre 30-45 sec avec le modèle rapide)...")
    resultat = attendre_operation(operation_id)

    print("Résultat brut de l'opération :")
    print(resultat)
    print()
    print("⚠️  Regardez la structure de 'response' ci-dessus pour trouver")
    print("    le bon champ contenant l'URL VR, puis ajustez")
    print("    marble/client.py -> generer_monde() en conséquence.")


if __name__ == "__main__":
    main()