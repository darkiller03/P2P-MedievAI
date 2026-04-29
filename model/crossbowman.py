# crossbowman.py
import random
from .guerrier import Guerrier
from .pikeman import Pikeman

class Crossbowman(Guerrier):
    def __init__(self, x=0.0, y=0.0):
        super().__init__(
            hp=35, attaque=0, armor=0, pierceArmor=0, range=7, lineOfSight=9, speed=0.96,
            buildTime=27, reloadTime=2.0, cooldown=0,
            basePierceAttack=5, accuracy=85, spearUnits=3,
            x=x, y=y
        )

    def get_attack_components(self, target):
        """
        Crossbowman : Attaque perçante avec bonus anti-piquiers
        - basePierceAttack (5) contre pierceArmor
        - Bonus de +3 contre Pikeman (spearUnits bonus)

        Formule finale : Σ max(0, Attack_i - Armor_i)
        = max(0, 5 - pierceArmor) + max(0, 3 - pierceArmor) si cible = Pikeman
        = max(0, 5 - pierceArmor) sinon
        """
        components = []

        # Attaque perçante de base
        base_pierce = float(getattr(self, "basePierceAttack", 0))
        components.append((base_pierce, 'pierceArmor'))

        # Bonus anti-Pikeman (spear units)
        if isinstance(target, Pikeman):
            bonus_vs_spears = float(getattr(self, "spearUnits", 0))
            components.append((bonus_vs_spears, 'pierceArmor'))

        return components

    def attaquer(self, target, distance, k_elev=1.0):
        """Crossbowman a une mécanique spéciale : accuracy (précision)"""
        ok, _ = self.can_strike(distance, target)
        if not ok:
            return 0

        # Test de précision
        acc = float(getattr(self, "accuracy", 100))
        if random.randint(1, 100) > acc:
            # Raté ! Mais consomme quand même le cooldown
            self.start_cooldown()
            return 0

        # Touché ! Calcul des dégâts avec la formule standard
        dmg = self.calculer_degats(target, k_elev)
        self.apply_damage(target, dmg)
        self.start_cooldown()
        return dmg
