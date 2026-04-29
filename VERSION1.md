# VERSION 1: Best-Effort Network Synchronization

## Objectif
Démontrer une première version du jeu distribué P2P où:
1. Chaque joueur peut placer ses objets dans la scène à son arrivée
2. Une IA envoie immédiatement une mise à jour lorsqu'elle modifie la scène
3. La mise à jour modifie la scène distante
4. Un nouvel arrivant place ses ressources en concurrence sauvage
5. **On observe et on documente les incohérences intentionnelles**

## Architecture

### Composants principaux

#### 1. **NetworkBridge** (Main.py)
- Établit la connexion TCP avec le serveur relay C
- Envoie/reçoit les messages via un protocole texte newline-délimité
- **V1 NEW**: Synchronise l'état initial avec `PLAYER_JOINED` et `INITIAL_STATE_SYNC`
- **V1 NEW**: Détecte et enregistre les incohérences (races conditions)

#### 2. **tcp_relay_server.c**
- Serveur de relais multicast simple (broadcast à tous les clients)
- Reçoit et relaie toutes les lignes du protocole
- Ne valide RIEN (best-effort mode)
- **V1**: Supporte les nouveaux messages PLAYER_JOINED et INITIAL_STATE_SYNC

#### 3. **NetworkMetrics.py** (NEW)
- Classe `NetworkMetrics` pour tracker:
  - Latence des messages (envoi → réception)
  - Race conditions (modifications concurrentes)
  - Mismatches d'état (position, HP, alive)
  - Événements réseau (joins, disconnects)
- Génère un rapport JSON summarisant les incohérences observées

#### 4. **p2p_client.py**
- Client TCP qui communique avec le serveur relay
- Thread récepteur asynchrone
- Queue non-bloquante pour messages entrants

## Protocole V1

### Messages supportés:

```
HELLO|python|playerX
  → Announce client type and player ID

PLAYER_JOINED|playerX
  → A new player joined; trigger state sync
  → Receivers send back INITIAL_STATE_SYNC for all their units

INITIAL_STATE_SYNC|playerX|unit_id|x|y|hp|attack|range|speed|unit_type
  → Snapshot of a unit (sent after PLAYER_JOINED)
  → Allows newcomers to see existing units

MOVE|playerX|unit_id|x|y
  → Unit moved to (x, y)

ATTACK|playerX|attacker_id|target_id
  → Attacker targets target

STATE|playerX|unit_id|x|y|hp|alive|target_id
  → Full authoritative state of a unit
  → Sent every tick for each local unit (idempotent)
```

## Détection des incohérences (V1)

### Types détectés:

1. **POSITION_RACE**
   - Distance > 1.0 unit entre état local et distant
   - Indique: unité a bougé différemment localement vs à distance

2. **HP_RACE**
   - Différence HP > 0.5 entre local et distant
   - Indique: dommage/healing appliqué différemment

3. **ALIVE_RACE**
   - État alive diffère entre local et distant
   - Indique: une copie pense morte, l'autre vivante

### Métriques collectées:

- `total_races`: Nombre total de race conditions
- `races_by_type`: Décomposition par type
- `state_mismatches`: Nombre de units avec mismatch
- `message_latencies`: Latence de chaque message
- `player_events`: Joins et disconnects

## Utilisation

### 1. Démarrer le serveur relay C:
```bash
tcp_relay_server.exe 9001
```

### 2. Lancer deux clients Python en mode réseau:

**Client 1 (Player 1):**
```bash
cd age/FinalCode
python Main.py run tiny_scenario DAFT BrainDead --net-enable --net-local-player 1
```

**Client 2 (Player 2):**
```bash
cd age/FinalCode
python Main.py run tiny_scenario DAFT BrainDead --net-enable --net-local-player 2
```

### 3. Observer les résultats:

#### Dans la console:
```
[NET] Connected as player1, requesting initial state sync
[NET INCONSISTENCY] POSITION_RACE: unit_1 local=15.2,10.5 vs remote=15.8,10.1 dist=0.65
[NET INCONSISTENCY] HP_RACE: unit_1 local_hp=50.0 vs remote_hp=45.3

Battle ended at t=36.0s steps=180. Winner: P1
[V1 NETWORK ANALYSIS]
  Total inconsistencies detected: 23
  Position races: 15
  HP races: 6
  Alive races: 2
```

#### Dans le fichier de données (`-d flag`):
```
[V1 NETWORK INCONSISTENCY REPORT]
Total inconsistencies: 23
  Position races: 15
  HP races: 6
  Alive races: 2

[V1 NETWORK METRICS]
Duration: 7.45s
Messages sent: 1450
Messages received: 1448
Avg latency: 3.2ms
Total race conditions: 23
Total state mismatches: 12
```

## Résultats attendus

### Sans réseau (mode offline):
- Aucun message réseau
- Les deux simulations s'exécutent indépendamment
- Aucune incohérence (pas de race possible)

### Avec réseau V1:
- Les deux clients voient les même unités
- Mais les états peuvent diverger (races)
- Les incohérences augmentent avec:
  - La latence réseau
  - Le nombre de modifications simultanées
  - La fréquence des changements d'état

## Structure de code

```
Main.py
├── NetworkBridge
│   ├── connect() → envoie HELLO + PLAYER_JOINED
│   ├── publish_local_actions() → envoie STATE, MOVE, ATTACK
│   ├── integrate_network() → traite messages entrants
│   ├── _handle_player_joined() → répond avec INITIAL_STATE_SYNC
│   ├── _handle_initial_state_sync() → crée units distantes
│   ├── _handle_state() → applique état, détecte races
│   ├── _check_inconsistency() → enregistre mismatches
│   └── get_inconsistency_report() → résumé des races
│
NetworkMetrics.py
├── NetworkMetrics (dataclass)
│   ├── record_race_condition()
│   ├── record_state_mismatch()
│   ├── get_summary() → dict JSON
│   └── print_summary() → rapport formaté
│
└── p2p_client.py
    └── P2PClient
        ├── connect() → établit TCP
        ├── send_message() → envoie ligne
        └── receive_messages() → thread async
```

## Limitations intentionnelles (V1)

❌ **Pas de validation**: N'importe qui peut modifier n'importe quelle unité
❌ **Pas de cohérence**: Les races conditions ne sont pas résolues automatiquement
❌ **Pas de timeout**: Les propriétés orphelines ne sont jamais libérées
❌ **Pas de compression**: Chaque état est envoyé entièrement, même sans changement

Ces limitations sont **intentionnelles** pour démontrer les problèmes de "best-effort" et justifier VERSION 2.

## Next: VERSION 2

VERSION 2 ajoutera:
- ✅ REQUEST_OWNERSHIP / GRANT_OWNERSHIP
- ✅ Validation côté serveur
- ✅ Arbitrage des conflits
- ✅ Garantie de cohérence

Voir [VERSION2.md](VERSION2.md) pour détails.
