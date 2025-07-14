#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Nov 12 17:17:29 2024

@author: stereo
"""

# ██████╗░██╗███████╗░█████╗░███████╗
# ██╔══██╗██║██╔════╝██╔══██╗██╔════╝
# ██████╔╝██║█████╗░░██║░░╚═╝█████╗░░
# ██╔═══╝░██║██╔══╝░░██║░░██╗██╔══╝░░
# ██║░░░░░██║███████╗╚█████╔╝███████╗
# ╚═╝░░░░░╚═╝╚══════╝░╚════╝░╚══════╝

import os

class Piece:
    
    def __init__(self, name, color, value, texture=None, dead_texture=None, texture_rect=None):
        self.name = name
        self.color = color
        value_sign = 1 if color == 'white' else -1
        self.value = value * value_sign
        self.idx3 = 0
        self.moves = []
        self.moved = False
        self.texture = texture
        self.set_texture()
        self.dead_texture = dead_texture
        self.set_dead_texture()
        self.texture_rect = texture_rect
        
    def set_texture(self, size=80):
        textures = [f'assets/images/imgs-{size}px/{self.color}_{self.name}.png', \
                    f'assets/images/new_kset/{self.color}_{self.name}.svg']
        self.texture = os.path.join(
                textures[self.idx3]
                )
        
    def add_move(self, move):
        self.moves.append(move)
        
    def clear_moves(self):
        self.moves = []
        
    def set_dead_texture(self):
        textures = [f'assets/images/dead_{self.color}_{self.name}.png', \
                    f'assets/images/new_kset/dead_{self.color}_{self.name}.png']
        self.dead_texture = os.path.join(
                textures[self.idx3]
                )
        
    def change_texture(self):
        self.idx3 += 1
        self.idx3 %= 2

class Raider(Piece):
    
    def __init__(self, color):
        super().__init__('raider', color, 1.0)
                
class Knight(Piece):
        
    def __init__(self, color):
        super().__init__('knight', color, 3.0)
                    
class Rook(Piece):
                
    def __init__(self, color):
        super().__init__('rook', color, 5.0)
        
            
class Queen(Piece):
                
    def __init__(self, color):
        super().__init__('queen', color, 9.0)
            
class King(Piece):
                
    def __init__(self, color):
        super().__init__('king', color, 10000.0)
            