# Comment Lancer MedievAIl BAIttle GenerAIl

## 🚀 Méthodes de Lancement

### Option 1: Launcher Interactif (RECOMMANDÉ)
```bash
python launch.py
```
Menu interactif avec toutes les options disponibles.

---

### Option 2: Menu GUI

#### Menu Plein Écran (Par défaut)
```bash
python run_menu.py
# ou
python -m view.menu
```

#### Menu Fenêtré (Si problème avec plein écran)
```bash
python run_menu_windowed.py
```

---

### Option 3: Simulation Visuelle
```bash
python visual_simulation.py
```
Lance directement une bataille avec interface graphique.

---

### Option 4: Simulation Console
```bash
python main.py
```
Mode texte avec affichage dans le terminal.

---

### Option 5: Vue Terminal (Curses)
```bash
python run_terminal.py
```
Interface texte avancée avec ncurses.

---

### Option 6: CLI Battle (Ligne de commande)
```bash
# Lancer une bataille
python -m presenter.battle run Scenario_Standard Daft Braindead

# Mode terminal
python -m presenter.battle run Scenario_Standard Daft Braindead -t

# Tournoi
python -m presenter.battle tourney -G Daft Braindead GeneralStrategus -N 10

# Charger une sauvegarde
python -m presenter.battle load quicksave.pkl
```

### Pendant une Bataille
- **P**: Pause / Lecture
- **ESPACE**: Pas à pas
- **Molette**: Zoom
- **Clic gauche/droit**: Déplacer la caméra
- **M**: Afficher/Cacher la minimap
- **Flèches**: Déplacer la caméra
- **F11/F12**: Sauvegarde/Chargement rapide
- **ESC**: Retour au menu


## 📊 Modes de Jeu Disponibles

1. **GUI Menu**: Interface complète avec sélection IA/scénario
2. **Visual Simulation**: Bataille pré-configurée avec rendu graphique
3. **Console Simulation**: Bataille en mode texte avec statistiques
4. **Terminal View**: Interface curses pour observation détaillée
5. **CLI Battle**: Contrôle complet via ligne de commande

---
