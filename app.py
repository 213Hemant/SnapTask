# app.py
import os
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_login import LoginManager, login_required, current_user
from datetime import datetime, timezone
from dotenv import load_dotenv

from extensions import db
from models import User, Room, Task
from authorize import authorize_room
from auth import auth_bp
from room import room_bp

# Load environment
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY']            = os.getenv('SECRET_KEY', 'secret!')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'

db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'auth.login'
socketio = SocketIO(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

app.register_blueprint(auth_bp)
app.register_blueprint(room_bp)

@app.context_processor
def inject_current_year():
    return {'current_year': datetime.now(timezone.utc).year}

@app.route('/')
@login_required
def index():
    try:
        rooms = current_user.rooms.all()
    except:
        rooms = current_user.rooms
    return render_template('index.html',
                           rooms=rooms,
                           current_username=current_user.username)

# —— Socket.IO handlers ——

@socketio.on('join_room')
@login_required
def handle_join(data):
    room_name = data['room']
    room = authorize_room(room_name)              # get Room instance
    join_room(room_name)
    # Load persisted tasks
    tasks = [t.to_dict() for t in room.tasks]
    emit('room_data', {'tasks': tasks}, room=request.sid)
    emit('notification', {
        'message': f"{current_user.username} joined room '{room_name}'",
        'username': current_user.username
    }, room=room_name)

@socketio.on('add_task')
@login_required
def handle_add_task(data):
    room_name, text = data['room'], data['text']
    room = authorize_room(room_name)
    # Persist
    new_task = Task(
        text=text,
        done=False,
        room=room,
        creator=current_user,
        last_editor=current_user
    )
    db.session.add(new_task)
    db.session.commit()
    # Broadcast
    emit('task_added', new_task.to_dict(), room=room_name)
    emit('notification', {
        'message': f"{current_user.username} added: '{text}'",
        'username': current_user.username
    }, room=room_name)

@socketio.on('remove_task')
@login_required
def handle_remove_task(data):
    room_name, t_id = data['room'], data['id']
    authorize_room(room_name)
    task = Task.query.get_or_404(t_id)
    db.session.delete(task)
    db.session.commit()
    emit('task_removed', {'id': t_id}, room=room_name)
    emit('notification', {
        'message': f"{current_user.username} removed task {t_id}",
        'username': current_user.username
    }, room=room_name)

@socketio.on('toggle_done')
@login_required
def handle_toggle_done(data):
    room_name, t_id = data['room'], data['id']
    authorize_room(room_name)
    task = Task.query.get_or_404(t_id)
    task.done = not task.done
    task.last_editor = current_user
    db.session.commit()
    emit('task_toggled', {'id': t_id, 'done': task.done}, room=room_name)
    state = 'completed' if task.done else 'reopened'
    emit('notification', {
        'message': f"{current_user.username} {state} '{task.text}'",
        'username': current_user.username
    }, room=room_name)

@socketio.on('edit_task')
@login_required
def handle_edit_task(data):
    room_name, t_id, new_text = data['room'], data['id'], data['text']
    authorize_room(room_name)
    task = Task.query.get_or_404(t_id)
    task.text = new_text
    task.last_editor = current_user
    db.session.commit()
    emit('task_edited', {'id': t_id, 'text': new_text}, room=room_name)
    emit('notification', {
        'message': f"{current_user.username} edited: '{new_text}'",
        'username': current_user.username
    }, room=room_name)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    socketio.run(app, debug=True)
