# Répartition des IAs - Jeu Distribué Multi-Participants

## 1. Introduction

L’objectif est d’étendre un projet existant afin de permettre à plusieurs intelligences artificielles (IAs) d’interagir dans un environnement distribué, sans serveur central.

Chaque participant possède une copie locale du jeu et interagit avec celle-ci. Les actions locales sont propagées aux autres participants afin de maintenir une vision globale de la scène.

Les principaux défis sont :
- La cohérence des états
- La gestion de la concurrence
- L’absence de serveur central

---

## 2. Principe de Répartition

Chaque IA possède une copie locale du jeu et peut interagir avec :
- ses propres entités
- celles des autres joueurs

Caractéristiques principales :
- Pas de système de tours (jeu concurrent)
- Actions simultanées possibles
- Synchronisation via transmission des états

Une propriété clé est introduite :
**la propriété réseau**, qui garantit qu’une entité a un seul propriétaire à un instant donné.

---

## 3. Combativité

Le jeu doit être attractif et compétitif.

### Éléments à définir :
- Règles de combat communes
- Possibilité d’alliances ou de trahisons
- Gestion des interactions entre joueurs

### Fonctionnalités attendues :
- Création de parties (type invitation)
- Arrivée dynamique de joueurs
- Monde potentiellement infini
- Génération procédurale (graines aléatoires)
- Ajout d’objets et ressources dynamiques

---

## 4. Travail du point de vue Réseau

Vous devez :
- Concevoir les protocoles réseau
- Justifier leur fonctionnement
- Implémenter une solution fonctionnelle

Pour chaque protocole :
- expliquer son rôle
- détailler son implémentation
- analyser ses limites

---

## 5. Travail du point de vue Système

Vous devez définir une architecture système comprenant :
- processus
- communications
- synchronisation

Contraintes :
- séparation claire des responsabilités
- gestion de la concurrence
- traitement des erreurs

---

## 6. Passage à l’échelle

Le système doit supporter plusieurs joueurs.

### Éléments à évaluer :
- nombre de joueurs supportés
- performance du système
- charge réseau
- fluidité du jeu

Des expérimentations sont attendues pour justifier les performances.

---

## 7. Objectifs de sécurité

Optionnel mais valorisé :

- authentification des joueurs
- chiffrement des communications
- protection contre :
  - rejeu
  - falsification
  - injection de données

---

## 8. Organisation de l’équipe

- travail en groupe
- un coordinateur désigné
- auto-évaluation individuelle
- évaluation entre pairs

Chaque membre doit contribuer de manière identifiable.

---

## 9. Contraintes de développement

- Réseau en C (sockets)
- Jeu en Python
- Communication inter-processus obligatoire

Architecture imposée :
- 1 processus C (réseau)
- 1 processus Python (jeu)

---

## 10. Travail attendu

## 🔹 Version 1 : Prototype initial

Objectif : implémenter rapidement une version fonctionnelle.

### Attentes :
1. Jeu multi-joueurs (minimum 2)
2. Chaque joueur peut placer des objets
3. Envoi immédiat des mises à jour
4. Synchronisation simple des scènes
5. Interaction entre joueurs
6. Mode best-effort

### Comportement attendu :
- incohérences possibles
- conflits non gérés
- concurrence sauvage

---

## 🔹 Version 2 : Version cohérente

Objectif : corriger les incohérences.

### Principe :
Utilisation de la **propriété réseau**

### Étapes :
1. Demande de propriété avant action
2. Réception de l’état + propriété
3. Vérification de l’action
4. Mise à jour locale
5. Diffusion aux autres joueurs
6. Mise à jour distante

### Résultat :
- cohérence garantie
- concurrence contrôlée

---

## 11. Livraison finale

- Soutenance avec démonstration
- 2 diapositives :
  - solution
  - avantages / inconvénients
- dépôt Git avec preuves
- rapport d’auto-évaluation

---

## Conclusion

Le projet consiste à construire progressivement un système distribué :

- Version 1 : fonctionnement basique avec erreurs
- Version 2 : système cohérent et robuste

L’accent est mis sur :
- la compréhension des problèmes distribués
- la justification des choix techniques
- la qualité de l’implémentation