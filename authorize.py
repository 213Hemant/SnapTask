from flask import abort
from flask_login import current_user
from models import Room

# Helper: verify user membership
def authorize_room(room_name):
    room = Room.query.filter_by(name=room_name).first()
    if not room or current_user not in room.members:
        abort(403)
    return room