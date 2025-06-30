# app.py
import os
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_login import LoginManager, login_required, current_user
from datetime import datetime, timezone
from dotenv import load_dotenv

from extensions import db
from models import User, Room
from authorize import authorize_room
from auth import auth_bp
from room import room_bp

# Load environment
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'secret!')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'

# Initialize extensions
db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'auth.login'
socketio = SocketIO(app)

# User loader
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(room_bp)

# In-memory task store per room
tasks = {}    # { room_name: [ {id, text, done}, … ] }
next_id = {}  # { room_name: next_task_id }

# Inject current year into templates
@app.context_processor
def inject_current_year():
    return {'current_year': datetime.now(timezone.utc).year}

# Main page: pass rooms and username
@app.route('/')
@login_required
def index():
    # get all rooms (if dynamic relationship)
    try:
        rooms = current_user.rooms.all()
    except:
        rooms = current_user.rooms
    return render_template('index.html',
                           rooms=rooms,
                           current_username=current_user.username)

# ——— Socket.IO Events ———

@socketio.on('join_room')
@login_required
def handle_join(data):
    room_name = data['room']
    authorize_room(room_name)
    if room_name not in tasks:
        tasks[room_name] = []
        next_id[room_name] = 1
    join_room(room_name)
    emit('room_data', {'tasks': tasks[room_name]}, room=request.sid)
    emit('notification', {'message': f"A user has joined room '{room_name}'",
                          'username': data.get('username')},
         room=room_name)

@socketio.on('leave_room')
@login_required
def handle_leave(data):
    room_name = data['room']
    authorize_room(room_name)
    leave_room(room_name)
    emit('notification', {'message': f"A user has left room '{room_name}'",
                          'username': data.get('username')},
         room=room_name)

@socketio.on('add_task')
@login_required
def handle_add_task(data):
    room_name, text = data['room'], data['text']
    authorize_room(room_name)
    task = {'id': next_id[room_name], 'text': text, 'done': False}
    tasks[room_name].append(task)
    next_id[room_name] += 1
    emit('task_added', task, room=room_name)
    emit('notification', {'message': f"Task added: '{text}'",
                          'username': data.get('username')},
         room=room_name)

@socketio.on('remove_task')
@login_required
def handle_remove_task(data):
    room_name, t_id = data['room'], data['id']
    authorize_room(room_name)
    tasks[room_name] = [t for t in tasks[room_name] if t['id'] != t_id]
    emit('task_removed', {'id': t_id}, room=room_name)
    emit('notification', {'message': f"Task removed (ID {t_id})",
                          'username': data.get('username')},
         room=room_name)

@socketio.on('toggle_done')
@login_required
def handle_toggle_done(data):
    room_name, t_id = data['room'], data['id']
    authorize_room(room_name)
    for t in tasks[room_name]:
        if t['id'] == t_id:
            t['done'] = not t['done']
            emit('task_toggled', {'id': t_id, 'done': t['done']}, room=room_name)
            state = 'completed' if t['done'] else 'reopened'
            emit('notification', {'message': f"Task {state}: '{t['text']}'",
                                  'username': data.get('username')},
                 room=room_name)
            break

@socketio.on('edit_task')
@login_required
def handle_edit_task(data):
    room_name, t_id, new_text = data['room'], data['id'], data['text']
    authorize_room(room_name)
    for t in tasks[room_name]:
        if t['id'] == t_id:
            t['text'] = new_text
            emit('task_edited', {'id': t_id, 'text': new_text}, room=room_name)
            emit('notification', {'message': f"Task edited: '{new_text}'",
                                  'username': data.get('username')},
                 room=room_name)
            break

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    socketio.run(app, debug=True)
