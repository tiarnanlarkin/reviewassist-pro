from flask import Blueprint, request, jsonify, current_app
from src.models.user import db
from src.models.auth import AuthUser, UserSession, Notification, UserRole
from datetime import datetime, timedelta
from functools import wraps
import re

auth_bp = Blueprint('auth', __name__)

def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password):
    """Validate password strength"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number"
    return True, "Password is valid"

def token_required(f):
    """Decorator to require authentication token"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Check for token in Authorization header
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]  # Bearer <token>
            except IndexError:
                return jsonify({'error': 'Invalid token format'}), 401
        
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        
        try:
            current_user = AuthUser.verify_token(token)
            if current_user is None:
                return jsonify({'error': 'Token is invalid or expired'}), 401
            
            # Update last login
            current_user.last_login = datetime.utcnow()
            db.session.commit()
            
        except Exception as e:
            return jsonify({'error': 'Token verification failed'}), 401
        
        return f(current_user, *args, **kwargs)
    
    return decorated

def role_required(required_role):
    """Decorator to require specific role"""
    def decorator(f):
        @wraps(f)
        def decorated(current_user, *args, **kwargs):
            if not current_user.has_permission(required_role):
                return jsonify({'error': 'Insufficient permissions'}), 403
            return f(current_user, *args, **kwargs)
        return decorated
    return decorator

@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['email', 'password', 'first_name', 'last_name']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        email = data['email'].lower().strip()
        password = data['password']
        first_name = data['first_name'].strip()
        last_name = data['last_name'].strip()
        role = data.get('role', 'agent')
        
        # Validate email format
        if not validate_email(email):
            return jsonify({'error': 'Invalid email format'}), 400
        
        # Validate password strength
        is_valid, message = validate_password(password)
        if not is_valid:
            return jsonify({'error': message}), 400
        
        # Check if user already exists
        if AuthUser.query.filter_by(email=email).first():
            return jsonify({'error': 'User with this email already exists'}), 409
        
        # Validate role
        try:
            user_role = UserRole(role)
        except ValueError:
            user_role = UserRole.AGENT
        
        # Create new user
        user = AuthUser(
            email=email,
            first_name=first_name,
            last_name=last_name,
            role=user_role
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        # Generate token
        token = user.generate_token()
        
        # Create welcome notification
        notification = Notification(
            user_id=user.id,
            title="Welcome to ReviewAssist Pro!",
            message=f"Welcome {first_name}! Your account has been created successfully.",
            type="success"
        )
        db.session.add(notification)
        db.session.commit()
        
        return jsonify({
            'message': 'User registered successfully',
            'user': user.to_dict(),
            'token': token
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    """Authenticate user and return token"""
    try:
        data = request.get_json()
        
        email = data.get('email', '').lower().strip()
        password = data.get('password', '')
        
        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400
        
        # Find user
        user = AuthUser.query.filter_by(email=email).first()
        
        if not user or not user.check_password(password):
            return jsonify({'error': 'Invalid email or password'}), 401
        
        if not user.is_active:
            return jsonify({'error': 'Account is deactivated'}), 401
        
        # Update last login
        user.last_login = datetime.utcnow()
        
        # Generate token
        token = user.generate_token()
        
        # Create session record
        session = UserSession(
            user_id=user.id,
            token_hash=token[:50],  # Store partial token for tracking
            expires_at=datetime.utcnow() + timedelta(hours=24),
            user_agent=request.headers.get('User-Agent', ''),
            ip_address=request.remote_addr
        )
        
        db.session.add(session)
        db.session.commit()
        
        return jsonify({
            'message': 'Login successful',
            'user': user.to_dict(),
            'token': token
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/logout', methods=['POST'])
@token_required
def logout(current_user):
    """Logout user and invalidate token"""
    try:
        # In a real implementation, you would add the token to a blacklist
        # For now, we'll just return success
        return jsonify({'message': 'Logout successful'}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/profile', methods=['GET'])
@token_required
def get_profile(current_user):
    """Get current user profile"""
    try:
        return jsonify({
            'user': current_user.to_dict(include_sensitive=True)
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/profile', methods=['PUT'])
@token_required
def update_profile(current_user):
    """Update user profile"""
    try:
        data = request.get_json()
        
        # Update allowed fields
        if 'first_name' in data:
            current_user.first_name = data['first_name'].strip()
        
        if 'last_name' in data:
            current_user.last_name = data['last_name'].strip()
        
        if 'email' in data:
            new_email = data['email'].lower().strip()
            if new_email != current_user.email:
                if not validate_email(new_email):
                    return jsonify({'error': 'Invalid email format'}), 400
                
                # Check if email is already taken
                existing_user = User.query.filter_by(email=new_email).first()
                if existing_user and existing_user.id != current_user.id:
                    return jsonify({'error': 'Email is already taken'}), 409
                
                current_user.email = new_email
        
        current_user.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': 'Profile updated successfully',
            'user': current_user.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/change-password', methods=['POST'])
@token_required
def change_password(current_user):
    """Change user password"""
    try:
        data = request.get_json()
        
        current_password = data.get('current_password')
        new_password = data.get('new_password')
        
        if not current_password or not new_password:
            return jsonify({'error': 'Current password and new password are required'}), 400
        
        # Verify current password
        if not current_user.check_password(current_password):
            return jsonify({'error': 'Current password is incorrect'}), 401
        
        # Validate new password
        is_valid, message = validate_password(new_password)
        if not is_valid:
            return jsonify({'error': message}), 400
        
        # Update password
        current_user.set_password(new_password)
        current_user.updated_at = datetime.utcnow()
        db.session.commit()
        
        # Create notification
        notification = Notification(
            user_id=current_user.id,
            title="Password Changed",
            message="Your password has been changed successfully.",
            type="info"
        )
        db.session.add(notification)
        db.session.commit()
        
        return jsonify({'message': 'Password changed successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/users', methods=['GET'])
@token_required
@role_required(UserRole.MANAGER)
def get_users(current_user):
    """Get all users (Manager+ only)"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        users = AuthUser.query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        return jsonify({
            'users': [user.to_dict() for user in users.items],
            'total': users.total,
            'pages': users.pages,
            'current_page': page
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/users/<int:user_id>/role', methods=['PUT'])
@token_required
@role_required(UserRole.ADMIN)
def update_user_role(current_user, user_id):
    """Update user role (Admin only)"""
    try:
        data = request.get_json()
        new_role = data.get('role')
        
        if not new_role:
            return jsonify({'error': 'Role is required'}), 400
        
        try:
            role_enum = UserRole(new_role)
        except ValueError:
            return jsonify({'error': 'Invalid role'}), 400
        
        user = AuthUser.query.get_or_404(user_id)
        user.role = role_enum
        user.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        # Create notification
        notification = Notification(
            user_id=user.id,
            title="Role Updated",
            message=f"Your role has been updated to {role_enum.value}.",
            type="info"
        )
        db.session.add(notification)
        db.session.commit()
        
        return jsonify({
            'message': 'User role updated successfully',
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/notifications', methods=['GET'])
@token_required
def get_notifications(current_user):
    """Get user notifications"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        unread_only = request.args.get('unread_only', 'false').lower() == 'true'
        
        query = Notification.query.filter_by(user_id=current_user.id)
        
        if unread_only:
            query = query.filter_by(is_read=False)
        
        notifications = query.order_by(Notification.created_at.desc()).paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        return jsonify({
            'notifications': [notification.to_dict() for notification in notifications.items],
            'total': notifications.total,
            'pages': notifications.pages,
            'current_page': page,
            'unread_count': Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/notifications/<int:notification_id>/read', methods=['POST'])
@token_required
def mark_notification_read(current_user, notification_id):
    """Mark notification as read"""
    try:
        notification = Notification.query.filter_by(
            id=notification_id,
            user_id=current_user.id
        ).first_or_404()
        
        notification.mark_as_read()
        
        return jsonify({'message': 'Notification marked as read'}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/notifications/mark-all-read', methods=['POST'])
@token_required
def mark_all_notifications_read(current_user):
    """Mark all notifications as read"""
    try:
        notifications = Notification.query.filter_by(
            user_id=current_user.id,
            is_read=False
        ).all()
        
        for notification in notifications:
            notification.is_read = True
            notification.read_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({'message': f'Marked {len(notifications)} notifications as read'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/seed-auth-data', methods=['POST'])
def seed_auth_data():
    """Seed authentication data for demo purposes"""
    try:
        # Create demo users if they don't exist
        demo_users = [
            {
                'email': 'admin@reviewassist.com',
                'password': 'Admin123!',
                'first_name': 'Admin',
                'last_name': 'User',
                'role': UserRole.ADMIN
            },
            {
                'email': 'manager@reviewassist.com',
                'password': 'Manager123!',
                'first_name': 'Manager',
                'last_name': 'User',
                'role': UserRole.MANAGER
            },
            {
                'email': 'agent@reviewassist.com',
                'password': 'Agent123!',
                'first_name': 'Agent',
                'last_name': 'User',
                'role': UserRole.AGENT
            }
        ]
        
        created_users = []
        for user_data in demo_users:
            existing_user = AuthUser.query.filter_by(email=user_data['email']).first()
            if not existing_user:
                user = AuthUser(
                    email=user_data['email'],
                    first_name=user_data['first_name'],
                    last_name=user_data['last_name'],
                    role=user_data['role']
                )
                user.set_password(user_data['password'])
                db.session.add(user)
                created_users.append(user_data['email'])
        
        db.session.commit()
        
        return jsonify({
            'message': 'Demo authentication data seeded successfully',
            'created_users': created_users
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

