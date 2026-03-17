#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Sep 25 15:46:27 2025

@author: stereo
"""
import time
# from typing import Dict, List, Tuple, Optional, Any


class ComprehensiveCastCache:
    def __init__(self):
        self.cache = {}  # state_hash -> { 'moves': [], 'timestamp': time }
        self.last_state_hashes = {}  # player_color -> last_state_hash
        
    def store_moves(self, player_color, state_hash, moves):
        """Store calculated moves in cache"""
        self.cache[state_hash] = {
            'moves': moves.copy(),  # Store a copy to avoid modification
            'timestamp': time.time()
        }
        self.last_state_hashes[player_color] = state_hash
    
    def get_cached_moves(self, player_color, current_state_hash):
        if player_color in self.last_state_hashes:
            last_hash = self.last_state_hashes[player_color]
            
            # If state unchanged, return full cache
            if current_state_hash == last_hash and current_state_hash in self.cache:
                return self.cache[current_state_hash]['moves']
            
            # If similar state, try incremental update
            if self._states_are_similar(last_hash, current_state_hash):
                return self._incremental_update(last_hash, current_state_hash, player_color)
        
        # No usable cache
        return None
    
    def _states_are_similar(self, old_hash, new_hash):
        """Check if states are similar enough for incremental update"""
        # Compare specific components that affect cast moves
        if old_hash not in self.cache or new_hash not in self.cache:
            return False
    
        # For now, just use timestamp-based similarity
        # You can enhance this later with actual state comparison
        old_time = self.cache[old_hash]['timestamp']
        new_time = self.cache[new_hash]['timestamp']
        
        # Consider states similar if they're within a short time window
        return abs(new_time - old_time) < 2.0  # Allow 1-2 piece changes
    
    def _incremental_update(self, old_hash, new_hash, player_color):
        """Update cached moves incrementally"""
        old_moves = self.cache[old_hash]['moves']
        old_state = self.cache[old_hash]['fingerprint']
        new_state = self._decode_state_hash(new_hash)
        
        # Identify which moves are still valid
        valid_moves = []
        for move in old_moves:
            if self._is_cast_move_still_valid(move, old_state, new_state, player_color):
                valid_moves.append(move)
        
        # Calculate only new moves that became possible
        new_moves = self._calculate_new_cast_moves(old_state, new_state, player_color)
        
        return valid_moves + new_moves
    
    def _is_cast_move_still_valid(self, move, old_state, new_state, player_color):
        """Check if a cached cast move is still valid given state changes"""
        # 1. Check if required cards are still available
        if not self._cards_still_available(move.cards, old_state, new_state, player_color):
            return False
        
        # 2. Check if target square is still valid
        if move.cast_type == 1:  # Raise move - square must be empty
            target_pos = (move.final.col, move.final.row)
            if not self._square_still_empty(target_pos, old_state, new_state):
                return False
        
        # 3. Check if graveyard piece is still available (for raise moves)
        if hasattr(move, 'requires_grave_piece') and move.requires_grave_piece:
            if not self._grave_piece_still_available(move, old_state, new_state, player_color):
                return False
        
        return True
    
class CardComboCache:
    def __init__(self):
        self.combo_cache = {}  # (available_cards_hash) -> list of valid 21-sum combos
    
    def get_valid_combinations(self, available_cards, target_sum=21):
        cards_hash = self._hash_available_cards(available_cards)
        
        if cards_hash in self.combo_cache:
            return self.combo_cache[cards_hash]
        
        # Calculate and cache
        combinations = self._find_21_combinations(available_cards, target_sum)
        self.combo_cache[cards_hash] = combinations
        return combinations
    
    def _hash_available_cards(self, available_cards):
        """Create hash based on available cards"""
        card_tuples = []
        for card in available_cards:
            if hasattr(card, 'suit') and hasattr(card, 'rank'):
                card_tuples.append((card.suit, card.rank, card.is_cast()))
            else:
                # Handle board squares with cards
                card_tuples.append((getattr(card, 'suit', -1), 
                                  getattr(card, 'rank', -1), 
                                  getattr(card, 'is_cast', False)()))
        return hash(tuple(sorted(card_tuples)))
    
