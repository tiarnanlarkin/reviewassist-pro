from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, JSON, ForeignKey, Enum
from sqlalchemy.orm import relationship
import enum
import uuid
from src.models.user import db

class TicketStatus(enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_PROGRESS"
    WAITING_FOR_CUSTOMER = "waiting_for_customer"
    RESOLVED = "resolved"
    CLOSED = "closed"

class TicketPriority(enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class ChatStatus(enum.Enum):
    ACTIVE = "active"
    WAITING = "waiting"
    ENDED = "ended"

class ArticleStatus(enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"

class CustomerHealthStatus(enum.Enum):
    HEALTHY = "healthy"
    AT_RISK = "at_risk"
    CRITICAL = "critical"
    CHURNED = "churned"

class HelpArticle(db.Model):
    """Knowledge base articles"""
    __tablename__ = 'help_articles'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False)
    content = Column(Text, nullable=False)
    excerpt = Column(Text)
    category_id = Column(Integer, ForeignKey('help_categories.id'))
    author_id = Column(Integer, ForeignKey('auth_users.id'), nullable=False)
    status = Column(Enum(ArticleStatus), default=ArticleStatus.DRAFT)
    is_active = Column(Boolean, default=True)
    featured = Column(Boolean, default=False)
    view_count = Column(Integer, default=0)
    helpful_votes = Column(Integer, default=0)
    unhelpful_votes = Column(Integer, default=0)
    tags = Column(JSON, default=list)
    meta_description = Column(String(160))
    search_keywords = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    published_at = Column(DateTime)
    
    category = relationship("HelpCategory", back_populates="articles")

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'slug': self.slug,
            'content': self.content,
            'excerpt': self.excerpt,
            'category_id': self.category_id,
            'author_id': self.author_id,
            'status': self.status.value,
            'is_active': self.is_active,
            'featured': self.featured,
            'view_count': self.view_count,
            'helpful_votes': self.helpful_votes,
            'unhelpful_votes': self.unhelpful_votes,
            'tags': self.tags,
            'meta_description': self.meta_description,
            'search_keywords': self.search_keywords,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'published_at': self.published_at.isoformat() if self.published_at else None
        }

class HelpCategory(db.Model):
    """Help article categories"""
    __tablename__ = 'help_categories'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    icon = Column(String(50))
    color = Column(String(7))
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    articles = relationship("HelpArticle", back_populates="category")

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'slug': self.slug,
            'description': self.description,
            'icon': self.icon,
            'color': self.color,
            'sort_order': self.sort_order,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat()
        }

class SupportTicket(db.Model):
    """Customer support tickets"""
    __tablename__ = 'support_tickets'
    
    id = Column(Integer, primary_key=True)
    ticket_number = Column(String(20), unique=True, nullable=False)
    user_id = Column(Integer, ForeignKey('auth_users.id'), nullable=False)
    organization_id = Column(Integer, ForeignKey('organizations.id'))
    subject = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(Enum(TicketStatus), default=TicketStatus.OPEN)
    priority = Column(Enum(TicketPriority), default=TicketPriority.MEDIUM)
    assigned_to = Column(Integer, ForeignKey('auth_users.id'))
    category = Column(String(100))
    tags = Column(JSON, default=list)
    customer_email = Column(String(255))
    customer_name = Column(String(255))
    resolution_notes = Column(Text)
    satisfaction_rating = Column(Integer)
    satisfaction_feedback = Column(Text)
    first_response_at = Column(DateTime)
    resolved_at = Column(DateTime)
    closed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'ticket_number': self.ticket_number,
            'user_id': self.user_id,
            'organization_id': self.organization_id,
            'subject': self.subject,
            'description': self.description,
            'status': self.status.value,
            'priority': self.priority.value,
            'assigned_to': self.assigned_to,
            'category': self.category,
            'tags': self.tags,
            'customer_email': self.customer_email,
            'customer_name': self.customer_name,
            'resolution_notes': self.resolution_notes,
            'satisfaction_rating': self.satisfaction_rating,
            'satisfaction_feedback': self.satisfaction_feedback,
            'first_response_at': self.first_response_at.isoformat() if self.first_response_at else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'closed_at': self.closed_at.isoformat() if self.closed_at else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class TicketMessage(db.Model):
    """Messages within support tickets"""
    __tablename__ = 'ticket_messages'
    
    id = Column(Integer, primary_key=True)
    ticket_id = Column(Integer, ForeignKey('support_tickets.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('auth_users.id'), nullable=False)
    message = Column(Text, nullable=False)
    is_internal = Column(Boolean, default=False)
    attachments = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'ticket_id': self.ticket_id,
            'user_id': self.user_id,
            'message': self.message,
            'is_internal': self.is_internal,
            'attachments': self.attachments,
            'created_at': self.created_at.isoformat()
        }

class LiveChatSession(db.Model):
    """Live chat sessions"""
    __tablename__ = 'live_chat_sessions'
    
    id = Column(Integer, primary_key=True)
    session_id = Column(String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey('auth_users.id'))
    visitor_id = Column(String(36))
    agent_id = Column(Integer, ForeignKey('auth_users.id'))
    status = Column(Enum(ChatStatus), default=ChatStatus.WAITING)
    subject = Column(String(255))
    visitor_name = Column(String(255))
    visitor_email = Column(String(255))
    visitor_info = Column(JSON, default=dict)
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime)
    rating = Column(Integer)
    feedback = Column(Text)

    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'user_id': self.user_id,
            'visitor_id': self.visitor_id,
            'agent_id': self.agent_id,
            'status': self.status.value,
            'subject': self.subject,
            'visitor_name': self.visitor_name,
            'visitor_email': self.visitor_email,
            'visitor_info': self.visitor_info,
            'started_at': self.started_at.isoformat(),
            'ended_at': self.ended_at.isoformat() if self.ended_at else None,
            'rating': self.rating,
            'feedback': self.feedback
        }

class ChatMessage(db.Model):
    """Messages within live chat sessions"""
    __tablename__ = 'chat_messages'
    
    id = Column(Integer, primary_key=True)
    session_id = Column(String(36), ForeignKey('live_chat_sessions.session_id'), nullable=False)
    sender_type = Column(String(20), nullable=False)
    sender_id = Column(Integer)
    sender_name = Column(String(255))
    message = Column(Text, nullable=False)
    message_type = Column(String(20), default='text')
    attachments = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'sender_type': self.sender_type,
            'sender_id': self.sender_id,
            'sender_name': self.sender_name,
            'message': self.message,
            'message_type': self.message_type,
            'attachments': self.attachments,
            'created_at': self.created_at.isoformat()
        }

class CustomerHealthScore(db.Model):
    """Customer health and success tracking"""
    __tablename__ = 'customer_health_scores'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('auth_users.id'), nullable=False)
    organization_id = Column(Integer, ForeignKey('organizations.id'))
    overall_score = Column(Float, nullable=False)
    status = Column(Enum(CustomerHealthStatus), nullable=False)
    login_frequency_score = Column(Float, default=0)
    feature_adoption_score = Column(Float, default=0)
    support_interaction_score = Column(Float, default=0)
    billing_health_score = Column(Float, default=0)
    engagement_score = Column(Float, default=0)
    days_since_last_login = Column(Integer, default=0)
    total_logins = Column(Integer, default=0)
    features_used = Column(Integer, default=0)
    support_tickets_count = Column(Integer, default=0)
    satisfaction_rating = Column(Float)
    risk_factors = Column(JSON, default=list)
    recommendations = Column(JSON, default=list)
    calculated_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'organization_id': self.organization_id,
            'overall_score': self.overall_score,
            'status': self.status.value,
            'login_frequency_score': self.login_frequency_score,
            'feature_adoption_score': self.feature_adoption_score,
            'support_interaction_score': self.support_interaction_score,
            'billing_health_score': self.billing_health_score,
            'engagement_score': self.engagement_score,
            'days_since_last_login': self.days_since_last_login,
            'total_logins': self.total_logins,
            'features_used': self.features_used,
            'support_tickets_count': self.support_tickets_count,
            'satisfaction_rating': self.satisfaction_rating,
            'risk_factors': self.risk_factors,
            'recommendations': self.recommendations,
            'calculated_at': self.calculated_at.isoformat(),
            'created_at': self.created_at.isoformat()
        }

class FeatureAdoption(db.Model):
    """Track feature usage and adoption"""
    __tablename__ = 'feature_adoption'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('auth_users.id'), nullable=False)
    organization_id = Column(Integer, ForeignKey('organizations.id'))
    feature_name = Column(String(100), nullable=False)
    first_used_at = Column(DateTime, nullable=False)
    last_used_at = Column(DateTime, nullable=False)
    usage_count = Column(Integer, default=1)
    time_to_adoption = Column(Integer)
    is_power_user = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'organization_id': self.organization_id,
            'feature_name': self.feature_name,
            'first_used_at': self.first_used_at.isoformat(),
            'last_used_at': self.last_used_at.isoformat(),
            'usage_count': self.usage_count,
            'time_to_adoption': self.time_to_adoption,
            'is_power_user': self.is_power_user,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class OnboardingProgress(db.Model):
    """Track user onboarding progress"""
    __tablename__ = 'onboarding_progress'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('auth_users.id'), nullable=False)
    organization_id = Column(Integer, ForeignKey('organizations.id'))
    step_name = Column(String(100), nullable=False)
    step_category = Column(String(50))
    completed = Column(Boolean, default=False)
    completion_percentage = Column(Float, default=0)
    time_spent = Column(Integer, default=0)
    attempts = Column(Integer, default=0)
    skipped = Column(Boolean, default=False)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'organization_id': self.organization_id,
            'step_name': self.step_name,
            'step_category': self.step_category,
            'completed': self.completed,
            'completion_percentage': self.completion_percentage,
            'time_spent': self.time_spent,
            'attempts': self.attempts,
            'skipped': self.skipped,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class VideoTutorial(db.Model):
    """Video tutorials and learning content"""
    __tablename__ = 'video_tutorials'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    video_url = Column(String(500), nullable=False)
    thumbnail_url = Column(String(500))
    duration = Column(Integer)
    category = Column(String(100))
    difficulty_level = Column(String(20))
    tags = Column(JSON, default=list)
    view_count = Column(Integer, default=0)
    like_count = Column(Integer, default=0)
    dislike_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    is_featured = Column(Boolean, default=False)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'video_url': self.video_url,
            'thumbnail_url': self.thumbnail_url,
            'duration': self.duration,
            'category': self.category,
            'difficulty_level': self.difficulty_level,
            'tags': self.tags,
            'view_count': self.view_count,
            'like_count': self.like_count,
            'dislike_count': self.dislike_count,
            'is_active': self.is_active,
            'is_featured': self.is_featured,
            'sort_order': self.sort_order,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class UserVideoProgress(db.Model):
    """Tracks user progress in video tutorials"""
    __tablename__ = 'user_video_progress'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('auth_users.id'), nullable=False)
    video_id = Column(Integer, ForeignKey('video_tutorials.id'), nullable=False)
    progress_seconds = Column(Integer, default=0)
    completion_percentage = Column(Float, default=0.0)
    completed = Column(Boolean, default=False)
    last_watched_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    video = relationship("VideoTutorial")

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'video_id': self.video_id,
            'progress_seconds': self.progress_seconds,
            'completion_percentage': self.completion_percentage,
            'completed': self.completed,
            'last_watched_at': self.last_watched_at.isoformat(),
            'created_at': self.created_at.isoformat()
        }

class CustomerSuccessMetric(db.Model):
    """Stores historical and aggregated customer success metrics"""
    __tablename__ = 'customer_success_metrics'

    id = Column(Integer, primary_key=True)
    metric_name = Column(String(100), nullable=False)
    metric_value = Column(Float, nullable=False)
    user_id = Column(Integer, ForeignKey('auth_users.id'))
    organization_id = Column(Integer, ForeignKey('organizations.id'))
    timestamp = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'metric_name': self.metric_name,
            'metric_value': self.metric_value,
            'user_id': self.user_id,
            'organization_id': self.organization_id,
            'timestamp': self.timestamp.isoformat()
        }

