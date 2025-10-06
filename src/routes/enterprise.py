from flask import Blueprint, request, jsonify, current_app
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import uuid
import json
from functools import wraps

from src.models.enterprise import (
    Organization, Team, OrganizationUser, TeamMember, BusinessLocation,
    Permission, Role, AuditLog, SSOProvider, WhiteLabelConfig,
    OrganizationTier, PermissionType, AuditAction
)
from src.models.auth import AuthUser, UserRole
from src.routes.auth import token_required

enterprise_bp = Blueprint('enterprise', __name__)
db = SQLAlchemy()

def organization_required(f):
    """Decorator to ensure user belongs to an organization"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get organization from request or user context
        org_id = request.headers.get('X-Organization-ID')
        if not org_id:
            return jsonify({'error': 'Organization ID required'}), 400
        
        # Verify user has access to this organization
        user_id = request.current_user['id']
        org_user = OrganizationUser.query.filter_by(
            user_id=user_id,
            organization_id=org_id,
            is_active=True
        ).first()
        
        if not org_user:
            return jsonify({'error': 'Access denied to organization'}), 403
        
        request.current_organization = org_user.organization
        request.current_org_user = org_user
        return f(*args, **kwargs)
    
    return decorated_function

def permission_required(resource, action):
    """Decorator to check specific permissions"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(request, 'current_org_user'):
                return jsonify({'error': 'Organization context required'}), 400
            
            # Check if user has required permission
            if not has_permission(request.current_org_user, resource, action):
                return jsonify({'error': 'Insufficient permissions'}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def has_permission(org_user, resource, action):
    """Check if organization user has specific permission"""
    # System admins have all permissions
    if org_user.role == 'admin':
        return True
    
    # Check user's direct permissions
    for perm in org_user.permissions:
        if perm.get('resource') == resource and perm.get('action') == action:
            return True
    
    # Check role-based permissions
    role = Role.query.filter_by(
        organization_id=org_user.organization_id,
        name=org_user.role
    ).first()
    
    if role:
        for perm_id in role.permissions:
            permission = Permission.query.get(perm_id)
            if permission and permission.resource == resource and permission.action.value == action:
                return True
    
    return False

def log_audit_event(action, resource_type, resource_id=None, details=None):
    """Log audit event"""
    try:
        audit_log = AuditLog(
            organization_id=request.current_organization.id,
            user_id=request.current_user['id'],
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', '')
        )
        db.session.add(audit_log)
        db.session.commit()
    except Exception as e:
        print(f"Failed to log audit event: {e}")

# Organization Management
@enterprise_bp.route('/organizations', methods=['GET'])
@token_required
def get_organizations():
    """Get organizations for current user"""
    try:
        user_id = request.current_user['id']
        
        org_users = OrganizationUser.query.filter_by(
            user_id=user_id,
            is_active=True
        ).all()
        
        organizations = []
        for org_user in org_users:
            org_data = org_user.organization.to_dict()
            org_data['user_role'] = org_user.role
            org_data['user_permissions'] = org_user.permissions
            organizations.append(org_data)
        
        return jsonify({
            'organizations': organizations,
            'total': len(organizations)
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@enterprise_bp.route('/organizations', methods=['POST'])
@token_required
def create_organization():
    """Create new organization"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('name'):
            return jsonify({'error': 'Organization name is required'}), 400
        
        # Generate slug from name
        slug = data['name'].lower().replace(' ', '-').replace('_', '-')
        
        # Check if slug already exists
        existing_org = Organization.query.filter_by(slug=slug).first()
        if existing_org:
            slug = f"{slug}-{uuid.uuid4().hex[:8]}"
        
        # Create organization
        organization = Organization(
            name=data['name'],
            slug=slug,
            description=data.get('description'),
            tier=OrganizationTier(data.get('tier', 'starter')),
            primary_color=data.get('primary_color'),
            secondary_color=data.get('secondary_color'),
            settings=data.get('settings', {})
        )
        
        db.session.add(organization)
        db.session.flush()  # Get the ID
        
        # Add current user as admin
        org_user = OrganizationUser(
            organization_id=organization.id,
            user_id=request.current_user['id'],
            role='admin',
            permissions=[]
        )
        
        db.session.add(org_user)
        db.session.commit()
        
        # Log audit event
        log_audit_event(
            AuditAction.CREATE,
            'organization',
            organization.id,
            {'name': organization.name}
        )
        
        return jsonify({
            'message': 'Organization created successfully',
            'organization': organization.to_dict()
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@enterprise_bp.route('/organizations/<org_id>', methods=['GET'])
@token_required
@organization_required
def get_organization(org_id):
    """Get organization details"""
    try:
        organization = request.current_organization
        
        # Get additional stats
        stats = {
            'total_users': OrganizationUser.query.filter_by(
                organization_id=org_id,
                is_active=True
            ).count(),
            'total_teams': Team.query.filter_by(
                organization_id=org_id,
                is_active=True
            ).count(),
            'total_locations': BusinessLocation.query.filter_by(
                organization_id=org_id,
                is_active=True
            ).count()
        }
        
        org_data = organization.to_dict()
        org_data['stats'] = stats
        
        return jsonify({'organization': org_data})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@enterprise_bp.route('/organizations/<org_id>', methods=['PUT'])
@token_required
@organization_required
@permission_required('organization', 'write')
def update_organization(org_id):
    """Update organization"""
    try:
        data = request.get_json()
        organization = request.current_organization
        
        # Update fields
        if 'name' in data:
            organization.name = data['name']
        if 'description' in data:
            organization.description = data['description']
        if 'primary_color' in data:
            organization.primary_color = data['primary_color']
        if 'secondary_color' in data:
            organization.secondary_color = data['secondary_color']
        if 'settings' in data:
            organization.settings = data['settings']
        
        organization.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        # Log audit event
        log_audit_event(
            AuditAction.UPDATE,
            'organization',
            organization.id,
            {'updated_fields': list(data.keys())}
        )
        
        return jsonify({
            'message': 'Organization updated successfully',
            'organization': organization.to_dict()
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Team Management
@enterprise_bp.route('/organizations/<org_id>/teams', methods=['GET'])
@token_required
@organization_required
@permission_required('teams', 'read')
def get_teams(org_id):
    """Get teams for organization"""
    try:
        teams = Team.query.filter_by(
            organization_id=org_id,
            is_active=True
        ).all()
        
        teams_data = []
        for team in teams:
            team_data = team.to_dict()
            team_data['member_count'] = TeamMember.query.filter_by(team_id=team.id).count()
            teams_data.append(team_data)
        
        return jsonify({
            'teams': teams_data,
            'total': len(teams_data)
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@enterprise_bp.route('/organizations/<org_id>/teams', methods=['POST'])
@token_required
@organization_required
@permission_required('teams', 'write')
def create_team(org_id):
    """Create new team"""
    try:
        data = request.get_json()
        
        if not data.get('name'):
            return jsonify({'error': 'Team name is required'}), 400
        
        team = Team(
            organization_id=org_id,
            name=data['name'],
            description=data.get('description'),
            settings=data.get('settings', {})
        )
        
        db.session.add(team)
        db.session.commit()
        
        # Log audit event
        log_audit_event(
            AuditAction.CREATE,
            'team',
            team.id,
            {'name': team.name}
        )
        
        return jsonify({
            'message': 'Team created successfully',
            'team': team.to_dict()
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# User Management
@enterprise_bp.route('/organizations/<org_id>/users', methods=['GET'])
@token_required
@organization_required
@permission_required('users', 'read')
def get_organization_users(org_id):
    """Get users for organization"""
    try:
        org_users = OrganizationUser.query.filter_by(
            organization_id=org_id,
            is_active=True
        ).all()
        
        users_data = []
        for org_user in org_users:
            # Get user details from AuthUser
            auth_user = AuthUser.query.get(org_user.user_id)
            if auth_user:
                user_data = org_user.to_dict()
                user_data['email'] = auth_user.email
                user_data['full_name'] = auth_user.full_name
                user_data['last_login'] = auth_user.last_login.isoformat() if auth_user.last_login else None
                users_data.append(user_data)
        
        return jsonify({
            'users': users_data,
            'total': len(users_data)
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@enterprise_bp.route('/organizations/<org_id>/users/<user_id>/role', methods=['PUT'])
@token_required
@organization_required
@permission_required('users', 'write')
def update_user_role(org_id, user_id):
    """Update user role in organization"""
    try:
        data = request.get_json()
        new_role = data.get('role')
        
        if not new_role:
            return jsonify({'error': 'Role is required'}), 400
        
        org_user = OrganizationUser.query.filter_by(
            organization_id=org_id,
            user_id=user_id
        ).first()
        
        if not org_user:
            return jsonify({'error': 'User not found in organization'}), 404
        
        old_role = org_user.role
        org_user.role = new_role
        
        db.session.commit()
        
        # Log audit event
        log_audit_event(
            AuditAction.UPDATE,
            'user_role',
            user_id,
            {'old_role': old_role, 'new_role': new_role}
        )
        
        return jsonify({
            'message': 'User role updated successfully',
            'user': org_user.to_dict()
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Permissions Management
@enterprise_bp.route('/permissions', methods=['GET'])
@token_required
def get_permissions():
    """Get all available permissions"""
    try:
        permissions = Permission.query.all()
        return jsonify({
            'permissions': [perm.to_dict() for perm in permissions]
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@enterprise_bp.route('/organizations/<org_id>/roles', methods=['GET'])
@token_required
@organization_required
@permission_required('roles', 'read')
def get_roles(org_id):
    """Get roles for organization"""
    try:
        roles = Role.query.filter_by(organization_id=org_id).all()
        return jsonify({
            'roles': [role.to_dict() for role in roles]
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Audit Logs
@enterprise_bp.route('/organizations/<org_id>/audit-logs', methods=['GET'])
@token_required
@organization_required
@permission_required('audit', 'read')
def get_audit_logs(org_id):
    """Get audit logs for organization"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        
        # Filter parameters
        action = request.args.get('action')
        resource_type = request.args.get('resource_type')
        user_id = request.args.get('user_id')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        query = AuditLog.query.filter_by(organization_id=org_id)
        
        if action:
            query = query.filter(AuditLog.action == AuditAction(action))
        if resource_type:
            query = query.filter(AuditLog.resource_type == resource_type)
        if user_id:
            query = query.filter(AuditLog.user_id == user_id)
        if start_date:
            query = query.filter(AuditLog.timestamp >= datetime.fromisoformat(start_date))
        if end_date:
            query = query.filter(AuditLog.timestamp <= datetime.fromisoformat(end_date))
        
        query = query.order_by(AuditLog.timestamp.desc())
        
        # Paginate
        audit_logs = query.offset((page - 1) * per_page).limit(per_page).all()
        total = query.count()
        
        return jsonify({
            'audit_logs': [log.to_dict() for log in audit_logs],
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': (total + per_page - 1) // per_page
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# White Label Configuration
@enterprise_bp.route('/organizations/<org_id>/whitelabel', methods=['GET'])
@token_required
@organization_required
@permission_required('branding', 'read')
def get_whitelabel_config(org_id):
    """Get white label configuration"""
    try:
        config = WhiteLabelConfig.query.filter_by(organization_id=org_id).first()
        
        if not config:
            return jsonify({'whitelabel_config': None})
        
        return jsonify({'whitelabel_config': config.to_dict()})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@enterprise_bp.route('/organizations/<org_id>/whitelabel', methods=['POST', 'PUT'])
@token_required
@organization_required
@permission_required('branding', 'write')
def update_whitelabel_config(org_id):
    """Update white label configuration"""
    try:
        data = request.get_json()
        
        config = WhiteLabelConfig.query.filter_by(organization_id=org_id).first()
        
        if not config:
            config = WhiteLabelConfig(organization_id=org_id)
            db.session.add(config)
        
        # Update fields
        for field in ['app_name', 'logo_url', 'favicon_url', 'primary_color', 
                     'secondary_color', 'accent_color', 'custom_css', 
                     'email_logo_url', 'email_footer_text', 'mobile_app_name',
                     'mobile_logo_url', 'mobile_splash_url', 'custom_domain']:
            if field in data:
                setattr(config, field, data[field])
        
        config.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        # Log audit event
        log_audit_event(
            AuditAction.UPDATE,
            'whitelabel_config',
            config.id,
            {'updated_fields': list(data.keys())}
        )
        
        return jsonify({
            'message': 'White label configuration updated successfully',
            'whitelabel_config': config.to_dict()
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Business Locations
@enterprise_bp.route('/organizations/<org_id>/locations', methods=['GET'])
@token_required
@organization_required
@permission_required('locations', 'read')
def get_business_locations(org_id):
    """Get business locations for organization"""
    try:
        locations = BusinessLocation.query.filter_by(
            organization_id=org_id,
            is_active=True
        ).all()
        
        return jsonify({
            'locations': [location.to_dict() for location in locations],
            'total': len(locations)
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@enterprise_bp.route('/organizations/<org_id>/locations', methods=['POST'])
@token_required
@organization_required
@permission_required('locations', 'write')
def create_business_location(org_id):
    """Create new business location"""
    try:
        data = request.get_json()
        
        if not data.get('name'):
            return jsonify({'error': 'Location name is required'}), 400
        
        location = BusinessLocation(
            organization_id=org_id,
            name=data['name'],
            address=data.get('address'),
            phone=data.get('phone'),
            email=data.get('email'),
            website=data.get('website'),
            google_place_id=data.get('google_place_id'),
            yelp_business_id=data.get('yelp_business_id'),
            facebook_page_id=data.get('facebook_page_id'),
            tripadvisor_location_id=data.get('tripadvisor_location_id'),
            settings=data.get('settings', {})
        )
        
        db.session.add(location)
        db.session.commit()
        
        # Log audit event
        log_audit_event(
            AuditAction.CREATE,
            'business_location',
            location.id,
            {'name': location.name}
        )
        
        return jsonify({
            'message': 'Business location created successfully',
            'location': location.to_dict()
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Initialize default permissions
@enterprise_bp.route('/admin/init-permissions', methods=['POST'])
@token_required
def init_default_permissions():
    """Initialize default permissions (admin only)"""
    try:
        # Check if user is system admin
        user = AuthUser.query.get(request.current_user['id'])
        if not user or user.role != UserRole.ADMIN:
            return jsonify({'error': 'Admin access required'}), 403
        
        default_permissions = [
            # Reviews
            {'name': 'reviews.read', 'resource': 'reviews', 'action': PermissionType.READ, 'description': 'View reviews'},
            {'name': 'reviews.write', 'resource': 'reviews', 'action': PermissionType.WRITE, 'description': 'Create and edit reviews'},
            {'name': 'reviews.delete', 'resource': 'reviews', 'action': PermissionType.DELETE, 'description': 'Delete reviews'},
            
            # Analytics
            {'name': 'analytics.read', 'resource': 'analytics', 'action': PermissionType.READ, 'description': 'View analytics'},
            {'name': 'analytics.export', 'resource': 'analytics', 'action': PermissionType.WRITE, 'description': 'Export analytics data'},
            
            # Users
            {'name': 'users.read', 'resource': 'users', 'action': PermissionType.READ, 'description': 'View users'},
            {'name': 'users.write', 'resource': 'users', 'action': PermissionType.WRITE, 'description': 'Manage users'},
            {'name': 'users.delete', 'resource': 'users', 'action': PermissionType.DELETE, 'description': 'Remove users'},
            
            # Teams
            {'name': 'teams.read', 'resource': 'teams', 'action': PermissionType.READ, 'description': 'View teams'},
            {'name': 'teams.write', 'resource': 'teams', 'action': PermissionType.WRITE, 'description': 'Manage teams'},
            {'name': 'teams.delete', 'resource': 'teams', 'action': PermissionType.DELETE, 'description': 'Delete teams'},
            
            # Organization
            {'name': 'organization.read', 'resource': 'organization', 'action': PermissionType.READ, 'description': 'View organization settings'},
            {'name': 'organization.write', 'resource': 'organization', 'action': PermissionType.WRITE, 'description': 'Manage organization settings'},
            
            # Audit
            {'name': 'audit.read', 'resource': 'audit', 'action': PermissionType.READ, 'description': 'View audit logs'},
            
            # Branding
            {'name': 'branding.read', 'resource': 'branding', 'action': PermissionType.READ, 'description': 'View branding settings'},
            {'name': 'branding.write', 'resource': 'branding', 'action': PermissionType.WRITE, 'description': 'Manage branding settings'},
            
            # Locations
            {'name': 'locations.read', 'resource': 'locations', 'action': PermissionType.READ, 'description': 'View business locations'},
            {'name': 'locations.write', 'resource': 'locations', 'action': PermissionType.WRITE, 'description': 'Manage business locations'},
            {'name': 'locations.delete', 'resource': 'locations', 'action': PermissionType.DELETE, 'description': 'Delete business locations'},
        ]
        
        created_count = 0
        for perm_data in default_permissions:
            existing = Permission.query.filter_by(name=perm_data['name']).first()
            if not existing:
                permission = Permission(**perm_data)
                db.session.add(permission)
                created_count += 1
        
        db.session.commit()
        
        return jsonify({
            'message': f'Initialized {created_count} default permissions',
            'total_permissions': len(default_permissions)
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

