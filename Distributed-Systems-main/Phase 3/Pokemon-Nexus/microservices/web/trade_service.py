import json
from bson.objectid import ObjectId
from flask import request, jsonify
from web.db_utils import create_app, get_current_user_email
from datetime import datetime

# Initialize the Flask App and MongoDB connection for this service
app, mongo = create_app(__name__)

# --- Routes ---

@app.route('/api/trade/', methods=['GET'])
def get_trade_menu_data():
    """Returns the current player's inventory and all pending trades."""
    # 1. Get current player's available (unlocked) inventory
    available_inventory = mongo.db.pokemon.find({"player": get_current_user_email(), "locked": False})
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
        "current_player": get_current_user_email()
    })

@app.route('/api/trade/create/', methods=['POST'])
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
        {'_id': object_id, 'player': get_current_user_email(), 'locked': False},
        {'$set': {'locked': True}}
    )

    if lock_result.modified_count != 1:
        return jsonify({"message": "Could not lock the selected Pokémon. It may be locked or not yours."}), 409

    # 3. Create the trade request document (always looking for 1)
    trade_request = {
        "creator": get_current_user_email(),
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

@app.route('/api/trade/fulfill/', methods=['PUT'])
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
        {'_id': fulfilling_obj_id, 'player': get_current_user_email()},
        {'$set': {'player': trade['creator'], 'locked': False}}
    )
    
    # B. CURRENT_PLAYER (TrainerA) receives the Original Creator's (TrainerB's) Pokemon (and unlocks it)
    mongo.db.pokemon.update_one(
        {'_id': original_offered_id},
        {'$set': {'player': get_current_user_email(), 'locked': False}}
    )

    # 3. Delete the fulfilled trade request
    mongo.db.trade.delete_one({'_id': trade_obj_id})

    return jsonify({
        "message": "Trade successful! 1-for-1 Pokémon swap completed.",
        "traded_in": str(original_offered_id),
        "traded_out": str(fulfilling_obj_id)
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
