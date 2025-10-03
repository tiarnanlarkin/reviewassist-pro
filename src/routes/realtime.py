from flask import request, current_app
from flask_socketio import SocketIO, emit, join_room, leave_room, disconnect
from src.models.user import db
from src.models.auth import AuthUser
from src.models.realtime import (
    RealtimeNotification, UserActivity, LiveMetrics, ConnectedUser, NotificationType
)
from src.models.review import Review, Analytics
from datetime import datetime, timedelta
import json
import uuid

# Initialize SocketIO
socketio = SocketIO(cors_allowed_origins="*", logger=True, engineio_logger=True)

# Store active connections
active_connections = {}

@socketio.on('connect')
def handle_connect(auth):
    """Handle client connection"""
    try:
        print(f"Client connecting: {request.sid}")
        
        # Get user info from auth token if provided
        user = None
        if auth and 'token' in auth:
            user = AuthUser.verify_token(auth['token'])
        
        if user:
            # Authenticated user
            session_id = str(uuid.uuid4())
            
            # Store connection info
            connected_user = ConnectedUser(
                user_id=user.id,
                session_id=session_id,
                socket_id=request.sid,
                status='online'
            )
            db.session.add(connected_user)
            
            # Log user activity
            activity = UserActivity(
                user_id=user.id,
                activity_type='websocket_connect',
                description=f'User {user.full_name} connected via WebSocket',
                ip_address=request.environ.get('REMOTE_ADDR'),
                user_agent=request.headers.get('User-Agent')
            )
            db.session.add(activity)
            db.session.commit()
            
            # Join user-specific room
            join_room(f"user_{user.id}")
            join_room("authenticated_users")
            
            # Store in active connections
            active_connections[request.sid] = {
                'user_id': user.id,
                'user': user,
                'session_id': session_id,
                'connected_at': datetime.utcnow()
            }
            
            # Send welcome message
            emit('connection_established', {
                'status': 'authenticated',
                'user': user.to_dict(),
                'session_id': session_id,
                'message': 'Connected successfully'
            })
            
            # Broadcast user online status to other users
            socketio.emit('user_status_update', {
                'user_id': user.id,
                'user_name': user.full_name,
                'status': 'online',
                'timestamp': datetime.utcnow().isoformat()
            }, room='authenticated_users', include_self=False)
            
            # Send unread notifications
            send_unread_notifications(user.id)
            
        else:
            # Guest user
            join_room("guests")
            active_connections[request.sid] = {
                'user_id': None,
                'user': None,
                'session_id': str(uuid.uuid4()),
                'connected_at': datetime.utcnow()
            }
            
            emit('connection_established', {
                'status': 'guest',
                'message': 'Connected as guest'
            })
        
        print(f"Client connected successfully: {request.sid}")
        
    except Exception as e:
        print(f"Error in connect handler: {e}")
        emit('error', {'message': 'Connection failed'})
        disconnect()

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    try:
        print(f"Client disconnecting: {request.sid}")
        
        if request.sid in active_connections:
            connection_info = active_connections[request.sid]
            user = connection_info.get('user')
            
            if user:
                # Update connected user status
                connected_user = ConnectedUser.query.filter_by(
                    socket_id=request.sid
                ).first()
                if connected_user:
                    db.session.delete(connected_user)
                
                # Log user activity
                activity = UserActivity(
                    user_id=user.id,
                    activity_type='websocket_disconnect',
                    description=f'User {user.full_name} disconnected from WebSocket',
                    ip_address=request.environ.get('REMOTE_ADDR')
                )
                db.session.add(activity)
                db.session.commit()
                
                # Leave rooms
                leave_room(f"user_{user.id}")
                leave_room("authenticated_users")
                
                # Broadcast user offline status
                socketio.emit('user_status_update', {
                    'user_id': user.id,
                    'user_name': user.full_name,
                    'status': 'offline',
                    'timestamp': datetime.utcnow().isoformat()
                }, room='authenticated_users')
            
            # Remove from active connections
            del active_connections[request.sid]
        
        print(f"Client disconnected: {request.sid}")
        
    except Exception as e:
        print(f"Error in disconnect handler: {e}")

@socketio.on('join_room')
def handle_join_room(data):
    """Handle joining specific rooms"""
    try:
        room = data.get('room')
        if room and request.sid in active_connections:
            join_room(room)
            emit('room_joined', {'room': room, 'status': 'success'})
    except Exception as e:
        emit('error', {'message': f'Failed to join room: {str(e)}'})

@socketio.on('leave_room')
def handle_leave_room(data):
    """Handle leaving specific rooms"""
    try:
        room = data.get('room')
        if room:
            leave_room(room)
            emit('room_left', {'room': room, 'status': 'success'})
    except Exception as e:
        emit('error', {'message': f'Failed to leave room: {str(e)}'})

@socketio.on('update_user_status')
def handle_update_user_status(data):
    """Handle user status updates"""
    try:
        if request.sid in active_connections:
            connection_info = active_connections[request.sid]
            user = connection_info.get('user')
            
            if user:
                status = data.get('status', 'online')
                
                # Update connected user status
                connected_user = ConnectedUser.query.filter_by(
                    socket_id=request.sid
                ).first()
                if connected_user:
                    connected_user.status = status
                    connected_user.last_activity = datetime.utcnow()
                    db.session.commit()
                
                # Broadcast status update
                socketio.emit('user_status_update', {
                    'user_id': user.id,
                    'user_name': user.full_name,
                    'status': status,
                    'timestamp': datetime.utcnow().isoformat()
                }, room='authenticated_users', include_self=False)
                
                emit('status_updated', {'status': status})
    except Exception as e:
        emit('error', {'message': f'Failed to update status: {str(e)}'})

@socketio.on('request_live_metrics')
def handle_request_live_metrics():
    """Send current live metrics to client"""
    try:
        metrics = get_live_metrics()
        emit('live_metrics_update', metrics)
    except Exception as e:
        emit('error', {'message': f'Failed to get metrics: {str(e)}'})

@socketio.on('mark_notification_read')
def handle_mark_notification_read(data):
    """Mark notification as read"""
    try:
        notification_id = data.get('notification_id')
        if notification_id and request.sid in active_connections:
            connection_info = active_connections[request.sid]
            user = connection_info.get('user')
            
            if user:
                notification = RealtimeNotification.query.filter_by(
                    id=notification_id,
                    user_id=user.id
                ).first()
                
                if notification:
                    notification.is_read = True
                    db.session.commit()
                    emit('notification_marked_read', {'notification_id': notification_id})
    except Exception as e:
        emit('error', {'message': f'Failed to mark notification as read: {str(e)}'})

def send_unread_notifications(user_id):
    """Send unread notifications to user"""
    try:
        notifications = RealtimeNotification.query.filter_by(
            user_id=user_id,
            is_read=False
        ).order_by(RealtimeNotification.created_at.desc()).limit(10).all()
        
        if notifications:
            socketio.emit('unread_notifications', {
                'notifications': [notif.to_dict() for notif in notifications],
                'count': len(notifications)
            }, room=f"user_{user_id}")
    except Exception as e:
        print(f"Error sending unread notifications: {e}")

def broadcast_notification(notification_type, title, message, data=None, user_id=None, room=None):
    """Broadcast notification to users"""
    try:
        # Create notification record
        notification = RealtimeNotification(
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            message=message,
            data=data
        )
        db.session.add(notification)
        db.session.commit()
        
        # Broadcast to appropriate room
        if user_id:
            target_room = f"user_{user_id}"
        elif room:
            target_room = room
        else:
            target_room = "authenticated_users"
        
        socketio.emit('new_notification', notification.to_dict(), room=target_room)
        
        return notification
    except Exception as e:
        print(f"Error broadcasting notification: {e}")
        return None

def broadcast_live_metrics():
    """Broadcast updated live metrics to all connected users"""
    try:
        metrics = get_live_metrics()
        socketio.emit('live_metrics_update', metrics, room='authenticated_users')
    except Exception as e:
        print(f"Error broadcasting live metrics: {e}")

def get_live_metrics():
    """Get current live metrics"""
    try:
        # Get review metrics
        total_reviews = Review.query.count()
        today_reviews = Review.query.filter(
            Review.created_at >= datetime.utcnow().date()
        ).count()
        
        # Get response metrics
        responded_reviews = Review.query.filter(
            Review.ai_response.isnot(None)
        ).count()
        response_rate = (responded_reviews / total_reviews * 100) if total_reviews > 0 else 0
        
        # Get average rating
        avg_rating_result = db.session.query(db.func.avg(Review.rating)).scalar()
        avg_rating = round(float(avg_rating_result), 1) if avg_rating_result else 0
        
        # Get connected users count
        connected_users_count = len([conn for conn in active_connections.values() if conn['user_id']])
        
        return {
            'total_reviews': total_reviews,
            'today_reviews': today_reviews,
            'response_rate': round(response_rate, 1),
            'avg_rating': avg_rating,
            'connected_users': connected_users_count,
            'timestamp': datetime.utcnow().isoformat()
        }
    except Exception as e:
        print(f"Error getting live metrics: {e}")
        return {}

def simulate_new_review():
    """Simulate a new review for demo purposes"""
    try:
        # This would be called when a real review comes in
        broadcast_notification(
            NotificationType.NEW_REVIEW,
            "New Review Received",
            "A new 4-star review has been posted on Google",
            data={
                'platform': 'Google',
                'rating': 4,
                'sentiment': 'Positive'
            }
        )
        
        # Update live metrics
        broadcast_live_metrics()
        
    except Exception as e:
        print(f"Error simulating new review: {e}")

def simulate_response_generated(review_id, response_text):
    """Simulate AI response generation"""
    try:
        broadcast_notification(
            NotificationType.RESPONSE_GENERATED,
            "AI Response Generated",
            f"AI response has been generated for review #{review_id}",
            data={
                'review_id': review_id,
                'response_preview': response_text[:100] + "..." if len(response_text) > 100 else response_text
            }
        )
        
        # Update live metrics
        broadcast_live_metrics()
        
    except Exception as e:
        print(f"Error simulating response generation: {e}")

# Utility function to get connected users
def get_connected_users():
    """Get list of currently connected users"""
    connected_users = []
    for connection in active_connections.values():
        if connection['user']:
            connected_users.append({
                'user_id': connection['user'].id,
                'user_name': connection['user'].full_name,
                'connected_at': connection['connected_at'].isoformat()
            })
    return connected_users

