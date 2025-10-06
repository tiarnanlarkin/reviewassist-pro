from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, JSON, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from enum import Enum as PyEnum
import uuid

Base = declarative_base()

class OrganizationTier(PyEnum):
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"
    CUSTOM = "custom"

class PermissionType(PyEnum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"

class AuditAction(PyEnum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    EXPORT = "export"
    IMPORT = "import"

class Organization(Base):
    __tablename__ = 'organizations'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    tier = Column(Enum(OrganizationTier), default=OrganizationTier.STARTER)
    
    # Branding
    logo_url = Column(String(500))
    primary_color = Column(String(7))  # Hex color
    secondary_color = Column(String(7))
    custom_domain = Column(String(255), unique=True)
    
    # Settings
    settings = Column(JSON, default=dict)
    is_active = Column(Boolean, default=True)
    max_users = Column(Integer, default=5)
    max_locations = Column(Integer, default=1)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    users = relationship("OrganizationUser", back_populates="organization")
    teams = relationship("Team", back_populates="organization")
    locations = relationship("BusinessLocation", back_populates="organization")
    audit_logs = relationship("AuditLog", back_populates="organization")
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'slug': self.slug,
            'description': self.description,
            'tier': self.tier.value if self.tier else None,
            'logo_url': self.logo_url,
            'primary_color': self.primary_color,
            'secondary_color': self.secondary_color,
            'custom_domain': self.custom_domain,
            'settings': self.settings,
            'is_active': self.is_active,
            'max_users': self.max_users,
            'max_locations': self.max_locations,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Team(Base):
    __tablename__ = 'teams'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String(36), ForeignKey('organizations.id'), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    
    # Settings
    settings = Column(JSON, default=dict)
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    organization = relationship("Organization", back_populates="teams")
    members = relationship("TeamMember", back_populates="team")
    
    def to_dict(self):
        return {
            'id': self.id,
            'organization_id': self.organization_id,
            'name': self.name,
            'description': self.description,
            'settings': self.settings,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class OrganizationUser(Base):
    __tablename__ = 'organization_users'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String(36), ForeignKey('organizations.id'), nullable=False)
    user_id = Column(String(36), nullable=False)  # References AuthUser
    role = Column(String(50), default='member')
    
    # Permissions
    permissions = Column(JSON, default=list)
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    joined_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime)
    
    # Relationships
    organization = relationship("Organization", back_populates="users")
    team_memberships = relationship("TeamMember", back_populates="user")
    
    def to_dict(self):
        return {
            'id': self.id,
            'organization_id': self.organization_id,
            'user_id': self.user_id,
            'role': self.role,
            'permissions': self.permissions,
            'is_active': self.is_active,
            'joined_at': self.joined_at.isoformat() if self.joined_at else None,
            'last_active': self.last_active.isoformat() if self.last_active else None
        }

class TeamMember(Base):
    __tablename__ = 'team_members'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    team_id = Column(String(36), ForeignKey('teams.id'), nullable=False)
    user_id = Column(String(36), ForeignKey('organization_users.id'), nullable=False)
    role = Column(String(50), default='member')
    
    # Timestamps
    joined_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    team = relationship("Team", back_populates="members")
    user = relationship("OrganizationUser", back_populates="team_memberships")
    
    def to_dict(self):
        return {
            'id': self.id,
            'team_id': self.team_id,
            'user_id': self.user_id,
            'role': self.role,
            'joined_at': self.joined_at.isoformat() if self.joined_at else None
        }

class BusinessLocation(Base):
    __tablename__ = 'business_locations'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String(36), ForeignKey('organizations.id'), nullable=False)
    name = Column(String(255), nullable=False)
    address = Column(Text)
    phone = Column(String(50))
    email = Column(String(255))
    website = Column(String(500))
    
    # Platform IDs
    google_place_id = Column(String(255))
    yelp_business_id = Column(String(255))
    facebook_page_id = Column(String(255))
    tripadvisor_location_id = Column(String(255))
    
    # Settings
    settings = Column(JSON, default=dict)
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    organization = relationship("Organization", back_populates="locations")
    
    def to_dict(self):
        return {
            'id': self.id,
            'organization_id': self.organization_id,
            'name': self.name,
            'address': self.address,
            'phone': self.phone,
            'email': self.email,
            'website': self.website,
            'google_place_id': self.google_place_id,
            'yelp_business_id': self.yelp_business_id,
            'facebook_page_id': self.facebook_page_id,
            'tripadvisor_location_id': self.tripadvisor_location_id,
            'settings': self.settings,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Permission(Base):
    __tablename__ = 'permissions'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    resource = Column(String(100), nullable=False)  # reviews, analytics, settings, etc.
    action = Column(Enum(PermissionType), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'resource': self.resource,
            'action': self.action.value if self.action else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Role(Base):
    __tablename__ = 'roles'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String(36), ForeignKey('organizations.id'), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    
    # Permissions
    permissions = Column(JSON, default=list)  # List of permission IDs
    is_system_role = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'organization_id': self.organization_id,
            'name': self.name,
            'description': self.description,
            'permissions': self.permissions,
            'is_system_role': self.is_system_role,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class AuditLog(Base):
    __tablename__ = 'audit_logs'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String(36), ForeignKey('organizations.id'), nullable=False)
    user_id = Column(String(36), nullable=False)
    action = Column(Enum(AuditAction), nullable=False)
    resource_type = Column(String(100), nullable=False)
    resource_id = Column(String(36))
    
    # Details
    details = Column(JSON, default=dict)
    ip_address = Column(String(45))
    user_agent = Column(Text)
    
    # Timestamps
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    organization = relationship("Organization", back_populates="audit_logs")
    
    def to_dict(self):
        return {
            'id': self.id,
            'organization_id': self.organization_id,
            'user_id': self.user_id,
            'action': self.action.value if self.action else None,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'details': self.details,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }

class SSOProvider(Base):
    __tablename__ = 'sso_providers'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String(36), ForeignKey('organizations.id'), nullable=False)
    name = Column(String(100), nullable=False)
    provider_type = Column(String(50), nullable=False)  # saml, oauth, oidc
    
    # Configuration
    config = Column(JSON, default=dict)
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'organization_id': self.organization_id,
            'name': self.name,
            'provider_type': self.provider_type,
            'config': self.config,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class WhiteLabelConfig(Base):
    __tablename__ = 'whitelabel_configs'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String(36), ForeignKey('organizations.id'), nullable=False)
    
    # Branding
    app_name = Column(String(255))
    logo_url = Column(String(500))
    favicon_url = Column(String(500))
    primary_color = Column(String(7))
    secondary_color = Column(String(7))
    accent_color = Column(String(7))
    
    # Custom CSS
    custom_css = Column(Text)
    
    # Email branding
    email_logo_url = Column(String(500))
    email_footer_text = Column(Text)
    
    # Mobile app branding
    mobile_app_name = Column(String(255))
    mobile_logo_url = Column(String(500))
    mobile_splash_url = Column(String(500))
    
    # Domain settings
    custom_domain = Column(String(255))
    ssl_certificate = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'organization_id': self.organization_id,
            'app_name': self.app_name,
            'logo_url': self.logo_url,
            'favicon_url': self.favicon_url,
            'primary_color': self.primary_color,
            'secondary_color': self.secondary_color,
            'accent_color': self.accent_color,
            'custom_css': self.custom_css,
            'email_logo_url': self.email_logo_url,
            'email_footer_text': self.email_footer_text,
            'mobile_app_name': self.mobile_app_name,
            'mobile_logo_url': self.mobile_logo_url,
            'mobile_splash_url': self.mobile_splash_url,
            'custom_domain': self.custom_domain,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

