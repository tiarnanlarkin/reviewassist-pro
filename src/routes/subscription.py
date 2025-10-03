from flask import Blueprint, request, jsonify
from src.models.user import db
from src.models.subscription import (
    SubscriptionPlan, PlanFeature, UserSubscription, FeatureUsage,
    PlanType, BillingCycle, SubscriptionStatus, FeatureType, SubscriptionManager
)
from src.models.auth import AuthUser
from src.routes.auth import token_required
from datetime import datetime, timedelta
from sqlalchemy import func
import json

subscription_bp = Blueprint('subscription', __name__)

@subscription_bp.route('/plans', methods=['GET'])
def get_subscription_plans():
    """Get all available subscription plans"""
    try:
        plans = SubscriptionPlan.query.filter_by(is_active=True).order_by(SubscriptionPlan.sort_order).all()
        return jsonify({
            'success': True,
            'data': [plan.to_dict() for plan in plans]
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error fetching plans: {str(e)}'
        }), 500

@subscription_bp.route('/plans/<plan_type>', methods=['GET'])
def get_plan_details(plan_type):
    """Get details for a specific plan"""
    try:
        plan = SubscriptionPlan.query.filter_by(plan_type=PlanType(plan_type), is_active=True).first()
        if not plan:
            return jsonify({
                'success': False,
                'message': 'Plan not found'
            }), 404
        
        return jsonify({
            'success': True,
            'data': plan.to_dict()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error fetching plan: {str(e)}'
        }), 500

@subscription_bp.route('/user/subscription', methods=['GET'])
@token_required
def get_user_subscription(current_user):
    """Get current user's subscription"""
    try:
        subscription = SubscriptionManager.get_user_subscription(current_user.id)
        
        if not subscription:
            return jsonify({
                'success': True,
                'data': None,
                'message': 'No active subscription found'
            })
        
        return jsonify({
            'success': True,
            'data': subscription.to_dict()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error fetching subscription: {str(e)}'
        }), 500

@subscription_bp.route('/user/subscription/create', methods=['POST'])
@token_required
def create_subscription(current_user):
    """Create a new subscription for user"""
    try:
        data = request.get_json()
        plan_type = data.get('plan_type')
        billing_cycle = data.get('billing_cycle', 'monthly')
        
        if not plan_type:
            return jsonify({
                'success': False,
                'message': 'Plan type is required'
            }), 400
        
        # Check if user already has an active subscription
        existing_subscription = SubscriptionManager.get_user_subscription(current_user.id)
        if existing_subscription:
            return jsonify({
                'success': False,
                'message': 'User already has an active subscription'
            }), 400
        
        # Get the plan
        plan = SubscriptionPlan.query.filter_by(plan_type=PlanType(plan_type), is_active=True).first()
        if not plan:
            return jsonify({
                'success': False,
                'message': 'Invalid plan type'
            }), 400
        
        # Create subscription
        subscription = UserSubscription(
            user_id=current_user.id,
            plan_id=plan.id,
            billing_cycle=BillingCycle(billing_cycle),
            status=SubscriptionStatus.TRIALING,  # Start with trial
            trial_end_date=datetime.utcnow() + timedelta(days=14)  # 14-day trial
        )
        
        db.session.add(subscription)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': subscription.to_dict(),
            'message': 'Subscription created successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error creating subscription: {str(e)}'
        }), 500

@subscription_bp.route('/user/subscription/upgrade', methods=['POST'])
@token_required
def upgrade_subscription(current_user):
    """Upgrade user's subscription plan"""
    try:
        data = request.get_json()
        new_plan_type = data.get('plan_type')
        new_billing_cycle = data.get('billing_cycle')
        
        if not new_plan_type:
            return jsonify({
                'success': False,
                'message': 'New plan type is required'
            }), 400
        
        # Get current subscription
        subscription = SubscriptionManager.get_user_subscription(current_user.id)
        if not subscription:
            return jsonify({
                'success': False,
                'message': 'No active subscription found'
            }), 404
        
        # Get new plan
        new_plan = SubscriptionPlan.query.filter_by(plan_type=PlanType(new_plan_type), is_active=True).first()
        if not new_plan:
            return jsonify({
                'success': False,
                'message': 'Invalid plan type'
            }), 400
        
        # Update subscription
        subscription.plan_id = new_plan.id
        if new_billing_cycle:
            subscription.billing_cycle = BillingCycle(new_billing_cycle)
            subscription.set_billing_period()
        
        subscription.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': subscription.to_dict(),
            'message': 'Subscription upgraded successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error upgrading subscription: {str(e)}'
        }), 500

@subscription_bp.route('/user/subscription/cancel', methods=['POST'])
@token_required
def cancel_subscription(current_user):
    """Cancel user's subscription"""
    try:
        subscription = SubscriptionManager.get_user_subscription(current_user.id)
        if not subscription:
            return jsonify({
                'success': False,
                'message': 'No active subscription found'
            }), 404
        
        # Mark subscription as canceled but keep it active until period end
        subscription.status = SubscriptionStatus.CANCELED
        subscription.canceled_at = datetime.utcnow()
        subscription.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': subscription.to_dict(),
            'message': 'Subscription canceled successfully. Access will continue until the end of the current billing period.'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error canceling subscription: {str(e)}'
        }), 500

@subscription_bp.route('/user/feature-access/<feature_type>', methods=['GET'])
@token_required
def check_feature_access(current_user, feature_type):
    """Check if user has access to a specific feature"""
    try:
        feature_enum = FeatureType(feature_type)
        has_access = SubscriptionManager.check_feature_access(current_user.id, feature_enum)
        
        return jsonify({
            'success': True,
            'data': {
                'feature_type': feature_type,
                'has_access': has_access
            }
        })
    except ValueError:
        return jsonify({
            'success': False,
            'message': 'Invalid feature type'
        }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error checking feature access: {str(e)}'
        }), 500

@subscription_bp.route('/user/feature-usage/<feature_type>', methods=['GET'])
@token_required
def get_feature_usage(current_user, feature_type):
    """Get feature usage information for user"""
    try:
        feature_enum = FeatureType(feature_type)
        usage_info = SubscriptionManager.check_feature_limit(current_user.id, feature_enum)
        
        return jsonify({
            'success': True,
            'data': {
                'feature_type': feature_type,
                **usage_info
            }
        })
    except ValueError:
        return jsonify({
            'success': False,
            'message': 'Invalid feature type'
        }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error getting feature usage: {str(e)}'
        }), 500

@subscription_bp.route('/user/feature-usage/<feature_type>/increment', methods=['POST'])
@token_required
def increment_feature_usage(current_user, feature_type):
    """Increment feature usage for user"""
    try:
        data = request.get_json()
        count = data.get('count', 1)
        
        feature_enum = FeatureType(feature_type)
        
        # Check if user has access and is within limits
        usage_info = SubscriptionManager.check_feature_limit(current_user.id, feature_enum)
        if not usage_info['allowed']:
            return jsonify({
                'success': False,
                'message': 'Feature usage limit exceeded or access denied'
            }), 403
        
        # Increment usage
        success = SubscriptionManager.increment_feature_usage(current_user.id, feature_enum, count)
        
        if success:
            # Get updated usage info
            updated_usage = SubscriptionManager.check_feature_limit(current_user.id, feature_enum)
            return jsonify({
                'success': True,
                'data': {
                    'feature_type': feature_type,
                    **updated_usage
                },
                'message': 'Feature usage incremented successfully'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to increment feature usage'
            }), 500
            
    except ValueError:
        return jsonify({
            'success': False,
            'message': 'Invalid feature type'
        }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error incrementing feature usage: {str(e)}'
        }), 500

@subscription_bp.route('/user/usage-summary', methods=['GET'])
@token_required
def get_usage_summary(current_user):
    """Get comprehensive usage summary for user"""
    try:
        subscription = SubscriptionManager.get_user_subscription(current_user.id)
        if not subscription:
            return jsonify({
                'success': False,
                'message': 'No active subscription found'
            }), 404
        
        # Get usage for all features
        usage_summary = {}
        for feature_type in FeatureType:
            usage_info = SubscriptionManager.check_feature_limit(current_user.id, feature_type)
            usage_summary[feature_type.value] = usage_info
        
        return jsonify({
            'success': True,
            'data': {
                'subscription': subscription.to_dict(),
                'usage': usage_summary
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error getting usage summary: {str(e)}'
        }), 500

@subscription_bp.route('/admin/seed-plans', methods=['POST'])
@token_required
def seed_subscription_plans(current_user):
    """Seed default subscription plans (admin only)"""
    try:
        # Check if user is admin
        if current_user.role.value != 'admin':
            return jsonify({
                'success': False,
                'message': 'Admin access required'
            }), 403
        
        # Check if plans already exist
        if SubscriptionPlan.query.first():
            return jsonify({
                'success': False,
                'message': 'Subscription plans already exist'
            }), 400
        
        # Create Starter Plan
        starter_plan = SubscriptionPlan(
            name='Starter',
            plan_type=PlanType.STARTER,
            description='Perfect for small businesses getting started with review management',
            monthly_price=29.00,
            annual_price=290.00,  # 2 months free
            sort_order=1
        )
        db.session.add(starter_plan)
        db.session.flush()  # Get the ID
        
        # Starter plan features
        starter_features = [
            PlanFeature(plan_id=starter_plan.id, feature_type=FeatureType.REVIEWS_PER_MONTH, 
                       feature_name='Reviews per month', feature_description='Number of reviews you can manage per month', 
                       limit_value=100, is_included=True),
            PlanFeature(plan_id=starter_plan.id, feature_type=FeatureType.TEAM_MEMBERS, 
                       feature_name='Team members', feature_description='Number of team members who can access the platform', 
                       limit_value=2, is_included=True),
            PlanFeature(plan_id=starter_plan.id, feature_type=FeatureType.AUTOMATION_RULES, 
                       feature_name='Automation rules', feature_description='Number of automation rules you can create', 
                       limit_value=3, is_included=True),
            PlanFeature(plan_id=starter_plan.id, feature_type=FeatureType.API_CALLS_PER_MONTH, 
                       feature_name='API calls per month', feature_description='Number of API calls per month', 
                       limit_value=1000, is_included=True),
            PlanFeature(plan_id=starter_plan.id, feature_type=FeatureType.ADVANCED_ANALYTICS, 
                       feature_name='Advanced analytics', feature_description='Access to advanced analytics and reporting', 
                       limit_value=None, is_included=False),
            PlanFeature(plan_id=starter_plan.id, feature_type=FeatureType.PRIORITY_SUPPORT, 
                       feature_name='Priority support', feature_description='Priority customer support', 
                       limit_value=None, is_included=False)
        ]
        
        # Create Professional Plan
        professional_plan = SubscriptionPlan(
            name='Professional',
            plan_type=PlanType.PROFESSIONAL,
            description='Advanced features for growing businesses with comprehensive review management needs',
            monthly_price=79.00,
            annual_price=790.00,  # 2 months free
            sort_order=2
        )
        db.session.add(professional_plan)
        db.session.flush()
        
        # Professional plan features
        professional_features = [
            PlanFeature(plan_id=professional_plan.id, feature_type=FeatureType.REVIEWS_PER_MONTH, 
                       feature_name='Reviews per month', feature_description='Number of reviews you can manage per month', 
                       limit_value=1000, is_included=True),
            PlanFeature(plan_id=professional_plan.id, feature_type=FeatureType.TEAM_MEMBERS, 
                       feature_name='Team members', feature_description='Number of team members who can access the platform', 
                       limit_value=10, is_included=True),
            PlanFeature(plan_id=professional_plan.id, feature_type=FeatureType.AUTOMATION_RULES, 
                       feature_name='Automation rules', feature_description='Number of automation rules you can create', 
                       limit_value=15, is_included=True),
            PlanFeature(plan_id=professional_plan.id, feature_type=FeatureType.SCHEDULED_REPORTS, 
                       feature_name='Scheduled reports', feature_description='Number of scheduled reports you can create', 
                       limit_value=10, is_included=True),
            PlanFeature(plan_id=professional_plan.id, feature_type=FeatureType.API_CALLS_PER_MONTH, 
                       feature_name='API calls per month', feature_description='Number of API calls per month', 
                       limit_value=10000, is_included=True),
            PlanFeature(plan_id=professional_plan.id, feature_type=FeatureType.ADVANCED_ANALYTICS, 
                       feature_name='Advanced analytics', feature_description='Access to advanced analytics and reporting', 
                       limit_value=None, is_included=True),
            PlanFeature(plan_id=professional_plan.id, feature_type=FeatureType.PRIORITY_SUPPORT, 
                       feature_name='Priority support', feature_description='Priority customer support', 
                       limit_value=None, is_included=False)
        ]
        
        # Create Enterprise Plan
        enterprise_plan = SubscriptionPlan(
            name='Enterprise',
            plan_type=PlanType.ENTERPRISE,
            description='Complete solution for large organizations with unlimited features and priority support',
            monthly_price=199.00,
            annual_price=1990.00,  # 2 months free
            sort_order=3
        )
        db.session.add(enterprise_plan)
        db.session.flush()
        
        # Enterprise plan features
        enterprise_features = [
            PlanFeature(plan_id=enterprise_plan.id, feature_type=FeatureType.REVIEWS_PER_MONTH, 
                       feature_name='Reviews per month', feature_description='Unlimited reviews per month', 
                       limit_value=None, is_included=True),
            PlanFeature(plan_id=enterprise_plan.id, feature_type=FeatureType.TEAM_MEMBERS, 
                       feature_name='Team members', feature_description='Unlimited team members', 
                       limit_value=None, is_included=True),
            PlanFeature(plan_id=enterprise_plan.id, feature_type=FeatureType.AUTOMATION_RULES, 
                       feature_name='Automation rules', feature_description='Unlimited automation rules', 
                       limit_value=None, is_included=True),
            PlanFeature(plan_id=enterprise_plan.id, feature_type=FeatureType.SCHEDULED_REPORTS, 
                       feature_name='Scheduled reports', feature_description='Unlimited scheduled reports', 
                       limit_value=None, is_included=True),
            PlanFeature(plan_id=enterprise_plan.id, feature_type=FeatureType.API_CALLS_PER_MONTH, 
                       feature_name='API calls per month', feature_description='Unlimited API calls per month', 
                       limit_value=None, is_included=True),
            PlanFeature(plan_id=enterprise_plan.id, feature_type=FeatureType.CUSTOM_INTEGRATIONS, 
                       feature_name='Custom integrations', feature_description='Custom platform integrations', 
                       limit_value=None, is_included=True),
            PlanFeature(plan_id=enterprise_plan.id, feature_type=FeatureType.ADVANCED_ANALYTICS, 
                       feature_name='Advanced analytics', feature_description='Access to advanced analytics and reporting', 
                       limit_value=None, is_included=True),
            PlanFeature(plan_id=enterprise_plan.id, feature_type=FeatureType.WHITE_LABEL, 
                       feature_name='White label', feature_description='White label branding options', 
                       limit_value=None, is_included=True),
            PlanFeature(plan_id=enterprise_plan.id, feature_type=FeatureType.PRIORITY_SUPPORT, 
                       feature_name='Priority support', feature_description='24/7 priority customer support', 
                       limit_value=None, is_included=True)
        ]
        
        # Add all features
        for feature in starter_features + professional_features + enterprise_features:
            db.session.add(feature)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Subscription plans seeded successfully',
            'data': {
                'plans_created': 3,
                'features_created': len(starter_features + professional_features + enterprise_features)
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error seeding plans: {str(e)}'
        }), 500

