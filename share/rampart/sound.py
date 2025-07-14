#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jan  1 19:37:28 2025

@author: stereo
"""

# ░██████╗░█████╗░██╗░░░██╗███╗░░██╗██████╗░
# ██╔════╝██╔══██╗██║░░░██║████╗░██║██╔══██╗
# ╚█████╗░██║░░██║██║░░░██║██╔██╗██║██║░░██║
# ░╚═══██╗██║░░██║██║░░░██║██║╚████║██║░░██║
# ██████╔╝╚█████╔╝╚██████╔╝██║░╚███║██████╔╝
# ╚═════╝░░╚════╝░░╚═════╝░╚═╝░░╚══╝╚═════╝░

import pygame

class Sound:
    
    def __init__(self, path):
        self.path = path
        self.sound = pygame.mixer.Sound(path)
    
    def play(self):
        pygame.mixer.Sound.play(self.sound)