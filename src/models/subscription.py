from datetime import datetime, timedelta
from src.models.user import db
from src.models.auth import AuthUser
import enum
from sqlalchemy import func, Numeric
from decimal import Decimal

class PlanType(enum.Enum):
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"

class BillingCycle(enum.Enum):
    MONTHLY = "monthly"
    ANNUAL = "annual"

class SubscriptionStatus(enum.Enum):
    ACTIVE = "active"
    CANCELED = "canceled"
    PAST_DUE = "past_due"
    TRIALING = "trialing"
    INCOMPLETE = "incomplete"

class FeatureType(enum.Enum):
    REVIEWS_PER_MONTH = "reviews_per_month"
    TEAM_MEMBERS = "team_members"
    AUTOMATION_RULES = "automation_rules"
    SCHEDULED_REPORTS = "scheduled_reports"
    API_CALLS_PER_MONTH = "api_calls_per_month"
    CUSTOM_INTEGRATIONS = "custom_integrations"
    PRIORITY_SUPPORT = "priority_support"
    ADVANCED_ANALYTICS = "advanced_analytics"
    WHITE_LABEL = "white_label"

class SubscriptionPlan(db.Model):
    __tablename__ = 'subscription_plans'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    plan_type = db.Column(db.Enum(PlanType), nullable=False, unique=True)
    description = db.Column(db.Text)
    monthly_price = db.Column(Numeric(10, 2), nullable=False)
    annual_price = db.Column(Numeric(10, 2), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    features = db.relationship('PlanFeature', backref='plan', lazy=True, cascade='all, delete-orphan')
    subscriptions = db.relationship('UserSubscription', backref='plan', lazy=True)
    
    def __repr__(self):
        return f'<SubscriptionPlan {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'plan_type': self.plan_type.value,
            'description': self.description,
            'monthly_price': float(self.monthly_price),
            'annual_price': float(self.annual_price),
            'annual_discount': round((1 - (float(self.annual_price) / 12) / float(self.monthly_price)) * 100, 0),
            'is_active': self.is_active,
            'features': [feature.to_dict() for feature in self.features],
            'sort_order': self.sort_order
        }
    
    def get_price(self, billing_cycle):
        """Get price for specific billing cycle"""
        if billing_cycle == BillingCycle.ANNUAL:
            return self.annual_price
        return self.monthly_price

class PlanFeature(db.Model):
    __tablename__ = 'plan_features'
    
    id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(db.Integer, db.ForeignKey('subscription_plans.id'), nullable=False)
    feature_type = db.Column(db.Enum(FeatureType), nullable=False)
    feature_name = db.Column(db.String(200), nullable=False)
    feature_description = db.Column(db.Text)
    limit_value = db.Column(db.Integer)  # NULL means unlimited
    is_included = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<PlanFeature {self.feature_name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'feature_type': self.feature_type.value,
            'feature_name': self.feature_name,
            'feature_description': self.feature_description,
            'limit_value': self.limit_value,
            'is_included': self.is_included,
            'limit_display': 'Unlimited' if self.limit_value is None else str(self.limit_value)
        }

class UserSubscription(db.Model):
    __tablename__ = 'user_subscriptions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('auth_users.id'), nullable=False)
    plan_id = db.Column(db.Integer, db.ForeignKey('subscription_plans.id'), nullable=False)
    status = db.Column(db.Enum(SubscriptionStatus), nullable=False, default=SubscriptionStatus.ACTIVE)
    billing_cycle = db.Column(db.Enum(BillingCycle), nullable=False, default=BillingCycle.MONTHLY)
    
    # Subscription dates
    start_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    end_date = db.Column(db.DateTime)
    trial_end_date = db.Column(db.DateTime)
    canceled_at = db.Column(db.DateTime)
    
    # Billing information
    current_period_start = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    current_period_end = db.Column(db.DateTime, nullable=False)
    
    # External payment provider data
    stripe_subscription_id = db.Column(db.String(255))
    stripe_customer_id = db.Column(db.String(255))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('AuthUser', backref='subscriptions')
    usage_records = db.relationship('FeatureUsage', backref='subscription', lazy=True)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.current_period_end:
            self.set_billing_period()
    
    def set_billing_period(self):
        """Set the current billing period based on billing cycle"""
        if self.billing_cycle == BillingCycle.ANNUAL:
            self.current_period_end = self.current_period_start + timedelta(days=365)
        else:
            self.current_period_end = self.current_period_start + timedelta(days=30)
    
    def is_active(self):
        """Check if subscription is currently active"""
        return (self.status == SubscriptionStatus.ACTIVE and 
                self.current_period_end > datetime.utcnow())
    
    def is_trial(self):
        """Check if subscription is in trial period"""
        return (self.status == SubscriptionStatus.TRIALING and 
                self.trial_end_date and 
                self.trial_end_date > datetime.utcnow())
    
    def days_until_renewal(self):
        """Get days until next renewal"""
        if self.current_period_end:
            delta = self.current_period_end - datetime.utcnow()
            return max(0, delta.days)
        return 0
    
    def __repr__(self):
        return f'<UserSubscription {self.user.email} - {self.plan.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'plan': self.plan.to_dict() if self.plan else None,
            'status': self.status.value,
            'billing_cycle': self.billing_cycle.value,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'current_period_start': self.current_period_start.isoformat() if self.current_period_start else None,
            'current_period_end': self.current_period_end.isoformat() if self.current_period_end else None,
            'trial_end_date': self.trial_end_date.isoformat() if self.trial_end_date else None,
            'is_active': self.is_active(),
            'is_trial': self.is_trial(),
            'days_until_renewal': self.days_until_renewal(),
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class FeatureUsage(db.Model):
    __tablename__ = 'feature_usage'
    
    id = db.Column(db.Integer, primary_key=True)
    subscription_id = db.Column(db.Integer, db.ForeignKey('user_subscriptions.id'), nullable=False)
    feature_type = db.Column(db.Enum(FeatureType), nullable=False)
    usage_count = db.Column(db.Integer, default=0)
    usage_period_start = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    usage_period_end = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<FeatureUsage {self.feature_type.value}: {self.usage_count}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'feature_type': self.feature_type.value,
            'usage_count': self.usage_count,
            'usage_period_start': self.usage_period_start.isoformat(),
            'usage_period_end': self.usage_period_end.isoformat(),
            'created_at': self.created_at.isoformat()
        }

class SubscriptionManager:
    """Helper class for subscription management operations"""
    
    @staticmethod
    def get_user_subscription(user_id):
        """Get active subscription for user"""
        return UserSubscription.query.filter_by(
            user_id=user_id,
            status=SubscriptionStatus.ACTIVE
        ).first()
    
    @staticmethod
    def check_feature_access(user_id, feature_type):
        """Check if user has access to a specific feature"""
        subscription = SubscriptionManager.get_user_subscription(user_id)
        if not subscription or not subscription.is_active():
            return False
        
        # Check if feature is included in plan
        feature = PlanFeature.query.filter_by(
            plan_id=subscription.plan_id,
            feature_type=feature_type
        ).first()
        
        return feature and feature.is_included
    
    @staticmethod
    def check_feature_limit(user_id, feature_type):
        """Check feature usage against limits"""
        subscription = SubscriptionManager.get_user_subscription(user_id)
        if not subscription:
            return {'allowed': False, 'limit': 0, 'used': 0, 'remaining': 0}
        
        # Get feature limit from plan
        feature = PlanFeature.query.filter_by(
            plan_id=subscription.plan_id,
            feature_type=feature_type
        ).first()
        
        if not feature or not feature.is_included:
            return {'allowed': False, 'limit': 0, 'used': 0, 'remaining': 0}
        
        # If no limit (unlimited), return allowed
        if feature.limit_value is None:
            return {'allowed': True, 'limit': None, 'used': 0, 'remaining': None}
        
        # Get current usage
        current_usage = FeatureUsage.query.filter_by(
            subscription_id=subscription.id,
            feature_type=feature_type
        ).filter(
            FeatureUsage.usage_period_start <= datetime.utcnow(),
            FeatureUsage.usage_period_end >= datetime.utcnow()
        ).first()
        
        used = current_usage.usage_count if current_usage else 0
        remaining = max(0, feature.limit_value - used)
        
        return {
            'allowed': used < feature.limit_value,
            'limit': feature.limit_value,
            'used': used,
            'remaining': remaining
        }
    
    @staticmethod
    def increment_feature_usage(user_id, feature_type, count=1):
        """Increment feature usage for user"""
        subscription = SubscriptionManager.get_user_subscription(user_id)
        if not subscription:
            return False
        
        # Get or create usage record for current period
        period_start = subscription.current_period_start
        period_end = subscription.current_period_end
        
        usage = FeatureUsage.query.filter_by(
            subscription_id=subscription.id,
            feature_type=feature_type
        ).filter(
            FeatureUsage.usage_period_start <= datetime.utcnow(),
            FeatureUsage.usage_period_end >= datetime.utcnow()
        ).first()
        
        if not usage:
            usage = FeatureUsage(
                subscription_id=subscription.id,
                feature_type=feature_type,
                usage_count=0,
                usage_period_start=period_start,
                usage_period_end=period_end
            )
            db.session.add(usage)
        
        usage.usage_count += count
        usage.updated_at = datetime.utcnow()
        
        try:
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            print(f"Error incrementing feature usage: {e}")
            return False

