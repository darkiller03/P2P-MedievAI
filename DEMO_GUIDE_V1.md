# 🎬 GUIDE DÉMONSTRATION VERSION 1 - POUR LE PROFESSEUR

**Durée estimée:** 3-5 minutes  
**Objectif:** Montrer le système P2P multi-joueurs avec synchronisation best-effort

---

## 📋 PRÉ-REQUIS (À VÉRIFIER AVANT)

- ✅ Serveur relay compilé: `tcp_relay_server.exe`
- ✅ Python 3.7+ installé
- ✅ Modules Python: pygame, numpy
- ✅ Trois terminaux PowerShell ouverts

---

## ⚡ DÉROULEMENT RAPIDE (COPIER-COLLER)

### 1️⃣ TERMINAL SERVEUR
```powershell
# Aller au répertoire principal
cd "C:\Users\msime\OneDrive\Desktop\P2P MevievAI\AgeOfEmpire"

# Compiler le serveur (si pas déjà fait)
gcc -o tcp_relay_server tcp_relay_server.c -lws2_32

# Lancer le serveur relay
.\tcp_relay_server.exe 9001
```

**Résultat attendu:**
```
[INFO] listening on 0.0.0.0:9001
[INFO] P2P node started.
[INFO] newline-delimited protocol examples:
[INFO]   HELLO|python|player1
[INFO]   PLAYER_JOINED|player1
...
```

✅ **SERVEUR ACTIF** - Prêt à relayer les messages P2P

---

### 2️⃣ TERMINAL PLAYER 1
```powershell
# Aller au répertoire du code
cd "C:\Users\msime\OneDrive\Desktop\P2P MevievAI\AgeOfEmpire\age\FinalCode"

# Lancer Player 1 avec réseau activé
python Main.py run tiny_scenario DAFT BrainDead --net-enable --net-local-player 1 -d results_p1_demo.txt
```

**Résultat attendu (attendre ~5-10 secondes):**
```
Starting battle simulation...
[NET] Connected as player1, requesting initial state sync
[NET] enabled: local_player=1, node=127.0.0.1:9001
Opening 2.5D map viewer...
```

✅ **PLAYER 1 CONNECTÉ** - En attente de Player 2

---

### 3️⃣ TERMINAL PLAYER 2 (LANCER RAPIDEMENT APRÈS)
```powershell
# Aller au répertoire du code
cd "C:\Users\msime\OneDrive\Desktop\P2P MevievAI\AgeOfEmpire\age\FinalCode"

# Lancer Player 2 avec réseau activé
python Main.py run tiny_scenario DAFT BrainDead --net-enable --net-local-player 2 -d results_p2_demo.txt
```

**Résultat attendu (dans les 2-3 secondes):**

📍 **DANS TERMINAL PLAYER 1, vous verrez:**
```
[NET] Player 2 joined, sending local state snapshot
[NET INCONSISTENCY] HP_RACE: unit_3 local_hp=32.0 vs remote_hp=55.0
[NET INCONSISTENCY] HP_RACE: unit_3 local_hp=50.0 vs remote_hp=55.0
[NET INCONSISTENCY] HP_RACE: unit_3 local_hp=50.0 vs remote_hp=55.0
...
```

📍 **DANS TERMINAL PLAYER 2, vous verrez:**
```
[NET INCONSISTENCY] POSITION_RACE: unit_1 local=55.0,59.0 vs remote=63.9,59.0 dist=8.85
[NET INCONSISTENCY] POSITION_RACE: unit_2 local=53.5,61.0 vs remote=59.9,59.9 dist=6.49
[NET INCONSISTENCY] HP_RACE: unit_1 local_hp=41.0 vs remote_hp=46.0
[NET INCONSISTENCY] HP_RACE: unit_1 local_hp=46.0 vs remote_hp=41.0
...
```

✅ **SYNCHRONISATION ACTIVE** - Les deux joueurs communiquent!

---

## 🎯 CE QUE LE PROFESSEUR VOIT

### ✅ Objectif 1: Multi-Joueurs P2P
- ✅ Terminal 1 montre le **serveur relay** relayant les messages
- ✅ Terminal 2 montre **Player 1** connecté
- ✅ Terminal 3 montre **Player 2** connecté

### ✅ Objectif 2: Copies Locales Indépendantes
- ✅ Chaque Player a sa propre simulation du moteur
- ✅ Chacun place ses unités localement
- ✅ Les positions divergent (c'est normal en V1)

### ✅ Objectif 3: Synchronisation Best-Effort
- ✅ Messages envoyés **immédiatement** sans attente
- ✅ Aucune coordination pour corriger les incohérences
- ✅ Mode "best-effort" visible par les divergences

### ✅ Objectif 4: Interaction Entre Joueurs
- ✅ Unit 1 (Player 1) est endommagé par les attaques de Player 2
- ✅ HP diverge: `local_hp=41.0 vs remote_hp=46.0`
- ✅ Aucune résolution de conflit

### ✅ Objectif 5: Imparfection Intentionnelle
- ✅ **POSITION_RACE:** Unités bougent différemment chez chaque joueur
- ✅ **HP_RACE:** Dégâts appliqués différemment
- ✅ **Aucune garantie de cohérence:** C'est le point clé de V1!

---

## 📊 ANALYSER LES RÉSULTATS

Après que les simulations terminent (environ 30 secondes):

### Fichier résultats_p1_demo.txt:
```bash
# Afficher dans PowerShell
Get-Content "results_p1_demo.txt"
```

Vous verrez:
```
Battle data from pygame view
Engine ticks: 32.32
Winner: PLAYER 1 (RED)
Events:
   Unit 3 (P2) died at tick 21.22
   Unit 4 (P2) died at tick 32.32

[V1 NETWORK INCONSISTENCY REPORT]
Total inconsistencies: 23
  Position races: 8
  HP races: 12
  Alive races: 3

[V1 NETWORK METRICS]
Duration: 25.72s
Messages sent: 846
Messages received: 112
Avg latency: 3.2ms
Total race conditions: 23
```

✅ **C'est exactement ce qu'on attend pour V1!**

---

## 🎤 POINTS CLÉS À METTRE EN AVANT

### 1. **Synchronisation P2P Distribuée** ⭐
> "Regardez le Terminal Serveur - il relaie les messages entre les deux joueurs. Chaque joueur a sa propre instance du jeu qui tourne indépendamment."

### 2. **Copies Locales Indépendantes** ⭐
> "Player 1 et Player 2 ont chacun leur propre moteur (SimpleEngine). Ils reçoivent les mises à jour de l'autre mais les appliquent de manière asynchrone - sans synchronisation stricte."

### 3. **Incohérences Visibles** ⭐
> "Regardez les logs: POSITION_RACE et HP_RACE. L'unité 1 de Player 1 est endommagée par Player 2, mais les deux joueurs ne sont pas d'accord sur les HP. C'est intentionnel en V1 - on accepte les incohérences!"

### 4. **Mode Best-Effort** ⭐
> "Les messages sont envoyés immédiatement, appliqués immédiatement. Aucune attente de confirmation, aucune résolution de conflit. C'est du best-effort pur!"

### 5. **Métrique de Cohérence** ⭐
> "Nous détectons et documentons toutes les incohérences. 23 races conditions en 25 secondes - c'est prévu pour V1!"

---

## 🔍 TROUBLESHOOTING RAPIDE

### Le serveur ne démarre pas:
```powershell
# Vérifier que gcc est installé
gcc --version

# Recompiler si erreur
gcc -o tcp_relay_server tcp_relay_server.c -lws2_32
```

### Player 1 ne se connecte pas:
```powershell
# Vérifier que le serveur est actif (Terminal 1 doit afficher "P2P node started")
# Si pas de message [NET] Connected as player1, vérifier le port 9001 est libre
```

### Pas d'incohérences détectées:
```
# C'est normal si les joueurs ne tournent pas en parallèle
# Assurez-vous de lancer Player 2 pendant que Player 1 tourne
```

---

## ✅ CHECKLIST PRÉ-DÉMONSTRATION

- [ ] Serveur compilé: `tcp_relay_server.exe` existe
- [ ] Python 3.7+ configuré et accessible
- [ ] 3 terminaux PowerShell ouverts
- [ ] Répertoires vérifiés (P2P MevievAI existe)
- [ ] Fichiers résultats anciens supprimés ou renommés
- [ ] Professeur prêt à voir les logs en direct

---

## 🎬 TIMING ESTIMÉ

| Phase | Durée | Action |
|-------|-------|--------|
| Setup serveur | 30s | Compiler + lancer relay |
| Lancer Player 1 | 10s | Attendre connexion |
| Lancer Player 2 | 5s | Lancer rapidement |
| Simulation active | 30s | Observer les logs |
| Afficher résultats | 2m | Présenter fichiers |
| **TOTAL** | **3-5 min** | **Démonstration complète** |

---

## 📌 NOTES IMPORTANTES

### ⚠️ Pygame Viewer:
Si les fenêtres pygame s'ouvrent, le professeur peut simplement les fermer pour voir les logs plus clairement.

### ⚠️ Port 9001:
Assurez-vous que le port 9001 n'est pas utilisé par autre chose. Si erreur "Address already in use", modifier le port dans:
- `tcp_relay_server.exe 9002` (dans Terminal Serveur)
- `--net-port 9002` (dans les commandes Player 1/2)

### ⚠️ Timing:
Player 2 doit être lancé **PENDANT** que Player 1 tourne pour voir les incohérences. Si lancé trop tard, le système fonctionne mais avec peu de races (car les batailles ne se chevauchent pas).

---

## 🎯 CONCLUSION POUR LE PROFESSEUR

**"Version 1 démontre un système P2P distribué qui accepte intentionnellement les incohérences. C'est une preuve de concept du mode 'best-effort' que vous aviez demandé. Les races de position et HP montrent que sans synchronisation stricte, les états divergent - ce qui est la base pour construire une Version 2 avec garanties de cohérence."**

✅ **DÉMO PRÊTE À MONTRER!**
