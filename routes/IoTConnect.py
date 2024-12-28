from datetime import datetime, timezone
import json
import logging
import uuid
from flask import Blueprint, jsonify, request
from utils import token_required
from utils import getUniqueID, cdb
from cache import redisClient
IoTConnectBP = Blueprint("IoTConnect", __name__)

@IoTConnectBP.route("/createServiceConnect", methods=["POST"])
@token_required
def createServicesConnect(userid, email, username):
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid request, no data provided"}), 400

        connection_name = data.get('connection_name')
        if not connection_name:
            return jsonify({"error": "connection_name is required"}), 400

        data['connection_id'] = str(uuid.uuid4())
        data['created_at'] =str(datetime.now(timezone.utc).timestamp())
        userDoc=json.loads(redisClient.get(userid))
        if userDoc is None:
            userDoc = cdb.get(userid)
        if not userDoc:
            return jsonify({"error": "User document not found"}), 404

        if 'IoTConnect' not in userDoc:
            userDoc['IoTConnect'] = []

        existing_names = {conn['connection_name'] for conn in userDoc['IoTConnect']}
        if connection_name in existing_names:
            return jsonify({"error": f"connection_name '{connection_name}' already exists"}), 409

        userDoc['IoTConnect'].append(data)            
        cdb.save(userDoc)
        if redisClient:
            redisClient.set(userid, json.dumps(userDoc)) 
            logging.info(redisClient.get(userid))
        return jsonify({
            "message": "Service connection created successfully.",
            "connection_id": data['connection_id'],
            "IoTConnect": userDoc['IoTConnect']
        }), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@IoTConnectBP.route("/deleteServiceConnect/<connection_id>", methods=["DELETE"])
@token_required
def deleteServiceConnect(userid, email, username, connection_id):
    try:
        userDoc=json.loads(redisClient.get(userid))
        if userDoc is None:
            userDoc = cdb.get(userid)
        if not userDoc:
            return jsonify({"error": "User document not found"}), 404

        if 'IoTConnect' not in userDoc or not userDoc['IoTConnect']:
            return jsonify({"error": "No IoT connections found"}), 404

        original_count = len(userDoc['IoTConnect'])
        userDoc['IoTConnect'] = [
            conn for conn in userDoc['IoTConnect']
            if conn.get('connection_id') != connection_id
        ]

        if len(userDoc['IoTConnect']) == original_count:
            return jsonify({"error": f"No connection found with ID '{connection_id}'"}), 404

        cdb.save(userDoc)
        redisClient.set(userid,json.dumps(userDoc))
        return jsonify({"message": f"Connection with ID '{connection_id}' deleted successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@IoTConnectBP.route("/getConnectionById/<connection_id>", methods=["GET"])
@token_required
def getConnectionById(userid, email, username, connection_id):
    try:
        userDoc = json.loads(redisClient.get(userid))
        if not userDoc:
            userDoc = cdb.get(userid)
        if not userDoc:
            return jsonify({"error": "User document not found"}), 404
        if 'IoTConnect' in userDoc:
            for connection in userDoc['IoTConnect']:
                if connection.get('connection_id') == str(connection_id):
                    return jsonify(connection), 200
        
        return jsonify({"error": "Connection ID not found"}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@IoTConnectBP.route("/getAllIoTConnections", methods=["GET"])
@token_required
def getAllIoTConnections(userid, email, username):
    try:
        userDoc = json.loads(redisClient.get(userid))
        if not userDoc:
            userDoc = cdb.get(userid)
        if not userDoc:
            return jsonify([]), 404
        iotConnections = userDoc.get('IoTConnect', [])
        return jsonify(iotConnections), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


