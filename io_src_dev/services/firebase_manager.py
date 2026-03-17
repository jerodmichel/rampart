import pyrebase
import time
from typing import Callable

class FirebaseManager:
    def __init__(self):
        self.active_listeners = {}
        
        # actual web config
        firebaseConfig = {
            "apiKey": "AIzaSyC9k3NRCA4VhzPOof8fcpVGYdSZ582vsKo",
            "authDomain": "rampart-bea61.firebaseapp.com",
            "databaseURL": "https://rampart-bea61-default-rtdb.firebaseio.com",
            "projectId": "rampart-bea61",
            "storageBucket": "rampart-bea61.firebasestorage.app",
            "messagingSenderId": "69040292066",
            "appId": "1:69040292066:web:3ad41d9e4ff57bfe7a9ebb",
            "measurementId": "G-RF3TTQYXV8"
        }
        
        # initialize client-side firebase
        self.firebase = pyrebase.initialize_app(firebaseConfig)
        self.auth = self.firebase.auth()
        self.db = self.firebase.database()
        
        # automatically sign the player in anonymously
        print("DEBUG: Authenticating player anonymously...")
        self.user = self.auth.sign_in_anonymous()
        print(f"DEBUG: Authenticated with UID: {self.user['localId']}")
        
    def create_game(self, initial_board_state: dict) -> str:
        try:
            new_game = self.db.child('games').push({
                'board_state': initial_board_state,
                'status': 'waiting',
                'created_at': int(time.time() * 1000)
            }, self.user['idToken'])
            return new_game['name'] 
        except Exception as e:
            print(f"Error creating game: {e}")
            raise
            
    def game_exists(self, game_id: str) -> bool:
        try:
            game = self.db.child('games').child(game_id).get(self.user['idToken']).val()
            return game is not None
        except Exception as e:
            print(f"Error checking game: {e}")
            return False
            
    def send_move(self, game_id: str, move_data: dict) -> None:
        try:
            self.db.child('games').child(game_id).child('moves').push(move_data, self.user['idToken'])
            print(f"DEBUG: Move sent to Firebase: {move_data['type']}")
        except Exception as e:
            print(f"Error sending move: {e}")
            
    def send_chat_message(self, game_id, player, text):
        try:
            self.db.child('games').child(game_id).child('chat').push({
                'player': player,
                'text': text,
                'timestamp': int(time.time() * 1000)
            }, self.user['idToken'])
        except Exception as e:
            print(f"Chat send error: {e}")
            
    def listen_for_moves(self, game_id: str, callback: Callable[[dict], None]) -> None:
        class DummyEvent:
            def __init__(self, message):
                self.data = message['data']
                self.path = message['path']
        
        def _handle_event(message):
            if message.get('data'):  
                callback(DummyEvent(message))
        
        try:
            stream = self.db.child('games').child(game_id).child('moves').stream(_handle_event, token=self.user['idToken'])
            self.active_listeners[f"{game_id}_moves"] = stream
        except Exception as e:
            print(f"FIREBASE LISTENER CRASHED: {e}")
            raise
            
    def update_heartbeat(self, game_id, color):
        try:
            # Matches main.py path 'heartbeats'
            self.db.child('games').child(game_id).child('heartbeats').update({
                color: int(time.time() * 1000)
            }, self.user['idToken'])
        except Exception as e:
            print(f"Heartbeat error: {e}")

    def update_rematch_status(self, game_id, color, status, initiator=None):
        try:
            data = {color: status}
            if initiator:
                data['initiator'] = initiator
            self.db.child('games').child(game_id).child('rematch').update(data, self.user['idToken'])
        except Exception as e:
            print(f"Rematch update error: {e}")

    def cleanup(self):
        print("🔥 FIREBASE: Initiating cleanup")
        start_time = time.time()
        listeners = list(self.active_listeners.items())
        self.active_listeners.clear()
        for name, listener in listeners:
            try:
                listener.close()
            except:
                pass
        print(f"⏱️ FIREBASE: Cleanup completed in {time.time()-start_time:.2f}s")