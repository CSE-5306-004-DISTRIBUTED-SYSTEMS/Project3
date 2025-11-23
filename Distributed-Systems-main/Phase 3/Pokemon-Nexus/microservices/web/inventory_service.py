import json
from bson.objectid import ObjectId
from flask import request, jsonify
from web.db_utils import create_app, get_current_user_email

# Initialize the Flask App and MongoDB connection for this service
app, mongo = create_app(__name__)

# --- Helper to serialize MongoDB documents ---
def serialize_inventory(monster):
    """Converts a single MongoDB monster document to a JSON-safe dictionary."""
    if monster:
        monster['_id'] = str(monster['_id'])
    return monster

@app.route('/api/inventory/', methods=['GET'])
def get_inventory():
    """Retrieves all monsters owned by the current user."""
    user_email = get_current_user_email()

    # Fetch all monsters belonging to the user
    inventory = mongo.db.pokemon.find({"player": user_email})
    
    return jsonify(inventory)

@app.route('/api/release/', methods=['PUT'])
def release_monster():
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000) # Microservices run on default 5000 internally
