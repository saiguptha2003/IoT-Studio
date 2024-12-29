from datetime import datetime, timezone
import logging
import uuid
import os
from flask import Blueprint, jsonify, request
from werkzeug.utils import secure_filename
from utils import token_required, getDocument, updateDocument
from cache import redisClient

WareHouseBP = Blueprint("WareHouseBP", __name__)
UPLOAD_FOLDER = './uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}
WARE_HOUSE_DOC_ID = '2343243'
WARE_HOUSE_ATTACHMENT=''
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    """Check if the uploaded file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@WareHouseBP.route('/uploadFile', methods=['POST'])
@token_required
def uploadFile(userid, email, username):
    try:
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({"error": "Authorization token is missing"}), 401

        headers = {"Authorization": f"Bearer {token}"}

        if 'file' not in request.files:
            return jsonify({"error": "No file part in the request."}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No file selected for upload."}), 400
        if not allowed_file(file.filename):
            return jsonify({"error": "File type not allowed."}), 400
        
        filename = secure_filename(file.filename)
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)

        with open(file_path, 'rb') as f:
            file_content = f.read()

        fileID = str(uuid.uuid4())
        document = getDocument(WARE_HOUSE_DOC_ID)
        if not document:
            return jsonify({"error": "Document not found in CouchDB"}), 404

        if fileID not in document:
            document[fileID] = {
                "metadata": {
                    "userid": userid,
                    "filename": filename,
                    "uploaded_at": datetime.now(timezone.utc).isoformat()
                },
                "_attachments": {}
            }

        attachment_name = f"{fileID}_{filename}"
        document[fileID]['_attachments'][attachment_name] = {
            "content_type": file.mimetype,
            "data": file_content.decode('latin1')
        }

        updateSuccess = updateDocument(WARE_HOUSE_DOC_ID, document)

        if not updateSuccess:
            return jsonify({"error": "Failed to update document in CouchDB"}), 500

        return jsonify({
            "message": "File uploaded and saved successfully.",
            "trigger_id": fileID,
            "attachment_name": attachment_name
        }), 201

    except Exception as e:
        logging.exception("An error occurred while processing the file upload.")
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
