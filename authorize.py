from flask import abort
from flask_login import current_user
from models import Room


def authorize_room(room_name):
    room = Room.query.filter_by(name=room_name).first()

    if not room or not current_user.is_authenticated:
        abort(403)

    if not room.members.filter_by(id=current_user.id).first():
        abort(403)

    return room


def authorize_task(task, room):
    if task.room_id != room.id:
        abort(403)

    return task