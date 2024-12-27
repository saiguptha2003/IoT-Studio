from dotenv import load_dotenv
from flask import Flask
from models import db
from Config import Config
from routes import authBP, IoTConnectBP,SecureStoreBP,BasicBP,TriggerBP
from flask_cors import CORS
import os
import couchdb
load_dotenv()
FLASK_PORT=os.getenv('FLASK_PORT')
app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

with app.app_context():
    db.create_all()

CORS(app)
    
app.register_blueprint(authBP, url_prefix='/auth')
app.register_blueprint(IoTConnectBP, url_prefix='/services/IotConnect')
app.register_blueprint(SecureStoreBP, url_prefix='/services/SecureStore')
app.register_blueprint(BasicBP,url_prefix='/')
app.register_blueprint(TriggerBP,url_prefix='/Trigger')
@app.route("/",methods=["GET"])
def index():
    return {"message": "hello User.."}
@app.route("/contact-us",methods=["GET"])
def contactUs():
    return {"Name": "V D Panduranga Sai Guptha", "Email":"saiguptha_v@srmap.edu.in"}
    
if __name__ == "__main__":
    import sys
    testing = "--test" in sys.argv
    if testing:
        print("Running in test mode")
    else:
        app.run(host="0.0.0.0", port=FLASK_PORT,debug=True)
