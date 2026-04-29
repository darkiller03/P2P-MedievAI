from .guerrier import Guerrier

class Wonder(Guerrier):
    """
    Batiment 'Merveille'. 
    Victoire si l'ennemi detruit le notre.
    Gros HP, taille 5x5, ne bouge pas, n'attaque pas.
    """
    def __init__(self, x, y, team):
        super().__init__(
            x=x, 
            y=y, 
            team=team,
            hp=4800, 
            attaque=0, 
            armor=3, 
            pierceArmor=10, 
            range=0, 
            lineOfSight=8, 
            speed=0,
            buildTime=1000, # Construit longtemps
            reloadTime=1000 # Ne tire pas
        )
        
        # Surcharge pour garantir le comportement
        self.max_hp = 4800.0
        
        # Taille (5x5) - Rayon approximatif pour les collisions
        self.radius = 2.5
        
    def attaquer(self, target, dist, k_elev=1.0):
        # Un batiment ne riposte pas (dans cette version simple)
        return 0.0
        
    def tick(self, dt):
        # Ne fait rien (pas de regen, pas de mouvement)
        pass
