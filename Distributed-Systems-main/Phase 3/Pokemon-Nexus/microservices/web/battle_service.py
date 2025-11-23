import os
import random
from math import ceil
from datetime import datetime
from bson.objectid import ObjectId
from flask import request, jsonify, session
from flask_socketio import SocketIO, emit, join_room, leave_room
from web.db_utils import create_app, get_current_user_email
import redis

# Use a non-standard port 5001 for SocketIO service (as per typical deployment)
app, mongo = create_app(__name__)

# --- SocketIO Setup ---
# Retrieve Redis URL from environment variables via the db_utils shared setup
REDIS_URL = os.environ.get('SESSION_REDIS', 'redis://localhost:6379/1') 
# Initialize SocketIO with message queue for multiple workers
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    manage_session=False,
    message_queue=REDIS_URL,
    async_mode='eventlet',
    logger=True,            # Enable python-socketio logging
    engineio_logger=True    # Enable engineio (handshake/transport) logging
)

# --- Global State for Battle Service (Queue) ---
BATTLE_QUEUE = []
BATTLES_IN_PROGRESS = {} 
XP_PER_WIN = 100
LEVEL_UP_XP = 100

# --- SOCKETIO EVENT HANDLERS ---

@socketio.on('connect')
def handle_connect():
    """Logs the client connecting and associates the session ID (sid) with the current user."""
    user_email = get_current_user_email()
    app.logger.info(f"Client Connected: SID={request.sid}, User={user_email}")
    if user_email:
        app.logger.info(f"User {user_email} connected with SID={request.sid}")
    else:
        app.logger.warning(f"Unauthenticated connection with SID={request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    """Removes player from the queue if they disconnect."""
    global BATTLE_QUEUE
    player_name = get_current_user_email()
    if player_name:
        # Remove from queue if present
        BATTLE_QUEUE = [player for player in BATTLE_QUEUE if player['sid'] != request.sid]
        app.logger.info(f"Client Disconnected: {player_name} removed from queue.")

@socketio.on('join_queue')
def handle_join_queue():
    """Handles queue entry and immediate matchmaking attempt."""
    global BATTLE_QUEUE, BATTLES_IN_PROGRESS
    player_name = get_current_user_email()
    player_sid = request.sid

    # Check if already in queue
    if any(player['sid'] == player_sid for player in BATTLE_QUEUE):
        return
    
    # Enter queue
    BATTLE_QUEUE.append({'name': player_name, 'sid': player_sid})

    # Attempt Matchmaking (if at least 2 players are in the queue)
    if len(BATTLE_QUEUE) >= 2:
        
        # Pop the two players off the queue
        player1 = BATTLE_QUEUE.pop(0) 
        player2 = BATTLE_QUEUE.pop(0)
            
        # --- Match Found & Simulation ---
        
        # Select Pokémon, Simulate Battle, Update XP/Level (using existing logic)
        player1_mon_docs = list(mongo.db.pokemon.find({"player": player1['name'], "locked": False}))
        player2_mon_docs = list(mongo.db.pokemon.find({"player": player2['name'], "locked": False}))
        
        if not player1_mon_docs or not player2_mon_docs:
             # Send error event back to client
             emit('queue_error', {'message': "Not enough available Pokemon to battle!"}, room=player1['sid'])
             return

        p1_mon = random.choice(player1_mon_docs)
        p2_mon = random.choice(player2_mon_docs)
        
        is_p1_winner = simulate_battle(p1_mon, p2_mon)
        
        p1_xp, p1_level_up = update_user_xp(player1['name'], is_p1_winner)
        p2_xp, p2_level_up = update_user_xp(player2['name'], not is_p1_winner)

        result_data = {
            "winner": player1['name'] if is_p1_winner else player2['name']
        }
        
        # --- Create a result object tailored for each player ---
        
        for player in [player1, player2]:
            is_winner = player['name'] == result_data["winner"]
            
            # 1. Create the final result payload
            final_result_payload = {
                "status": "complete",
                "message": f"Battle finished! {'WIN!' if is_winner else 'LOSS!'}",
                "result": {
                    "player_mon": p1_mon['name'] if player['name'] == player1['name'] else p2_mon['name'],
                    "opponent_mon": p2_mon['name'] if player['name'] == player1['name'] else p1_mon['name'],
                    "player_xp_gain": p1_xp if player['name'] == player1['name'] else p2_xp,
                    "player_level_up": p1_level_up if player['name'] == player1['name'] else p2_level_up,
                    "result_message": "WIN!" if is_winner else "LOSS!"
                }
            }

            # 2. Emit the FULL result data directly to the client
            socketio.emit('battle_result', final_result_payload, room=player['sid'])
            app.logger.info(f"Match found! Sent FULL result to {player['name']} (SID: {player['sid']})")
        
    else:
        # No match found, notify client of position
        position = BATTLE_QUEUE.index({'name': player_name, 'sid': player_sid}) + 1
        emit('queue_update', {'message': "Searching...", 'position': position}, room=player_sid)

# --- Helper Functions ---
def update_user_xp(user_name, is_winner):
    """Adds XP to the user and handles leveling up."""
    user = mongo.db.players.find_one({"email": user_name})
    if not user:
        return

    xp_gained = XP_PER_WIN if is_winner else 10 # Small XP gain for participating
    
    new_xp = user['xp'] + xp_gained
    new_level = user['level']
    level_increase = 0
    
    # Simple Level Up Logic
    while new_xp >= LEVEL_UP_XP:
        new_xp -= LEVEL_UP_XP
        new_level += 1
        level_increase += 1

    update_fields = {
        '$set': {
            'level': new_level, 
            'xp': new_xp,
        },
        '$inc': {
            'wins': 1 if is_winner else 0,
            'losses': 1 if not is_winner else 0
        }
    }
    mongo.db.players.update_one({"email": user_name}, update_fields)
    
    return xp_gained, level_increase

def simulate_battle(player_mon, opponent_mon):
    """Simulates the battle based on ATK/DEF, returns true if player_mon wins."""
    # Simplified simulation: higher HP Pokémon wins if ATK/DEF difference is small.
    # We still use the existing logic for damage calculation.
    
    p1 = {"doc": player_mon, "hp": player_mon['hp']}
    p2 = {"doc": opponent_mon, "hp": opponent_mon['hp']}
    
    p1_atk = p1['doc']['atk']
    p2_atk = p2['doc']['atk']

    # Determine who attacks first (higher ATK stat)
    attacker = p1 if p1_atk >= p2_atk else p2
    defender = p2 if p1_atk >= p2_atk else p1
    
    # Battle loop (max 10 rounds to prevent infinite loop just in case)
    for _ in range(20):
        if p1['hp'] <= 0 or p2['hp'] <= 0:
            break
            
        defender_def = defender['doc']['def']
        damage = max(1, attacker['doc']['atk'] - ceil(defender_def / 2))
        defender['hp'] -= damage
        
        # Swap roles
        attacker, defender = defender, attacker

    return p1['hp'] > 0 # Returns True if player's mon (p1) wins


if __name__ == '__main__':
    # Run Flask-SocketIO with eventlet or gevent worker, or use socketio.run
    socketio.run(app, host='0.0.0.0', port=5001)
