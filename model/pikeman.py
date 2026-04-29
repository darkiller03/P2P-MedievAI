# pikeman.py
from .guerrier import Guerrier
from .knight import Knight

class Pikeman(Guerrier):
    def __init__(self, x=0.0, y=0.0):
        super().__init__(
            hp=55, attaque=4, armor=0, pierceArmor=0, range=0, lineOfSight=4, speed=1.1,
            buildTime=22, reloadTime=3.0, cooldown=0,
            baseMelee=4, shockInfantry=1, elephants=25,
            x=x, y=y
        )

    def get_attack_components(self, target):
        """
        Pikeman : Attaque de mêlée avec bonus anti-cavalerie
        - baseMelee (4) contre armor
        - Bonus de +8 contre Knight (shockInfantry bonus)

        Formule finale : Σ max(0, Attack_i - Armor_i)
        = max(0, 4 - armor) + max(0, 8 - armor) si cible = Knight
        = max(0, 4 - armor) sinon
        """
        components = []

        # Attaque de base
        base_melee = float(getattr(self, "baseMelee", 0))
        components.append((base_melee, 'armor'))

        # Bonus anti-Knight (cavalerie montée)
        if isinstance(target, Knight):
            bonus_vs_cavalry = 8.0  # Bonus anti-cavalerie
            components.append((bonus_vs_cavalry, 'armor'))

        return components
