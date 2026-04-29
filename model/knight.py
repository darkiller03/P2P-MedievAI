# knight.py
from .guerrier import Guerrier

class Knight(Guerrier):
    def __init__(self, x=0.0, y=0.0):
        super().__init__(
            hp=100, attaque=8, armor=2, pierceArmor=1, range=0, lineOfSight=4, speed=1.6,
            buildTime=30, reloadTime=1.8, cooldown=0,
            baseMelee=8, x=x, y=y
        )

    def get_attack_components(self, target):
        """
        Knight : Attaque de mêlée pure
        - baseMelee (8) contre armor
        """
        base_melee = float(getattr(self, "baseMelee", 0))
        return [(base_melee, 'armor')]
