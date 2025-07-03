# models.py
from datetime import datetime
from flask_login import UserMixin
from extensions import db

# Association table: users ↔ rooms
room_members = db.Table(
    'room_members',
    db.Column('user_id',    db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('room_id',    db.Integer, db.ForeignKey('rooms.id'), primary_key=True),
)

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

class Room(db.Model):
    __tablename__ = 'rooms'

    id      = db.Column(db.Integer, primary_key=True)
    name    = db.Column(db.String(100), unique=True, nullable=False)

    members = db.relationship(
        'User',
        secondary=room_members,
        backref=db.backref('rooms', lazy='dynamic'),
        lazy='dynamic',
    )

    tasks   = db.relationship(
        'Task',
        backref='room',
        lazy=True,
        cascade='all, delete-orphan',
    )

class Task(db.Model):
    __tablename__ = 'tasks'

    id             = db.Column(db.Integer, primary_key=True)
    text           = db.Column(db.String(255), nullable=False)
    done           = db.Column(db.Boolean, default=False)
    due_date       = db.Column(db.Date, nullable=True)

    room_id        = db.Column(db.Integer, db.ForeignKey('rooms.id'),    nullable=False)
    creator_id     = db.Column(db.Integer, db.ForeignKey('users.id'),    nullable=False)
    last_editor_id = db.Column(db.Integer, db.ForeignKey('users.id'),    nullable=True)

    created_at     = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at     = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    creator     = db.relationship(
        'User',
        foreign_keys=[creator_id],
        backref=db.backref('created_tasks', lazy=True)
    )
    last_editor = db.relationship(
        'User',
        foreign_keys=[last_editor_id],
        backref=db.backref('edited_tasks',  lazy=True)
    )

    def to_dict(self):
        return {
            'id': self.id,
            'text': self.text,
            'done': self.done,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'created_by': self.creator.username,
            'last_modified_by': (
                self.last_editor.username
                if self.last_editor else self.creator.username
            )
        }
