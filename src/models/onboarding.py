from datetime import datetime, timedelta
from src.models.user import db
from src.models.auth import AuthUser
import enum
import json
from sqlalchemy import Text, Boolean

class OnboardingStatus(enum.Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"

class TourType(enum.Enum):
    WELCOME = "welcome"
    DASHBOARD = "dashboard"
    REVIEWS = "reviews"
    ANALYTICS = "analytics"
    INTEGRATIONS = "integrations"
    AUTOMATION = "automation"
    SETTINGS = "settings"
    FEATURE_ANNOUNCEMENT = "feature_announcement"

class WidgetType(enum.Enum):
    METRICS_CARD = "metrics_card"
    CHART = "chart"
    RECENT_REVIEWS = "recent_reviews"
    ACTIVITY_FEED = "activity_feed"
    QUICK_ACTIONS = "quick_actions"
    NOTIFICATIONS = "notifications"
    PERFORMANCE_SUMMARY = "performance_summary"
    TEAM_ACTIVITY = "team_activity"

class UserOnboarding(db.Model):
    __tablename__ = 'user_onboarding'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('auth_users.id'), nullable=False, unique=True)
    
    # Onboarding progress
    status = db.Column(db.Enum(OnboardingStatus), nullable=False, default=OnboardingStatus.NOT_STARTED)
    current_step = db.Column(db.Integer, default=0)
    total_steps = db.Column(db.Integer, default=5)
    
    # Completed steps tracking
    completed_steps = db.Column(Text)  # JSON array of completed step IDs
    skipped_steps = db.Column(Text)    # JSON array of skipped step IDs
    
    # User preferences
    show_tooltips = db.Column(Boolean, default=True)
    show_feature_announcements = db.Column(Boolean, default=True)
    preferred_tour_speed = db.Column(db.String(20), default='normal')  # slow, normal, fast
    
    # Progress tracking
    profile_completed = db.Column(Boolean, default=False)
    first_integration_added = db.Column(Boolean, default=False)
    first_review_responded = db.Column(Boolean, default=False)
    dashboard_customized = db.Column(Boolean, default=False)
    team_invited = db.Column(Boolean, default=False)
    
    # Timestamps
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    last_active_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('AuthUser', backref='onboarding')
    tour_progress = db.relationship('UserTourProgress', backref='onboarding', lazy=True)
    
    def __repr__(self):
        return f'<UserOnboarding {self.user.email} - {self.status.value}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'status': self.status.value,
            'current_step': self.current_step,
            'total_steps': self.total_steps,
            'progress_percentage': round((self.current_step / max(1, self.total_steps)) * 100, 1),
            'completed_steps': json.loads(self.completed_steps) if self.completed_steps else [],
            'skipped_steps': json.loads(self.skipped_steps) if self.skipped_steps else [],
            'show_tooltips': self.show_tooltips,
            'show_feature_announcements': self.show_feature_announcements,
            'preferred_tour_speed': self.preferred_tour_speed,
            'milestones': {
                'profile_completed': self.profile_completed,
                'first_integration_added': self.first_integration_added,
                'first_review_responded': self.first_review_responded,
                'dashboard_customized': self.dashboard_customized,
                'team_invited': self.team_invited
            },
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'last_active_at': self.last_active_at.isoformat(),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def get_completed_steps(self):
        """Get list of completed step IDs"""
        if not self.completed_steps:
            return []
        try:
            return json.loads(self.completed_steps)
        except:
            return []
    
    def set_completed_steps(self, step_list):
        """Set list of completed step IDs"""
        self.completed_steps = json.dumps(step_list)
    
    def add_completed_step(self, step_id):
        """Add a step to completed list"""
        completed = self.get_completed_steps()
        if step_id not in completed:
            completed.append(step_id)
            self.set_completed_steps(completed)
            self.current_step = len(completed)
    
    def get_skipped_steps(self):
        """Get list of skipped step IDs"""
        if not self.skipped_steps:
            return []
        try:
            return json.loads(self.skipped_steps)
        except:
            return []
    
    def set_skipped_steps(self, step_list):
        """Set list of skipped step IDs"""
        self.skipped_steps = json.dumps(step_list)
    
    def add_skipped_step(self, step_id):
        """Add a step to skipped list"""
        skipped = self.get_skipped_steps()
        if step_id not in skipped:
            skipped.append(step_id)
            self.set_skipped_steps(skipped)

class UserTourProgress(db.Model):
    __tablename__ = 'user_tour_progress'
    
    id = db.Column(db.Integer, primary_key=True)
    onboarding_id = db.Column(db.Integer, db.ForeignKey('user_onboarding.id'), nullable=False)
    tour_type = db.Column(db.Enum(TourType), nullable=False)
    
    # Tour progress
    status = db.Column(db.Enum(OnboardingStatus), nullable=False, default=OnboardingStatus.NOT_STARTED)
    current_step = db.Column(db.Integer, default=0)
    total_steps = db.Column(db.Integer, default=0)
    
    # Tour data
    tour_data = db.Column(Text)  # JSON with tour-specific data
    
    # Timestamps
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    last_step_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<UserTourProgress {self.tour_type.value} - {self.status.value}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'tour_type': self.tour_type.value,
            'status': self.status.value,
            'current_step': self.current_step,
            'total_steps': self.total_steps,
            'progress_percentage': round((self.current_step / max(1, self.total_steps)) * 100, 1),
            'tour_data': json.loads(self.tour_data) if self.tour_data else {},
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'last_step_at': self.last_step_at.isoformat() if self.last_step_at else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class DashboardLayout(db.Model):
    __tablename__ = 'dashboard_layouts'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('auth_users.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    
    # Layout configuration
    layout_data = db.Column(Text, nullable=False)  # JSON with widget positions and configurations
    is_default = db.Column(Boolean, default=False)
    is_active = db.Column(Boolean, default=True)
    
    # Metadata
    description = db.Column(db.String(500))
    tags = db.Column(db.String(500))  # Comma-separated tags
    
    # Usage tracking
    last_used_at = db.Column(db.DateTime)
    usage_count = db.Column(db.Integer, default=0)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('AuthUser', backref='dashboard_layouts')
    
    def __repr__(self):
        return f'<DashboardLayout {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'layout_data': json.loads(self.layout_data) if self.layout_data else {},
            'is_default': self.is_default,
            'is_active': self.is_active,
            'description': self.description,
            'tags': self.tags.split(',') if self.tags else [],
            'last_used_at': self.last_used_at.isoformat() if self.last_used_at else None,
            'usage_count': self.usage_count,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def get_layout_data(self):
        """Get parsed layout data"""
        if not self.layout_data:
            return {}
        try:
            return json.loads(self.layout_data)
        except:
            return {}
    
    def set_layout_data(self, layout_dict):
        """Set layout data as JSON"""
        self.layout_data = json.dumps(layout_dict)

class UserPreferences(db.Model):
    __tablename__ = 'user_preferences'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('auth_users.id'), nullable=False, unique=True)
    
    # UI Preferences
    theme = db.Column(db.String(20), default='light')  # light, dark, auto
    language = db.Column(db.String(10), default='en')
    timezone = db.Column(db.String(50), default='UTC')
    date_format = db.Column(db.String(20), default='MM/DD/YYYY')
    time_format = db.Column(db.String(10), default='12h')  # 12h, 24h
    
    # Dashboard Preferences
    default_dashboard_layout_id = db.Column(db.Integer, db.ForeignKey('dashboard_layouts.id'))
    items_per_page = db.Column(db.Integer, default=25)
    auto_refresh_interval = db.Column(db.Integer, default=300)  # seconds
    
    # Notification Preferences
    email_notifications = db.Column(Boolean, default=True)
    push_notifications = db.Column(Boolean, default=True)
    desktop_notifications = db.Column(Boolean, default=False)
    notification_sound = db.Column(Boolean, default=True)
    
    # Feature Preferences
    keyboard_shortcuts_enabled = db.Column(Boolean, default=True)
    advanced_mode = db.Column(Boolean, default=False)
    beta_features_enabled = db.Column(Boolean, default=False)
    analytics_tracking = db.Column(Boolean, default=True)
    
    # Quick Actions
    favorite_actions = db.Column(Text)  # JSON array of favorite action IDs
    recent_searches = db.Column(Text)   # JSON array of recent search terms
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('AuthUser', backref='preferences')
    default_layout = db.relationship('DashboardLayout', foreign_keys=[default_dashboard_layout_id])
    
    def __repr__(self):
        return f'<UserPreferences {self.user.email}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'theme': self.theme,
            'language': self.language,
            'timezone': self.timezone,
            'date_format': self.date_format,
            'time_format': self.time_format,
            'default_dashboard_layout_id': self.default_dashboard_layout_id,
            'items_per_page': self.items_per_page,
            'auto_refresh_interval': self.auto_refresh_interval,
            'notifications': {
                'email': self.email_notifications,
                'push': self.push_notifications,
                'desktop': self.desktop_notifications,
                'sound': self.notification_sound
            },
            'features': {
                'keyboard_shortcuts': self.keyboard_shortcuts_enabled,
                'advanced_mode': self.advanced_mode,
                'beta_features': self.beta_features_enabled,
                'analytics_tracking': self.analytics_tracking
            },
            'favorite_actions': json.loads(self.favorite_actions) if self.favorite_actions else [],
            'recent_searches': json.loads(self.recent_searches) if self.recent_searches else [],
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def get_favorite_actions(self):
        """Get list of favorite action IDs"""
        if not self.favorite_actions:
            return []
        try:
            return json.loads(self.favorite_actions)
        except:
            return []
    
    def set_favorite_actions(self, action_list):
        """Set list of favorite action IDs"""
        self.favorite_actions = json.dumps(action_list)
    
    def add_favorite_action(self, action_id):
        """Add an action to favorites"""
        favorites = self.get_favorite_actions()
        if action_id not in favorites:
            favorites.append(action_id)
            self.set_favorite_actions(favorites)
    
    def get_recent_searches(self):
        """Get list of recent search terms"""
        if not self.recent_searches:
            return []
        try:
            return json.loads(self.recent_searches)
        except:
            return []
    
    def set_recent_searches(self, search_list):
        """Set list of recent search terms"""
        self.recent_searches = json.dumps(search_list[-10:])  # Keep only last 10
    
    def add_recent_search(self, search_term):
        """Add a search term to recent searches"""
        searches = self.get_recent_searches()
        if search_term in searches:
            searches.remove(search_term)
        searches.insert(0, search_term)
        self.set_recent_searches(searches)

class FeatureAnnouncement(db.Model):
    __tablename__ = 'feature_announcements'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(Text, nullable=False)
    
    # Announcement configuration
    announcement_type = db.Column(db.String(50), default='feature')  # feature, update, maintenance, etc.
    priority = db.Column(db.String(20), default='normal')  # low, normal, high, urgent
    target_roles = db.Column(db.String(200))  # JSON array of target user roles
    
    # Display configuration
    show_as_modal = db.Column(Boolean, default=False)
    show_as_banner = db.Column(Boolean, default=True)
    show_as_notification = db.Column(Boolean, default=True)
    
    # Media
    image_url = db.Column(db.String(500))
    video_url = db.Column(db.String(500))
    
    # Scheduling
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime)
    is_active = db.Column(Boolean, default=True)
    
    # Tracking
    view_count = db.Column(db.Integer, default=0)
    click_count = db.Column(db.Integer, default=0)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user_views = db.relationship('UserAnnouncementView', backref='announcement', lazy=True)
    
    def __repr__(self):
        return f'<FeatureAnnouncement {self.title}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'announcement_type': self.announcement_type,
            'priority': self.priority,
            'target_roles': json.loads(self.target_roles) if self.target_roles else [],
            'display': {
                'modal': self.show_as_modal,
                'banner': self.show_as_banner,
                'notification': self.show_as_notification
            },
            'media': {
                'image_url': self.image_url,
                'video_url': self.video_url
            },
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'is_active': self.is_active,
            'stats': {
                'view_count': self.view_count,
                'click_count': self.click_count
            },
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def is_visible_now(self):
        """Check if announcement should be visible now"""
        now = datetime.utcnow()
        if not self.is_active:
            return False
        if now < self.start_date:
            return False
        if self.end_date and now > self.end_date:
            return False
        return True

class UserAnnouncementView(db.Model):
    __tablename__ = 'user_announcement_views'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('auth_users.id'), nullable=False)
    announcement_id = db.Column(db.Integer, db.ForeignKey('feature_announcements.id'), nullable=False)
    
    # View details
    viewed_at = db.Column(db.DateTime, default=datetime.utcnow)
    clicked = db.Column(Boolean, default=False)
    clicked_at = db.Column(db.DateTime)
    dismissed = db.Column(Boolean, default=False)
    dismissed_at = db.Column(db.DateTime)
    
    # Relationships
    user = db.relationship('AuthUser', backref='announcement_views')
    
    def __repr__(self):
        return f'<UserAnnouncementView {self.user.email} - {self.announcement.title}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'announcement_id': self.announcement_id,
            'viewed_at': self.viewed_at.isoformat(),
            'clicked': self.clicked,
            'clicked_at': self.clicked_at.isoformat() if self.clicked_at else None,
            'dismissed': self.dismissed,
            'dismissed_at': self.dismissed_at.isoformat() if self.dismissed_at else None
        }

class OnboardingManager:
    """Helper class for onboarding management operations"""
    
    @staticmethod
    def get_or_create_onboarding(user_id):
        """Get or create onboarding record for user"""
        onboarding = UserOnboarding.query.filter_by(user_id=user_id).first()
        if not onboarding:
            onboarding = UserOnboarding(user_id=user_id)
            db.session.add(onboarding)
            db.session.commit()
        return onboarding
    
    @staticmethod
    def start_onboarding(user_id):
        """Start onboarding process for user"""
        onboarding = OnboardingManager.get_or_create_onboarding(user_id)
        if onboarding.status == OnboardingStatus.NOT_STARTED:
            onboarding.status = OnboardingStatus.IN_PROGRESS
            onboarding.started_at = datetime.utcnow()
            db.session.commit()
        return onboarding
    
    @staticmethod
    def complete_onboarding_step(user_id, step_id):
        """Mark an onboarding step as completed"""
        onboarding = OnboardingManager.get_or_create_onboarding(user_id)
        onboarding.add_completed_step(step_id)
        onboarding.last_active_at = datetime.utcnow()
        
        # Check if onboarding is complete
        if onboarding.current_step >= onboarding.total_steps:
            onboarding.status = OnboardingStatus.COMPLETED
            onboarding.completed_at = datetime.utcnow()
        
        db.session.commit()
        return onboarding
    
    @staticmethod
    def get_user_preferences(user_id):
        """Get or create user preferences"""
        preferences = UserPreferences.query.filter_by(user_id=user_id).first()
        if not preferences:
            preferences = UserPreferences(user_id=user_id)
            db.session.add(preferences)
            db.session.commit()
        return preferences
    
    @staticmethod
    def get_active_announcements(user_role=None):
        """Get active feature announcements for user role"""
        query = FeatureAnnouncement.query.filter(
            FeatureAnnouncement.is_active == True,
            FeatureAnnouncement.start_date <= datetime.utcnow()
        )
        
        # Filter by end date
        query = query.filter(
            db.or_(
                FeatureAnnouncement.end_date.is_(None),
                FeatureAnnouncement.end_date > datetime.utcnow()
            )
        )
        
        announcements = query.all()
        
        # Filter by user role if specified
        if user_role:
            filtered_announcements = []
            for announcement in announcements:
                if announcement.target_roles:
                    try:
                        target_roles = json.loads(announcement.target_roles)
                        if user_role.value in target_roles or 'all' in target_roles:
                            filtered_announcements.append(announcement)
                    except:
                        filtered_announcements.append(announcement)
                else:
                    filtered_announcements.append(announcement)
            return filtered_announcements
        
        return announcements

