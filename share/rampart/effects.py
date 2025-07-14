#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Mar 25 16:08:13 2025

@author: stereo
"""

# ███████╗███████╗███████╗███████╗░█████╗░████████╗░██████╗
# ██╔════╝██╔════╝██╔════╝██╔════╝██╔══██╗╚══██╔══╝██╔════╝
# █████╗░░█████╗░░█████╗░░█████╗░░██║░░╚═╝░░░██║░░░╚█████╗░
# ██╔══╝░░██╔══╝░░██╔══╝░░██╔══╝░░██║░░██╗░░░██║░░░░╚═══██╗
# ███████╗██║░░░░░██║░░░░░███████╗╚█████╔╝░░░██║░░░██████╔╝
# ╚══════╝╚═╝░░░░░╚═╝░░░░░╚══════╝░╚════╝░░░░╚═╝░░░╚═════╝░

import pygame
import random as rd

from const import *

def generate_lightning(start_x, start_y, end_x, end_y, depth=50):
    # generate lightning bolt coordinates between two points
    points = [(start_x, start_y)]
    
    # calculate direction vector
    dx = (end_x - start_x) / depth
    dy = (end_y - start_y) / depth
    
    for i in range(1, depth):
        # base position along the line
        base_x = start_x + dx * i
        base_y = start_y + dy * i
        
        # add some randomness
        if i < depth-1:  # Don't randomize the last point
            offset_x = rd.randint(-15, 15)
            offset_y = rd.randint(-5, 5)
            
            # reduce randomness as we approach the end
            scale = 1 - (i / depth)
            offset_x *= scale
            offset_y *= scale
            
            points.append((base_x + offset_x, base_y + offset_y))
        else:
            points.append((end_x, end_y))
    
    return points

class Lightning_effect:
    def __init__(self, game):
        self.game = game
        self.active = False
        self.frame = 0
        self.max_frames = 30  # animation duration
        # new color properties:
        self.base_color = (150, 220, 255)  # bright cyan-blue
        self.core_color = (220, 240, 255)   # white-hot core
        self.bloom_color = (100, 150, 255)  # outer glow
        self.points = []  # stores lightning path coordinates
    
    def trigger(self, player_color, persist_frames=30):
        # start the lightning animation for the given player"""
        self.active = True
        self.frame = 0
        self.persist_frames = persist_frames
        
        # Base Y adjustments for rampart
        rampart_adj = RAMPART_HEIGHT if not self.game.flipped else 0
        
        # calculate positions based on layout
        if player_color == 'white':
            # white's graveyard and deck are on the right
            if not self.game.flipped:
                # normal orientation
                start_x = 908 + GWIDTH//2  # graveyard center (right side)
                start_y = 90 + GHEIGHT//2
                end_x = 908 + CWIDTH//2   # deck center (right side)
                end_y = CEM_HEIGHT + CHEIGHT//2
            else:
                # flipped orientation - swap to left side
                start_x = 2 + GWIDTH//2   # graveyard center (left side)
                start_y = (HEIGHT - CEM_HEIGHT + 65 + RAMPART_HEIGHT) + GHEIGHT//2 + 300
                end_x = 2 + CWIDTH//2     # deck center (left side)
                end_y = CHEIGHT//2 + 300
        else:  # black
            # black's graveyard and deck are on the left
            if not self.game.flipped:
                # normal orientation
                start_x = 2 + GWIDTH//2   # graveyard center (left side)
                start_y = (HEIGHT - CEM_HEIGHT + 65 + RAMPART_HEIGHT) + GHEIGHT//2 + 300
                end_x = 2 + CWIDTH//2     # deck center (left side)
                end_y = CHEIGHT//2 + 300
            else:
                # flipped orientation - swap to right side
                start_x = 908 + GWIDTH//2  # graveyard center (right side)
                start_y = 90 + GHEIGHT//2
                end_x = 908 + CWIDTH//2   # deck center (right side)
                end_y = CEM_HEIGHT + CHEIGHT//2 + rampart_adj
        
        # generate the lightning path
        self.points = generate_lightning(start_x, start_y, end_x, end_y)
    
    def update(self):
        # update animation frame
        if self.active:
            self.frame += 1
            if self.frame >= self.max_frames:
                self.active = False
    
    def draw(self, surface):
        if not self.active or len(self.points) < 2:
            return

        # create temporary surface for additive blending
        lightning_surface = pygame.Surface((surface.get_size()), pygame.SRCALPHA)
        
        # calculate fade (1.0 at start, 0.0 at end)
        fade = 1.0 - (self.frame / self.max_frames)
        
        # draw three layered components:
        for i in range(len(self.points)-1):
            # 1. outer glow (widest)
            pygame.draw.line(
                lightning_surface, 
                (*self.bloom_color, int(80*fade)),  # With alpha
                self.points[i], 
                self.points[i+1], 
                int(18 * fade)  # thickness decreases
            )
            
            # 2. main bolt
            pygame.draw.line(
                lightning_surface,
                (*self.base_color, int(200*fade)),
                self.points[i],
                self.points[i+1],
                int(10 * fade)
            )
            
            # 3. core (brightest)
            pygame.draw.line(
                lightning_surface,
                (*self.core_color, int(255*fade)),
                self.points[i],
                self.points[i+1],
                int(4 * fade)
            )
        
        # apply additive blending
        surface.blit(lightning_surface, (0, 0), special_flags=pygame.BLEND_ADD)
        
        # first-frame flash effect
        if self.frame == 0:
            flash = pygame.Surface((surface.get_size()), pygame.SRCALPHA)
            flash.fill((*self.core_color, 150))  # bright flash
            surface.blit(flash, (0, 0), special_flags=pygame.BLEND_ADD)