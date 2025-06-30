import os
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_login import LoginManager, current_user, login_required
from dotenv import load_dotenv

from extensions import db, login_manager  # ✅ shared db & login_manager
from models import User, Room, room_members  # ✅ uses shared db

# Load environment variables
load_dotenv()

# Flask app and configuration
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'secret!')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'

# Initialize extensions
db.init_app(app)                # ✅ DO NOT reassign db = SQLAlchemy()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
socketio = SocketIO(app)

# Register auth blueprint
from auth import auth_bp
app.register_blueprint(auth_bp)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# In-memory task store per room
tasks = {}   # { room_name: [ {id, text, done}, ... ] }
next_id = {} # { room_name: next_task_id }

@app.route('/')
@login_required
def index():
    return render_template('index.html')

@socketio.on('join_room')
def handle_join(data):
    room = data['room']
    if room not in tasks:
        tasks[room] = []
        next_id[room] = 1
    join_room(room)
    emit('room_data', {'tasks': tasks[room]}, room=request.sid)
    emit('notification', {'message': f"A user has joined room '{room}'"}, room=room)

@socketio.on('leave_room')
def handle_leave(data):
    leave_room(data['room'])
    emit('notification', {'message': f"A user has left room '{data['room']}'"}, room=data['room'])

@socketio.on('add_task')
def handle_add_task(data):
    room, text = data['room'], data['text']
    task = {'id': next_id[room], 'text': text, 'done': False}
    tasks[room].append(task)
    next_id[room] += 1
    emit('task_added', task, room=room)
    emit('notification', {'message': f"Task added: '{text}'"}, room=room)

@socketio.on('remove_task')
def handle_remove_task(data):
    room, t_id = data['room'], data['id']
    tasks[room] = [t for t in tasks[room] if t['id'] != t_id]
    emit('task_removed', {'id': t_id}, room=room)
    emit('notification', {'message': f"Task removed (ID {t_id})"}, room=room)

@socketio.on('toggle_done')
def handle_toggle_done(data):
    room, t_id = data['room'], data['id']
    for t in tasks[room]:
        if t['id'] == t_id:
            t['done'] = not t['done']
            emit('task_toggled', {'id': t_id, 'done': t['done']}, room=room)
            state = 'completed' if t['done'] else 'reopened'
            emit('notification', {'message': f"Task {state}: '{t['text']}'"}, room=room)
            break

@socketio.on('edit_task')
def handle_edit_task(data):
    room, t_id, new_text = data['room'], data['id'], data['text']
    for t in tasks[room]:
        if t['id'] == t_id:
            t['text'] = new_text
            emit('task_edited', {'id': t_id, 'text': new_text}, room=room)
            emit('notification', {'message': f"Task edited: '{new_text}'"}, room=room)
            break

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    socketio.run(app, debug=True)
