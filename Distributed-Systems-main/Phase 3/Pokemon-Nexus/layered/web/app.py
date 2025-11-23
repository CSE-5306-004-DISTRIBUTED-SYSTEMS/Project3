# Import for converting string IDs back to ObjectId
from bson.objectid import ObjectId 
from flask import Flask, request, render_template, redirect, url_for, flash, jsonify, session
from flask_cors import CORS
from flask_pymongo import PyMongo
from flask_socketio import SocketIO, emit
from flask_session import Session 
from math import ceil 
from datetime import datetime
import random
import os
import redis 

# --- SETUP AND CONFIGURATION ---

app = Flask(__name__)
# Enable CORS for the client running on a different port/origin
# Ensure CORS is configured for SocketIO as well
CORS(app, resources={r"/*": {"origins": "*"}}) 

# --- Configuration ---
# Load configuration from environment variables defined in docker-compose.yaml
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default_secret') 
app.config['SESSION_TYPE'] = os.environ.get('SESSION_TYPE', 'filesystem') # Using os.environ.get for reliability
SESSION_REDIS_URL = os.environ.get('SESSION_REDIS') # Temporarily store the URL string

app.config["MONGO_URI"] = os.environ.get("MONGO_URI", "mongodb://localhost:27017/fallback_db")

# --- Convert URL string to Redis object ---
if app.config['SESSION_TYPE'] == 'redis' and SESSION_REDIS_URL:
    # Use the redis.from_url() method to create a client instance from the connection string
    try:
        app.config['SESSION_REDIS'] = redis.from_url(SESSION_REDIS_URL)
        app.logger.info("Redis client initialized successfully from URL.")
    except Exception as e:
        app.logger.info(f"ERROR: Could not initialize Redis client from URL: {e}")
        # If it fails, Flask-Session will fall back, but we want the error to be visible.

# --- Initialize Flask-Session ---
# This step must happen before you use the session object.
server_session = Session(app)

# Initialize SocketIO with message queue for multiple workers
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    manage_session=False,
    message_queue='redis://redis:6379/0',
    async_mode='eventlet',
    logger=True,            # Enable python-socketio logging
    engineio_logger=True    # Enable engineio (handshake/transport) logging
)

# Initialize Flask-PyMongo
mongo = PyMongo(app)

# --- Global Battle Queue Management (Simplified In-Memory) ---
BATTLE_QUEUE = [] 
BATTLES_IN_PROGRESS = {} 
XP_PER_WIN = 100
LEVEL_UP_XP = 100

# --- ROUTES FOR USER INTERACTION ---

@app.route('/', methods=['GET'])
def index():
    """Renders the main page with login/register forms."""
    return render_template('login.html')

@app.route('/register', methods=['POST'])
def register():
    """Handles the form submission from the Registration form and stores data in MongoDB."""
    
    email = request.form.get('email')
    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')

    if password != confirm_password:
        flash('Passwords do not match.', 'error')
        return redirect(url_for('index'))

    # Check if user already exists (Read operation)
    existing_user = mongo.db.players.find_one({'email': email})
    if existing_user:
        flash('Email already registered. Please log in.', 'error')
        return redirect(url_for('index'))

    # Store user data (Create operation)
    try:
        # In a real app, use generate_password_hash for security:
        # hashed_password = generate_password_hash(password, method='sha256')
        
        user_data = {
            "email": email,
            "password": password, # ⚠️ DANGER: Replace with hashed password in production
            "level": 1,
            "xp": 0,
            "wins": 0,
            "losses": 0,
            "created_at": datetime.now()
        }
        
        # Insert the new document into the 'players' collection
        mongo.db.players.insert_one(user_data)
        
        flash(f'Account created for {email}! Please log in.', 'success')
        
    except Exception as e:
        flash(f'An error occurred during registration: {e}', 'error')

    return redirect(url_for('index'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handles the form submission from the Login form and retrieves data from MongoDB."""
    
    email = request.form.get('email')
    password = request.form.get('password')

    if not email or not password:
        flash('Both email and password are required for login.', 'error')
        return redirect(url_for('index'))

    # Retrieve user data (Read operation)
    user = mongo.db.players.find_one({'email': email})

    if user:
        # Check if the retrieved password matches the submitted password
        # In a real app, use: if check_password_hash(user['password'], password):
        if user['password'] == password: # ⚠️ DANGER: Replace with bcrypt check in production
            flash(f'Successfully logged in as {email}!', 'success')
            # Set a session variable to keep the user logged in
            session['email'] = email   
            # session.pop('email', None) # To log out, remove the session variable
            return redirect(url_for('home'))
        else:
            flash('Invalid email or password.', 'error')
    else:
        # If no user is found with that email
        flash('Invalid email or password.', 'error')

    return redirect(url_for('index'))

@app.route('/logout', methods=['GET'])
def logout():
    """Logs out the current user by clearing the session."""
    session.pop('email', None)
    return redirect(url_for('login'))

@app.route('/home')
def home():
    # A page the user sees after a successful login
    return render_template('home.html')

@app.route('/api/inventory', methods=['GET'])
def get_inventory():
    """Returns a list of all Pokemon in the player inventory."""
    inventory = list(mongo.db.pokemon.find({'player': session.get('email')}))
    return jsonify(inventory)

@app.route('/api/release', methods=['DELETE'])
def release_pokemon():
    """Deletes multiple Pokemon documents based on their unique IDs."""
    data = request.get_json()
    pokemon_ids_to_release = data.get('ids', [])

    if not pokemon_ids_to_release:
        return jsonify({"message": "No Pokemon IDs provided for release."}), 400

    # Convert string IDs back to MongoDB ObjectId objects
    object_ids = [ObjectId(p_id) for p_id in pokemon_ids_to_release]

    # Use $in operator to find all documents whose _id is in the list
    result = mongo.db.pokemon.delete_many({
        '_id': {'$in': object_ids}
    })

    return jsonify({
        "message": f"Successfully released {result.deleted_count} Pokemon!",
        "deleted_count": result.deleted_count
    })

@app.route('/api/gatcha', methods=['POST'])
def run_gatcha():
    """Pulls a random Pokemon and adds it to the inventory."""
    
    # Define a pool of possible gatcha pulls
    # Add the player's email to associate the Pokemon with the user

    gatcha_pool = [
        {"player":session.get('email'), "name": "Squirtle", "atk": 48, "def": 65, "hp": 44, "locked":False, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/7.png"},
        {"player":session.get('email'), "name": "Jigglypuff", "atk": 45, "def": 20, "hp": 115, "locked":False, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/39.png"},
        {"player":session.get('email'), "name": "Snorlax", "atk": 110, "def": 65, "hp": 160, "locked":False, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/143.png"}
    ]
    
    new_pokemon = random.choice(gatcha_pool)

    # Save the new Pokemon to the database
    mongo.db.pokemon.insert_one(new_pokemon)

    # Return the newly caught Pokemon data
    return jsonify({"message": "Gatcha successful!", "new_pokemon": new_pokemon})

@app.route('/api/battle', methods=['GET'])
def get_battle_queue():
    """Returns placeholder data for the battle queue."""
    return jsonify({
        "status": "In Queue",
        "position": random.randint(1, 10),
        "message": "Searching for opponents..."
    })

@app.route('/api/trade', methods=['GET'])
def get_trade_menu_data():
    """Returns the current player's inventory and all pending trades."""
    # 1. Get current player's available (unlocked) inventory
    available_inventory = mongo.db.pokemon.find({"player": session.get('email'), "locked": False})
    available_inventory = list(available_inventory)
    
    # 2. Get all pending trades
    pending_trades = []
    for doc in mongo.db.trade.find({"status": "pending"}):
        doc['id'] = str(doc.pop('_id'))
        
        # Look up the details of the offered pokemon (for display)
        offered_pokemon_details = []
        for p_id in doc['offering_ids']:
            p_doc = mongo.db.pokemon.find_one({'_id': ObjectId(p_id)})
            if p_doc:
                offered_pokemon_details.append({"name": p_doc['name'], "image": p_doc['image']})
        
        doc['offered_details'] = offered_pokemon_details
        pending_trades.append(doc)

    return jsonify({
        "inventory": available_inventory,
        "pending_trades": pending_trades,
        "current_player": session.get('email')
    })

@app.route('/api/trade/create', methods=['POST'])
def create_trade():
    """Locks the selected single Pokemon and creates a new trade request, requesting one in return."""
    data = request.get_json()
    offering_ids = data.get('offering_ids', [])
    
    # 1. Enforce 1-for-1 rule: must offer exactly one Pokemon
    if len(offering_ids) != 1:
        return jsonify({"message": "You must offer exactly one Pokémon for a 1-for-1 trade."}), 400

    object_id = ObjectId(offering_ids[0])
    
    # 2. Lock the Pokemon for trade
    lock_result = mongo.db.pokemon.update_one(
        {'_id': object_id, 'player': session.get('email'), 'locked': False},
        {'$set': {'locked': True}}
    )

    if lock_result.modified_count != 1:
        return jsonify({"message": "Could not lock the selected Pokémon. It may be locked or not yours."}), 409

    # 3. Create the trade request document (always looking for 1)
    trade_request = {
        "creator": session.get('email'),
        "offering_ids": offering_ids, 
        "looking_for_count": 1, # Fixed at 1
        "status": "pending",
        "timestamp": datetime.now()
    }
    mongo.db.trade.insert_one(trade_request)
    
    return jsonify({
        "message": "1-for-1 Trade request created! Your Pokémon is locked.",
        "locked_count": 1
    })

@app.route('/api/trade/fulfill', methods=['PUT'])
def fulfill_trade():
    """Requires exactly one Pokémon to fulfill the trade, swaps ownership, and removes the request."""
    data = request.get_json()
    trade_id = data.get('trade_id')
    fulfilling_ids = data.get('fulfilling_ids', [])

    if not trade_id or len(fulfilling_ids) != 1:
        return jsonify({"message": "Missing trade ID or you must offer exactly one Pokémon."}), 400

    trade_obj_id = ObjectId(trade_id)
    fulfilling_obj_id = ObjectId(fulfilling_ids[0])
    
    # 1. Retrieve the trade request
    trade = mongo.db.trade.find_one({'_id': trade_obj_id})
    if not trade or trade.get('looking_for_count') != 1:
        return jsonify({"message": "Trade request not found or is not a 1-for-1 trade."}), 404
    
    # The Pokemon offered in the original trade
    original_offered_id = ObjectId(trade['offering_ids'][0])
    
    # 2. Perform the swap using two atomic updates
    
    # A. Original Creator (e.g., TrainerB) receives CURRENT_PLAYER's (TrainerA's) Pokemon
    mongo.db.pokemon.update_one(
        {'_id': fulfilling_obj_id, 'player': session.get('email')},
        {'$set': {'player': trade['creator'], 'locked': False}}
    )
    
    # B. CURRENT_PLAYER (TrainerA) receives the Original Creator's (TrainerB's) Pokemon (and unlocks it)
    mongo.db.pokemon.update_one(
        {'_id': original_offered_id},
        {'$set': {'player': session.get('email'), 'locked': False}}
    )

    # 3. Delete the fulfilled trade request
    mongo.db.trade.delete_one({'_id': trade_obj_id})

    return jsonify({
        "message": "Trade successful! 1-for-1 Pokémon swap completed.",
        "traded_in": str(original_offered_id),
        "traded_out": str(fulfilling_obj_id)
    })

# --- API Route: Get User Info ---

@app.route('/api/user/info', methods=['GET'])
def get_user_info():
    """Returns the current player's level and XP."""
    user = mongo.db.players.find_one({'email': session.get('email')})
    if not user:
        return jsonify({"message": "User not found."}), 404
    
    return jsonify({
        "email": user.get('email', "email-placeholder"),
        "level": user.get('level', 1),
        "xp": user.get('xp', 0),
        "xp_to_next_level": LEVEL_UP_XP - user.get('xp', 0),
        "wins": user.get('wins', 0),
        "losses": user.get('losses', 0)
    })

# --- SOCKETIO EVENT HANDLERS ---

@socketio.on('connect')
def handle_connect():
    """Logs the client connecting and associates the session ID (sid) with the current user."""
    user_email = session.get('email')
    app.logger.info(f"Client Connected: SID={request.sid}, User={user_email}")
    if user_email:
        app.logger.info(f"User {user_email} connected with SID={request.sid}")
    else:
        app.logger.warning(f"Unauthenticated connection with SID={request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    """Removes player from the queue if they disconnect."""
    global BATTLE_QUEUE
    player_name = session.get('email')
    if player_name:
        # Remove from queue if present
        BATTLE_QUEUE = [player for player in BATTLE_QUEUE if player['sid'] != request.sid]
        app.logger.info(f"Client Disconnected: {player_name} removed from queue.")

@socketio.on('join_queue')
def handle_join_queue():
    """Handles queue entry and immediate matchmaking attempt."""
    global BATTLE_QUEUE, BATTLES_IN_PROGRESS
    player_name = session.get('email')
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
    socketio.run(debug=True) # Setting debug=True enables auto-reloading during development