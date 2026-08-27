import eventlet
eventlet.monkey_patch()

import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from flask import Flask, redirect, render_template, url_for, request
from flask_login import LoginManager, login_required, current_user
from flask_migrate import Migrate
from flask_socketio import SocketIO, emit, join_room

from extensions import db
from models import User, Room, Task
from authorize import authorize_room, authorize_task
from auth import auth_bp
from room import room_bp


# ─────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────

load_dotenv()

app = Flask(__name__)

app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key")

database_url = os.getenv("DATABASE_URL", "")

if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Only require SSL for PostgreSQL.
if database_url.startswith("postgresql://"):
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "connect_args": {
            "sslmode": "require"
        }
    }


# ─────────────────────────────────────────────────────────────
# Extensions
# ─────────────────────────────────────────────────────────────

db.init_app(app)

migrate = Migrate(app, db)

login_manager = LoginManager(app)
login_manager.login_view = "auth.login"

socketio = SocketIO(
    app,
    async_mode="eventlet"
)


# ─────────────────────────────────────────────────────────────
# Authentication
# ─────────────────────────────────────────────────────────────

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# ─────────────────────────────────────────────────────────────
# Blueprints
# ─────────────────────────────────────────────────────────────

app.register_blueprint(auth_bp)
app.register_blueprint(room_bp)


# ─────────────────────────────────────────────────────────────
# Context processors
# ─────────────────────────────────────────────────────────────

@app.context_processor
def inject_current_year():
    return {
        "current_year": datetime.now(timezone.utc).year
    }


# ─────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────

@app.route("/welcome")
def landing():
    return render_template("landing.html")


@app.route("/")
def root():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    return redirect(url_for("landing"))


@app.route("/index")
@login_required
def index():
    rooms = current_user.rooms.all()

    return render_template(
        "index.html",
        rooms=rooms,
        current_username=current_user.username
    )


# ─────────────────────────────────────────────────────────────
# Socket.IO Events
# ─────────────────────────────────────────────────────────────

@socketio.on("join_room")
@login_required
def handle_join(data):
    room_name = data.get("room")

    if not room_name:
        return

    room = authorize_room(room_name)

    join_room(room_name)

    tasks_list = [
        task.to_dict()
        for task in room.tasks
    ]

    tasks_list.sort(
        key=lambda task: (
            task["due_date"] is None,
            task["due_date"]
        )
    )

    emit(
        "room_data",
        {"tasks": tasks_list},
        room=request.sid
    )

    emit(
        "notification",
        {
            "message": (
                f"{current_user.username} "
                f"joined room '{room_name}'"
            ),
            "username": current_user.username
        },
        room=room_name
    )


@socketio.on("add_task")
@login_required
def handle_add_task(data):
    room_name = data.get("room")
    text = (data.get("text") or "").strip()
    due_iso = data.get("due_date")

    if not room_name or not text:
        return

    room = authorize_room(room_name)

    try:
        due = (
            datetime.fromisoformat(due_iso).date()
            if due_iso
            else None
        )
    except ValueError:
        return

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

    emit(
        "task_added",
        new_task.to_dict(),
        room=room_name
    )

    emit(
        "notification",
        {
            "message": (
                f"{current_user.username} "
                f"added: '{text}'"
            ),
            "username": current_user.username
        },
        room=room_name
    )


@socketio.on("remove_task")
@login_required
def handle_remove_task(data):
    room_name = data.get("room")
    task_id = data.get("id")

    if not room_name or not task_id:
        return

    room = authorize_room(room_name)

    task = db.session.get(Task, task_id)

    if not task:
        return

    # Critical authorization check:
    # task must actually belong to the selected room.
    authorize_task(task, room)

    db.session.delete(task)
    db.session.commit()

    emit(
        "task_removed",
        {"id": task_id},
        room=room_name
    )

    emit(
        "notification",
        {
            "message": (
                f"{current_user.username} "
                f"removed task {task_id}"
            ),
            "username": current_user.username
        },
        room=room_name
    )


@socketio.on("toggle_done")
@login_required
def handle_toggle_done(data):
    room_name = data.get("room")
    task_id = data.get("id")

    if not room_name or not task_id:
        return

    room = authorize_room(room_name)

    task = db.session.get(Task, task_id)

    if not task:
        return

    # Critical authorization check.
    authorize_task(task, room)

    task.done = not task.done
    task.last_editor = current_user

    db.session.commit()

    emit(
        "task_toggled",
        {
            "id": task.id,
            "done": task.done
        },
        room=room_name
    )

    state = "completed" if task.done else "reopened"

    emit(
        "notification",
        {
            "message": (
                f"{current_user.username} "
                f"{state} '{task.text}'"
            ),
            "username": current_user.username
        },
        room=room_name
    )


@socketio.on("edit_task")
@login_required
def handle_edit_task(data):
    room_name = data.get("room")
    task_id = data.get("id")
    new_text = (data.get("text") or "").strip()
    due_iso = data.get("due_date")

    if not room_name or not task_id or not new_text:
        return

    room = authorize_room(room_name)

    task = db.session.get(Task, task_id)

    if not task:
        return

    # Critical authorization check.
    authorize_task(task, room)

    try:
        due = (
            datetime.fromisoformat(due_iso).date()
            if due_iso
            else None
        )
    except ValueError:
        return

    task.text = new_text
    task.due_date = due
    task.last_editor = current_user

    db.session.commit()

    emit(
        "task_edited",
        {
            "id": task.id,
            "text": task.text,
            "due_date": (
                task.due_date.isoformat()
                if task.due_date
                else None
            )
        },
        room=room_name
    )

    emit(
        "notification",
        {
            "message": (
                f"{current_user.username} "
                f"edited: '{new_text}'"
            ),
            "username": current_user.username
        },
        room=room_name
    )


@socketio.on("typing")
@login_required
def handle_typing(data):
    room_name = data.get("room")

    if not room_name:
        return

    authorize_room(room_name)

    # Never trust username supplied by the browser.
    emit(
        "user_typing",
        {
            "username": current_user.username
        },
        room=room_name,
        include_self=False
    )


@socketio.on("stop_typing")
@login_required
def handle_stop_typing(data):
    room_name = data.get("room")

    if not room_name:
        return

    authorize_room(room_name)

    emit(
        "user_stop_typing",
        {},
        room=room_name,
        include_self=False
    )


# ─────────────────────────────────────────────────────────────
# Run locally
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    socketio.run(
        app,
        debug=False
    )