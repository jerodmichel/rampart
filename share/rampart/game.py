#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Nov 11 12:05:17 2024

@author: stereo
"""

#  ██████     █████     ██  ██     ███████
#  ██        ██   ██   ██████     ██
#  ██  ███   ███████   ██ ███     █████
#  ██    ██  ██   ██   ██  ██     ██
#  ██████    ██   ██   ██  ██     ███████
#  ┌────┐    ┌───┐    ┌┐┌┌┐    ┌─────┐
#  │ ██ │    │███│    │││││    │ ███ │
#  │ ██ │    │   │    │└┴┘│    │     │
#  └────┘    └───┘    └───┘    └─────┘

import pygame
import threading

from const import *
from board import Board
from dragger import Dragger
from clicker import Clicker
from config import Config
from square import Square
from card import Card
from effects import Lightning_effect

from move import Move
from cast_move import Cast_move


class Game:
    
    def __init__(self):
        # ensure Pygame font is available
        if not pygame.font.get_init():
            pygame.font.init()
        self.turn_lock = threading.Lock()
        self.flipped = False
        self.next_player = 'white'
        self.next_state = None
        self.queen_raid_pending = False
        # self.in_check_flag = False
        self.hovered_sqr = None
        self.hovered_crd = None
        self.hovered_btn = None
        self.hovered_dom = None
        self.hovered_grave = None
        self.white_cast_prompt = ''
        self.black_cast_prompt = ''
        self.lightning = Lightning_effect(self)
        self.board = Board(self.flipped)
        self.dragger = Dragger()
        self.clicker = Clicker()
        self.config = Config()
        
    def set_player_color(self, color):
        # set the player's color (white or black)
        self.player_color = color
        # to set initial turn based on color:
        self.next_player = color
        
# ╭━━━┳╮╱╭┳━━━┳╮╭╮╭╮╭━━╮╭━━━┳━━━┳╮╭━┳━━━┳━━━┳━━━┳╮╱╭┳━╮╱╭┳━━━╮
# ┃╭━╮┃┃╱┃┃╭━╮┃┃┃┃┃┃┃╭╮┃┃╭━╮┃╭━╮┃┃┃╭┫╭━╮┃╭━╮┃╭━╮┃┃╱┃┃┃╰╮┃┣╮╭╮┃
# ┃╰━━┫╰━╯┃┃╱┃┃┃┃┃┃┃┃╰╯╰┫┃╱┃┃┃╱╰┫╰╯╯┃┃╱╰┫╰━╯┃┃╱┃┃┃╱┃┃╭╮╰╯┃┃┃┃┃
# ╰━━╮┃╭━╮┃┃╱┃┃╰╯╰╯┃┃╭━╮┃╰━╯┃┃╱╭┫╭╮┃┃┃╭━┫╭╮╭┫┃╱┃┃┃╱┃┃┃╰╮┃┃┃┃┃┃
# ┃╰━╯┃┃╱┃┃╰━╯┣╮╭╮╭╯┃╰━╯┃╭━╮┃╰━╯┃┃┃╰┫╰┻━┃┃┃╰┫╰━╯┃╰━╯┃┃╱┃┃┣╯╰╯┃
# ╰━━━┻╯╱╰┻━━━╯╰╯╰╯╱╰━━━┻╯╱╰┻━━━┻╯╰━┻━━━┻╯╰━┻━━━┻━━━┻╯╱╰━┻━━━╯
    
    # show methods
    def show_bg(self, surface):
        theme = self.config.theme
        
        for sq in SQS:
            # get raw board coordinates
            col, row = sq[0], sq[1]
            
            # convert to display coordinates
            if self.flipped:
                display_col = COLS - 1 - col
                display_row = ROWS - 1 - row
            else:
                display_col = col
                display_row = row
            
            # draw squares
            color = theme.bg.dark if sq in CARDSQS else theme.bg.light
            rect = (display_col * RWIDTH + 100, (display_row * RHEIGHT if display_row < 3 else \
                        display_row * RHEIGHT + RAMPART_HEIGHT), RWIDTH-2, RHEIGHT-2)
            pygame.draw.rect(surface, color, rect)
            
        # rampart image between rows 2 and 3
        rampart_y = 3 * RHEIGHT  # position after row 2
        rampart_rect = pygame.Rect(
            100,  # x position (same as board)
            rampart_y,
            RWIDTH * COLS,  # width of entire board
            RAMPART_HEIGHT
        )
        surface.blit(self.config.rampart_img, rampart_rect)
    
        # card table text (fixed positions, doesn't flip)
        font = pygame.font.SysFont("timesnewroman", 24, bold=True)
        for crd in TABLE:
            col, row = crd[0], crd[1]
            if self.flipped:
                display_col = COLS - 1 - col
                display_row = ROWS - 1 - row
            else:
                display_col = col
                display_row = row
            
            text1 = font.render(f'{crd[2]}', True, (255,0,0))
            text2 = font.render(f'{crd[3]}', True, (255,0,0))
            surface.blit(text1, (display_col * RWIDTH + 7 + 100, (display_row * RHEIGHT \
                        if display_row < 3 else display_row * RHEIGHT + RAMPART_HEIGHT)))
            surface.blit(text2, (display_col * RWIDTH + 7 + 100, (display_row * RHEIGHT + 20 \
                        if display_row < 3 else display_row * RHEIGHT + 20 + RAMPART_HEIGHT)))
    
        # decks and graveyards (remain in fixed screen positions)
        for sq in DECK_SQS:
            suit, rank = sq[0], sq[1]
            color = theme.bg.dark if suit == 1 else theme.bg.light
            
            if self.flipped:
                # flip left/right but maintain top/bottom order
                if suit == 0:  # black deck (normally left)
                    x_pos = 908  # moves to right
                    y_pos = (12 - rank) * CHEIGHT + CEM_HEIGHT + RAMPART_HEIGHT
                else:  # white deck (normally right)
                    x_pos = 2    # moves to left
                    y_pos = rank * CHEIGHT + 2
            else:
                if suit == 0:  # black deck left
                    x_pos = 2
                    y_pos = rank * CHEIGHT + 2
                else:  # white deck right
                    x_pos = 908
                    y_pos = (12 - rank) * CHEIGHT + CEM_HEIGHT + RAMPART_HEIGHT
                    
            rect = (x_pos, y_pos, CWIDTH, CHEIGHT - 2)
            pygame.draw.rect(surface, color, rect)
        
        font = pygame.font.SysFont("timesnewroman", 24, bold=True)
    
        # card suit rendering
        for crd in TABLE:
            col, row = crd[0], crd[1]
            display_col = COLS - 1 - col if self.flipped else col
            display_row = ROWS - 1 - row if self.flipped else row
            
            # clear the exact card area
            clear_rect = pygame.Rect(
                display_col * RWIDTH + 100,
                display_row * RHEIGHT if display_row < 3 else display_row * RHEIGHT \
                    + RAMPART_HEIGHT,
                RWIDTH-2,
                RHEIGHT-2
            )
            bg_color = theme.bg.dark if (col, row) in CARDSQS else theme.bg.light
            pygame.draw.rect(surface, bg_color, clear_rect)
    
        # render cards with flip handling
        for crd in TABLE:
            col, row, rank, suit = crd[0], crd[1], crd[2], crd[3]
            
            if not rank and not suit:  # skip empty positions
                continue
                
            # get display position
            if self.flipped:
                display_col = COLS - 1 - col
                display_row = ROWS - 1 - row
                
                # transform suits based on original position
                original_pos = (col, row)
                if original_pos in TABLE_DICT:
                    original_rank, original_suit_idx = TABLE_DICT[original_pos]
                    
                    # only swap between:
                    # - hearts (SUITS[1] = '\u2665') 
                    # - diamonds (SUITS[2] = '\u2666')
                    if original_suit_idx == 3:  # if was heart
                        new_suit_idx = 1        # change to diamond
                    elif original_suit_idx == 2:  # if was diamond
                        new_suit_idx = 2        # change to heart
                    else:
                        new_suit_idx = original_suit_idx  # keep other suits same
                    
                    suit = SUITS[new_suit_idx]
            else:
                display_col = col
                display_row = row
                
            # render
            if rank:
                text_rank = font.render(rank, True, (255, 0, 0))
                surface.blit(text_rank, (display_col * RWIDTH + 7 + 100, (display_row * RHEIGHT if \
                                display_row < 3 else display_row * RHEIGHT + RAMPART_HEIGHT)))
            if suit:
                text_suit = font.render(suit, True, (255, 0, 0))
                surface.blit(text_suit, (display_col * RWIDTH + 7 + 100, (display_row * RHEIGHT + 20 if \
                                display_row < 3 else display_row * RHEIGHT + 20 + RAMPART_HEIGHT)))
    
        # deck text rendering (accounts for flipping)
        font = pygame.font.SysFont("timesnewroman", 24, bold=True)
        for crd in DECK_TABLE:
            suit, rank = crd[0], crd[1]
            
            if self.flipped:
                # flip deck positions
                if suit == 0:  # black deck (normally left)
                    x_pos = 908  # moves to right
                    y_pos = (12 - rank) * CHEIGHT + CEM_HEIGHT + 20
                else:  # white deck (normally right)
                    x_pos = 2    # moves to left
                    y_pos = rank * CHEIGHT + 2
            else:
                if suit == 0:  # black deck left
                    x_pos = 2
                    y_pos = rank * CHEIGHT + 2
                else:  # white deck right
                    x_pos = 908
                    y_pos = (12 - rank) * CHEIGHT + CEM_HEIGHT + 20
            
            text1 = font.render(f'{crd[2]}', True, (0, 0, 0))
            text2 = font.render(f'{crd[3]}', True, (0, 0, 0))
            
            if suit == 0:  # black deck
                surface.blit(text1, (x_pos + 5, y_pos))
                surface.blit(text2, (x_pos + 30, y_pos))
            else:  # white deck
                surface.blit(text1, (x_pos + 42, y_pos))
                surface.blit(text2, (x_pos + 67, y_pos))
                
        # row letters (vertical labels)
        if not self.flipped:
            # label first column (left edge) when not flipped
            for row in range(ROWS):
                # determine color based on original square
                color = theme.bg.dark if (row == 5 or row % 2 == 0) else theme.bg.light
                
                # get label text (A-F)
                label_text = Square.get_alpharow(ROWS - row - 1)
                
                # position on left edge
                lbl = self.config.font.render(label_text, 1, color)
                surface.blit(lbl, (5 + 100, (row * RHEIGHT + RHEIGHT - 25 if row < 3 else \
                                row * RHEIGHT + RHEIGHT - 25 + RAMPART_HEIGHT)))
        else:
            # label last column (right edge) when flipped
            for row in range(ROWS):
                # get flipped row position
                display_row = ROWS - 1 - row
                
                # determine color based on original square (column 0)
                color = theme.bg.dark if (row == 5 or row % 2 == 0) else theme.bg.light
                
                # get label text (A-F)
                label_text = Square.get_alpharow(ROWS - row - 1)
                
                # position on right edge
                lbl = self.config.font.render(label_text, 1, color)
                surface.blit(lbl, ((COLS-1)*RWIDTH + RWIDTH - 25 + 100, 
                                  (display_row * RHEIGHT + RHEIGHT - 25 if display_row < 3 else \
                                   display_row * RHEIGHT + RHEIGHT - 25 + RAMPART_HEIGHT)))
      
        # column numbers (horizontal labels)
        if not self.flipped:
            # label bottom row when not flipped
            for col in range(COLS):
                # determine color
                ref_sq = (col, ROWS-1)  # bottom row squares
                color = theme.bg.light if ref_sq in CARDSQS else theme.bg.dark
                
                # get label text (1-10)
                label_text = str(col + 1)
                
                # position on bottom
                lbl = self.config.font.render(label_text, 1, color)
                surface.blit(lbl, (col * RWIDTH + RWIDTH - 25 + 100, \
                                   (HEIGHT - 25 + RAMPART_HEIGHT)))
                
        else:
            # label top row when flipped
            for col in range(COLS):
                # get flipped column position
                display_col = COLS - 1 - col
                
                # determine color (using original bottom row squares)
                ref_sq = (col, ROWS-1)  # Original bottom row
                color = theme.bg.light if ref_sq in CARDSQS else theme.bg.dark
                
                # get label text (1-10)
                label_text = str(col + 1)
                
                # position on top
                lbl = self.config.font.render(label_text, 1, color)
                surface.blit(lbl, (display_col * RWIDTH + RWIDTH - 25 + 100, 5))

        # graveyards (flip sides when board is flipped)
        for grv in GRAVEYARD:
            grave_col, grave_row = grv[0], grv[1]
            color = (0, 0, 0)
            
            if self.flipped:
                if grave_col == 0:  # black graveyard (normally left)
                    x_pos = 908  # moves to right
                    y_pos = (8 - grave_row) * GHEIGHT + 90
                else:  # white graveyard (normally right)
                    x_pos = 2    # moves to left
                    y_pos = grave_row * GHEIGHT + (HEIGHT - CEM_HEIGHT + 65) + RAMPART_HEIGHT
            else:
                if grave_col == 0:  # black graveyard left
                    x_pos = 2
                    y_pos = grave_row * GHEIGHT + (HEIGHT - CEM_HEIGHT + 65) + RAMPART_HEIGHT
                else:  # white graveyard right
                    x_pos = 908
                    y_pos = (8 - grave_row) * GHEIGHT + 90
                    
            rect = (x_pos, y_pos, GWIDTH, GHEIGHT - 2)
            pygame.draw.rect(surface, color, rect)

# ╭━━━┳╮╱╭┳━━━┳╮╭╮╭╮╭━╮╭━┳━━━┳━━━━┳━━━┳━━━┳━━┳━━━┳╮╱╱╭━━━╮
# ┃╭━╮┃┃╱┃┃╭━╮┃┃┃┃┃┃┃┃╰╯┃┃╭━╮┃╭╮╭╮┃╭━━┫╭━╮┣┫┣┫╭━╮┃┃╱╱┃╭━╮┃
# ┃╰━━┫╰━╯┃┃╱┃┃┃┃┃┃┃┃╭╮╭╮┃┃╱┃┣╯┃┃╰┫╰━━┫╰━╯┃┃┃┃┃╱┃┃┃╱╱┃╰━━╮
# ╰━━╮┃╭━╮┃┃╱┃┃╰╯╰╯┃┃┃┃┃┃┃╰━╯┃╱┃┃╱┃╭━━┫╭╮╭╯┃┃┃╰━╯┃┃╱╭╋━━╮┃
# ┃╰━╯┃┃╱┃┃╰━╯┣╮╭╮╭╯┃┃┃┃┃┃╭━╮┃╱┃┃╱┃╰━━┫┃┃╰┳┫┣┫╭━╮┃╰━╯┃╰━╯┃
# ╰━━━┻╯╱╰┻━━━╯╰╯╰╯╱╰╯╰╯╰┻╯╱╰╯╱╰╯╱╰━━━┻╯╰━┻━━┻╯╱╰┻━━━┻━━━╯
    
    def show_pieces(self, surface):
        for col in range(COLS):
            for row in range(ROWS):
                if self.board.squares[col][row].has_piece():
                    piece = self.board.squares[col][row].piece
                    if piece is not self.dragger.piece:
                        # get display position
                        disp_col, disp_row = self.get_screen_position(col, row)
                        piece.set_texture(size=80)
                        img = pygame.image.load(piece.texture)
                        if img.get_size() != (80, 80):
                            img = pygame.transform.scale(img, (80, 80))
                        img_center = disp_col * RWIDTH + RWIDTH // 2 + 100, \
                                    (disp_row * RHEIGHT + RHEIGHT // 2 if disp_row < 3 \
                                     else disp_row * RHEIGHT + RHEIGHT // 2 + RAMPART_HEIGHT)
                        piece.texture_rect = img.get_rect(center=img_center)
                        surface.blit(img, piece.texture_rect)
                    
    def show_dead(self, surface):
        for grv in GRAVEYARD:
            if self.board.graves[grv[0]][grv[1]].has_piece():
                piece = self.board.graves[grv[0]][grv[1]].piece
                piece.set_dead_texture()
                img = pygame.image.load(piece.dead_texture)
                img = pygame.transform.scale(img, (35, 35))
                
                # determine visual position based on flip state
                if self.flipped:
                    # swap grave positions visually but keep ownership
                    visual_grave_col = 1 - grv[0]  # flips 0→1 and 1→0
                    if visual_grave_col == 0:  # visually left (black's original graves)
                        x_pos = GWIDTH // 2 + 2
                        y_pos = grv[1] * GHEIGHT + GHEIGHT // 2 + (HEIGHT - CEM_HEIGHT + 65) \
                            + RAMPART_HEIGHT
                    else:  # visually right (white's original graves)
                        x_pos = GWIDTH // 2 + 908
                        y_pos = grv[1] * GHEIGHT + GHEIGHT // 2 + 90
                else:
                    # normal positions
                    if grv[0] == 0:  # black graves (left)
                        x_pos = GWIDTH // 2 + 2
                        y_pos = grv[1] * GHEIGHT + GHEIGHT // 2 + (HEIGHT - CEM_HEIGHT + 65) \
                            + RAMPART_HEIGHT
                    else:  # white graves (right)
                        x_pos = GWIDTH // 2 + 908
                        y_pos = grv[1] * GHEIGHT + GHEIGHT // 2 + 90
                
                # render the piece
                piece.texture_rect = img.get_rect(center=(x_pos, y_pos))
                surface.blit(img, piece.texture_rect)
                
    def show_dead_cards(self, surface):
        for sq in DECK_SQS:
            if self.board.cards[sq[0]][sq[1]].is_cast():
                img0 = pygame.image.load(self.config.dead_card)
                img0 = pygame.transform.scale(img0, (CWIDTH, CHEIGHT - 1))
                
                # determine visual position based on flip
                if self.flipped:
                    visual_suit = 1 - sq[0]  # flip suit for display only
                    if visual_suit == 0:  # visually left (originally right)
                        x_pos = 2
                        y_pos = sq[1] * CHEIGHT
                    else:  # visually right (originally left)
                        x_pos = 908
                        y_pos = (12 - sq[1]) * CHEIGHT + CEM_HEIGHT + RAMPART_HEIGHT
                else:
                    if sq[0] == 0:  # black deck (left)
                        x_pos = 2
                        y_pos = sq[1] * CHEIGHT
                    else:  # white deck (right)
                        x_pos = 908
                        y_pos = (12 - sq[1]) * CHEIGHT + CEM_HEIGHT + RAMPART_HEIGHT
                
                surface.blit(img0, (x_pos, y_pos))
                    
    
    def show_clicked_cards(self, surface):
        if self.clicker.clicked:
            for card in self.clicker.clicked_cards:
                color = (100, 216, 220)
                if not card.is_cast():
                    # handle deck cards
                    if card.suit in [0, 1]:  # black (0) or White (1) deck cards
                        if self.flipped:
                            # flip deck positions but keep card ownership
                            if card.suit == 1:  # white deck
                                x_pos = 2
                                y_pos = card.rank * CHEIGHT+2
                            else:  # black deck
                                x_pos = 908
                                y_pos = (12 - card.rank) * CHEIGHT + CEM_HEIGHT \
                                    + RAMPART_HEIGHT
                        else:
                            # normal deck positions
                            if card.suit == 1:  # white deck (right)
                                x_pos = 908
                                y_pos = (12 - card.rank) * CHEIGHT + CEM_HEIGHT \
                                    + RAMPART_HEIGHT
                            else:  # black deck (left)
                                x_pos = 2
                                y_pos = card.rank * CHEIGHT+2
                        
                        rect = (x_pos, y_pos, CWIDTH, CHEIGHT - 1)
                    
                    # handle board cards
                    else:
                        col = REV_TAB_DICT[(card.rank, card.suit)][0]
                        row = REV_TAB_DICT[(card.rank, card.suit)][1]
                        # convert board position to display coordinates
                        disp_col, disp_row = self.get_screen_position(col, row)
                        rect = (
                            disp_col * RWIDTH + 100, 
                            disp_row * RHEIGHT if disp_row < 3 else disp_row * RHEIGHT \
                                + RAMPART_HEIGHT,
                            RWIDTH-2, 
                            RHEIGHT-2
                        )
                    
                    pygame.draw.rect(surface, color, rect, width=2)
                    
    def show_cemetery(self, surface):
        try:
            img0 = pygame.image.load(self.config.emblem[0])
            img0 = pygame.transform.scale(img0, (80, 80))
            surface.blit(img0, (5, 715 + RAMPART_HEIGHT))
            img1 = pygame.image.load(self.config.emblem[1])
            img1 = pygame.transform.scale(img1, (80, 80))
            surface.blit(img1, (908, 2))
        except Exception as e:
            print(f"Error loading emblems: {e}")
            print(f"Attempted paths: {self.config.emblem}")
        
        
    def show_cast_buttons(self, surface):
        font = pygame.font.SysFont("timesnewroman", 24, bold=True)
        
        for btn in CASTBUTTONS:
            # color
            color = self.config.theme.bg.dark
            #rect
            rect = (102, 802 + RAMPART_HEIGHT, 100, 35) if btn == 0 else \
                (205, 802 + RAMPART_HEIGHT, 83, 35)
            # blit
            pygame.draw.rect(surface, color, rect)
            
        for btn in CASTBUTTONS:
            
            text1 = font.render('STRIKE',True,
                            (0, 0, 0))
            text2 = font.render('RAISE',True, 
                            (0, 0, 0))
            if btn == 0:
                surface.blit(text1,(108, 805 + RAMPART_HEIGHT))
            else:
                surface.blit(text2,(210, 805 + RAMPART_HEIGHT))
                
    def show_clicked_btns(self, surface):
        # color
        color = (159, 43, 104)
        # rect
        if self.clicker.clicked_btn == 0:
            rect = (102, 802 + RAMPART_HEIGHT, 100, 35) 
            pygame.draw.rect(surface, color, rect, width=2)
        elif self.clicker.clicked_btn == 1:
            rect = (205, 802 + RAMPART_HEIGHT, 83, 35)
            pygame.draw.rect(surface, color, rect, width=2)
            
    
    def show_chosen_piece(self, surface):
        if self.clicker.clicked_grv:
            color = (100, 216, 220)
            grv = self.clicker.clicked_grv
            
            # calculate visual position accounting for flip
            if self.flipped:
                visual_col = 1 - grv.col  # flip the column
                if visual_col == 0:  # visually left (originally right)
                    x_pos = 2
                    y_pos = grv.row * GHEIGHT + (HEIGHT - CEM_HEIGHT + 65) \
                        + RAMPART_HEIGHT
                else:  # visually right (originally left)
                    x_pos = 908
                    y_pos = grv.row * GHEIGHT + 90
            else:
                if grv.col == 0:  # left (black)
                    x_pos = 2
                    y_pos = grv.row * GHEIGHT + (HEIGHT - CEM_HEIGHT + 65) \
                        + RAMPART_HEIGHT
                else:  # right (white)
                    x_pos = 908
                    y_pos = grv.row * GHEIGHT + 90
            
            rect = (x_pos, y_pos, GWIDTH - 1, GHEIGHT - 1)
            pygame.draw.rect(surface, color, rect, width=2)
        
                    
    def show_moves(self, surface):
        theme = self.config.theme
        
        if self.dragger.dragging:
            piece = self.dragger.piece
            for move in piece.moves:
                # get display coordinates (account for flipping)
                disp_col, disp_row = self.get_screen_position(move.final.col, move.final.row)
                
                # color
                color = theme.moves.light if (move.final.col, move.final.row) in CARDSQS else theme.moves.dark
                
                # rect (using display coordinates)
                rect = (
                    disp_col * RWIDTH + 100,  # +100 offset for board positioning
                    disp_row * RHEIGHT if disp_row < 3 else disp_row * RHEIGHT + RAMPART_HEIGHT,
                    RWIDTH-2, 
                    RHEIGHT-2
                )
                
                # blit
                pygame.draw.rect(surface, color, rect)
    
    def show_last_move(self, surface):
        theme = self.config.theme
        
        if self.board.last_move:
            if isinstance(self.board.last_move, Move):
                initial = self.board.last_move.initial
                final = self.board.last_move.final
                for pos in [initial, final]:
                    # convert to display coordinates
                    disp_col, disp_row = self.get_screen_position(pos.col, pos.row)
                    # color
                    color = theme.trace.light if (pos.col, pos.row) in CARDSQS else \
                        theme.trace.dark
                    # rect
                    rect = (
                        disp_col * RWIDTH + 100, 
                        disp_row * RHEIGHT if disp_row < 3 else \
                            disp_row * RHEIGHT + RAMPART_HEIGHT, 
                        RWIDTH - 2, 
                        RHEIGHT - 2
                    )
                    # blit
                    pygame.draw.rect(surface, color, rect, width=5)
                    
            elif isinstance(self.board.last_move, Cast_move):
                final = self.board.last_move.final
                # convert to display coordinates
                disp_col, disp_row = self.get_screen_position(final.col, final.row)
                # color
                color = theme.trace.light if (final.col, final.row) in CARDSQS else \
                    theme.trace.dark
                # rect
                rect = (
                    disp_col * RWIDTH + 100, 
                    disp_row * RHEIGHT if disp_row < 3 else disp_row * RHEIGHT \
                        + RAMPART_HEIGHT, 
                    RWIDTH - 2, 
                    RHEIGHT - 2
                )
                # blit
                pygame.draw.rect(surface, color, rect, width=5)
                
# ╭━━━┳╮╱╭┳━━━┳╮╭╮╭╮╭╮╱╭┳━━━┳╮╱╱╭┳━━━┳━━━┳━━━╮
# ┃╭━╮┃┃╱┃┃╭━╮┃┃┃┃┃┃┃┃╱┃┃╭━╮┃╰╮╭╯┃╭━━┫╭━╮┃╭━╮┃
# ┃╰━━┫╰━╯┃┃╱┃┃┃┃┃┃┃┃╰━╯┃┃╱┃┣╮┃┃╭┫╰━━┫╰━╯┃╰━━╮
# ╰━━╮┃╭━╮┃┃╱┃┃╰╯╰╯┃┃╭━╮┃┃╱┃┃┃╰╯┃┃╭━━┫╭╮╭┻━━╮┃
# ┃╰━╯┃┃╱┃┃╰━╯┣╮╭╮╭╯┃┃╱┃┃╰━╯┃╰╮╭╯┃╰━━┫┃┃╰┫╰━╯┃
# ╰━━━┻╯╱╰┻━━━╯╰╯╰╯╱╰╯╱╰┻━━━╯╱╰╯╱╰━━━┻╯╰━┻━━━╯
                
                
    def show_hover(self, surface):
        if self.hovered_sqr:
            # color
            color = (180, 180, 180)
            # rect
            rect = (self.hovered_sqr.col * RWIDTH + 100, self.hovered_sqr.row * RHEIGHT \
                    if self.hovered_sqr.row < 3 else self.hovered_sqr.row * RHEIGHT \
                    + RAMPART_HEIGHT, RWIDTH - 2, RHEIGHT - 2)
            # blit
            pygame.draw.rect(surface, color, rect, width=3)
            
        if self.hovered_crd:
            # color
            color = (173, 216, 230)
            # rect
            if self.hovered_crd.suit == 1:
                rect = (self.hovered_crd.suit * 908, (12 - self.hovered_crd.rank) * CHEIGHT \
                    + CEM_HEIGHT + RAMPART_HEIGHT, CWIDTH, CHEIGHT - 1)
            else:
                rect = (self.hovered_crd.suit, self.hovered_crd.rank * CHEIGHT, \
                    CWIDTH + 2, CHEIGHT + 1)
            pygame.draw.rect(surface, color, rect, width=2)
            
        if self.hovered_btn:
            # color
            color = (173, 216, 230)
            # rect
            rect = (102, 802 + RAMPART_HEIGHT, 100, 35) if self.hovered_btn.categ == 0 \
                else (205, 802 + RAMPART_HEIGHT, 83, 35)
                
            pygame.draw.rect(surface, color, rect, width=2)
            
        if self.hovered_dom:
            # convert to display coordinates
            disp_col, disp_row = self.get_screen_position(
                self.hovered_dom.col, 
                self.hovered_dom.row
            )
            
            color = (159, 43, 104)
            rect = (
                disp_col * RWIDTH + 100,
                disp_row * RHEIGHT if disp_row < 3 else disp_row * RHEIGHT + RAMPART_HEIGHT,
                RWIDTH - 2,
                RHEIGHT - 2
            )
            pygame.draw.rect(surface, color, rect, width=3)
            
        if self.hovered_grave:
            # color
            color = (159, 43, 104)
            
            # calculate visual position to account for flipping
            if self.flipped:
                # flip column but keep row and vertical offsets
                visual_col = 1 - self.hovered_grave.col
                print("visual:", visual_col)
                if visual_col == 0:  # visually left (originally right)
                    x_pos = 2  # left edge
                    y_pos = self.hovered_grave.row * GHEIGHT + (HEIGHT - CEM_HEIGHT + 65) \
                        + RAMPART_HEIGHT
                else:  # visually right (originally left)
                    x_pos = 908  # right edge
                    y_pos = self.hovered_grave.row * GHEIGHT + 90
            else:
                # original positions
                if self.hovered_grave.col == 0:  # left (black)
                    x_pos = 2
                    y_pos = self.hovered_grave.row * GHEIGHT + (HEIGHT - CEM_HEIGHT + 65) \
                        + RAMPART_HEIGHT
                else:  # right (white)
                    x_pos = 908
                    y_pos = self.hovered_grave.row * GHEIGHT + 90
            
            # create rectangle (keeping original dimensions)
            rect = (x_pos, y_pos, GWIDTH - 1, GHEIGHT - 1)
            
            # draw highlight
            pygame.draw.rect(surface, color, rect, width=2)
                        

# ░█████╗░████████╗██╗░░██╗███████╗██████╗░
# ██╔══██╗╚══██╔══╝██║░░██║██╔════╝██╔══██╗
# ██║░░██║░░░██║░░░███████║█████╗░░██████╔╝
# ██║░░██║░░░██║░░░██╔══██║██╔══╝░░██╔══██╗
# ╚█████╔╝░░░██║░░░██║░░██║███████╗██║░░██║
# ░╚════╝░░░░╚═╝░░░╚═╝░░╚═╝╚══════╝╚═╝░░╚═╝

# ███╗░░░███╗███████╗████████╗██╗░░██╗░█████╗░██████╗░░██████╗
# ████╗░████║██╔════╝╚══██╔══╝██║░░██║██╔══██╗██╔══██╗██╔════╝
# ██╔████╔██║█████╗░░░░░██║░░░███████║██║░░██║██║░░██║╚█████╗░
# ██║╚██╔╝██║██╔══╝░░░░░██║░░░██╔══██║██║░░██║██║░░██║░╚═══██╗
# ██║░╚═╝░██║███████╗░░░██║░░░██║░░██║╚█████╔╝██████╔╝██████╔╝
# ╚═╝░░░░░╚═╝╚══════╝░░░╚═╝░░░╚═╝░░╚═╝░╚════╝░╚═════╝░╚═════╝░

    
    def cast_cards(self):
        for card in self.clicker.clicked_cards:
            if card.suit in [0, 1]:
                suit, rank = card.suit, card.rank
                self.board.cards[suit][rank] = Card(suit, rank, True)
                
        self.clicker.clicked_cards = []
        
    def cast_cards_networked(self, cards):
        print('cast_cards accessed')
        for card in cards:
            if card.suit in [0, 1]:
                suit, rank = card.suit, card.rank
                self.board.cards[suit][rank] = Card(suit, rank, True)

# ╭━━━┳━━━┳━━━┳━╮╭━┳━━━┳━━━━┳━━━╮
# ┃╭━╮┃╭━╮┃╭━╮┃┃╰╯┃┃╭━╮┃╭╮╭╮┃╭━╮┃
# ┃╰━╯┃╰━╯┃┃╱┃┃╭╮╭╮┃╰━╯┣╯┃┃╰┫╰━━╮
# ┃╭━━┫╭╮╭┫┃╱┃┃┃┃┃┃┃╭━━╯╱┃┃╱╰━━╮┃
# ┃┃╱╱┃┃┃╰┫╰━╯┃┃┃┃┃┃┃╱╱╱╱┃┃╱┃╰━╯┃
# ╰╯╱╱╰╯╰━┻━━━┻╯╰╯╰┻╯╱╱╱╱╰╯╱╰━━━╯
            
    def show_cast_prompt(self, surface, color):
        font = pygame.font.SysFont("timesnewroman", 24, bold=True)
        if color == 'white' and self.white_cast_prompt:
            if self.white_cast_prompt == 'cast':
                text = font.render('To begin casting, click on a card in your deck.',True,(255, 255, 255))
                surface.blit(text,(320, 805 + RAMPART_HEIGHT))
            elif self.white_cast_prompt == 'strike':
                text = font.render('Choose a raider to send to the grave.',True,(255, 255, 255))
                surface.blit(text,(320, 805 + RAMPART_HEIGHT))
            elif self.white_cast_prompt == 'raise':
                text = font.render('Choose a tile where you want to place a raider.',True,(255, 255, 255))
                surface.blit(text,(320, 805 + RAMPART_HEIGHT))
            elif self.white_cast_prompt == 'raiseq':
                text = font.render('Choose a tile where you want to place the queen.',True,(255, 255, 255))
                surface.blit(text,(320, 805 + RAMPART_HEIGHT))
            elif self.white_cast_prompt == 'choosegrv':
                text = font.render('Choose a peice from the cemetery to raise.',True,(255, 255, 255))
                surface.blit(text,(320, 805 + RAMPART_HEIGHT))
            elif self.white_cast_prompt == 'make21':
                text = font.render('Choose cards from your deck and from the board that sum to 21.',True,(255, 255, 255))
                surface.blit(text,(320, 805 + RAMPART_HEIGHT))
            elif self.white_cast_prompt == 'choosecast':
                text = font.render('Click one of the "strike" or "raise" buttons.',True,(255, 255, 255))
                surface.blit(text,(320, 805 + RAMPART_HEIGHT))
            elif self.white_cast_prompt == 'in-check':
                text = font.render("White's king is in check -- ",True,(255, 0, 0))
                surface.blit(text,(320, 805 + RAMPART_HEIGHT))
            elif self.white_cast_prompt[1] == 'mated':
                	font = pygame.font.SysFont("timesnewroman", 24, bold=True)
                	text1 = font.render('White mated Black',True,(255, 255, 255)) if self.white_cast_prompt[0] \
                        == 'black' else font.render('Black mated White',True,(255, 255, 255))
                	surface.blit(text1,(320, 805 + RAMPART_HEIGHT))
                	text2 = font.render('-- Press "r" key to start new game.',True,(255, 255, 255))
                	surface.blit(text2,(540, 805 + RAMPART_HEIGHT))
            elif self.white_cast_prompt[1] == 'stale-mated':
                	font = pygame.font.SysFont("timesnewroman", 24, bold=True)
                	text1 = font.render('Black stalemated',True,(255, 255, 255)) if self.white_cast_prompt[0] \
                        == 'black' else font.render('White stalemated',True,(255, 255, 255))
                	surface.blit(text1,(320, 805 + RAMPART_HEIGHT))
                	text2 = font.render('-- Press "r" key to start new game.',True,(255, 255, 255))
                	surface.blit(text2,(540, 805 + RAMPART_HEIGHT))
            
        if color == 'black' and self.black_cast_prompt:
            if self.black_cast_prompt == 'cast':
                text = font.render('To begin casting, click on a card in your deck.',True,(255, 255, 255))
                surface.blit(text,(320, 805 + RAMPART_HEIGHT))
            elif self.black_cast_prompt == 'strike':
                text = font.render('Choose a raider to send to the grave.',True,(255, 255, 255))
                surface.blit(text,(320, 805 + RAMPART_HEIGHT))
            elif self.black_cast_prompt == 'raise':
                text = font.render('Choose a tile where you want to place a raider.',True,(255, 255, 255))
                surface.blit(text,(320, 805 + RAMPART_HEIGHT))
            elif self.black_cast_prompt == 'raiseq':
                text = font.render('Choose a tile where you want to place the queen.',True,(255, 255, 255))
                surface.blit(text,(320, 805 + RAMPART_HEIGHT))
            elif self.black_cast_prompt == 'choosegrv':
                text = font.render('Choose a peice from the cemetery to raise.',True,(255, 255, 255))
                surface.blit(text,(320, 805 + RAMPART_HEIGHT))
            elif self.black_cast_prompt == 'make21':
                text = font.render('Choose a peice from the cemetery to raise.',True,(255, 255, 255))
                surface.blit(text,(320, 805 + RAMPART_HEIGHT))
            elif self.black_cast_prompt == 'choosecast':
                text = font.render('Click one of the "strike" or "raise" buttons.',True,(255, 255, 255))
                surface.blit(text,(320, 805 + RAMPART_HEIGHT))
            elif self.black_cast_prompt == 'in-check':
                text = font.render("Black's king is in check -- ",True,(255, 0, 0))
                surface.blit(text,(320, 805 + RAMPART_HEIGHT))
            elif self.black_cast_prompt[1] == 'mated':
               	font = pygame.font.SysFont("timesnewroman", 24, bold=True)
               	text1 = font.render('White mated Black',True,(255, 255, 255)) if self.black_cast_prompt[0] \
                        == 'black' else font.render('Black mated White',True,(255, 255, 255))
               	surface.blit(text1,(320, 805 + RAMPART_HEIGHT))
               	text2 = font.render('-- Press "r" key to start new game.',True,(255, 255, 255))
               	surface.blit(text2,(540, 805 + RAMPART_HEIGHT))
            elif self.black_cast_prompt[1] == 'stale-mated':
               	font = pygame.font.SysFont("timesnewroman", 24, bold=True)
               	text1 = font.render('Black stalemated',True,(255, 255, 255)) if self.black_cast_prompt[0] \
                        == 'black' else font.render('White stalemated',True,(255, 255, 255))
               	surface.blit(text1,(320, 805 + RAMPART_HEIGHT))
               	text2 = font.render('-- Press "r" key to start new game.',True,(255, 255, 255))
               	surface.blit(text2,(540, 805 + RAMPART_HEIGHT))

    def next_turn(self):
        with self.turn_lock:  # thread safety
            if not self.queen_raid_pending:
                if self.next_player == 'white':
                    self.next_player = 'black'
                else:
                    self.next_player = 'white'
                    
                self.next_state = 'update1'
                
    def change_state(self):
        if self.next_state == 'update1':
            self.next_state = 'update2'
            self.lightning.active = False
            self.lightning.persist_frames = 0
            self.next_state = None
    
    def flip_board(self):
        self.flipped = not self.flipped
        
    def get_screen_position(self, col, row):
        if self.flipped:
            return (COLS - 1 - col, ROWS - 1 - row)
        return (col, row)
    
    def get_board_position(self, screen_x, screen_y):
        # convert screen coordinates to board coordinates accounting for flip
        if screen_x >= 100 and screen_x < 900:  # main board area
            col = (screen_x - 100) // RWIDTH
            if screen_y < 3 * RHEIGHT: # above rampart
                row = screen_y // RHEIGHT
            else: # below rampart
                row = (screen_y - RAMPART_HEIGHT) // RHEIGHT
                row = min(row, 5)
                
            if self.flipped:
                return (COLS - 1 - col, ROWS - 1 - row)
            return (col, row)
        return (None, None)
    
    def get_card_position(self, screen_x, screen_y):
        # returns (suit, rank) accounting for visual flip without changing card ownership
        # deck boundaries (adjust if needed)
        in_black_deck = (0 <= screen_x < 100)       # always left visually
        in_white_deck = (900 <= screen_x <= 1000)   # always right visually
        
        if not (in_black_deck or in_white_deck):
            return (None, None)
        
        # determine actual deck ownership (not affected by flip)
        if in_black_deck:
            suit = 1 if self.flipped else 0  # visually left deck
        else:
            suit = 0 if self.flipped else 1  # visually right deck
        
        # calculate rank (handles both decks' vertical positions)
        if (suit == 1 and not self.flipped) or (suit == 0 and self.flipped):
            # white deck position (top-aligned when unflipped)
            rank = max(0, min(12, 12 - (screen_y - CEM_HEIGHT - RAMPART_HEIGHT) // CHEIGHT)) if \
                (screen_y - CEM_HEIGHT - RAMPART_HEIGHT) >= 0 else 0
        else:
            # black deck position (bottom-aligned when unflipped)
            rank = max(0, min(12, screen_y // CHEIGHT))
        
        return (suit, rank)
        
    def get_grave_position(self, screen_x, screen_y):
        # preserves original calculations but accounts for flipping
        if self.flipped:
            # when flipped, swap which side to check based on player
            if (screen_x < 100 and self.next_player == 'white') or \
               (screen_x >= 900 and self.next_player == 'black'):
                
                # convert to unflipped coordinates for calculation
                calc_x = screen_x
                calc_y = screen_y
                
                # black graveyard (now on right when flipped)
                if self.next_player == 'black' and screen_x >= 900:
                    motion_col = 1
                    adjusted_y = calc_y - 80  # original white graveyard calculation
                    if adjusted_y <= 0:
                        motion_row = 0
                    elif adjusted_y // GHEIGHT > 8:
                        motion_row = 8
                    else:
                        motion_row = adjusted_y // GHEIGHT
                    return (motion_col, motion_row)
                
                # white graveyard (now on left when flipped)
                elif self.next_player == 'white' and screen_x < 100:
                    motion_col = 0
                    adjusted_y = calc_y - (HEIGHT - CEM_HEIGHT + 65 + RAMPART_HEIGHT)  # original black calculation
                    if adjusted_y < 0:
                        motion_row = 0
                    elif adjusted_y // GHEIGHT > 8:
                        motion_row = 8
                    else:
                        motion_row = (adjusted_y // GHEIGHT) + 1 if (adjusted_y // GHEIGHT) + 1 <= 8 else 8
                    return (motion_col, motion_row)
        
        else:
            # original unflipped logic
            if screen_x < 100 and self.next_player == 'black':
                motion_col = 0
                adjusted_y = screen_y - (HEIGHT - CEM_HEIGHT + 10 + RAMPART_HEIGHT) - 90
                if adjusted_y < 0:
                    motion_row = 0
                elif adjusted_y // GHEIGHT > 8:
                    motion_row = 8
                else:
                    motion_row = (adjusted_y // GHEIGHT) + 1 if (adjusted_y // GHEIGHT) + 1 <= 8 else 8
                return (motion_col, motion_row)
                
            elif screen_x >= 900 and self.next_player == 'white':
                motion_col = 1
                adjusted_y = screen_y - 80
                if adjusted_y <= 0:
                    motion_row = 0
                elif adjusted_y // GHEIGHT > 8:
                    motion_row = 8
                else:
                    motion_row = adjusted_y // GHEIGHT
                return (motion_col, motion_row)
        
        return (None, None)
        
    def set_mated_prompt(self, color):
        if self.board.king_mated:
            self.white_cast_prompt = [color, 'mated']
            self.black_cast_prompt = [color, 'mated']
        elif self.board.king_stalemated:
            self.white_cast_prompt = [color, 'stale-mated']
            self.black_cast_prompt = [color, 'stale-mated']
        
    def set_in_check_prompt(self, color):
        if color == 'white':
            self.white_cast_prompt = 'in-check'
        else:
            self.black_cast_prompt = 'in-check'
        
    def set_cast_prompt(self, color):
        if color == 'white':
            self.white_cast_prompt = 'cast'
        else:
            self.black_cast_prompt = 'cast'
        
    def set_strike_prompt(self, color):
        if color == 'white':
            self.white_cast_prompt = 'strike'
        else:
            self.black_cast_prompt = 'strike'
        
    def set_raise_prompt(self, color):
        if color == 'white':
            self.white_cast_prompt = 'raise'
        else:
            self.black_cast_prompt = 'raise'
        
    def set_raise_queen_prompt(self, color):
        if color == 'white':
            self.white_cast_prompt = 'raiseq'
        else:
            self.black_cast_prompt = 'raiseq'
        
    def set_choose_grave_prompt(self, color):
        if color == 'white':
            self.white_cast_prompt = 'choosegrv'
        else:
            self.black_cast_prompt = 'choosegrv'
            
    def set_make_21_prompt(self, color):
        if color == 'white':
            self.white_cast_prompt = 'make21'
        else:
            self.black_cast_prompt = 'make21'
            
    def set_choose_cast_prompt(self, color):
        if color == 'white':
            self.white_cast_prompt = 'choosecast'
        else:
            self.black_cast_prompt = 'choosecast'
        
    def kill_prompt(self, color):
        if color == 'white':
            self.white_cast_prompt = ''
        else:
            self.black_cast_prompt = ''
        
    def set_sq_hover(self, col, row):
        if self.flipped:
            col, row = COLS-1-col, ROWS-1-row
            
        if (0 <= col < COLS) and (0 <= row < ROWS):
            self.hovered_sqr = self.board.squares[col][row]
        else:
            self.hovered_sqr = None
        
    def set_dom_hover(self, col, row):
        # sets hover using board coordinates - display conversion happens in rendering
        if 0 <= col < COLS and 0 <= row < ROWS:
            self.hovered_dom = self.board.squares[col][row]
        else:
            self.hovered_dom = None
        
    def kill_dom_hover(self):
        self.hovered_dom = None
        
    def set_crd_hover(self, suit, rank):
        self.hovered_crd = self.board.cards[suit][rank]
        
    def set_btn_hover(self, categ):
        self.hovered_btn = self.board.cast_buttons[categ]
    
    def set_grave_hover(self, col, row):
        if col is None or row is None:
            self.hovered_grave = None
            return
        if (isinstance(col, int) and isinstance(row, int) and \
            0 <= col < len(self.board.graves) and \
            0 <= row < len(self.board.graves[col])):
            self.hovered_grave = self.board.graves[col][row]
        else:
            self.hovered_grave = None
        
    def kill_grave_hover(self):
        self.hovered_grave = None
        
    def change_theme(self):
        self.config.change_theme()
        
    def change_emblem(self):
        self.config.change_emblem()
        
    def change_dead_card(self):
        self.config.change_dead_card()
        
    def play_sound(self, captured=False):
        if captured:
            self.config.capture_sound.play()
        else:
            self.config.move_sound.play()
            
    def play_card_sound(self):
        self.config.card_click_sound.play()
        
    def play_strike_sound(self):
        self.config.strike_sound.play()
        
    def play_raise_sound(self):
        self.config.raise_sound.play()
            
    def reset(self):
        self.__init__()
    
                
                
