from datetime import datetime, timezone
import json
import uuid
from flask import Blueprint, jsonify, request
from services import generateUUID,generateTokens
from utils import token_required, cdb,getUniqueIDInt
from cache import redisClient
SecureStoreBP = Blueprint("SecureStoreBP", __name__)

@SecureStoreBP.route('/createSecureId', methods=['POST'])
@token_required
def createUniqueID(userid, email, username):
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid request, no data provided"}), 400

        type_of_id = data.get('type_of_id')
        description = data.get('description')
        secureid_name = data.get('secureid_name')

        if not type_of_id:
            return jsonify({"error": "Missing required field: 'type_of_id'"}), 400
        if not description:
            return jsonify({"error": "Missing required field: 'description'"}), 400
        if not secureid_name:
            return jsonify({"error": "Missing required field: 'secureid_name'"}), 400
        userDoc=json.loads(redisClient.get(userid))
        if userDoc is None:
            userDoc = cdb.get(userid)
        if not userDoc:
            return jsonify({"error": "User document not found"}), 404
        print("dsaf3",flush=True)
        if 'SecureStore' not in userDoc:
            userDoc['SecureStore'] = []
        if not any('SecureID' in entry for entry in userDoc['SecureStore']):
            userDoc['SecureStore'].append({'SecureID': []})

        for secureEntry in userDoc['SecureStore']:
            if 'SecureID' in secureEntry:
                for existingEntry in secureEntry['SecureID']:
                    if existingEntry.get('secureid_name') == secureid_name:
                        return jsonify({"error": f"secureid_name '{secureid_name}' already exists."}), 400
       
        secure_id = generateUUID(type_of_id)
        unique_id = getUniqueIDInt()
        created_at = str(datetime.now(timezone.utc).timestamp())

        new_entry = {
            "id": str(unique_id),
            "secure_id": str(secure_id),
            "secureid_name": secureid_name,
            "type_of_id": type_of_id,
            "description": description,
            "created_at": created_at
        }
        for secureEntry in userDoc['SecureStore']:
            if 'SecureID' in secureEntry:
                secureEntry['SecureID'].append(new_entry)
        print(userDoc,flush=True)
        cdb.save(userDoc)
        redisClient.set(userid,json.dumps(userDoc))
        print("dsaf4",flush=True)
        print("saved",flush=True)
        redisClient.set(userid,json.dumps(userDoc))
        return jsonify({
            "message": "Secure ID created successfully.",
            "secure_id": secure_id,
            "entry": new_entry
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@SecureStoreBP.route('/deleteSecureID/<id>', methods=['DELETE'])
@token_required
def deleteSecureID(userid, email, username, id):
    try:
        id=str(id)
        if not id:
            return jsonify({"error": "Missing required parameter: 'id'"}), 400
        userDoc=json.loads(redisClient.get(userid))
        if userDoc is None:
            userDoc = cdb.get(userid)
        if not userDoc or 'SecureStore' not in userDoc:
            return jsonify({"error": "No SecureStore data found for the user."}), 404

        deletedId = None
        for secureEntry in userDoc['SecureStore']:
            if 'SecureID' in secureEntry:
                for entry in secureEntry['SecureID'][:]: 
                    if entry.get('id') == id:
                        secureEntry['SecureID'].remove(entry)
                        deletedId = id
                        break

        if not deletedId:
            return jsonify({"error": f"No Secure ID found with id '{id}'."}), 404

        cdb.save(userDoc)
        redisClient.set(userid,json.dumps(userDoc))
        return jsonify({
            "message": f"Secure ID with id '{id}' deleted successfully.",
            "deleted_id": deletedId
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@SecureStoreBP.route('/getSecureID/<id>', methods=['GET'])
@token_required
def getSecureID(userid, email, username, id):
    try:
        if not id:
            return jsonify({"error": "Missing required parameter: 'id'"}), 400
        userDoc=json.loads(redisClient.get(userid))
        if userDoc is None:            
            userDoc = cdb.get(userid)
        if not userDoc or 'SecureStore' not in userDoc:
            return jsonify({"error": "No SecureStore data found for the user."}), 404

        for secureEntry in userDoc['SecureStore']:
            if 'SecureID' in secureEntry:
                for entry in secureEntry['SecureID']:
                    if entry.get('id') == id:
                        return jsonify(entry), 200

        return jsonify({"error": f"No Secure ID found with id '{id}'."}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
    
    
@SecureStoreBP.route('/getAllSecureIDs', methods=['GET'])
@token_required
def getAllSecureIDs(userid, email, username):
    try:
        userDoc=json.loads(redisClient.get(userid))
        if userDoc is None:
            userDoc = cdb.get(userid)
        if not userDoc or 'SecureStore' not in userDoc:
            return jsonify({"error": "No SecureStore data found for the user."}), 404

        allSecureIds = []
        for secureEntry in userDoc['SecureStore']:
            if 'SecureID' in secureEntry:
                for entry in secureEntry['SecureID']:
                    allSecureIds.append(entry)

        return jsonify(allSecureIds), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@SecureStoreBP.route('/createSecureToken', methods=['POST'])
@token_required
def createSecureToken(userid, email, username):
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid request, no data provided"}), 400

        type_of_token = data.get('type_of_token')
        description = data.get('description')
        token_name = data.get('token_name')
        expire_date_time = data.get('expire_date_time')
        nbytes=data.get('nbytes')

        if not type_of_token:
            return jsonify({"error": "Missing required field: 'type_of_token'"}), 400
        if not description:
            return jsonify({"error": "Missing required field: 'description'"}), 400
        if not token_name:
            return jsonify({"error": "Missing required field: 'token_name'"}), 400
        if not expire_date_time:
            return jsonify({"error": "Missing required field: 'expire_date_time'"}), 400
        if not nbytes:
            return jsonify({"error": "Missing required field: 'nbytes'"}), 400
        print("assess",flush=True)
        userDoc=json.loads(redisClient.get(userid))
        print("assess",flush=True)
        if userDoc is None:
            userDoc = cdb.get(userid)
        if not userDoc:
            return jsonify({"error": "User document not found"}), 404

        if 'SecureStore' not in userDoc:
            userDoc['SecureStore'] = []
        if not any('SecureToken' in entry for entry in userDoc['SecureStore']):
            userDoc['SecureStore'].append({'SecureToken': []})

        for secureEntry in userDoc['SecureStore']:
            if 'SecureToken' in secureEntry:
                for existingEntry in secureEntry['SecureToken']:
                    if existingEntry.get('token_name') == token_name:
                        return jsonify({"error": f"token_name '{token_name}' already exists."}), 400
        unique_id=str(uuid.uuid4())
        token=generateTokens(type_of_token,nbytes)
        created_at = str(datetime.now(timezone.utc).timestamp())

        new_entry = {
            "id": str(unique_id),
            "token_name": token_name,
            "type_of_token":type_of_token,
            "token":token,
            "nbytes":nbytes,
            "description": description,
            "expire_date_time": expire_date_time,
            "created_at": created_at
        }
        for secureEntry in userDoc['SecureStore']:
            if 'SecureToken' in secureEntry:
                secureEntry['SecureToken'].append(new_entry)
        cdb.save(userDoc)
        redisClient.set(userid,json.dumps(userDoc))
        return jsonify({
            "message": "Secure Token created successfully.",
            "token_name": token_name,
            "entry": new_entry
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@SecureStoreBP.route('/deleteSecureToken/<token_id>', methods=['DELETE'])
@token_required
def deleteSecureTokenById(userid, email, username, token_id):
    try:
        userDoc=json.loads(redisClient.get(userid))
        if userDoc is None:
            userDoc = cdb.get(userid)
        if not userDoc:
            return jsonify({"error": "User document not found"}), 404

        if 'SecureStore' not in userDoc or not any('SecureToken' in entry for entry in userDoc['SecureStore']):
            return jsonify({"error": "No Secure Tokens found"}), 404

        for secureEntry in userDoc['SecureStore']:
            if 'SecureToken' in secureEntry:
                secureTokens = secureEntry['SecureToken']
                token_to_delete = next((token for token in secureTokens if token['id'] == token_id), None)
                if token_to_delete:
                    secureTokens.remove(token_to_delete)
                    cdb.save(userDoc)
                    redisClient.set(userid,json.dumps(userDoc))
                    return jsonify({"message": "Secure Token deleted successfully"}), 200

        return jsonify({"error": f"Secure Token with id '{token_id}' not found"}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500



@SecureStoreBP.route('/getSecureToken/<token_id>', methods=['GET'])
@token_required
def getSecureTokenById(userid, email, username, token_id):
    try:
        userDoc=json.loads(redisClient.get(userid))
        if userDoc is None:
            userDoc = cdb.get(userid)
        if not userDoc:
            return jsonify({"error": "User document not found"}), 404

        if 'SecureStore' not in userDoc or not any('SecureToken' in entry for entry in userDoc['SecureStore']):
            return jsonify({"error": "No Secure Tokens found"}), 404

        for secureEntry in userDoc['SecureStore']:
            if 'SecureToken' in secureEntry:
                token = next((t for t in secureEntry['SecureToken'] if t['id'] == token_id), None)
                if token:
                    return jsonify({"token": token}), 200

        return jsonify({"error": f"Secure Token with id '{token_id}' not found"}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@SecureStoreBP.route('/getAllSecureTokens', methods=['GET'])
@token_required
def getAllSecureTokens(userid, email, username):
    try:
        userDoc=json.loads(redisClient.get(userid))
        if userDoc is None:
            userDoc = cdb.get(userid)
        if not userDoc:
            return jsonify({"error": "User document not found"}), 404

        if 'SecureStore' not in userDoc or not any('SecureToken' in entry for entry in userDoc['SecureStore']):
            return jsonify({"tokens": []}), 200
        all_tokens = []
        for secureEntry in userDoc['SecureStore']:
            if 'SecureToken' in secureEntry:
                all_tokens.extend(secureEntry['SecureToken'])

        return jsonify(all_tokens), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

