import random
from datetime import datetime
from flask import request, jsonify
from web.db_utils import create_app, get_current_user_email

# Initialize the Flask App and MongoDB connection for this service
app, mongo = create_app(__name__)

# --- Core Monster Generation Logic (Moved from app.py) ---
def generate_monster_stats(base_name, level=1):
    """Generates base stats for a new monster based on provided level."""
    # Simplified stats for a random monster
    return {
        'name': base_name,
        'species': base_name.split('-')[0],
        'level': level,
        'hp': random.randint(30, 50) + level * 5,
        'atk': random.randint(10, 20) + level * 2,
        'def': random.randint(10, 20) + level * 2,
        'xp': 0,
        'created_at': datetime.now()
    }

def get_random_monster_name():
    """Returns a random monster name from a predefined list (simplified)."""
    monsters = ["Ignis", "Aqua", "Terra", "Aero", "Lumen", "Umbra", "Bolt"]
    suffix = ["Jr", "S", "Alpha", "Omega", "Max"]
    return f"{random.choice(monsters)}-{random.choice(suffix)}"

# --- Routes ---

@app.route('/api/gatcha', methods=['GET'])
def run_gatcha():
    """This endpoint is no longer available. Use POST instead."""
    return jsonify({'message': 'Method Not Allowed'}), 405

@app.route('/api/gatcha/', methods=['POST'])
def run_gatcha_post():
    user_email = get_current_user_email()
    """Pulls a random Pokemon and adds it to the inventory."""
    
    # Define a pool of possible gatcha pulls
    # Add the player's email to associate the Pokemon with the user

    gatcha_pool = [
        {"player":user_email, "name": "Squirtle", "atk": 48, "def": 65, "hp": 44, "locked":False, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/7.png"},
        {"player":user_email, "name": "Jigglypuff", "atk": 45, "def": 20, "hp": 115, "locked":False, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/39.png"},
        {"player":user_email, "name": "Snorlax", "atk": 110, "def": 65, "hp": 160, "locked":False, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/143.png"}
    ]
    
    new_pokemon = random.choice(gatcha_pool)

    # Save the new Pokemon to the database
    mongo.db.pokemon.insert_one(new_pokemon)

    # Return the newly caught Pokemon data
    return jsonify({"message": "Gatcha successful!", "new_pokemon": new_pokemon}), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
