#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Firebase Manager for Rampart Chess Game
Handles all Firebase realtime database operations
"""


#███████╗██╗██████╗░███████╗██████╗░░█████╗░░██████╗███████╗
#██╔════╝██║██╔══██╗██╔════╝██╔══██╗██╔══██╗██╔════╝██╔════╝
#█████╗░░██║██████╔╝█████╗░░██████╦╝███████║╚█████╗░█████╗░░
#██╔══╝░░██║██╔══██╗██╔══╝░░██╔══██╗██╔══██║░╚═══██╗██╔══╝░░
#██║░░░░░██║██║░░██║███████╗██████╦╝██║░░██║██████╔╝███████╗
#╚═╝░░░░░╚═╝╚═╝░░╚═╝╚══════╝╚═════╝░╚═╝░░╚═╝╚═════╝░╚══════╝

#███╗░░░███╗░█████╗░███╗░░██╗░█████╗░░██████╗░███████╗██████╗░
#████╗░████║██╔══██╗████╗░██║██╔══██╗██╔════╝░██╔════╝██╔══██╗
#██╔████╔██║███████║██╔██╗██║███████║██║░░██╗░█████╗░░██████╔╝
#██║╚██╔╝██║██╔══██║██║╚████║██╔══██║██║░░╚██╗██╔══╝░░██╔══██╗
#██║░╚═╝░██║██║░░██║██║░╚███║██║░░██║╚██████╔╝███████╗██║░░██║
#╚═╝░░░░░╚═╝╚═╝░░╚═╝╚═╝░░╚══╝╚═╝░░╚═╝░╚═════╝░╚══════╝╚═╝░░╚═╝

import os
from pathlib import Path
import time

import firebase_admin
from firebase_admin import credentials, db
from typing import Callable, Optional, TYPE_CHECKING

# get the directory where main.py is located
project_root = Path(__file__).parent.parent  # Goes up from services/ to project root
cred_path = project_root / 'serviceAccountKey.json'

# verify the path
if not cred_path.exists():
    raise FileNotFoundError(f"Firebase key not found at: {cred_path}")

cred = credentials.Certificate(str(cred_path))

# for type hints without circular imports
if TYPE_CHECKING:
    from move import Move

class FirebaseManager:
    _initialized = False
    
    def __init__(self):
        self.active_listeners = {}
        # initialize Firebase app only once
        if not firebase_admin._apps:
            try:
                # path to service account key
                cred_path = os.path.join(os.path.dirname(__file__), '../serviceAccountKey.json')
                cred = credentials.Certificate(cred_path)
                
                # initialize with database URL
                firebase_admin.initialize_app(cred, {
                    'databaseURL': 'https://rampart-bea61-default-rtdb.firebaseio.com',
                    'projectId': 'rampart-bea61'
                })
                
            except Exception as e:
                raise RuntimeError(f"Firebase initialization failed: {str(e)}")
                
        try:
            app = firebase_admin.get_app()
            print(f"Initialized app name: {app.name}")
            print(f"Database URL: {app.project_id}")  # alternative way to check
            print(f"Full options: {app._options}")  # internal view of options
        except ValueError as e:
            print(f"No Firebase app initialized: {e}")

    def create_game(self, initial_board_state: dict) -> str:
        # create new game with initial state
        try:
            game_ref = db.reference('games')
            new_game = game_ref.push({
                'board_state': initial_board_state,
                'status': 'waiting',
                'created_at': {'.sv': 'timestamp'}
            })
            return new_game.key
        except Exception as e:
            print(f"Error creating game: {e}")
            raise
            
    def game_exists(self, game_id: str) -> bool:
        # check if a game exists in Firebase
        try:
            game_ref = db.reference(f'games/{game_id}')
            return game_ref.get() is not None
        except Exception as e:
            print(f"Error checking game: {e}")
            return False

    def send_move(self, game_id: str, move_data: dict) -> None:
        # simplified version that just sends raw move data
        try:
            db.reference(f'games/{game_id}/moves').push(move_data)
            print(f"DEBUG: Move sent to Firebase: {move_data}")
        except Exception as e:
            print(f"Error sending move: {e}")

    def listen_for_moves(self, game_id: str, callback: Callable[[dict], None]) -> None:
        print(f"DEBUG: Setting up listener for game {game_id}")
        
        def _handle_event(event):
            if event.data:  # only process if there's data
                print(f"DEBUG: Received move data: {event.data}")
                callback(event.data)
        
        try:
            moves_ref = db.reference(f'games/{game_id}/moves')
            print("DEBUG: Listener ACTIVE")
            # store the listener to allow proper cleanup
            self.active_listeners[game_id] = moves_ref.listen(_handle_event)
        except Exception as e:
            print(f"FIREBASE LISTENER CRASHED: {e}")
            raise

    def cleanup(self):
        print("🔥 FIREBASE: Initiating cleanup")
        start_time = time.time()
        
        # get a snapshot of active listeners
        listeners = list(self.active_listeners.items())
        self.active_listeners.clear()
        
        # close all with timeout protection
        for game_id, listener in listeners:
            try:
                print(f"🔥 FIREBASE: Closing {game_id}")
                listener.close()
            except Exception as e:
                print(f"🔥 FIREBASE ERROR on {game_id}: {e}")
        
        print(f"⏱️ FIREBASE: Cleanup completed in {time.time()-start_time:.2f}s")
        
    # emergency cleanup
    def emergency_cleanup():
        print("🚨 EMERGENCY CLEANUP")
        try:
            # delete all game data
            db.reference('games').delete()
            # delete all pins
            db.reference('pin_mappings').delete()
            print("🚨 All Firebase data wiped")
        except Exception as e:
            print(f"🚨 Emergency failed: {e}")

# ╭━━━┳╮╱╭┳━━━┳━━━━╮
# ┃╭━╮┃┃╱┃┃╭━╮┃╭╮╭╮┃
# ┃┃╱╰┫╰━╯┃┃╱┃┣╯┃┃╰╯
# ┃┃╱╭┫╭━╮┃╰━╯┃╱┃┃
# ┃╰━╯┃┃╱┃┃╭━╮┃╱┃┃
# ╰━━━┻╯╱╰┻╯╱╰╯╱╰╯
        
    def send_chat_message(self, game_id, player, text):
        try:
            db.reference(f'games/{game_id}/chat').push({
                'player': player,
                'text': text,
                'timestamp': {'.sv': 'timestamp'}
            })
        except Exception as e:
            print(f"Chat send error: {e}")
                
                
