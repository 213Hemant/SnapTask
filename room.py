from flask import Blueprint, request, redirect, url_for, render_template, flash
from flask_login import login_required, current_user
from models import db, Room, User

room_bp = Blueprint('room', __name__)

@room_bp.route('/rooms', methods=['GET', 'POST'])
@login_required
def rooms():
    if request.method == 'POST':
        name = request.form['name'].strip()
        if not name:
            flash('Room name cannot be empty')
        elif Room.query.filter_by(name=name).first():
            flash('Room name already exists.')
        else:
            room = Room(name=name)
            room.members.append(current_user)
            db.session.add(room)
            db.session.commit()
            return redirect(url_for('room.rooms'))
    # GET: show all rooms the user belongs to
    user_rooms = current_user.rooms
    return render_template('rooms.html', rooms=user_rooms)

@room_bp.route('/rooms/<int:room_id>/invite', methods=['POST'])
@login_required
def invite(room_id):
    username = request.form['username'].strip()
    user = User.query.filter_by(username=username).first()
    room = Room.query.get_or_404(room_id)
    if user and user not in room.members:
        room.members.append(user)
        db.session.commit()
        flash(f"User '{username}' invited to room '{room.name}'.")
    else:
        flash('Invalid user or already a member.')
    return redirect(url_for('room.rooms'))