#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Nov 11 11:49:17 2024

@author: stereo
"""


#███╗░░░███╗░█████╗░██╗███╗░░██╗
#████╗░████║██╔══██╗██║████╗░██║
#██╔████╔██║███████║██║██╔██╗██║
#██║╚██╔╝██║██╔══██║██║██║╚████║
#██║░╚═╝░██║██║░░██║██║██║░╚███║
#╚═╝░░░░░╚═╝╚═╝░░╚═╝╚═╝╚═╝░░╚══╝


from services.firebase_manager import FirebaseManager
from firebase_admin import db

import os
import time
import random

import pygame

# ╭━━━┳╮╱╭┳━━━┳━━┳━━━╮
# ┃╭━╮┃┃╱┃┣╮╭╮┣┫┣┫╭━╮┃
# ┃┃╱┃┃┃╱┃┃┃┃┃┃┃┃┃┃╱┃┃
# ┃╰━╯┃┃╱┃┃┃┃┃┃┃┃┃┃╱┃┃
# ┃╭━╮┃╰━╯┣╯╰╯┣┫┣┫╰━╯┃
# ╰╯╱╰┻━━━┻━━━┻━━┻━━━╯

def init_audio():
    # try pipeWire first
    os.environ.update({
        'SDL_AUDIODRIVER': 'pipewire',
        'PIPEWIRE_LATENCY': '512/48000',
        'PW_STREAM_RATE': '1'
    })
    
    try:
        pygame.mixer.init(frequency=48000)
        if pygame.mixer.get_init():
            print("Audio: Using PipeWire backend")
            return True
    except:
        pass
    
    # fallback to default
    os.environ.pop('SDL_AUDIODRIVER', None)
    os.environ.pop('PIPEWIRE_LATENCY', None)
    
    try:
        pygame.mixer.quit()
        pygame.mixer.init()  # default initialization
        print("Audio: Using system default backend")
        return True
    except:
        print("Audio: Failed to initialize - running without sound")
        return False

# usage:
if init_audio():
    sound = pygame.mixer.Sound('assets/sounds/thunder_strike.wav')
    sound.play()


pygame.init()
pygame.font.init()  # explicit font initialization

test_sound = pygame.mixer.Sound('assets/sounds/thunder_strike.wav')
test_sound.play()

import sys
import copy
import threading
import queue
import json

from const import *
from game import Game
from square import Square
from piece import *
from move import Move
from cast_move import Cast_move
from player import Player


class Main:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode( (WIDTH + 200, HEIGHT + 40 + RAMPART_HEIGHT) )
        pygame.display.set_caption('Rampart')
        self.game = Game()
        self.game.play_strike_sound()
        
        
# ╭━╮╱╭┳━━━┳━━━━┳╮╭╮╭┳━━━┳━━━┳╮╭━┳━━┳━╮╱╭┳━━━╮
# ┃┃╰╮┃┃╭━━┫╭╮╭╮┃┃┃┃┃┃╭━╮┃╭━╮┃┃┃╭┻┫┣┫┃╰╮┃┃╭━╮┃
# ┃╭╮╰╯┃╰━━╋╯┃┃╰┫┃┃┃┃┃┃╱┃┃╰━╯┃╰╯╯╱┃┃┃╭╮╰╯┃┃╱╰╯
# ┃┃╰╮┃┃╭━━╯╱┃┃╱┃╰╯╰╯┃┃╱┃┃╭╮╭┫╭╮┃╱┃┃┃┃╰╮┃┃┃╭━╮
# ┃┃╱┃┃┃╰━━╮╱┃┃╱╰╮╭╮╭┫╰━╯┃┃┃╰┫┃┃╰┳┫┣┫┃╱┃┃┃╰┻━┃
# ╰╯╱╰━┻━━━╯╱╰╯╱╱╰╯╰╯╰━━━┻╯╰━┻╯╰━┻━━┻╯╱╰━┻━━━╯
        
        self.game_id = None
        self.my_color = None
        self.process_flag = True
        self.opponent_rematch_requested = False
        
        self.queen_raid_context = None  # networked
        
        self.move_queue = queue.Queue()  # for thread-safe move handling
        self.fb = FirebaseManager()
        
        self.move_lock = threading.Lock()
        
        self.rematch_requested = False  # track if current player requested rematch
        self.awaiting_rematch_response = False  # track if waiting for opponent
    
        # start listener thread if in networked game
        if self.game_id:  
            threading.Thread(
                target=self._start_firebase_listener, 
                daemon=True
            ).start()
            
        # heartbeat system:
        self.running = False
        self.last_heartbeat = {}  # track last heartbeat timestamps
        self.heartbeat_interval = 5  # seconds between heartbeats
        self.timeout_threshold = 15  # seconds before considering disconnected
            
        # UI elements
        self.ui_font = pygame.font.SysFont('Arial', 24)
        self.input_text = ""
        self.active_input = False
        self.status_message = "Press H to host or J to join"
        
        # chat system variables
        self.chat_listener = None
        self.chat_font = pygame.font.SysFont('Arial', 16)
        self.chat_active = False
        self.chat_text = ""
        self.chat_messages = []
        self.chat_rect = pygame.Rect(WIDTH - 265, 23, 300, 100)
        self.max_messages = 4  # visible messages at once
        self.max_chars = 25 # maximum characters per message
        
    def start_networking(self, game_id):
        
        if hasattr(self, 'networking_thread') and self.networking_thread.is_alive():
            self.running = False
            self.networking_thread.join(timeout=1.0)
        
        self.running = True
        
        # simplified version with proper db access
        print(f"DEBUG: Attempting to connect to game {game_id}")
        print(f"\n SS FIREBASE PATH DEBUG SS")
        print(f"My Color: {self.my_color}")
        print(f"Game ID: {game_id}")
        print(f"Full Path: games/{game_id}/moves")
        
        # test if path exists
        test_ref = db.reference(f'games/{game_id}')
        exists = test_ref.get() is not None
        print(f"Path exists: {exists}")
        
        # test write
        test_ref.child('connection_test').set({
            'player': self.my_color,
            'timestamp': int(time.time())
        })
        print(f"Test write successful\n")
        # verify game exists using firebaseManager
        if not self.fb.game_exists(game_id):
            print("ERROR: Game ID does not exist or connection failed")
            return
    
        def handle_incoming_move(event):
            # case 1: firebase Event object
            if hasattr(event, 'data'):
                move_data = event.data
            # case 2: already extracted move dict
            elif isinstance(event, dict):
                move_data = event
            else:
                print(f"ERROR: Unknown event type {type(event)}: {event}")
                return
        
            if not move_data:
                print("DEBUG: Empty move data")
                return
            
            if isinstance(move_data, dict) and any(k.startswith('-') for k in move_data.keys()):
                print(f"DEBUG: Received full moves node, extracting latest")
                move_data = list(move_data.values())[-1]  # get most recent move
        
            print(f"DEBUG: Processing move data: {move_data}")
            
            if not isinstance(move_data, dict) or 'type' not in move_data:
                print(f"DEBUG: Invalid move structure: {move_data}")
                return
            
            if move_data['type'] == 'queen_raid_sequence':
                try:
                    sender = move_data.get('sender')
                    initial = self.game.board.squares[move_data['initial']['col']][\
                            move_data['initial']['row']]
                    final = self.game.board.squares[move_data['final']['col']][\
                            move_data['final']['row']]  
                    move = Move(initial, final)
                
                    queen_data = {
                        'col': move_data['queen_data']['col'],
                        'row': move_data['queen_data']['row']
                        }
                
                    self.move_queue.put({
                        'type': 'queen_raid_sequence',
                        'sender': sender,
                        'move': move,
                        'queen_data': queen_data
                        })
                    
                except Exception as e:
                    print(f"DEBUG [B]: Move processing failed: {e}")
                
            elif move_data['type'] == 'move':
                try:
                    print(f"DEBUG [B]: Creating Square objects...")
                    initial = self.game.board.squares[move_data['initial']['col']][move_data['initial']['row']]
                    final = self.game.board.squares[move_data['final']['col']][move_data['final']['row']]
                    move = Move(initial, final)
                    self.move_queue.put(move)
                    print("DEBUG [B]: Move queued successfully!")
                except Exception as e:
                    print(f"DEBUG [B]: Move processing failed: {e}")
                    
            elif move_data['type'] == 'cast':
                try:
                    cards = [self.game.board.get_card(c['suit'], c['rank']) for c in move_data['cards']]
                    final = self.game.board.squares[move_data['final']['col']][move_data['final']['row']]
                    cast_type = move_data['cast_type']
                    
                    cast_move = Cast_move(cards, final, cast_type)
                    
                    # player
                    player = self.game.board.players[0] if self.my_color == 'white' \
                        else self.game.board.players[1]
                    
                    # reconstruct piece
                    piece = None
                    if move_data['piece_type']:
                        piece_class = {
                            'raider': Raider,
                            'queen': Queen,
                            }[move_data['piece_type']]
                        piece = piece_class(move_data['piece_color'])
                    
                    # reconstruct card
                    card = None
                    if move_data.get('card_suit') is not None:
                        card = self.game.board.get_card(move_data['card_suit'], move_data['card_rank'])
                        
                    self.move_queue.put({
                        'type': 'cast_execution',
                        'player': player,
                        'piece': piece,
                        'card': card,
                        'move': cast_move,
                        })
                    
                    print("DEBUG [B]: Move queued successfully!")
                except Exception as e:
                    print(f"DEBUG [B]: Move processing failed: {e}")
                        
        print("DEBUG: Starting listener thread...")
        networking_thread = threading.Thread(
            target=self.fb.listen_for_moves,
            args=(game_id, handle_incoming_move),
            daemon=True
        )
        networking_thread.start()
        print(f"DEBUG [B]: Networking thread alive? {networking_thread.is_alive()}")
        
        def send_heartbeat():
            while getattr(self, 'running', False) and getattr(self, 'game_id', None) == game_id:
                try:
                    db.reference(f'games/{game_id}/heartbeats/{self.my_color}').set({
                        'timestamp': {'.sv': 'timestamp'},
                        'player': self.my_color
                    })
                    print(f"Heartbeat sent by {self.my_color}")
                except Exception as e:
                    print(f"Heartbeat failed: {e}")
                
                time.sleep(self.heartbeat_interval)
        
        threading.Thread(target=send_heartbeat, daemon=True).start()
        
        def handle_heartbeat(event):
            if event.path == '/':
                data = event.data
            else:
                color = event.path.split('/')[-1]
                data = {color: event.data}
            
            for player, heartbeat in (data or {}).items():
                if player != self.my_color:
                    self.last_heartbeat[player] = time.time()
                    print(f"Heartbeat received from {player}")
    
        db.reference(f'games/{game_id}/heartbeats').listen(handle_heartbeat)       

        # █▀▀ █░█ ▄▀█ ▀█▀
        # █▄▄ █▀█ █▀█ ░█░
        
        # chat listener
        def handle_incoming_chat(event):
            if event.data and isinstance(event.data, dict):
                msg_data = event.data
                if msg_data.get('player') != self.my_color:
                    msg = f"{msg_data.get('player', 'Opponent')}: {msg_data.get('text', '')}"
                    self.chat_messages.append(msg)
                    if len(self.chat_messages) > self.max_messages:
                        self.chat_messages.pop(0)
        
        # firebase managed listener
        db.reference(f'games/{self.game_id}/chat').listen(handle_incoming_chat)
        
        def handle_rematch_update(event):
            opponent = 'black' if self.my_color == 'white' else 'white'
            
            if event.path == '/':
                data = event.data or {}
            else:
                color = event.path.split('/')[-1]
                data = {color: event.data}
            
            # only care about opponent's state changes
            if opponent in data:
                opponent_state = data[opponent]
                if opponent_state != self.opponent_rematch_requested:
                    self.opponent_rematch_requested = opponent_state
                    if opponent_state:
                        self.status_message = "Opponent wants rematch! Press R to accept"
                    
                    # don't execute rematch here, just set flag
                    if opponent_state and self.rematch_requested:
                        self.execute_rematch()  # this now avoids direct display ops
    
        self.rematch_listener = db.reference(f'games/{game_id}/rematch').listen(
            lambda event: handle_rematch_update(event))
            
    def request_rematch(self):
        if not self.game_id:
            return
            
        status = db.reference(f'games/{self.game_id}/rematch').get() or {}
        opponent = 'black' if self.my_color == 'white' else 'white'
        
        # only request if haven't already and opponent hasn't requested
        if not status.get(self.my_color, False) and not status.get(opponent, False):
            db.reference(f'games/{self.game_id}/rematch/{self.my_color}').set(True)
            self.rematch_requested = True
            self.status_message = "Rematch requested - waiting"
    
    def check_rematch_status(self):
        status = db.reference(f'games/{self.game_id}/rematch').get() or {}
        self.opponent_rematch_requested = status.get('white' if self.my_color == 'black' else 'black', False)

    def execute_rematch(self):
        # reset game objects
        self.game.reset()
        self.game = Game()
        self.need_refresh = True
        
        # swap colors
        new_color = 'black' if self.my_color == 'white' else 'white'
        self.my_color = new_color
        
        # reset flags and states
        self.rematch_requested = False
        self.opponent_rematch_requested = False
        self.process_flag = True
        self.game.next_player = 'white'
        self.game.next_state = None
        self.game.board.last_player_color = None
        
        self.move_queue.queue.clear()
        
        # queue display update for main thread
        self.rematch_complete = True
        self.status_message = f"Rematch! You're now {self.my_color}. {'Your turn!' if self.my_color == 'white' else 'Waiting for white...'}"
        
        # send sync as move
        if self.game_id:
            sync_move = {
                'type': 'sync',
                'next_player': 'white',
                'sender': self.my_color,
                'process_flag': (self.my_color == 'white'),
                'reset': True  # flag to indicate full reset
            }
            self.fb.send_move(self.game_id, sync_move)
            
        print(
            f"REMATCH STATE CHECK:\n"
            f"My Color: {self.my_color}\n"
            f"Next Player: {self.game.next_player}\n"
            f"Board Last Color: {self.game.board.last_player_color}\n"
            f"Process Flag: {self.process_flag}\n"
        )
            
    def check_and_execute_rematch(self):
        if not self.game_id:
            return
            
        status = db.reference(f'games/{self.game_id}/rematch').get() or {}
        
        # only proceed if both players have agree to rematch
        if status.get('white', False) and status.get('black', False):
            self.execute_rematch()

    def send_move_to_opponent(self, move, piece=None, card=None):
        # minimal move sender without serialization
        if self.game.queen_raid_pending and isinstance(move, dict):
            move_data = {
                'type': 'queen_raid_sequence',
                'initial': {'col': self.queen_raid_context['move'].initial.col,
                                'row': self.queen_raid_context['move'].initial.row},
                'final': {'col': self.queen_raid_context['move'].final.col,
                              'row': self.queen_raid_context['move'].final.row},
                'queen_data': {
                    'col': self.queen_raid_context['queen_data']['col'],
                    'row': self.queen_raid_context['queen_data']['row']},
                'next_player': 'black' if self.game.next_player == 'white' else 'white',
                'process_flag': not self.process_flag,
                'sender': self.my_color
                }
            self.game.queen_raid_pending = False
        else:
              
            if isinstance(move, Move):
                move_data = {
                    'type': 'move',
                    'initial': {'col': move.initial.col, 'row': move.initial.row},
                    'final': {'col': move.final.col, 'row': move.final.row},
                    'next_player': 'black' if self.game.next_player == 'white' else 'white',
                    'process_flag': not self.process_flag
                }
                
            elif isinstance(move, Cast_move):
                move_data = {
                    'type': 'cast',
                    'cards': [{'suit': c.suit, 'rank': c.rank} for c in move.cards],
                    'final': {'col': move.final.col, 'row': move.final.row},
                    'cast_type': move.cast_type,
                    # context
                    'piece_type': piece.name if piece else None,
                    'piece_color': piece.color if piece else None,
                    'card_suit': card.suit if card else None,
                    'card_rank': card.rank if card else None,
                    'next_player': 'black' if self.game.next_player == 'white' else 'white',
                    'process_flag': not self.process_flag
                    }
        
        if isinstance(move_data, dict):
            move_data['next_player'] = 'black' if self.game.next_player == 'white' else 'white'
            
        self.fb.send_move(self.game_id, move_data)

    def process_networked_moves(self):
        while not self.move_queue.empty():
            item = self.move_queue.get()
            
            if isinstance(item, dict) and item.get('type') == 'sync':
                if item['sender'] != self.my_color:  # only process opponent's sync
                    # full state synchronization
                    self.game.next_player = item['next_player']
                    self.process_flag = item['process_flag']
                    if item.get('reset'):
                        self.game.next_state = None  # reset turn system
                        self.game.board.last_player_color = None
                continue
            
            print(f"DEBUG [C]: Processing queued item: {item}")
            if self.game.next_player == self.my_color:
                continue
            
            if isinstance(item, dict) and item.get('type') == 'queen_raid_sequence':
                if (not self.process_flag and self.my_color == 'white') or \
                    (self.process_flag and self.my_color == 'black'):
                    if item.get('sender') != self.my_color:
                        try:
                            move = item['move']
                            final_sq = move.final  # define final_sq here
                            captured = final_sq.has_piece()
                            self.game.board.apply_networked_move(move)
                            self.game.play_sound(captured)
                            
                            col = item['queen_data']['col']
                            row = item['queen_data']['row']
                            
                            color = 'white' if self.my_color == 'black' else 'black'
                            card = self.game.board.squares[col][row].card
                            
                            final = self.game.board.squares[col][row]
                            cards = []
                            cast_move = Cast_move(cards, final, 1)
                            
                            player = self.game.board.players[1] if self.my_color == 'black' \
                                else self.game.board.players[0]
                            piece = Queen(color)
                            
                            print(f"DEBUG: Attempting cast_move with:")
                            print(f"- Player: {player.color}")
                            print(f"- Piece: {piece.name} {piece.color}")
                            print(f"- Card: {card.suit if card else 'None'}")
                            print(f"- Move: {cast_move.final.col},{cast_move.final.row}")
                            
                            self.game.board.cast_move(player, piece, card, cast_move)
                            
                            self.game.lightning.trigger(color, persist_frames=10)
                            self.game.play_raise_sound()
                            
                            my_player = self.game.board.players[0] if self.my_color == 'black' \
                                else self.game.board.players[1]
                                
                            is_check = self.game.board.king_in_check(my_player)
                            
                            if self.my_color == 'white' and self.game.white_cast_prompt == 'in-check':
                                self.game.kill_prompt(self.my_color)
                            elif self.my_color == 'black' and self.game.black_cast_prompt == 'in-check':
                                self.game.kill_prompt(self.my_color)

                            # show if in check
                            if is_check:
                                self.game.set_in_check_prompt(self.my_color)
                                
                            if self.game.board._king_mated(my_player):
                                self.game.set_mated_prompt(my_player.color)
                            else:
                                # next turn/player
                                self.game.next_turn()
                        
                        except Exception as e:
                            print(f"DEBUG: Move failed - {e}")
            
            elif isinstance(item, Move):
                
                if hasattr(item, 'next_player'):  # for networked moves
                    self.game.next_player = item.next_player
                elif isinstance(item, dict) and 'next_player' in item:  # for queued moves
                    self.game.next_player = item['next_player']
                
                final_sq = item.final
                captured = final_sq.has_piece()
                captured_piece = final_sq.piece
                if (not self.process_flag and self.my_color == 'white') or \
                    (self.process_flag and self.my_color == 'black'):
                    try:
                        if captured and captured_piece.name in ['raider', 'queen']:
                            self.game.board._send_to_grave(captured_piece) 
                        self.game.board.apply_networked_move(item)  # apply to board
                        print("DEBUG: Move applied successfully")
                        
                        self.game.play_sound(captured)
                        
                        my_player = self.game.board.players[0] if self.my_color == 'black' \
                            else self.game.board.players[1]
                            
                        opponent = self.game.board.players[0] if self.my_color == 'white' \
                            else self.game.board.players[1]
                            
                        is_check = self.game.board.king_in_check(my_player)
                        print(f"[CHECK STATE] is_check={is_check}, my_player={my_player.color}, self.my_color={self.my_color}")
                        
                        if self.my_color == 'white' and self.game.white_cast_prompt == 'in-check':
                            self.game.kill_prompt(self.my_color)
                        elif self.my_color == 'black' and self.game.black_cast_prompt == 'in-check':
                            self.game.kill_prompt(self.my_color)
                        
                        if is_check:
                            print(">> Setting check prompt for", self.my_color)
                            self.game.set_in_check_prompt(self.my_color)
                        
                        if self.game.board.squares[item.final.col][item.final.row].is_own_king_house(my_player.color):
                            if self.game.board._opponent_king_on_noncard(opponent.color):
                                self.game.board.king_mated = True
                                self.game.set_mated_prompt(my_player.color)
                            
                        if self.game.board._king_mated(my_player):
                            self.game.set_mated_prompt(my_player.color)
                        else:
                            # next turn/player
                            self.game.next_turn()
                        
                    except Exception as e:
                        print(f"DEBUG: Move failed - {e}")
                        
            elif isinstance(item, dict) and item['type'] == 'cast_execution':
                if 'next_player' in item:
                    self.game.next_player = item['next_player']
                    
                if (not self.process_flag and self.my_color == 'white') or \
                    (self.process_flag and self.my_color == 'black'):
                    try:
                        player = item['player']
                        piece = item['piece']
                        card = item['card']
                        move = item['move']
                        
                        self.game.board.apply_networked_cast_move(player, piece, card, move)  # delegate to board
                        print("DEBUG: Move applied successfully")
                        
                        self.game.set_cast_prompt(self.my_color)
                        
                        self.game.lightning.trigger(self.game.next_player, persist_frames=10)
                        
                        print('cast_type:', move.cast_type)
                        if move.cast_type == 0:
                            self.game.play_strike_sound()
                        elif move.cast_type == 1:
                            self.game.play_raise_sound()
                        
                        print('cards:',move.cards)
                        self.game.cast_cards_networked(move.cards)
                        
                        my_player = self.game.board.players[0] if self.my_color == 'black' \
                            else self.game.board.players[1]
                            
                        is_check = self.game.board.king_in_check(my_player)
                        
                        if self.my_color == 'white' and self.game.white_cast_prompt == 'in-check':
                            self.game.kill_prompt(self.my_color)
                        elif self.my_color == 'black' and self.game.black_cast_prompt == 'in-check':
                            self.game.kill_prompt(self.my_color)

                        # show if in check
                        if is_check:
                            self.game.set_in_check_prompt(self.my_color)
                            
                        if self.game.board._king_mated(my_player):
                            self.game.set_mated_prompt(my_player.color)
                        else:
                            # next turn/player
                            self.game.next_turn()
                        
                    except Exception as e:
                        print(f"DEBUG: Move failed - {e}")
                        
        if self.game.board.last_player_color:
            # if not self.game.queen_raid_pending:
            last_color = self.game.board.last_player_color
            if last_color == 'white':
                self.process_flag = False
            else:
                self.process_flag = True
            
    def check_connection_health(self):
        if not self.game_id or not self.my_color:
            return True  # local game
        
        opponent = 'black' if self.my_color == 'white' else 'white'
        
        # start checking after at least one heartbeat
        if opponent not in self.last_heartbeat:
            return True  # opponent hasn't connected yet
            
        last_seen = self.last_heartbeat[opponent]
        time_since = time.time() - last_seen
        
        if time_since > self.timeout_threshold:
            self.status_message = "Opponent disconnected!"
            return False
            
        return True
            
    def _log_listeners(self):
        # debug statement to show active listeners
        print("ACTIVE LISTENERS:")
        print(f"- Rematch: {hasattr(self, '_rematch_listener')}")
        print(f"- Heartbeat: {hasattr(self, '_heartbeat_listener')}") 
        print(f"- Chat: {hasattr(self, '_chat_listener')}")
         
    def cleanup(self):
        print("🛑 DEBUG: Initiated shutdown sequence")
        
        print(f"🔍 Pre-cleanup listener state: {hasattr(self, 'rematch_listener')}")
        
        self.running = False  # this stops the heartbeat
        
        # 0. close rematch listener first
        if hasattr(self, 'rematch_listener') and self.rematch_listener:
            try:
                print("♻️ Closing rematch listener")
                self.rematch_listener.close()
            except Exception as e:
                print(f"⚠️ Rematch listener close error: {e}")
            finally:
                self.rematch_listener = None
    
        print("🛑 Stopping all threads...")
        
        threads = []
        if hasattr(self, 'networking_thread'):
            threads.append(('networking', self.networking_thread))
        if hasattr(self, 'heartbeat_thread'):  # if you has a separate heartbeat thread
            threads.append(('heartbeat', self.heartbeat_thread))
            
        for name, thread in threads:
            if thread and thread.is_alive():
                print(f"🛑 Stopping {name} thread...")
                thread.join(timeout=0.5)  # brief wait
                if thread.is_alive():
                    print(f"⚠️ {name} thread didn't stop gracefully")
        
        
        # cleanup heartbeats first
        if hasattr(self, 'game_id') and self.game_id and hasattr(self, 'my_color'):
            try:
                print("♻️ Removing heartbeat from Firebase")
                db.reference(f'games/{self.game_id}/heartbeats/{self.my_color}').delete()
            except Exception as e:
                print(f"⚠️ Heartbeat cleanup error: {e}")
        
        # 1. thread termination (with timeout tracking)
        thread = getattr(self, 'networking_thread', None)
        if thread and thread.is_alive():
            print("🛑 DEBUG: Stage 1 - Thread termination started")
            self.process_flag = False
            
            # triple termination
            start_time = time.time()
            try:
                # attempt graceful shutdown
                self.move_queue.put('TERMINATE', timeout=0.5)
                thread.join(timeout=1.0)
                
                if thread.is_alive():
                    print("⚠️ DEBUG: Graceful timeout - forcing daemon")
                    thread.daemon = True
            except Exception as e:
                print(f"⚠️ DEBUG: Thread termination error: {e}")
            finally:
                print(f"⏱️ DEBUG: Thread shutdown took {time.time()-start_time:.2f}s")
        
        # 2. firebase cleanup (with forced timeout)
        if hasattr(self, 'fb'):
            print("🛑 DEBUG: Stage 2 - Firebase cleanup")
            fb_cleanup_start = time.time()
            try:
                # create thread for firebase cleanup with timeout
                def fb_cleaner():
                    self.fb.cleanup()
                
                fb_thread = threading.Thread(target=fb_cleaner, daemon=True)
                fb_thread.start()
                fb_thread.join(timeout=2.0)
                
                if fb_thread.is_alive():
                    print("⚠️ DEBUG: Firebase cleanup timeout")
            except Exception as e:
                print(f"⚠️ DEBUG: Firebase error: {e}")
            finally:
                print(f"⏱️ DEBUG: Firebase cleanup took {time.time()-fb_cleanup_start:.2f}s")
        
        # 3. resource finalization
        print("🛑 DEBUG: Stage 3 - Final resource cleanup")
        try:
            while not self.move_queue.empty():
                self.move_queue.get_nowait()
        except:
            pass
        
        print(f"🔍 Post-cleanup listener state: {hasattr(self, 'rematch_listener')}")
        
        print("✅ DEBUG: Cleanup completed successfully")
        
    def _generate_pin(self):
        # generate a 4-digit pin and map it to the firebase ID
        self.game_pin = str(random.randint(1000, 9999))
        # store mapping in Firebase
        db.reference(f'pin_mappings/{self.game_pin}').set({
            'game_id': self.game_id,
            'created': {'.sv': 'timestamp'}
        })

    def _start_host_ui(self):
        self.status_message = "Creating game..."
        pygame.display.flip()  # force UI update
        
        # existing host code:
        self.host_new_game()  
        self.status_message = f"Game ID: {self.game_pin}"
    
    def _handle_join_ui(self):
        print(f"Attempting to join with PIN: {self.input_text}")
        pin = self.input_text.strip()
        if len(pin) != 4 or not pin.isdigit():
            self.status_message = "PIN must be 4 digits!"
            print("Invalid PIN format")
            return
        
        self.join_game(pin)  # update status_message on success/failure
        self.active_input = False  # important: close input after submitting
        
    def host_new_game(self):
        # original + PIN generation
        self.my_color = 'white'
        self.last_heartbeat = {}
        self.game_id = self.fb.create_game(  # keep existing firebase call
            self.game.board.get_serialized_state()
        )
        self._generate_pin()  # generate 4-digit PIN
        self.status_message = f"Game PIN: {self.game_pin}"  # show short PIN
        self.start_networking(self.game_id)  # start listening for moves
        
        db.reference(f'games/{self.game_id}/rematch').set({
            'white': False,
            'black': False,
            'initiator': None
        })
        
        print(f"DEBUG: Host networking started for game {self.game_id}")
    
    def join_game(self, pin):
        try:
            # clean up any existing listener first
            if hasattr(self, 'networking_thread'):
                self.cleanup()
            print(f"Looking up PIN: {pin}")  # debug
            mapping = db.reference(f'pin_mappings/{pin}').get()
            
            if not mapping or 'game_id' not in mapping:
                self.status_message = "Invalid PIN - Game not found"
                print("No game found for this PIN")  # debug
                return
                
            self.my_color = 'black'
            self.game_id = mapping['game_id']
            print(f"Success! Joining game: {self.game_id}")  # debug
            
            # clear any previous networking
            if hasattr(self, 'networking_thread'):
                self.cleanup()
                
            self.status_message = f"Joined game! Waiting for host..."
            self.start_networking(self.game_id)
            
        except Exception as e:
            print(f"Join failed: {str(e)}")  # debug
            self.status_message = f"Connection failed: {str(e)}"
            self.active_input = True  # keep input open if failed
            
    # █▀▀ █░█ ▄▀█ ▀█▀   █▀█ █▀▀ █▄░█ █▀▄ █▀▀ █▀█
    # █▄▄ █▀█ █▀█ ░█░    █▀▄ ██▄ █░▀█ █▄▀ ██▄ █▀▄            
    
    def show_chat(self):
        # draw chat box
        pygame.draw.rect(self.screen, (255, 255, 255), self.chat_rect)
        pygame.draw.rect(self.screen, (0, 0, 139), self.chat_rect, 2)  # blue border
        
        # display messages
        for i, msg in enumerate(self.chat_messages[-self.max_messages:]):
            msg_surface = self.chat_font.render(msg, True, (0, 0, 0))
            self.screen.blit(msg_surface, (self.chat_rect.x + 5, self.chat_rect.y + 5 + i * 20))
        
        # show current input
        if self.chat_active:
            input_surface = self.chat_font.render("> " + self.chat_text, True, (0, 0, 0))
            self.screen.blit(input_surface, (self.chat_rect.x + 5, self.chat_rect.y + 80))
        else:
            prompt_surface = self.chat_font.render("Press 'C' to chat", True, (100, 100, 100))
            self.screen.blit(prompt_surface, (self.chat_rect.x + 5, self.chat_rect.y + 80))
                

# ╭━╮╭━┳━━━┳━━┳━╮╱╭┳╮╱╱╭━━━┳━━━┳━━━╮
# ┃┃╰╯┃┃╭━╮┣┫┣┫┃╰╮┃┃┃╱╱┃╭━╮┃╭━╮┃╭━╮┃
# ┃╭╮╭╮┃┃╱┃┃┃┃┃╭╮╰╯┃┃╱╱┃┃╱┃┃┃╱┃┃╰━╯┃
# ┃┃┃┃┃┃╰━╯┃┃┃┃┃╰╮┃┃┃╱╭┫┃╱┃┃┃╱┃┃╭━━╯
# ┃┃┃┃┃┃╭━╮┣┫┣┫┃╱┃┃┃╰━╯┃╰━╯┃╰━╯┃┃
# ╰╯╰╯╰┻╯╱╰┻━━┻╯╱╰━┻━━━┻━━━┻━━━┻╯

    
    def mainloop(self):
        
        screen = self.screen
        game = self.game
        board = game.board
        dragger = game.dragger
        clicker = game.clicker
        
        # network:
        fb = FirebaseManager()
        
        
        clicked_suit = None
        clicked_rank = None
        casting = False
        queen_house_raided = False
        cast_sound = None
        
        # connection health
        last_health_check = 0
        health_check_interval = 3  # seconds
        
        while True:
            
            if hasattr(self, 'need_refresh') and self.need_refresh:
                game = self.game  # update local reference
                board = game.board
                dragger = game.dragger
                clicker = game.clicker
                del self.need_refresh  # clear flag
                print("References refreshed!")
            
            # show-methods
            screen.fill((0,0,0))
            game.show_bg(screen)
            game.show_last_move(screen)
            game.show_moves(screen)
            game.show_pieces(screen)    
            game.show_dead(screen)
            game.show_cemetery(screen)
            game.show_cast_buttons(screen)
            game.show_hover(screen)
            game.show_clicked_cards(screen)
            game.show_clicked_btns(screen)
            game.show_dead_cards(screen)
            game.show_chosen_piece(screen)
            game.show_cast_prompt(screen, self.my_color)
            
            self.show_chat()
            self.process_networked_moves()
            
            # network health:
            current_time = time.time()
        
            # connection health monitoring
            if current_time - last_health_check > health_check_interval:
                if not self.check_connection_health():
                    # handle disconnection (e.g. paused game)
                    pass
                last_health_check = current_time
            
            if dragger.dragging:
                dragger.update_blit(screen)
                
            if hasattr(self, 'rematch_complete') and self.rematch_complete:
                pygame.display.flip()
                del self.rematch_complete
            
            
            for event in pygame.event.get():
                
                if not board.king_mated and not board.king_stalemated:
                    
                    if game.next_state == 'update1':
                        
                        if game.lightning.active:
                            game.lightning.update()
                            if game.lightning.persist_frames > 0:
                                game.lightning.persist_frames -= 1
                            else:
                                game.lightning.active = False
                        
                        
                        # draw all game elements
                        screen.fill((0,0,0))
                        game.show_bg(screen)
                        game.show_last_move(screen)
                        game.show_moves(screen)
                        game.show_pieces(screen)
                        game.show_dead(screen)
                        game.show_cemetery(screen)
                        game.show_cast_buttons(screen)
                        game.show_hover(screen)
                        game.show_clicked_cards(screen)
                        game.show_clicked_btns(screen)
                        game.show_dead_cards(screen)
                        game.show_chosen_piece(screen)
                        game.show_cast_prompt(screen, self.my_color)
                        self.show_chat()
                        
                        # draw lightning if active
                        if game.lightning.active:
                            
                            # force a small delay to ensure animation is visible
                            pygame.time.delay(30)
                            
                            screen.fill((255,255,255))
                            game.show_bg(screen)
                            game.show_last_move(screen)
                            game.show_moves(screen)
                            game.show_pieces(screen)
                            game.show_cemetery(screen)
                            game.show_cast_buttons(screen)
                            game.show_hover(screen)
                            game.show_clicked_cards(screen)
                            game.show_clicked_btns(screen)
                            game.show_dead_cards(screen)
                            game.show_chosen_piece(screen)
                            game.show_cast_prompt(screen, self.my_color)
                            game.lightning.draw(screen)
                            
                            self.show_chat()
                            
                            if cast_sound == 'strike':
                                game.play_strike_sound()
                            elif cast_sound == 'raise':
                                game.play_raise_sound()
                            
                            cast_sound = None
                            
                        else:
                            # small delay to ensure animation is visible
                            pygame.time.delay(30)
                                
                            game.show_bg(screen)
                            game.show_last_move(screen)
                            game.show_moves(screen)
                            game.show_pieces(screen)
                            game.show_dead(screen)
                            game.show_cemetery(screen)
                            game.show_cast_buttons(screen)
                            game.show_hover(screen)
                            game.show_clicked_cards(screen)
                            game.show_clicked_btns(screen)
                            game.show_dead_cards(screen)
                            game.show_chosen_piece(screen)
                            game.show_cast_prompt(screen, self.my_color)
                            
                            self.show_chat()
                        
                        game.change_state()
                        
                    elif game.next_state == "update2":
                        
                        pygame.time.delay(30)
                            
                        game.show_bg(screen)
                        game.show_last_move(screen)
                        game.show_moves(screen)
                        game.show_pieces(screen)
                        game.show_dead(screen)
                        game.show_cemetery(screen)
                        game.show_cast_buttons(screen)
                        game.show_hover(screen)
                        game.show_clicked_cards(screen)
                        game.show_clicked_btns(screen)
                        game.show_dead_cards(screen)
                        game.show_chosen_piece(screen)
                        game.show_cast_prompt(screen, self.my_color)
                        
                        self.show_chat()
                        
                        game.change_state()
                    

# █▀▄▀█ █▀█ █░█ █▀ █▀▀ █▄▄ █░█ ▀█▀ ▀█▀ █▀█ █▄░█ █▀▄ █▀█ █░█░█ █▄░█
# █░▀░█ █▄█ █▄█ ▄█ ██▄  █▄█ █▄█ ░█░ ░█░ █▄█ █░▀█ █▄▀ █▄█ ▀▄▀▄▀ █░▀█
                    
                    # mouse click
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        dragger.update_mouse(event.pos)
                        clicker.update_mouse(event.pos)
                        
                        # first get all possible positions using the new methods
                        clicked_col, clicked_row = game.get_board_position(event.pos[0], event.pos[1])
                        clicked_suit, clicked_rank = game.get_card_position(event.pos[0], event.pos[1])
                        
                        if dragger.mouseX < 100:  # left side (black deck/graveyard)
                            clicked_col = 0
                            clicked_row = 5
                            if 2 <= dragger.mouseX <= 2 + CWIDTH:  # card deck area
                                clicked_suit, clicked_rank = game.get_card_position(event.pos[0], event.pos[1])
                                
                        elif dragger.mouseX >= 900:  # right side (white deck/graveyard)
                            clicked_col = 9
                            clicked_row = 5
                            if 902 <= dragger.mouseX <= 902 + CWIDTH:  # card deck area
                                clicked_suit, clicked_rank = game.get_card_position(event.pos[0], event.pos[1])
                            
                        if clicked_col is not None:  # clicked on main board
                            if clicker.clicked_btn == None:
                                if len(clicker.clicked_cards) > 0:
                                    if board.squares[clicked_col][clicked_row].is_card() and \
                                        board.squares[clicked_col][clicked_row].has_piece() and \
                                            clicked_row not in [0, 5]:
                                        card = board.squares[clicked_col][clicked_row].card
                                        piece = board.squares[clicked_col][clicked_row].piece
                                        if not clicker.is_clicked(card):
                                            if piece.name == 'raider' and \
                                                    piece.color == game.next_player:
                                                clicker.explic_save_card(card)
                                                clicker.click_card(card)
                                                # play sound
                                                game.play_card_sound()
                                                # show methods
                                                game.show_bg(screen)
                                                game.show_last_move(screen)
                                                game.show_moves(screen)
                                                game.show_pieces(screen)
                                                game.show_clicked_cards(screen)
                                                game.show_dead(screen)
                                                game.show_dead_cards(screen)
                                                self.show_chat()
                                                
                                                if clicker.has_sum_21(clicker.clicked_cards):
                                                    game.set_choose_cast_prompt(game.next_player)
                                        else:
                                            clicker.unclick_card(card)
                                            # play sound
                                            game.play_card_sound()
                                            if len(clicker.clicked_cards) == 0:
                                                casting = False
                                                game.set_cast_prompt(game.next_player)
                                else:
                                    # clicked square has a piece?
                                    if board.squares[clicked_col][clicked_row].has_piece():
                                        piece = board.squares[clicked_col][clicked_row].piece
                                        print("MOVE:", piece.color, game.next_player, self.my_color)
                                        # check if piece (color) is valid
                                        if piece.color == game.next_player and \
                                            self.my_color == game.next_player:
                                            board.calc_moves(piece, clicked_col, clicked_row, bool=True)
                                            dragger.save_initial(clicked_col, clicked_row)
                                            dragger.drag_piece(piece)
                                            # show methods
                                            game.show_bg(screen)
                                            game.show_last_move(screen)
                                            game.show_moves(screen)
                                            game.show_pieces(screen)
                                            game.show_clicked_cards(screen)
                                            game.show_dead(screen)
                                            game.show_dead_cards(screen)
                                            self.show_chat()
                        
    
                        if ((2 <= clicker.mouseX <= 2+CWIDTH and clicker.mouseY <= 800-CEM_HEIGHT) or 
                            (902 <= clicker.mouseX <= 902+CWIDTH and CEM_HEIGHT <= clicker.mouseY <= 800)):
                            clicked_suit, clicked_rank = game.get_card_position(event.pos[0], event.pos[1])
                            if clicked_suit is not None and clicked_rank is not None:  # click was on a card in deck
                                if not board.cards[clicked_suit][clicked_rank].is_cast():
                                    if not clicker.is_clicked(board.cards[clicked_suit][clicked_rank]):
                                        card = board.cards[clicked_suit][clicked_rank]
                                        if (card.suit == 0 and game.next_player == 'black') or \
                                           (card.suit == 1 and game.next_player == 'white'):
                                            # check if jack house is occupied for casting
                                            jack_col = 5 if game.next_player == 'black' else 4
                                            jack_row = 5 if game.next_player == 'black' else 0
                                            if board.squares[jack_col][jack_row].has_piece():
                                                clicker.save_card(event.pos)
                                                clicker.click_card(card)
                                                game.play_card_sound()
                                                game.set_make_21_prompt(game.next_player)
                                                if clicker.has_sum_21(clicker.clicked_cards):
                                                    game.set_choose_cast_prompt(game.next_player)
                                    else:
                                        mouse_x, mouse_y = event.pos
                                        in_deck_area = (
                                            (0 <= mouse_x < 100 and 0 <= mouse_y < HEIGHT - CEM_HEIGHT - 10) or
                                            (900 <= mouse_x <= 1000 and 800 - 13 * CHEIGHT <= mouse_y < HEIGHT)
                                        )
                                        
                                        if in_deck_area:
                                            clicker.unclick_card(board.cards[clicked_suit][clicked_rank])
                                            game.play_card_sound()
                                            if len(clicker.clicked_cards) == 0:
                                                casting = False
                                                game.set_cast_prompt(game.next_player)
                                                

# █▀▄▀█ █▀█ █░█ █▀ █▀▀ █▀▄▀█ █▀█ ▀█▀ █ █▀█ █▄░█
# █░▀░█ █▄█ █▄█ ▄█ ██▄  █░▀░█ █▄█ ░█░ █ █▄█ █░▀█

                    
                    elif event.type == pygame.MOUSEMOTION:
                        # initialize variables at the start
                        hover_col, hover_row = None, None
                        hover_suit, hover_rank = None, None
                        
                        # clear all hovers first
                        game.hovered_sqr = None
                        game.hovered_crd = None
                        game.hovered_btn = None
                        game.hovered_dom = None
                        game.hovered_grave = None
                    
                        # get mouse position
                        mouse_x, mouse_y = event.pos
                    
                        # 1. handle graveyard hover in specific context
                        if (not clicker.clicked_grv and clicker.clicked_btn == 1 and 
                            board._enemy_queen_house_occupied(game.next_player) and 
                            board._queen_isdead(game.next_player)):
                            
                            # determine logical grave column (0=black, 1=white)
                            grave_col = 0 if game.next_player == 'black' else 1
                            
                            # calculate visual positions based on flip
                            if game.flipped:
                                # visual positions swap but logical ownership stays the same
                                visual_left = grave_col == 1  # white graves appear left when flipped
                            else:
                                visual_left = grave_col == 0  # black graves are left normally
                            
                            # set area coordinates based on visual position
                            if visual_left:
                                grave_area_x = 0
                                grave_area_y = HEIGHT - CEM_HEIGHT + 65
                            else:
                                grave_area_x = 900
                                grave_area_y = 90
                            
                            # check mouse in visual area
                            if (grave_area_x <= mouse_x < grave_area_x + 100 and
                                grave_area_y <= mouse_y < grave_area_y + GHEIGHT * 9):
                                
                                # calculate row (same for both orientations)
                                grave_row = min(8, (mouse_y - grave_area_y) // GHEIGHT)
                                
                                # set hover using LOGICAL grave column
                                try:
                                    grave = board.graves[grave_col][grave_row]
                                    if grave.has_piece() and grave.piece.name in ['raider', 'queen']:
                                        game.set_grave_hover(grave_col, grave_row)
                                except IndexError:
                                    game.set_grave_hover(None, None)
                            else:
                                game.set_grave_hover(None, None)
                        
                    
                        # 2. handle destination hover after grave selection
                        if (clicker.clicked_grv and clicker.clicked_btn == 1 and
                            board._enemy_queen_house_occupied(game.next_player) and 
                            board._queen_isdead(game.next_player)):
                            
                            hover_col, hover_row = game.get_board_position(mouse_x, mouse_y)
                            if hover_col is not None and hover_row is not None:
                                # check valid placement area (white: rows 3-5, black: rows 1-3)
                                valid_rows = (3, 4) if game.next_player == 'white' else (1, 2)
                                if hover_row in valid_rows:
                                    dest_sq = board.squares[hover_col][hover_row]
                                    if dest_sq.is_empty():
                                        game.set_dom_hover(hover_col, hover_row)
                    
                        # 3. handle card deck hovers
                        if mouse_y <= 800:
                            if mouse_x < 100:  # left edge (black deck)
                                hover_col = 0
                                hover_suit = 0
                                hover_rank = mouse_y // CHEIGHT if (mouse_y // CHEIGHT) <= 12 else 12
                                game.set_crd_hover(hover_suit, hover_rank)
                                
                            elif mouse_x >= 900:  # right edge (white deck)
                                hover_col = 9
                                hover_suit = 1
                                if (mouse_y - CEM_HEIGHT - RAMPART_HEIGHT) >= 0:
                                    hover_rank = 12 - ((mouse_y - CEM_HEIGHT - RAMPART_HEIGHT) // CHEIGHT) if \
                                        12 - ((mouse_y - CEM_HEIGHT - RAMPART_HEIGHT) // CHEIGHT) >= 0 else 0
                                else:
                                    hover_rank = 12
                                game.set_crd_hover(hover_suit, hover_rank)
                    
                        # 4. handle button hover
                        if mouse_y > 800:  # button area
                            if 102 <= mouse_x <= 202:
                                game.set_btn_hover(0)
                            elif 205 <= mouse_x <= 288:
                                game.set_btn_hover(1)
                    
                        # 5. handle board square hover
                        hover_col, hover_row = game.get_board_position(mouse_x, mouse_y)
                        if hover_col is not None and hover_row is not None:
                            game.set_sq_hover(hover_col, hover_row)
                    
                            # handle dragging
                            if dragger.dragging:
                                dragger.update_mouse(event.pos)
                                # update display
                                game.show_bg(screen)
                                game.show_last_move(screen)
                                game.show_moves(screen)
                                game.show_pieces(screen)
                                game.show_clicked_cards(screen)
                                game.show_dead(screen)
                                game.show_dead_cards(screen)
                                game.show_hover(screen)
                                dragger.update_blit(screen)
                                self.show_chat()
                    
                       # 6. handle casting hover
                        if casting and not queen_house_raided:
                            # get display coordinates first
                            display_col = (mouse_x - 100) // RWIDTH
                            display_row = mouse_y // RHEIGHT
                            
                            # convert to board coordinates
                            if game.flipped:
                                board_col = COLS - 1 - display_col
                                board_row = ROWS - 1 - display_row
                            else:
                                board_col = display_col
                                board_row = display_row
                            
                            # validate board coordinates
                            if 0 <= board_col < COLS and 0 <= board_row < ROWS:
                                hover_sq = board.squares[board_col][board_row]
                                player = board.players[0] if game.next_player == 'black' else board.players[1]
                                
                                if clicker.clicked_btn == 0:  # strike
                                    move = Cast_move(clicker.clicked_cards, hover_sq, 0)
                                    if board.valid_cast_move(player, move):
                                        game.set_dom_hover(board_col, board_row)
                                        
                                elif clicker.clicked_btn == 1:  # raise
                                    valid_rows = range(3, 5) if game.next_player == 'white' else range(1, 3)
                                    if board_row in valid_rows and hover_sq.is_empty():
                                        move = Cast_move(clicker.clicked_cards, hover_sq, 1)
                                        print("CAST LIST SIZE:", len(player.cast_moves))
                                        if board.valid_cast_move(player, move):
                                            game.set_dom_hover(board_col, board_row)
                    
                        # 7. handle queen placement hover
                        if not casting and queen_house_raided and hover_col is not None and hover_row is not None:
                            # get fresh display coordinates (0-9 cols, 0-5 rows)
                            display_col = (mouse_x - 100) // RWIDTH
                            display_row = mouse_y // RHEIGHT
                            
                            # convert to board coordinates for validation
                            if game.flipped:
                                board_col = COLS - 1 - display_col
                                board_row = ROWS - 1 - display_row
                            else:
                                board_col = display_col
                                board_row = display_row
                            
                            # validate placement rows in BOARD coordinates
                            valid_rows = range(3, 5) if game.next_player == 'white' else range(1, 3)
                            if board_row in valid_rows:
                                hover_sq = board.squares[board_col][board_row]
                                if hover_sq.piece is None:
                                    # pass display coordinates to maintain existing behavior
                                    game.set_dom_hover(board_col, board_row)
                                    game.set_raise_queen_prompt(game.next_player)
                                    

# █▀▄▀█ █▀█ █░█ █▀ █▀▀ █▄▄ █░█ ▀█▀ ▀█▀ █▀█ █▄░█ █░█ █▀█
# █░▀░█ █▄█ █▄█ ▄█ ██▄  █▄█ █▄█ ░█░ ░█░ █▄█ █░▀█ █▄█ █▀▀
                    
                    # click release
                    elif event.type == pygame.MOUSEBUTTONUP:
                        if dragger.dragging:
                            dragger.update_mouse(event.pos)
                            
                            released_row = dragger.mouseY // RHEIGHT
                            released_col = (dragger.mouseX - 100) // RWIDTH
                            
                            # convert to board coordinates if flipped
                            if game.flipped:
                                released_col = COLS - 1 - released_col
                                released_row = ROWS - 1 - released_row
                            
                            # create possible move
                            initial = Square(dragger.initial_col, dragger.initial_row)
                            final = Square(released_col, released_row)
                            move = Move(initial, final)
    
    
                            # valid move?
                            if board.valid_move(dragger.piece, move):
                                captured = board.squares[released_col][released_row].\
                                    has_piece()
                                captured_piece = board.squares[released_col][released_row].piece
                                if captured and captured_piece.name in ['raider', 'queen']:
                                    board._send_to_grave(captured_piece)
                                    
                                if not (released_col == 3 and released_row == 0) and \
                                    not (released_col == 6 and released_row == 5):
                                        
                                    board.move(dragger.piece, move)
                                    if self.game_id:  # only if in a networked game
                                        self.send_move_to_opponent(move)
                                        print(f"DEBUG: Sent move to opponent: {move.initial.col},{move.initial.row} \
                                              -> {move.final.col},{move.final.row}")
                                    # sounds
                                    game.play_sound(captured)
                                    # show methods
                                    game.show_bg(screen)
                                    # show last move
                                    game.show_last_move(screen)
                                    # show pieces
                                    game.show_pieces(screen)
                                    # show clicked cards
                                    game.show_clicked_cards(screen)
                                    # show dead pieces
                                    game.show_dead(screen)
                                    
                                    game.show_dead_cards(screen)
                                    
                                    self.show_chat()
                                    
                                    rival_player = board.players[1] if game.next_player == 'black' else \
                                        board.players[0]
                                        
                                    if self.my_color == 'white' and self.game.white_cast_prompt == 'in-check':
                                        self.game.kill_prompt(self.my_color)
                                    elif self.my_color == 'black' and self.game.black_cast_prompt == 'in-check':
                                        self.game.kill_prompt(self.my_color)
                                        
                                    if board.squares[released_col][released_row].is_enemy_jack_house(game.next_player):
                                        game.set_cast_prompt(game.next_player)
                                        
                                    if board.squares[released_col][released_row].is_enemy_king_house(game.next_player):
                                        if board._opponent_king_on_noncard(game.next_player):
                                            board.king_mated = True
                                            game.set_mated_prompt(game.next_player)
                                        
                                    if board._king_mated(rival_player):
                                        game.set_mated_prompt(rival_player.color)
                                    else:
                                        # next turn/player
                                        game.next_turn()
                                    
                                else:
                                    if board._queen_isdead(game.next_player):
    
                                        queen_house_raided = True
                                        
                                        board.move(dragger.piece, move)
                                        if self.game_id:  # only if in a networked game
                                            self.game.queen_raid_pending = True
                                            self.queen_raid_context = {
                                                'move': move,
                                                'queen_data': None
                                            }
                                            # self.send_move_to_opponent(move)
                                            print(f"DEBUG: Sent move to opponent: {move.initial.col},{move.initial.row} \
                                                  -> {move.final.col},{move.final.row}")
                                        # sounds
                                        game.play_sound(captured)
                                        # show methods
                                        game.show_bg(screen)
                                        # show last move
                                        game.show_last_move(screen)
                                        # show pieces
                                        game.show_pieces(screen)
                                        # show clicked cards
                                        game.show_clicked_cards(screen)
                                        # show dead pieces
                                        game.show_dead(screen)
                                        
                                        game.show_dead_cards(screen)
                                        
                                        self.show_chat()
                                        
                                    else:
                                        
                                        board.move(dragger.piece, move)
                                        if self.game_id:  # only if in networked game
                                            self.send_move_to_opponent(move)
                                            print(f"DEBUG: Sent move to opponent: {move.initial.col},{move.initial.row} \
                                                  -> {move.final.col},{move.final.row}")
                                        # sounds
                                        game.play_sound(captured)
                                        # show methods
                                        game.show_bg(screen)
                                        # show last move
                                        game.show_last_move(screen)
                                        # show pieces
                                        game.show_pieces(screen)
                                        # show clicked cards
                                        game.show_clicked_cards(screen)
                                        # show dead pieces
                                        game.show_dead(screen)
                                        
                                        game.show_dead_cards(screen)
                                        
                                        self.show_chat()
                                        
                                        game.next_turn()
                                        
                        else:
                            mouse_x, mouse_y = event.pos
                            if mouse_y > 800:
                                if clicker.clicked_btn == None:
                                    if 102 <= mouse_x <= 202:
                                        if len(clicker.clicked_cards) > 0:
                                            if clicker.has_2_raider_cards(clicker.clicked_cards) and clicker.has_sum_21(clicker.clicked_cards):
                                                clicker.clicked_btn = 0
                                                game.set_strike_prompt(game.next_player)
                                                
                                                player = board.players[1] if game.next_player == 'white' \
                                                    else board.players[0]
                                                
                                                board.calc_cast_moves(player, None, booL=True)
                                                
                                                game.play_card_sound()
                                                casting = True
                                                game.show_clicked_btns(screen)
                                                
                                    elif 205 <= mouse_x <= 288:
                                        if len(clicker.clicked_cards) > 0:
                                            if clicker.has_board_card() and clicker.has_sum_21(clicker.clicked_cards):
                                                clicker.clicked_btn = 1
                                                
                                                player = board.players[1] if game.next_player == 'white' \
                                                        else board.players[0]
                                                        
                                                if not board._enemy_queen_house_occupied(game.next_player) or \
                                                    not board._queen_isdead(game.next_player) or \
                                                        not clicker.has_2_raider_cards(clicker.clicked_cards):
                                                    
                                                    game.set_raise_prompt(game.next_player)
                                                    board.calc_cast_moves(player, Raider(game.next_player), booL=True)
                                                    print(f"Valid moves: {[(m.cast_type, [c.rank for c in m.cards]) for m in player.cast_moves]}")
                                                                
                                                else:
                                                    game.set_choose_grave_prompt(game.next_player)
                                                    
                                                game.play_card_sound()
                                                casting = True
                                                game.show_clicked_btns(screen)
                                                    
                                else:
                                    if 102 <= mouse_x <= 202:
                                        game.play_card_sound()
                                        clicker.unclick_btn()
                                        clicker.unclick_grv()
                                        game.kill_dom_hover()
                                        game.kill_grave_hover()
                                                
                                    elif 205 <= mouse_x <= 288:
                                        game.play_card_sound()
                                        clicker.unclick_btn()
                                        clicker.unclick_grv()
                                        game.kill_dom_hover()
                                        game.kill_grave_hover()
                                    
                                    
                            else:
                                clicked_col = max(0, min(COLS-1, (mouse_x - 100) // RWIDTH))
                                clicked_row = max(0, min(ROWS-1, mouse_y // RHEIGHT))
                                # clicked_col = (mouse_x - 100) // RWIDTH if mouse_x < 900 else 9
                                # clicked_row = mouse_y // RHEIGHT if mouse_y < 800 else 5
                                if game.flipped:
                                    clicked_col = COLS - 1 - clicked_col
                                    clicked_row = ROWS - 1 - clicked_row
                                
                                print(clicked_col, clicked_row)
                                clicked_sq = board.squares[clicked_col][clicked_row]
                                if not queen_house_raided:
                                    if clicker.clicked_btn == 0:
                                        rAnge = range(1, 3) if self.my_color == 'white' else range(3, 5)
                                        if clicked_sq.has_piece() and clicked_sq.piece.name == \
                                            'raider' and clicked_row in rAnge and \
                                                game.next_player != clicked_sq.piece.color:
                                            
                                            cast_type = clicker.clicked_btn
                                            cards = clicker.clicked_cards.copy()
                                            print("CLICKER:", cards)
                                            
                                            clicker.unclick_btn()
                                            game.cast_cards()
                                            casting = False
                                            
                                            player = board.players[1] if game.next_player == 'white' \
                                                else board.players[0]
                                            final = clicked_sq
                                            move = Cast_move(cards, final, cast_type)
                                            
                                            if board.valid_cast_move(player, move):
                                            
                                                card = clicked_sq.card
                                                piece = Raider(game.next_player)
                                                
                                                board.cast_move(player, piece, card, move)
                                                if self.game_id:
                                                    self.send_move_to_opponent(move, piece, card)
                                                print(f"DEBUG: Sent move to opponent: {move.final.col},\
                                                      {move.final.row}")
                                                game.set_cast_prompt(game.next_player)
                                                game.kill_dom_hover()
                                                game.show_bg(screen)
                                                game.show_last_move(screen)
                                                game.show_pieces(screen)
                                                game.show_clicked_cards(screen)
                                                game.show_dead(screen)
                                                game.show_dead_cards(screen)
                                                
                                                self.show_chat()
                                                
                                                game.lightning.trigger(game.next_player, persist_frames=10)
                                                cast_sound = 'strike'
                                                
                                                rival_player = board.players[1] if game.next_player == 'black' else \
                                                    board.players[0]
                                                    
                                                if self.my_color == 'white' and self.game.white_cast_prompt == 'in-check':
                                                    self.game.kill_prompt(self.my_color)
                                                elif self.my_color == 'black' and self.game.black_cast_prompt == 'in-check':
                                                    self.game.kill_prompt(self.my_color)
                                        
                                                if board._king_mated(rival_player):
                                                    game.set_mated_prompt(rival_player.color)
                                                else:
                                                    # next turn/player
                                                    game.next_turn()
                                            
                                            
                                    elif clicker.clicked_btn == 1:
                                        
                                        if not board._enemy_queen_house_occupied(game.next_player) or \
                                            not clicker.has_2_raider_cards(clicker.clicked_cards) or not \
                                            board._queen_isdead(game.next_player):
                                                    
                                            cast_type = clicker.clicked_btn
                                            cards = clicker.clicked_cards
                                            print("CLICKER:", cards)
                                            for cd in cards:
                                                print("SUIT, RANK:", cd.suit, cd.rank)
                                                    
                                            player = board.players[1] if game.next_player == 'white' \
                                                else board.players[0]
                                            final = clicked_sq
                                            move = Cast_move(cards, final, cast_type)
                                            
                                            if board.valid_cast_move(player, move):
                                            
                                                piece = Raider(game.next_player)
                                                card = clicked_sq.card
                                                
                                                board.cast_move(player, piece, card, move)
                                                if self.game_id:
                                                    self.send_move_to_opponent(move, piece, card)
                                                print(f"DEBUG: Sent move to opponent: {move.final.col},\
                                                      {move.final.row}")
                                                clicker.unclick_btn()
                                                game.cast_cards()
                                                casting = False
                                                
                                                game.set_cast_prompt(game.next_player)
                                                game.kill_dom_hover()
                                                game.show_bg(screen)
                                                game.show_last_move(screen)
                                                game.show_pieces(screen)
                                                game.show_clicked_cards(screen)
                                                game.show_dead(screen)
                                                game.show_dead_cards(screen)
                                                
                                                self.show_chat()
                                                
                                                game.lightning.trigger(game.next_player, persist_frames=10)
                                                cast_sound = 'raise'
                                                
                                                rival_player = board.players[1] if game.next_player == 'black' else \
                                                    board.players[0]
                                                    
                                                if self.my_color == 'white' and self.game.white_cast_prompt == 'in-check':
                                                    self.game.kill_prompt(self.my_color)
                                                elif self.my_color == 'black' and self.game.black_cast_prompt == 'in-check':
                                                    self.game.kill_prompt(self.my_color)
                                                    
                                                if board._king_mated(rival_player):
                                                    
                                                    game.set_mated_prompt(rival_player.color)
                                                else:
                                                    # next turn/player
                                                    game.next_turn()
                                                    
                                        else:
                                            logical_grave_col = 0 if game.next_player == 'black' else 1

                                            # calculate visual positions based on flip
                                            if game.flipped:
                                                visual_left = (logical_grave_col == 1)  # white graves appear left when flipped
                                            else:
                                                visual_left = (logical_grave_col == 0)  # black graves appear left normally
                                            
                                            # check clicks in the correct VISUAL area
                                            if (visual_left and mouse_x < 100) or (not visual_left and mouse_x >= 900):
                                                # calculate clicked row
                                                grave_area_y = (HEIGHT - CEM_HEIGHT + 65) if visual_left else 90
                                                grave_row = (mouse_y - grave_area_y) // GHEIGHT
                                                grave_row = max(0, min(8, grave_row))  # nail to valid range
                                                
                                                # get grave (using LOGICAL column)
                                                clicked_grv = board.graves[logical_grave_col][grave_row]
                                                if clicked_grv.has_piece():
                                                    if not clicker.clicked_grv:
                                                        
                                                        game.play_card_sound()
                                                        clicker.explic_save_grv(clicked_grv)
                                                        clicker.click_grv(clicked_grv)
                                                        
                                                        piece = clicked_grv.piece
                                                        player = board.players[1] if game.next_player == 'white' else \
                                                            board.players[0]
                                                            
                                                        board.calc_cast_moves(player, piece, booL=True)
                                                        
                                                        game.show_chosen_piece(screen)
                                                        
                                                        if piece.name == 'raider':
                                                            game.set_raise_prompt(game.next_player)
                                                        elif piece.name == 'queen':
                                                            game.set_raise_queen_prompt(game.next_player)
                                                        
                                                    elif clicker.clicked_grv == clicked_grv:
                                                        game.play_card_sound()
                                                        clicker.unclick_grv()
                                                        game.show_chosen_piece(screen)
                                                        
                                                        
                                            elif dragger.mouseX >= 100 and dragger.mouseX < 900:
                                                if clicker.clicked_grv:
                                                    cast_type = clicker.clicked_btn
                                                    cards = clicker.clicked_cards
                                                    print("CLICKER:", cards)
                                                    
                                                    player = board.players[1] if game.next_player == 'white' \
                                                        else board.players[0]
                                                    final = clicked_sq
                                                    move = Cast_move(cards, final, cast_type)
                                                    
                                                    if board.valid_cast_move(player, move):
                                                        piece = clicker.clicked_grv.piece
                                                        card = clicked_sq.card
                                                        
                                                        board.cast_move(player, piece, card, move)
                                                        if self.game_id:
                                                            self.send_move_to_opponent(move, piece, card)
                                                        print(f"DEBUG: Sent move to opponent: {move.final.col},\
                                                              {move.final.row}")
                                                        clicker.unclick_btn()
                                                        clicker.unclick_grv()
                                                        game.cast_cards()
                                                        casting = False
                                                        
                                                        game.set_cast_prompt(game.next_player)
                                                        game.kill_dom_hover()
                                                        game.kill_grave_hover()
                                                        game.show_bg(screen)
                                                        game.show_last_move(screen)
                                                        game.show_pieces(screen)
                                                        game.show_clicked_cards(screen)
                                                        game.show_dead(screen)
                                                        game.show_dead_cards(screen)
                                                        self.show_chat()
                                                        
                                                        game.lightning.trigger(game.next_player, persist_frames=10)
                                                        cast_sound = 'raise'
                                                        
                                                        rival_player = board.players[1] if game.next_player == 'black' else \
                                                            board.players[0]
                                                            
                                                        if self.my_color == 'white' and self.game.white_cast_prompt == 'in-check':
                                                            self.game.kill_prompt(self.my_color)
                                                        elif self.my_color == 'black' and self.game.black_cast_prompt == 'in-check':
                                                            self.game.kill_prompt(self.my_color)
                                                            
                                                        if board._king_mated(rival_player):
                                                            
                                                            game.set_mated_prompt(rival_player.color)
                                                        else:
                                                            # next turn/player
                                                            game.next_turn()
                                                            
                                                            
                                else:
                                    if game.next_player == 'white' and (clicked_row >= 3 and \
                                            clicked_row <= 5):
                                        if clicked_sq.piece == None:
                                            
                                            board._raise_queen(clicked_col, clicked_row, \
                                                game.next_player, clicked_sq.card)
                                            
                                            queen_house_raided = False
                                            
                                            
                                            final = clicked_sq
                                            cards = clicker.clicked_cards
                                            move = Cast_move(cards, final, 1)
                                            
                                            player = board.players[1]
                                            piece = board.squares[clicked_col][clicked_row].piece
                                            card = clicked_sq.card
                                            
                                            board.cast_move(player, piece, card, move)
                                            if self.game_id:
                                                self.queen_raid_context['queen_data'] = \
                                                    {'col': clicked_sq.col, 'row': clicked_sq.row}
                                                self.send_move_to_opponent(self.queen_raid_context, piece, card)
                                            print(f"DEBUG: Sent move to opponent: {move.final.col},\
                                                  {move.final.row}")
                                            game.set_cast_prompt(game.next_player)
                                            game.kill_dom_hover()
                                            game.show_bg(screen)
                                            game.show_last_move(screen)
                                            game.show_pieces(screen)
                                            game.show_clicked_cards(screen)
                                            game.show_dead(screen)
                                            game.show_dead_cards(screen)
                                            self.show_chat()
                                            
                                            game.lightning.trigger(game.next_player, persist_frames=10)
                                            cast_sound = 'raise'
                                            
                                            rival_player = board.players[1] if game.next_player == 'black' else \
                                                board.players[0]
                                                
                                            if self.my_color == 'white' and self.game.white_cast_prompt == 'in-check':
                                                self.game.kill_prompt(self.my_color)
                                            elif self.my_color == 'black' and self.game.black_cast_prompt == 'in-check':
                                                self.game.kill_prompt(self.my_color)
                                                
                                            if board._king_mated(rival_player):
                                                
                                                game.set_mated_prompt(rival_player.color)
                                            else:
                                                # next turn/player
                                                game.next_turn()
                                            
                                    elif game.next_player == 'black' and (clicked_row <= 3 and \
                                        clicked_row >= 1):
                                        if clicked_sq.piece == None:
                                            
                                            board._raise_queen(clicked_col, clicked_row, \
                                                game.next_player, clicked_sq.card)
                                            
                                            queen_house_raided = False
                                            
                                            final = clicked_sq
                                            cards = clicker.clicked_cards
                                            move = Cast_move(cards, final, 1)
                                            
                                            player = board.players[0]
                                            piece = board.squares[clicked_col][clicked_row].piece
                                            card = clicked_sq.card
                                            
                                            board.cast_move(player, piece, card, move)
                                            if self.game_id:
                                                self.queen_raid_context['queen_data'] = \
                                                    {'col': clicked_sq.col, 'row': clicked_sq.row}
                                                self.send_move_to_opponent(self.queen_raid_context, piece, card)
                                            print(f"DEBUG: Sent move to opponent: {move.final.col},\
                                                  {move.final.row}")
                                            game.set_cast_prompt(game.next_player)
                                            game.kill_dom_hover()
                                            game.show_bg(screen)
                                            game.show_last_move(screen)
                                            game.show_pieces(screen)
                                            game.show_clicked_cards(screen)
                                            game.show_dead(screen)
                                            game.show_dead_cards(screen)   
                                            self.show_chat()
                                            
                                            game.lightning.trigger(game.next_player, persist_frames=10)
                                            cast_sound = 'raise'
                                            
                                            rival_player = board.players[1] if game.next_player == 'black' else \
                                                board.players[0]
                                                
                                            if self.my_color == 'white' and self.game.white_cast_prompt == 'in-check':
                                                self.game.kill_prompt(self.my_color)
                                            elif self.my_color == 'black' and self.game.black_cast_prompt == 'in-check':
                                                self.game.kill_prompt(self.my_color)
                                                
                                            if board._king_mated(rival_player):
                                                
                                                game.set_mated_prompt(rival_player.color)
                                            else:
                                                # next turn/player
                                                game.next_turn()
                        
                        
                        dragger.undrag_piece()
                        
                
                    # key press
                    elif event.type == pygame.KEYDOWN:
                        # chat functions
                        if self.chat_active:
                            if event.key == pygame.K_RETURN:
                                if self.chat_text.strip():
                                    self.fb.send_chat_message(self.game_id, self.my_color, self.chat_text)
                                    self.chat_messages.append(f"You: {self.chat_text}")
                                    self.chat_text = ""
                                self.chat_active = False
                            elif event.key == pygame.K_BACKSPACE:
                                self.chat_text = self.chat_text[:-1]
                            elif event.key == pygame.K_c:  # allow 'c' to be typed in chat
                                self.chat_text += 'c'
                            elif len(self.chat_text) < self.max_chars:
                                self.chat_text += event.unicode
                        else:
                            # change theme
                            if event.key == pygame.K_t:
                                game.change_theme()
                                game.change_emblem()
                                game.change_dead_card()
                                
                            # change piece styles
                            elif event.key == pygame.K_y:
                                game.board.change_all_piece_textures()
                                
                            # restart game
                            elif event.key == pygame.K_r:
                                if not self.rematch_requested and not self.opponent_rematch_requested:
                                    # first press - request rematch
                                    self.request_rematch()
                                elif self.opponent_rematch_requested and not self.rematch_requested:
                                    # accepting opponent's request
                                    self.rematch_requested = True
                                    db.reference(f'games/{self.game_id}/rematch/{self.my_color}').set(True)
                                    self.status_message = "Rematch accepted - waiting for game reset"
                                    # immediate check in case both players accepted simultaneously
                                    self.check_and_execute_rematch() 
                            
                            # flip board key
                            if event.key == pygame.K_f:
                                game.flip_board()
                            
                            # start network keys
                            if event.key == pygame.K_h:
                                self._start_host_ui()
                            elif event.key == pygame.K_j:
                                print("J key pressed - activating input")
                                self.active_input = True
                                self.status_message = "Enter 4-digit PIN:"
                                self.input_text = ""  # clear previous input
                            elif self.active_input:
                                if event.key == pygame.K_RETURN:
                                    self._handle_join_ui()
                                elif event.key == pygame.K_BACKSPACE:
                                    self.input_text = self.input_text[:-1]
                                else:
                                    self.input_text += event.unicode
                                
                            # chat toggle
                            elif event.key == pygame.K_c:  # toggle chat
                                self.chat_active = True
                    
                    # quit application
                    elif event.type == pygame.QUIT:
                        print("🛑 QUIT EVENT RECEIVED - STARTING CLEANUP")
                        try:
                            self.cleanup()
                        except Exception as e:
                            print(f"💥 CLEANUP CRASHED: {e}")
                            import traceback
                            traceback.print_exc()
                        finally:
                            print("🏁 CLEANUP COMPLETE - QUITTING PYGAME")
                            pygame.quit()
                            sys.exit()
                       
                     
                else:
                    opponent = self.game.board.players[0] if self.my_color == 'white' \
                        else self.game.board.players[1]
                    self.game.set_mated_prompt(opponent.color)
                    game.show_cast_prompt(screen, self.my_color)
                    
                    # key press
                    if event.type == pygame.KEYDOWN:
                    
                        # change theme
                        if event.key == pygame.K_t:
                            game.change_theme()
                            game.change_emblem()
                            game.change_dead_card()
                        
                        # change piece styles
                        elif event.key == pygame.K_y:
                            game.board.change_all_piece_textures()
                            
                        # restart game
                        if event.key == pygame.K_r:
                            if not self.rematch_requested and not self.opponent_rematch_requested:
                                # first press - request rematch
                                self.request_rematch()
                            elif self.opponent_rematch_requested and not self.rematch_requested:
                                # accepting opponent's request
                                self.rematch_requested = True
                                db.reference(f'games/{self.game_id}/rematch/{self.my_color}').set(True)
                                self.status_message = "Rematch accepted - waiting for game reset"
                                # immediate check in case both players accepted simultaneously
                                self.check_and_execute_rematch() 
                    
                    # quit application
                    elif event.type == pygame.QUIT:
                        print("QUIT EVENT RECEIVED - STARTING CLEANUP")
                        try:
                            self.cleanup()
                        except Exception as e:
                            print(f"💥 CLEANUP CRASHED: {e}")
                            import traceback
                            traceback.print_exc()
                        finally:
                            print("🏁 CLEANUP COMPLETE - QUITTING PYGAME")
                            pygame.quit()
                            sys.exit()
            
            self.ui_font = pygame.font.SysFont('Arial', 24, bold=True)
            status_surface = self.ui_font.render(self.status_message, True, (0, 0, 139))
            self.screen.blit(status_surface, (150, HEIGHT - 50))
            
            # input box
            if self.active_input:
                input_surface = self.ui_font.render(
                    f"Enter PIN: {self.input_text}",
                    True, (0, 0, 139)  # bright blue
                )
                self.screen.blit(input_surface, (150, HEIGHT - 25))  # positioned below status
                
            pygame.display.update()


if __name__ == "__main__":
    # initialize game
    main = Main()
    main.mainloop()
    

# ▀█▀ █▀▀ █▀█ █▀▄▀█ █ █▄░█ ▄▀█ █░░   █▀▄▀█ █▀█ █▀▄ █▀▀
# ░█░ ██▄ █▀▄ █░▀░█ █ █░▀█ █▀█ █▄▄    █░▀░█ █▄█ █▄▀ ██▄
    
    # print(main.game.board.get_serialized_state())
    
    # # TEMPORARY NETWORK TEST (will be replaced with proper UI later)
    # print("\n" + "="*40)
    # print("MULTIPLAYER TEST MODE")
    # print("="*40)
    
    # choice = input("Host new game (1) or join existing (2)? ").strip()
    
    # if choice == "1":
    #     # HOST PATH - Create game first, then show ID
    #     game_id = main.fb.create_game(main.game.board.get_serialized_state())
    #     print(f"\n✅ Game created! Share this ID with your opponent:\n\n\t{game_id}\n")
    #     print("Waiting for opponent...")
    #     main.game_id = game_id
    #     main.my_color = 'white'
    # elif choice == "2":
    #     # JOIN PATH
    #     game_id = input("Enter game ID to join: ").strip()
    #     main.game_id = game_id
    #     main.my_color = 'black'
    #     print("Connecting to game...")
    # else:
    #     print("Invalid choice - starting local game")
    
    # # Start networking and launch game
    # main.start_networking(game_id)  # Pass the game_id here
    # main.mainloop()