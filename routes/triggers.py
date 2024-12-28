import json
import os
import couchdb
from datetime import datetime, timezone
import uuid
import requests
from flask import Blueprint, jsonify, request
from services import generateUUID, generateTokens
from utils import token_required
from utils import cdb
from cache import redisClient
import logging
TriggerBP = Blueprint("TriggerBP", __name__)

DOCUMENT_ID = 'c08667781a0bd38fcaeeacc6eb003b3b'  
TRIGGERDOC='496f084796a84d1c542e50d439002052'

def getDocument(doc_id):
    try:
        doc = cdb[doc_id]
        return doc
    except couchdb.ResourceNotFound:
        return None

def updateDocument(doc_id, document_data):
    try:
        doc = cdb[doc_id]
        doc['_rev'] = doc['_rev']  
        doc.update(document_data) 
        cdb[doc_id] = doc  
        return True
    except Exception as e:
        print(f"Error updating document: {str(e)}")
        return False

def addTriggerToUserDoc(userid, trigger_data):
    try:
        userDoc = cdb[userid]  
        userDoc['_rev'] = userDoc['_rev']  

        if "triggers" not in userDoc:
            userDoc["triggers"] = []

        userDoc["triggers"].append(trigger_data) 
        cdb[userid] = userDoc  

        return True
    except couchdb.ResourceNotFound:
        print(f"User document with userid {userid} not found.")
        return False
    except Exception as e:
        print(f"Error updating user document: {str(e)}")
        return False

@TriggerBP.route('/createTrigger', methods=['POST'])
@token_required
def createTrigger(userid, email, username):
    try:
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({"error": "Authorization token is missing"}), 401

        headers = {"Authorization": f"Bearer {token}"}

        data = request.get_json()
        if not data:
            return jsonify({"error": "Request payload is missing"}), 400

        triggerName = data.get('trigger_name')
        triggerDiscription = data.get('trigger_discription')
        connectionId = data.get('connection_id')

        if not all([triggerName, triggerDiscription, connectionId]):
            return jsonify({"error": "Missing required fields: 'trigger_name', 'trigger_discription', 'connection_id'"}), 400

        triggerId = generateUUID('classic')
        connection_url = f'http://127.0.0.1:5000/services/IotConnect/getConnectionById/{connectionId}'
        response = requests.get(connection_url, headers=headers)

        if response.status_code != 200:
            return jsonify({"error": f"Failed to fetch connection details. Status Code: {response.status_code}"}), response.status_code

        connection = response.json()

        triggerData = {
            "trigger_id": triggerId,
            "trigger_name": triggerName,
            "trigger_description": triggerDiscription,
            "connection_id": connectionId,
            "connection_details": connection,
            "userid": userid,
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        document = getDocument(TRIGGERDOC)

        if not document:
            return jsonify({"error": "Document not found in CouchDB"}), 404

        document[triggerId] = triggerData
        updateSuccess = updateDocument(TRIGGERDOC, document)

        if not updateSuccess:
            return jsonify({"error": "Failed to update document in CouchDB"}), 500

        user_update_success = addTriggerToUserDoc(userid, triggerId)

        if not user_update_success:
            return jsonify({"error": "Failed to update user's document in CouchDB"}), 500

        return jsonify({
            "message": "Trigger created and saved successfully",
            "trigger_id": triggerId,
            "trigger_details": triggerData
        }), 201

    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500



@TriggerBP.route('/startConnection', methods=['POST'])
@token_required
def startConnection(userid, email, username):
    try:
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({"error": "Authorization token is missing"}), 401

        headers = {"Authorization": f"Bearer {token}"}

        data = request.get_json()
        if not data:
            return jsonify({"error": "Request payload is missing"}), 400

        triggerId = data.get('trigger_id')
        if not triggerId:
            return jsonify({"error": "Missing required field: 'trigger_id'"}), 400

        document = getDocument(TRIGGERDOC)
        if not document or triggerId not in document:
            return jsonify({"error": "Trigger not found in CouchDB"}), 404

        trigger_data = document[triggerId]
        connectionId = trigger_data.get("connection_id")
        connection_details = trigger_data.get("connection_details")
        if not connectionId:
            return jsonify({"error": "Trigger data is missing 'connection_id'"}), 500

        start_url = f'http://worker-node-app:4342/start_connection'
        start_request_payload = {
            "trigger_id": triggerId,
            "user_id": userid,
            "connection_details": connection_details
        }
        start_response = requests.post(start_url, json=start_request_payload)

        if start_response.status_code != 200:
            return jsonify({"error": f"Failed to start connection. Status Code: {start_response.status_code}"}), start_response.status_code

        start_response_data = start_response.json()
        connection_details = start_response_data.get("connection_details", {})

        trigger_data["status"] = "started"
        trigger_data["started_at"] = datetime.now(timezone.utc).isoformat()

        document[triggerId] = trigger_data
        updateSuccess = updateDocument(TRIGGERDOC, document)

        if not updateSuccess:
            return jsonify({"error": "Failed to update document in CouchDB"}), 500

        return jsonify({
            "message": "Connection started successfully",
            "trigger_id": triggerId,
            "connection_details": connection_details,
        }), 200

    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500


@TriggerBP.route('/stopConnection', methods=['POST'])
@token_required  
def stopConnection(userid, email, username):
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request payload is missing"}), 400

        triggerId = data.get('trigger_id')
        connectionId = data.get('connection_id')

        if not triggerId or not connectionId:
            return jsonify({"error": "Missing required fields: 'trigger_id' or 'connection_id'"}), 400

        document = getDocument(TRIGGERDOC)
        if not document or triggerId not in document:
            return jsonify({"error": "Trigger not found in CouchDB"}), 404
        logging.info("Trigger not found")
        trigger_data = document[triggerId]
        connection_details = trigger_data.get("connection_details")
        logging.info(connection_details)
        stop_url = f'http://worker-node-app:4342/stop_connection'
        stop_request_payload = {
            "user_id": userid,
            "trigger_id": triggerId,
            "connection_id": connectionId
        }
        stop_response = requests.post(stop_url, json=stop_request_payload)
        logging.info(stop_response)
        if stop_response.status_code != 200:
            return jsonify({"error": f"Failed to stop connection. Status Code: {stop_response.status_code}"}), stop_response.status_code

        file_content = stop_response.content
        logging.info(file_content)
        

        if file_content:

            file_path = f"{connectionId}_{triggerId}_{userid}.xlsx"
            attachment_name = f"{triggerId}"
            if DOCUMENT_ID in cdb:
                doc = cdb[DOCUMENT_ID]
            else:
                doc = {'_id': DOCUMENT_ID}
                cdb.save(doc)
            doc = cdb[DOCUMENT_ID]
            
            cdb.put_attachment(doc, file_content, filename=file_path, content_type='application/octet-stream')
            attachment = {
                'status': 'stopped',
                'file_path': file_path,
                'stopped_at': datetime.now(timezone.utc).isoformat()
            }
            document = getDocument(TRIGGERDOC)
            document[triggerId].update(attachment)
            
            if updateDocument(TRIGGERDOC,document):
                return jsonify({
                    "message": "Connection stopped successfully and file saved.",
                    "file_url": file_path
                }), 200
            else:
                return jsonify({"error": "Failed to update document in CouchDB"}), 500
        else:
            return jsonify({"error": "No file data returned from the worker server"}), 500

    except Exception as e:
        logging.error(f"Error stopping connection: {e}")
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500
