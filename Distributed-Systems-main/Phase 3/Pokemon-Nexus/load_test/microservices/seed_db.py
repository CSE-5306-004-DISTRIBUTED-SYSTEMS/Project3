import os
import sys
from pymongo import MongoClient
from datetime import datetime
import hashlib
import time

# --- CONFIGURATION ---
# Use the internal service name 'mongodb' for connection
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://admin:password@mongodb:27017/PokemonNexusDB?authSource=admin")
DATABASE_NAME = "PokemonNexusDB"
TEST_USER_EMAIL = "test_user@example.com"
TEST_USER_PASSWORD = "password123" 
SEED_MONSTER_COUNT = 5 # Number of base monsters to define
INITIAL_POKEMON_PER_USER = 3 # Number of Pokemon to give the test user

# --- Seed Data Definitions (Confirmed against app.py usage) ---
BASE_MONSTERS = [
    {"name": "Squirtle", "type": "Water", "atk": 48, "def": 65, "hp": 44, "base_rarity": 1.0},
    {"name": "Bulbasaur", "type": "Grass", "atk": 49, "def": 49, "hp": 45, "base_rarity": 1.0},
    {"name": "Charmander", "type": "Fire", "atk": 52, "def": 43, "hp": 39, "base_rarity": 1.0},
    {"name": "Pikachu", "type": "Electric", "atk": 55, "def": 40, "hp": 35, "base_rarity": 1.5},
    {"name": "Snorlax", "type": "Normal", "atk": 110, "def": 65, "hp": 160, "base_rarity": 0.5},
]


def create_user_document(email, password):
    """
    Creates a basic player document for the 'players' collection.
    Matches the fields used in app.py for login and stat updates.
    """
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    
    return {
        "email": email,
        "password": hashed_password,
        "username": email.split('@')[0],
        "xp": 0,
        "level": 1,
        "wins": 0,
        "losses": 0,
        "last_login": datetime.utcnow(),
    }

def create_inventory_document(owner_email, base_mon):
    """
    Creates an inventory document for the 'inventory' collection.
    Matches the fields used in app.py for battle simulation and inventory listing.
    """
    return {
        "owner": owner_email,
        "name": base_mon['name'],
        "type": base_mon['type'],
        "level": 1,
        "xp": 0,
        # Starting stats are the base stats
        "atk": base_mon['atk'],
        "def": base_mon['def'],
        "hp": base_mon['hp'],
        "locked": False, # Required for battle eligibility logic
        "creation_date": datetime.utcnow(),
    }

def seed_database():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Attempting to connect to MongoDB at: {MONGO_URI}...")
    try:
        # Connect to the MongoDB instance
        client = MongoClient(MONGO_URI)
        db = client[DATABASE_NAME]
        
        # --- 1. Clear existing test data for repeatability ---
        db.players.delete_one({"email": TEST_USER_EMAIL})
        db.inventory.delete_many({"owner": TEST_USER_EMAIL})
        db.monsters.delete_many({}) # Clear all base monsters
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Cleared previous test data.")

        # --- 2. Seed Base Monsters (Required for Gatcha and Battle) ---
        db.monsters.insert_many(BASE_MONSTERS)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Inserted {len(BASE_MONSTERS)} base monsters into 'monsters' collection.")

        # --- 3. Register Test Player ---
        player_doc = create_user_document(TEST_USER_EMAIL, TEST_USER_PASSWORD)
        db.players.insert_one(player_doc)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Registered test user: {TEST_USER_EMAIL}")
        
        # --- 4. Give Test Player Initial Pokémon ---
        # Ensure the test user has enough Pokemon for battles and inventory reads
        initial_inventory = [
            create_inventory_document(TEST_USER_EMAIL, BASE_MONSTERS[i % len(BASE_MONSTERS)]) 
            for i in range(INITIAL_POKEMON_PER_USER)
        ]
        db.inventory.insert_many(initial_inventory)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Gave test user {len(initial_inventory)} starter Pokémon.")

        print(f"[{datetime.now().strftime('%H:%M:%S')}] Seeding complete.")
        client.close()

    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] FAILED TO SEED DATABASE: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    # Wait for the MongoDB service to be ready (a simple sleep is usually sufficient)
    print("Waiting 10 seconds for MongoDB to start...")
    time.sleep(10) 
    seed_database()
