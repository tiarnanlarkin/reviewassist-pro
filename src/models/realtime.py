from src.models.user import db
from datetime import datetime
from enum import Enum

class NotificationType(Enum):
    NEW_REVIEW = "new_review"
    RESPONSE_GENERATED = "response_generated"
    USER_ACTIVITY = "user_activity"
    SYSTEM_ALERT = "system_alert"
    ANALYTICS_UPDATE = "analytics_update"

class RealtimeNotification(db.Model):
    __tablename__ = 'realtime_notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('auth_users.id'), nullable=True)  # None for broadcast
    notification_type = db.Column(db.Enum(NotificationType), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    data = db.Column(db.JSON, nullable=True)  # Additional data payload
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'type': self.notification_type.value,
            'title': self.title,
            'message': self.message,
            'data': self.data,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat(),
            'expires_at': self.expires_at.isoformat() if self.expires_at else None
        }

class UserActivity(db.Model):
    __tablename__ = 'user_activities'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('auth_users.id'), nullable=False)
    activity_type = db.Column(db.String(50), nullable=False)  # login, logout, review_response, etc.
    description = db.Column(db.String(500), nullable=False)
    activity_metadata = db.Column(db.JSON, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'activity_type': self.activity_type,
            'description': self.description,
            'activity_metadata': self.activity_metadata,
            'created_at': self.created_at.isoformat()
        }

class LiveMetrics(db.Model):
    __tablename__ = 'live_metrics'
    
    id = db.Column(db.Integer, primary_key=True)
    metric_name = db.Column(db.String(100), nullable=False)
    metric_value = db.Column(db.Float, nullable=False)
    metric_type = db.Column(db.String(50), nullable=False)  # count, percentage, average, etc.
    category = db.Column(db.String(50), nullable=False)  # reviews, responses, users, etc.
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    activity_metadata = db.Column(db.JSON, nullable=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'metric_name': self.metric_name,
            'metric_value': self.metric_value,
            'metric_type': self.metric_type,
            'category': self.category,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.activity_metadata
        }

class ConnectedUser(db.Model):
    __tablename__ = 'connected_users'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('auth_users.id'), nullable=False)
    session_id = db.Column(db.String(100), nullable=False, unique=True)
    socket_id = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), default='online')  # online, away, busy
    last_activity = db.Column(db.DateTime, default=datetime.utcnow)
    connected_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'session_id': self.session_id,
            'socket_id': self.socket_id,
            'status': self.status,
            'last_activity': self.last_activity.isoformat(),
            'connected_at': self.connected_at.isoformat()
        }

