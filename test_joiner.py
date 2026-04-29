
import pygame
from view.menu import MainMenu
from model.game import Game
from model.map import BattleMap
import time

pygame.init()
screen = pygame.display.set_mode((800, 600))
menu = MainMenu()
menu.screen = screen
# On force le lancement en mode JOIN
menu.launch_multiplayer(is_host=False)
