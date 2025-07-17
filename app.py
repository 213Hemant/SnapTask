import eventlet
eventlet.monkey_patch()


import os
from flask import Flask, redirect, render_template, url_for, request
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_login import LoginManager, login_required, current_user
from datetime import datetime, timezone
from dotenv import load_dotenv
from flask_migrate import Migrate

from extensions import db            # ← your single SQLAlchemy instance
from models import User, Room, Task
from authorize import authorize_room
from auth import auth_bp
from room import room_bp

# Load .env, including DATABASE_URL
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'secret!')

# Normalize any "postgres://" to "postgresql://"
database_url = os.getenv('DATABASE_URL', '')
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = database_url

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'connect_args': {
        'sslmode': 'require'
    }
}

# ─── Initialize your extensions ───────────────────────────────────────────────

db.init_app(app)                   # initialize the one db instance
migrate = Migrate(app, db)         # Flask‑Migrate

login_manager = LoginManager(app)
login_manager.login_view = 'auth.login'
# socketio = SocketIO(app)
socketio = SocketIO(app, async_mode="eventlet")

# ─── User loader ──────────────────────────────────────────────────────────────

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ─── Blueprints ───────────────────────────────────────────────────────────────

app.register_blueprint(auth_bp)
app.register_blueprint(room_bp)

# ─── Context processors ──────────────────────────────────────────────────────

@app.context_processor
def inject_current_year():
    return {'current_year': datetime.now(timezone.utc).year}

# ─── Routes ──────────────────────────────────────────────────────────────────

@app.route('/welcome')
def landing():
    return render_template('landing.html')

@app.route('/')
def root():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    return redirect(url_for('landing'))

@app.route('/index')
@login_required
def index():
    try:
        rooms = current_user.rooms.all()
    except AttributeError:
        rooms = current_user.rooms
    return render_template(
        'index.html',
        rooms=rooms,
        current_username=current_user.username
    )

# ─── Socket.IO Events ────────────────────────────────────────────────────────

@socketio.on('join_room')
@login_required
def handle_join(data):
    room_name = data['room']
    room = authorize_room(room_name)
    join_room(room_name)
    tasks_list = [t.to_dict() for t in room.tasks]
    tasks_list.sort(key=lambda x: (x['due_date'] is None, x['due_date']))
    emit('room_data', {'tasks': tasks_list}, room=request.sid)
    emit('notification', {
        'message': f"{current_user.username} joined room '{room_name}'",
        'username': current_user.username
    }, room=room_name)

@socketio.on('add_task')
@login_required
def handle_add_task(data):
    room_name = data['room']
    text = data['text']
    due_iso = data.get('due_date')
    room = authorize_room(room_name)
    due = datetime.fromisoformat(due_iso).date() if due_iso else None

    new_task = Task(
        text=text,
        done=False,
        due_date=due,
        room=room,
        creator=current_user,
        last_editor=current_user
    )
    db.session.add(new_task)
    db.session.commit()

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
    room_name = data['room']
    t_id = data['id']
    new_text = data['text']
    due_iso = data.get('due_date')
    authorize_room(room_name)

    task = Task.query.get_or_404(t_id)
    task.text = new_text
    task.due_date = datetime.fromisoformat(due_iso).date() if due_iso else None
    task.last_editor = current_user
    db.session.commit()

    emit('task_edited', {
        'id': t_id,
        'text': new_text,
        'due_date': task.due_date.isoformat() if task.due_date else None
    }, room=room_name)
    emit('notification', {
        'message': f"{current_user.username} edited: '{new_text}'",
        'username': current_user.username
    }, room=room_name)

@socketio.on('typing')
@login_required
def handle_typing(data):
    room_name = data['room']
    authorize_room(room_name)
    emit('user_typing', {'username': data['username']},
         room=room_name, include_self=False)

@socketio.on('stop_typing')
@login_required
def handle_stop_typing(data):
    room_name = data['room']
    authorize_room(room_name)
    emit('user_stop_typing', {}, room=room_name, include_self=False)

# ─── Run the app ─────────────────────────────────────────────────────────────

# At the bottom of app.py, just above socketio.run(app)
if __name__ == '__main__':
    # This will create all tables (users, rooms, tasks, room_members) 
    # if they don't already exist.
    with app.app_context():
        db.drop_all()
        # db.create_all()
        db.create_all()

    socketio.run(app,debug=True)
