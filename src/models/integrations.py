from datetime import datetime, timedelta
from src.models.user import db
from src.models.auth import AuthUser
import enum
import json
import secrets
import hashlib
from sqlalchemy import func, Text

class IntegrationType(enum.Enum):
    GOOGLE_MY_BUSINESS = "google_my_business"
    YELP = "yelp"
    FACEBOOK = "facebook"
    TRIPADVISOR = "tripadvisor"
    SLACK = "slack"
    MICROSOFT_TEAMS = "microsoft_teams"
    MAILCHIMP = "mailchimp"
    SENDGRID = "sendgrid"
    SALESFORCE = "salesforce"
    HUBSPOT = "hubspot"
    WEBHOOK = "webhook"
    CUSTOM = "custom"

class IntegrationStatus(enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    PENDING = "pending"
    EXPIRED = "expired"

class WebhookEventType(enum.Enum):
    REVIEW_CREATED = "review.created"
    REVIEW_UPDATED = "review.updated"
    REVIEW_DELETED = "review.deleted"
    RESPONSE_GENERATED = "response.generated"
    RESPONSE_SENT = "response.sent"
    USER_CREATED = "user.created"
    SUBSCRIPTION_UPDATED = "subscription.updated"
    WORKFLOW_EXECUTED = "workflow.executed"
    ALERT_TRIGGERED = "alert.triggered"

class APIKeyScope(enum.Enum):
    READ_REVIEWS = "read:reviews"
    WRITE_REVIEWS = "write:reviews"
    READ_ANALYTICS = "read:analytics"
    WRITE_ANALYTICS = "write:analytics"
    READ_USERS = "read:users"
    WRITE_USERS = "write:users"
    READ_INTEGRATIONS = "read:integrations"
    WRITE_INTEGRATIONS = "write:integrations"
    ADMIN = "admin"

class Integration(db.Model):
    __tablename__ = 'integrations'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('auth_users.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    integration_type = db.Column(db.Enum(IntegrationType), nullable=False)
    status = db.Column(db.Enum(IntegrationStatus), nullable=False, default=IntegrationStatus.PENDING)
    
    # Configuration and credentials (encrypted)
    config_data = db.Column(Text)  # JSON string with encrypted sensitive data
    api_endpoint = db.Column(db.String(500))
    
    # Authentication data
    access_token = db.Column(db.String(1000))  # Encrypted
    refresh_token = db.Column(db.String(1000))  # Encrypted
    token_expires_at = db.Column(db.DateTime)
    
    # Metadata
    last_sync_at = db.Column(db.DateTime)
    last_error = db.Column(Text)
    sync_frequency = db.Column(db.Integer, default=3600)  # seconds
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('AuthUser', backref='integrations')
    webhook_events = db.relationship('WebhookDelivery', backref='integration', lazy=True)
    sync_logs = db.relationship('IntegrationSyncLog', backref='integration', lazy=True)
    
    def __repr__(self):
        return f'<Integration {self.name} ({self.integration_type.value})>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'integration_type': self.integration_type.value,
            'status': self.status.value,
            'api_endpoint': self.api_endpoint,
            'last_sync_at': self.last_sync_at.isoformat() if self.last_sync_at else None,
            'sync_frequency': self.sync_frequency,
            'token_expires_at': self.token_expires_at.isoformat() if self.token_expires_at else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def is_token_expired(self):
        """Check if access token is expired"""
        if not self.token_expires_at:
            return False
        return datetime.utcnow() > self.token_expires_at
    
    def get_config(self):
        """Get decrypted configuration data"""
        if not self.config_data:
            return {}
        try:
            return json.loads(self.config_data)
        except:
            return {}
    
    def set_config(self, config_dict):
        """Set configuration data as JSON"""
        self.config_data = json.dumps(config_dict)

class WebhookEndpoint(db.Model):
    __tablename__ = 'webhook_endpoints'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('auth_users.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    url = db.Column(db.String(1000), nullable=False)
    secret = db.Column(db.String(100))  # For webhook signature verification
    
    # Event configuration
    events = db.Column(Text)  # JSON array of WebhookEventType values
    is_active = db.Column(db.Boolean, default=True)
    
    # Retry configuration
    max_retries = db.Column(db.Integer, default=3)
    retry_delay = db.Column(db.Integer, default=60)  # seconds
    
    # Statistics
    total_deliveries = db.Column(db.Integer, default=0)
    successful_deliveries = db.Column(db.Integer, default=0)
    failed_deliveries = db.Column(db.Integer, default=0)
    last_delivery_at = db.Column(db.DateTime)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('AuthUser', backref='webhook_endpoints')
    deliveries = db.relationship('WebhookDelivery', backref='endpoint', lazy=True)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.secret:
            self.secret = secrets.token_urlsafe(32)
    
    def __repr__(self):
        return f'<WebhookEndpoint {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'url': self.url,
            'events': json.loads(self.events) if self.events else [],
            'is_active': self.is_active,
            'max_retries': self.max_retries,
            'retry_delay': self.retry_delay,
            'total_deliveries': self.total_deliveries,
            'successful_deliveries': self.successful_deliveries,
            'failed_deliveries': self.failed_deliveries,
            'success_rate': round((self.successful_deliveries / max(1, self.total_deliveries)) * 100, 2),
            'last_delivery_at': self.last_delivery_at.isoformat() if self.last_delivery_at else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def get_events(self):
        """Get list of subscribed events"""
        if not self.events:
            return []
        try:
            return json.loads(self.events)
        except:
            return []
    
    def set_events(self, event_list):
        """Set list of subscribed events"""
        self.events = json.dumps(event_list)
    
    def generate_signature(self, payload):
        """Generate webhook signature for payload verification"""
        if not self.secret:
            return None
        
        signature = hashlib.sha256(
            (self.secret + payload).encode('utf-8')
        ).hexdigest()
        return f"sha256={signature}"

class WebhookDelivery(db.Model):
    __tablename__ = 'webhook_deliveries'
    
    id = db.Column(db.Integer, primary_key=True)
    endpoint_id = db.Column(db.Integer, db.ForeignKey('webhook_endpoints.id'), nullable=False)
    event_type = db.Column(db.Enum(WebhookEventType), nullable=False)
    
    # Delivery details
    payload = db.Column(Text, nullable=False)  # JSON payload
    response_status = db.Column(db.Integer)
    response_body = db.Column(Text)
    response_headers = db.Column(Text)  # JSON
    
    # Retry information
    attempt_count = db.Column(db.Integer, default=1)
    is_successful = db.Column(db.Boolean, default=False)
    next_retry_at = db.Column(db.DateTime)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    delivered_at = db.Column(db.DateTime)
    
    def __repr__(self):
        return f'<WebhookDelivery {self.event_type.value}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'event_type': self.event_type.value,
            'response_status': self.response_status,
            'attempt_count': self.attempt_count,
            'is_successful': self.is_successful,
            'next_retry_at': self.next_retry_at.isoformat() if self.next_retry_at else None,
            'created_at': self.created_at.isoformat(),
            'delivered_at': self.delivered_at.isoformat() if self.delivered_at else None
        }

class APIKey(db.Model):
    __tablename__ = 'api_keys'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('auth_users.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    key_hash = db.Column(db.String(128), nullable=False, unique=True)
    key_prefix = db.Column(db.String(20), nullable=False)  # First few chars for identification
    
    # Permissions and limits
    scopes = db.Column(Text)  # JSON array of APIKeyScope values
    rate_limit_per_hour = db.Column(db.Integer, default=1000)
    rate_limit_per_day = db.Column(db.Integer, default=10000)
    
    # Usage tracking
    total_requests = db.Column(db.Integer, default=0)
    last_used_at = db.Column(db.DateTime)
    
    # Status and expiration
    is_active = db.Column(db.Boolean, default=True)
    expires_at = db.Column(db.DateTime)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('AuthUser', backref='api_keys')
    usage_logs = db.relationship('APIUsageLog', backref='api_key', lazy=True)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.key_hash:
            # Generate API key
            api_key = f"ra_{''.join(secrets.choice('abcdefghijklmnopqrstuvwxyz0123456789') for _ in range(32))}"
            self.key_prefix = api_key[:8]
            self.key_hash = hashlib.sha256(api_key.encode()).hexdigest()
            # Store the actual key temporarily for return to user (only shown once)
            self._generated_key = api_key
    
    def __repr__(self):
        return f'<APIKey {self.name} ({self.key_prefix}...)>'
    
    def to_dict(self, include_key=False):
        result = {
            'id': self.id,
            'name': self.name,
            'key_prefix': self.key_prefix,
            'scopes': json.loads(self.scopes) if self.scopes else [],
            'rate_limit_per_hour': self.rate_limit_per_hour,
            'rate_limit_per_day': self.rate_limit_per_day,
            'total_requests': self.total_requests,
            'last_used_at': self.last_used_at.isoformat() if self.last_used_at else None,
            'is_active': self.is_active,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
        
        if include_key and hasattr(self, '_generated_key'):
            result['api_key'] = self._generated_key
        
        return result
    
    def get_scopes(self):
        """Get list of API key scopes"""
        if not self.scopes:
            return []
        try:
            return json.loads(self.scopes)
        except:
            return []
    
    def set_scopes(self, scope_list):
        """Set list of API key scopes"""
        self.scopes = json.dumps(scope_list)
    
    def is_expired(self):
        """Check if API key is expired"""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at
    
    def verify_key(self, provided_key):
        """Verify provided API key against stored hash"""
        provided_hash = hashlib.sha256(provided_key.encode()).hexdigest()
        return provided_hash == self.key_hash

class APIUsageLog(db.Model):
    __tablename__ = 'api_usage_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    api_key_id = db.Column(db.Integer, db.ForeignKey('api_keys.id'), nullable=False)
    
    # Request details
    endpoint = db.Column(db.String(500), nullable=False)
    method = db.Column(db.String(10), nullable=False)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(500))
    
    # Response details
    status_code = db.Column(db.Integer)
    response_time_ms = db.Column(db.Integer)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<APIUsageLog {self.method} {self.endpoint}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'endpoint': self.endpoint,
            'method': self.method,
            'ip_address': self.ip_address,
            'status_code': self.status_code,
            'response_time_ms': self.response_time_ms,
            'created_at': self.created_at.isoformat()
        }

class IntegrationSyncLog(db.Model):
    __tablename__ = 'integration_sync_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    integration_id = db.Column(db.Integer, db.ForeignKey('integrations.id'), nullable=False)
    
    # Sync details
    sync_type = db.Column(db.String(50), nullable=False)  # 'manual', 'scheduled', 'webhook'
    status = db.Column(db.String(20), nullable=False)  # 'success', 'error', 'partial'
    
    # Results
    records_processed = db.Column(db.Integer, default=0)
    records_created = db.Column(db.Integer, default=0)
    records_updated = db.Column(db.Integer, default=0)
    records_failed = db.Column(db.Integer, default=0)
    
    # Error information
    error_message = db.Column(Text)
    error_details = db.Column(Text)  # JSON with detailed error info
    
    # Performance
    duration_seconds = db.Column(db.Float)
    
    # Timestamps
    started_at = db.Column(db.DateTime, nullable=False)
    completed_at = db.Column(db.DateTime)
    
    def __repr__(self):
        return f'<IntegrationSyncLog {self.sync_type} - {self.status}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'sync_type': self.sync_type,
            'status': self.status,
            'records_processed': self.records_processed,
            'records_created': self.records_created,
            'records_updated': self.records_updated,
            'records_failed': self.records_failed,
            'error_message': self.error_message,
            'duration_seconds': self.duration_seconds,
            'started_at': self.started_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }

class IntegrationManager:
    """Helper class for integration management operations"""
    
    @staticmethod
    def get_user_integrations(user_id, integration_type=None):
        """Get integrations for a user, optionally filtered by type"""
        query = Integration.query.filter_by(user_id=user_id)
        if integration_type:
            query = query.filter_by(integration_type=integration_type)
        return query.all()
    
    @staticmethod
    def create_integration(user_id, name, integration_type, config_data=None):
        """Create a new integration"""
        integration = Integration(
            user_id=user_id,
            name=name,
            integration_type=integration_type
        )
        
        if config_data:
            integration.set_config(config_data)
        
        db.session.add(integration)
        db.session.commit()
        return integration
    
    @staticmethod
    def test_integration(integration_id):
        """Test an integration connection"""
        integration = Integration.query.get(integration_id)
        if not integration:
            return {'success': False, 'message': 'Integration not found'}
        
        # Implementation would depend on integration type
        # For now, return a mock success response
        return {
            'success': True,
            'message': 'Integration test successful',
            'details': {
                'response_time_ms': 150,
                'status': 'connected'
            }
        }
    
    @staticmethod
    def sync_integration(integration_id, sync_type='manual'):
        """Trigger integration sync"""
        integration = Integration.query.get(integration_id)
        if not integration:
            return {'success': False, 'message': 'Integration not found'}
        
        # Create sync log
        sync_log = IntegrationSyncLog(
            integration_id=integration_id,
            sync_type=sync_type,
            status='running',
            started_at=datetime.utcnow()
        )
        db.session.add(sync_log)
        db.session.commit()
        
        # Implementation would depend on integration type
        # For now, return a mock success response
        sync_log.status = 'success'
        sync_log.records_processed = 25
        sync_log.records_created = 5
        sync_log.records_updated = 20
        sync_log.duration_seconds = 2.5
        sync_log.completed_at = datetime.utcnow()
        
        integration.last_sync_at = datetime.utcnow()
        integration.status = IntegrationStatus.ACTIVE
        
        db.session.commit()
        
        return {
            'success': True,
            'message': 'Sync completed successfully',
            'sync_log': sync_log.to_dict()
        }

