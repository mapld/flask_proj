from flask import Flask, jsonify, abort, make_response, request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import websocket
import threading
import time
import json

import os
basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
class Config(object):
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
                              'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
app.config.from_object(Config)
db = SQLAlchemy(app)
migrate = Migrate(app, db)

class Event(db.Model):
    id = db.Column(db.String(1024), primary_key=True)
    machine_id = db.Column(db.String(1024))
    timestamp = db.Column(db.String(128))
    status = db.Column(db.String(64))

    def __repr__(self):
        return '<Event {}>'.format(self.id)

def event_to_dict(obj):
    dict_obj = {
        'id' : obj.id,
        'machine_id' : obj.machine_id,
        'timestamp' : obj.timestamp,
        'status' : obj.status
        }
    return dict_obj

def on_message(ws, message):
    status_json = json.loads(message)
    payload = status_json['payload']
    id = payload['id']
    machine_id = payload['machine_id']
    timestamp = payload['timestamp']
    status = payload['status']
    existing_event = Event.query.filter_by(id=id)
    if(existing_event is None):
        event = Event(id=id, machine_id=machine_id, timestamp=timestamp, status=status)
        db.session.add(event)
        db.session.commit()

def on_error(ws, error):
    print(error)

def on_close(ws):
    print("websocket closed")

@app.route('/zeiss/api/v1.0/events', methods=['GET'])
def get_events():
    events = Event.query.all();
    events_obj = []
    for event in events:
        events_obj.append(event_to_dict(event))
    return jsonify(events_obj)

@app.route('/zeiss/api/v1.0/events/<string:event_id>', methods=['GET'])
def get_event(event_id):
    event = Event.query.filter_by(id=event_id).first();
    return jsonify(event_to_dict(event))

@app.route('/zeiss/api/v1.0/machines/<string:machine_id>/events/', methods=['GET'])
def get_event_for_machine(machine_id):
    events = Event.query.filter_by(machine_id=machine_id);
    events_obj = []
    for event in events:
        events_obj.append(event_to_dict(event))
    return jsonify(events_obj)


if __name__ == '__main__':
    ws = websocket.WebSocketApp("ws://machinestream.herokuapp.com/ws",
                              on_message = on_message,
                              on_error = on_error,
                              on_close = on_close)

    ws_thread = threading.Thread(target=ws.run_forever)
    ws_thread.daemon = True
    ws_thread.start()

    app.run(debug=True)
