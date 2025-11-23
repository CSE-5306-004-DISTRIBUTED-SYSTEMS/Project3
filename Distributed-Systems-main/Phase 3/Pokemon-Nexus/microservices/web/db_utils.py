import os
from flask import Flask, session
from flask_pymongo import PyMongo
from flask_cors import CORS
from flask_session import Session 
import redis
import random

# --- Initialization Function ---
def create_app(service_name):
    """Initializes a Flask application with shared configuration (CORS, Redis, Mongo)."""
    app = Flask(service_name)
    
    # Load configuration from environment variables (defined in docker-compose.yaml)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default_secret') 
    app.config['SESSION_TYPE'] = os.environ.get('SESSION_TYPE', 'redis')
    
    # Mongo URI for database access
    app.config["MONGO_URI"] = os.environ.get("MONGO_URI", "mongodb://localhost:27017/fallback_db")
    
    # Redis URL for Session and later for Battle Service message broker
    SESSION_REDIS_URL = os.environ.get('SESSION_REDIS') 

    # --- Redis Configuration for Flask-Session ---
    if app.config['SESSION_TYPE'] == 'redis' and SESSION_REDIS_URL:
        # Flask-Session requires a redis client object for the connection
        try:
            # Use redis.from_url to get the client instance
            app.config['SESSION_REDIS'] = redis.from_url(SESSION_REDIS_URL)
            app.logger.info(f"[{service_name}] Redis client initialized.")
        except Exception as e:
            app.logger.error(f"[{service_name}] Failed to initialize Redis client: {e}")
            # Fallback to filesystem if Redis fails, though not ideal in production
            app.config['SESSION_TYPE'] = 'filesystem'
    
    # Initialize Flask-Session
    Session(app)
    
    # Initialize PyMongo
    mongo = PyMongo(app)
    
    # Enable CORS for cross-service communication (essential in microservices)
    CORS(app, supports_credentials=True, resources={r"/*": {"origins": "*"}})
    
    app.logger.info(f"[{service_name}] App configuration complete.")
    
    return app, mongo

# --- Utility Function for Authentication ---
# Every service will check this before processing business logic
def get_current_user_email():
    """Retrieves the authenticated user's email from the session."""
    return session.get('user_email')

# Create a mock monster for Gatcha and Trading to ensure consistency (Simplified for now)
def generate_monster_stats(base_name, level=1):
    """Generates base stats for a new monster."""
    return {
        'name': base_name,
        'species': base_name.split('-')[0],
        'level': level,
        'hp': random.randint(30, 50) + level * 5,
        'atk': random.randint(10, 20) + level * 2,
        'def': random.randint(10, 20) + level * 2,
        'xp': 0,
    }
