from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
from src.models.user import db
from src.models.auth import AuthUser, UserRole
from src.models.onboarding import (
    UserOnboarding, UserTourProgress, DashboardLayout, UserPreferences,
    FeatureAnnouncement, UserAnnouncementView, OnboardingManager,
    OnboardingStatus, TourType, WidgetType
)
from src.routes.auth import token_required
import json

onboarding_bp = Blueprint('onboarding', __name__)

# Onboarding Management Routes

@onboarding_bp.route('/onboarding/status', methods=['GET'])
@token_required
def get_onboarding_status(current_user):
    """Get user's onboarding status and progress"""
    try:
        onboarding = OnboardingManager.get_or_create_onboarding(current_user.id)
        
        # Get tour progress
        tours = UserTourProgress.query.filter_by(onboarding_id=onboarding.id).all()
        tour_progress = {tour.tour_type.value: tour.to_dict() for tour in tours}
        
        # Get user preferences
        preferences = OnboardingManager.get_user_preferences(current_user.id)
        
        return jsonify({
            'success': True,
            'onboarding': onboarding.to_dict(),
            'tour_progress': tour_progress,
            'preferences': preferences.to_dict(),
            'next_steps': _get_next_onboarding_steps(onboarding)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@onboarding_bp.route('/onboarding/start', methods=['POST'])
@token_required
def start_onboarding(current_user):
    """Start the onboarding process"""
    try:
        onboarding = OnboardingManager.start_onboarding(current_user.id)
        
        return jsonify({
            'success': True,
            'message': 'Onboarding started successfully',
            'onboarding': onboarding.to_dict()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@onboarding_bp.route('/onboarding/step/<step_id>/complete', methods=['POST'])
@token_required
def complete_onboarding_step(current_user, step_id):
    """Mark an onboarding step as completed"""
    try:
        data = request.get_json() or {}
        
        onboarding = OnboardingManager.complete_onboarding_step(current_user.id, step_id)
        
        # Update milestone if provided
        milestone = data.get('milestone')
        if milestone:
            setattr(onboarding, milestone, True)
            db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Step {step_id} completed successfully',
            'onboarding': onboarding.to_dict()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@onboarding_bp.route('/onboarding/skip', methods=['POST'])
@token_required
def skip_onboarding(current_user):
    """Skip the onboarding process"""
    try:
        onboarding = OnboardingManager.get_or_create_onboarding(current_user.id)
        onboarding.status = OnboardingStatus.SKIPPED
        onboarding.completed_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Onboarding skipped successfully',
            'onboarding': onboarding.to_dict()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Tour Management Routes

@onboarding_bp.route('/tours/available', methods=['GET'])
@token_required
def get_available_tours(current_user):
    """Get available tours for the user"""
    try:
        tours = [
            {
                'type': 'welcome',
                'title': 'Welcome to ReviewAssist Pro',
                'description': 'Get started with the basics of review management',
                'duration': '3-5 minutes',
                'steps': 5,
                'required': True
            },
            {
                'type': 'dashboard',
                'title': 'Dashboard Overview',
                'description': 'Learn about your analytics dashboard and key metrics',
                'duration': '2-3 minutes',
                'steps': 4,
                'required': False
            },
            {
                'type': 'reviews',
                'title': 'Review Management',
                'description': 'Master review filtering, responding, and bulk operations',
                'duration': '4-6 minutes',
                'steps': 6,
                'required': False
            },
            {
                'type': 'analytics',
                'title': 'Advanced Analytics',
                'description': 'Explore reporting, insights, and performance tracking',
                'duration': '3-4 minutes',
                'steps': 5,
                'required': False
            },
            {
                'type': 'integrations',
                'title': 'Platform Integrations',
                'description': 'Connect with Google, Yelp, Facebook, and other platforms',
                'duration': '5-7 minutes',
                'steps': 7,
                'required': False
            },
            {
                'type': 'automation',
                'title': 'Workflow Automation',
                'description': 'Set up automated responses and scheduled reports',
                'duration': '4-5 minutes',
                'steps': 6,
                'required': False
            }
        ]
        
        # Get user's tour progress
        onboarding = OnboardingManager.get_or_create_onboarding(current_user.id)
        tour_progress = UserTourProgress.query.filter_by(onboarding_id=onboarding.id).all()
        progress_dict = {tour.tour_type.value: tour.to_dict() for tour in tour_progress}
        
        # Add progress to each tour
        for tour in tours:
            tour['progress'] = progress_dict.get(tour['type'], {
                'status': 'not_started',
                'current_step': 0,
                'progress_percentage': 0
            })
        
        return jsonify({
            'success': True,
            'tours': tours
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@onboarding_bp.route('/tours/<tour_type>/start', methods=['POST'])
@token_required
def start_tour(current_user, tour_type):
    """Start a specific tour"""
    try:
        # Validate tour type
        try:
            tour_enum = TourType(tour_type)
        except ValueError:
            return jsonify({'success': False, 'error': 'Invalid tour type'}), 400
        
        onboarding = OnboardingManager.get_or_create_onboarding(current_user.id)
        
        # Get or create tour progress
        tour_progress = UserTourProgress.query.filter_by(
            onboarding_id=onboarding.id,
            tour_type=tour_enum
        ).first()
        
        if not tour_progress:
            tour_progress = UserTourProgress(
                onboarding_id=onboarding.id,
                tour_type=tour_enum,
                total_steps=_get_tour_steps(tour_type)
            )
            db.session.add(tour_progress)
        
        tour_progress.status = OnboardingStatus.IN_PROGRESS
        tour_progress.started_at = datetime.utcnow()
        tour_progress.last_step_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'{tour_type} tour started successfully',
            'tour_progress': tour_progress.to_dict(),
            'tour_steps': _get_tour_content(tour_type)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@onboarding_bp.route('/tours/<tour_type>/step/<int:step_number>', methods=['POST'])
@token_required
def update_tour_step(current_user, tour_type, step_number):
    """Update tour step progress"""
    try:
        tour_enum = TourType(tour_type)
        onboarding = OnboardingManager.get_or_create_onboarding(current_user.id)
        
        tour_progress = UserTourProgress.query.filter_by(
            onboarding_id=onboarding.id,
            tour_type=tour_enum
        ).first()
        
        if not tour_progress:
            return jsonify({'success': False, 'error': 'Tour not found'}), 404
        
        tour_progress.current_step = step_number
        tour_progress.last_step_at = datetime.utcnow()
        
        # Check if tour is completed
        if step_number >= tour_progress.total_steps:
            tour_progress.status = OnboardingStatus.COMPLETED
            tour_progress.completed_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'tour_progress': tour_progress.to_dict()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Dashboard Customization Routes

@onboarding_bp.route('/dashboard/layouts', methods=['GET'])
@token_required
def get_dashboard_layouts(current_user):
    """Get user's dashboard layouts"""
    try:
        layouts = DashboardLayout.query.filter_by(
            user_id=current_user.id,
            is_active=True
        ).order_by(DashboardLayout.is_default.desc(), DashboardLayout.last_used_at.desc()).all()
        
        # If no layouts exist, create default ones
        if not layouts:
            layouts = _create_default_layouts(current_user.id)
        
        return jsonify({
            'success': True,
            'layouts': [layout.to_dict() for layout in layouts]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@onboarding_bp.route('/dashboard/layouts', methods=['POST'])
@token_required
def create_dashboard_layout(current_user):
    """Create a new dashboard layout"""
    try:
        data = request.get_json()
        
        layout = DashboardLayout(
            user_id=current_user.id,
            name=data.get('name', 'Custom Layout'),
            description=data.get('description'),
            tags=','.join(data.get('tags', [])),
            is_default=data.get('is_default', False)
        )
        
        layout.set_layout_data(data.get('layout_data', {}))
        
        # If this is set as default, unset other defaults
        if layout.is_default:
            DashboardLayout.query.filter_by(
                user_id=current_user.id,
                is_default=True
            ).update({'is_default': False})
        
        db.session.add(layout)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Dashboard layout created successfully',
            'layout': layout.to_dict()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@onboarding_bp.route('/dashboard/layouts/<int:layout_id>', methods=['PUT'])
@token_required
def update_dashboard_layout(current_user, layout_id):
    """Update a dashboard layout"""
    try:
        layout = DashboardLayout.query.filter_by(
            id=layout_id,
            user_id=current_user.id
        ).first()
        
        if not layout:
            return jsonify({'success': False, 'error': 'Layout not found'}), 404
        
        data = request.get_json()
        
        if 'name' in data:
            layout.name = data['name']
        if 'description' in data:
            layout.description = data['description']
        if 'tags' in data:
            layout.tags = ','.join(data['tags'])
        if 'layout_data' in data:
            layout.set_layout_data(data['layout_data'])
        if 'is_default' in data:
            layout.is_default = data['is_default']
            
            # If this is set as default, unset other defaults
            if layout.is_default:
                DashboardLayout.query.filter_by(
                    user_id=current_user.id,
                    is_default=True
                ).filter(DashboardLayout.id != layout_id).update({'is_default': False})
        
        layout.last_used_at = datetime.utcnow()
        layout.usage_count += 1
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Dashboard layout updated successfully',
            'layout': layout.to_dict()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# User Preferences Routes

@onboarding_bp.route('/preferences', methods=['GET'])
@token_required
def get_user_preferences(current_user):
    """Get user preferences"""
    try:
        preferences = OnboardingManager.get_user_preferences(current_user.id)
        return jsonify({
            'success': True,
            'preferences': preferences.to_dict()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@onboarding_bp.route('/preferences', methods=['PUT'])
@token_required
def update_user_preferences(current_user):
    """Update user preferences"""
    try:
        preferences = OnboardingManager.get_user_preferences(current_user.id)
        data = request.get_json()
        
        # Update UI preferences
        if 'theme' in data:
            preferences.theme = data['theme']
        if 'language' in data:
            preferences.language = data['language']
        if 'timezone' in data:
            preferences.timezone = data['timezone']
        if 'date_format' in data:
            preferences.date_format = data['date_format']
        if 'time_format' in data:
            preferences.time_format = data['time_format']
        
        # Update dashboard preferences
        if 'items_per_page' in data:
            preferences.items_per_page = data['items_per_page']
        if 'auto_refresh_interval' in data:
            preferences.auto_refresh_interval = data['auto_refresh_interval']
        
        # Update notification preferences
        notifications = data.get('notifications', {})
        if 'email' in notifications:
            preferences.email_notifications = notifications['email']
        if 'push' in notifications:
            preferences.push_notifications = notifications['push']
        if 'desktop' in notifications:
            preferences.desktop_notifications = notifications['desktop']
        if 'sound' in notifications:
            preferences.notification_sound = notifications['sound']
        
        # Update feature preferences
        features = data.get('features', {})
        if 'keyboard_shortcuts' in features:
            preferences.keyboard_shortcuts_enabled = features['keyboard_shortcuts']
        if 'advanced_mode' in features:
            preferences.advanced_mode = features['advanced_mode']
        if 'beta_features' in features:
            preferences.beta_features_enabled = features['beta_features']
        if 'analytics_tracking' in features:
            preferences.analytics_tracking = features['analytics_tracking']
        
        # Update quick actions
        if 'favorite_actions' in data:
            preferences.set_favorite_actions(data['favorite_actions'])
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Preferences updated successfully',
            'preferences': preferences.to_dict()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Feature Announcements Routes

@onboarding_bp.route('/announcements', methods=['GET'])
@token_required
def get_feature_announcements(current_user):
    """Get active feature announcements for user"""
    try:
        announcements = OnboardingManager.get_active_announcements(current_user.role)
        
        # Get user's view history
        viewed_announcements = UserAnnouncementView.query.filter_by(
            user_id=current_user.id
        ).all()
        viewed_dict = {view.announcement_id: view.to_dict() for view in viewed_announcements}
        
        # Add view status to announcements
        result = []
        for announcement in announcements:
            announcement_dict = announcement.to_dict()
            announcement_dict['user_view'] = viewed_dict.get(announcement.id, {
                'viewed': False,
                'clicked': False,
                'dismissed': False
            })
            result.append(announcement_dict)
        
        return jsonify({
            'success': True,
            'announcements': result
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@onboarding_bp.route('/announcements/<int:announcement_id>/view', methods=['POST'])
@token_required
def mark_announcement_viewed(current_user, announcement_id):
    """Mark an announcement as viewed"""
    try:
        # Get or create view record
        view = UserAnnouncementView.query.filter_by(
            user_id=current_user.id,
            announcement_id=announcement_id
        ).first()
        
        if not view:
            view = UserAnnouncementView(
                user_id=current_user.id,
                announcement_id=announcement_id
            )
            db.session.add(view)
        
        # Update announcement view count
        announcement = FeatureAnnouncement.query.get(announcement_id)
        if announcement:
            announcement.view_count += 1
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Announcement marked as viewed'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@onboarding_bp.route('/announcements/<int:announcement_id>/dismiss', methods=['POST'])
@token_required
def dismiss_announcement(current_user, announcement_id):
    """Dismiss an announcement"""
    try:
        view = UserAnnouncementView.query.filter_by(
            user_id=current_user.id,
            announcement_id=announcement_id
        ).first()
        
        if not view:
            view = UserAnnouncementView(
                user_id=current_user.id,
                announcement_id=announcement_id
            )
            db.session.add(view)
        
        view.dismissed = True
        view.dismissed_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Announcement dismissed'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Quick Actions Routes

@onboarding_bp.route('/quick-actions', methods=['GET'])
@token_required
def get_quick_actions(current_user):
    """Get available quick actions for user"""
    try:
        # Define available quick actions based on user role
        all_actions = [
            {
                'id': 'respond_to_reviews',
                'title': 'Respond to Reviews',
                'description': 'Quickly respond to pending reviews',
                'icon': 'reply',
                'shortcut': 'Ctrl+R',
                'category': 'reviews',
                'roles': ['admin', 'manager', 'agent']
            },
            {
                'id': 'generate_report',
                'title': 'Generate Report',
                'description': 'Create analytics report',
                'icon': 'chart-bar',
                'shortcut': 'Ctrl+G',
                'category': 'analytics',
                'roles': ['admin', 'manager']
            },
            {
                'id': 'add_integration',
                'title': 'Add Integration',
                'description': 'Connect new platform',
                'icon': 'plus-circle',
                'shortcut': 'Ctrl+I',
                'category': 'integrations',
                'roles': ['admin', 'manager']
            },
            {
                'id': 'bulk_respond',
                'title': 'Bulk Respond',
                'description': 'Respond to multiple reviews',
                'icon': 'layers',
                'shortcut': 'Ctrl+B',
                'category': 'reviews',
                'roles': ['admin', 'manager', 'agent']
            },
            {
                'id': 'export_data',
                'title': 'Export Data',
                'description': 'Export reviews and analytics',
                'icon': 'download',
                'shortcut': 'Ctrl+E',
                'category': 'data',
                'roles': ['admin', 'manager']
            },
            {
                'id': 'create_automation',
                'title': 'Create Automation',
                'description': 'Set up automated workflow',
                'icon': 'cog',
                'shortcut': 'Ctrl+A',
                'category': 'automation',
                'roles': ['admin', 'manager']
            }
        ]
        
        # Filter actions by user role
        user_role = current_user.role.value
        available_actions = [
            action for action in all_actions
            if user_role in action['roles'] or 'all' in action['roles']
        ]
        
        # Get user's favorite actions
        preferences = OnboardingManager.get_user_preferences(current_user.id)
        favorite_action_ids = preferences.get_favorite_actions()
        
        # Mark favorite actions
        for action in available_actions:
            action['is_favorite'] = action['id'] in favorite_action_ids
        
        return jsonify({
            'success': True,
            'actions': available_actions,
            'categories': ['reviews', 'analytics', 'integrations', 'automation', 'data']
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@onboarding_bp.route('/quick-actions/<action_id>/favorite', methods=['POST'])
@token_required
def toggle_favorite_action(current_user, action_id):
    """Toggle favorite status for a quick action"""
    try:
        preferences = OnboardingManager.get_user_preferences(current_user.id)
        favorites = preferences.get_favorite_actions()
        
        if action_id in favorites:
            favorites.remove(action_id)
            is_favorite = False
        else:
            preferences.add_favorite_action(action_id)
            is_favorite = True
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'is_favorite': is_favorite,
            'message': f'Action {"added to" if is_favorite else "removed from"} favorites'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Helper Functions

def _get_next_onboarding_steps(onboarding):
    """Get next recommended onboarding steps"""
    steps = []
    
    if not onboarding.profile_completed:
        steps.append({
            'id': 'complete_profile',
            'title': 'Complete Your Profile',
            'description': 'Add your name, company, and preferences',
            'priority': 'high'
        })
    
    if not onboarding.first_integration_added:
        steps.append({
            'id': 'add_integration',
            'title': 'Connect Your First Platform',
            'description': 'Connect Google My Business, Yelp, or Facebook',
            'priority': 'high'
        })
    
    if not onboarding.dashboard_customized:
        steps.append({
            'id': 'customize_dashboard',
            'title': 'Customize Your Dashboard',
            'description': 'Arrange widgets to match your workflow',
            'priority': 'medium'
        })
    
    if not onboarding.first_review_responded:
        steps.append({
            'id': 'respond_to_review',
            'title': 'Respond to Your First Review',
            'description': 'Try the AI-powered response generator',
            'priority': 'medium'
        })
    
    if not onboarding.team_invited:
        steps.append({
            'id': 'invite_team',
            'title': 'Invite Your Team',
            'description': 'Add team members and assign roles',
            'priority': 'low'
        })
    
    return steps

def _get_tour_steps(tour_type):
    """Get number of steps for a tour type"""
    tour_steps = {
        'welcome': 5,
        'dashboard': 4,
        'reviews': 6,
        'analytics': 5,
        'integrations': 7,
        'automation': 6,
        'settings': 4
    }
    return tour_steps.get(tour_type, 5)

def _get_tour_content(tour_type):
    """Get tour content and steps"""
    tours = {
        'welcome': {
            'title': 'Welcome to ReviewAssist Pro',
            'steps': [
                {
                    'title': 'Welcome!',
                    'content': 'Welcome to ReviewAssist Pro! Let\'s take a quick tour to get you started.',
                    'target': '.dashboard-header',
                    'position': 'bottom'
                },
                {
                    'title': 'Dashboard Overview',
                    'content': 'This is your main dashboard where you can see all your review metrics at a glance.',
                    'target': '.metrics-cards',
                    'position': 'bottom'
                },
                {
                    'title': 'Review Management',
                    'content': 'Here you can view, filter, and respond to all your reviews from different platforms.',
                    'target': '.reviews-section',
                    'position': 'top'
                },
                {
                    'title': 'Analytics & Insights',
                    'content': 'Get detailed analytics and AI-powered insights about your review performance.',
                    'target': '.analytics-section',
                    'position': 'top'
                },
                {
                    'title': 'You\'re All Set!',
                    'content': 'Great! You\'re ready to start managing your reviews. Explore the features and let us know if you need help.',
                    'target': '.user-menu',
                    'position': 'bottom-left'
                }
            ]
        },
        'dashboard': {
            'title': 'Dashboard Overview',
            'steps': [
                {
                    'title': 'Key Metrics',
                    'content': 'These cards show your most important review metrics: total reviews, average rating, response time, and sentiment.',
                    'target': '.metrics-cards',
                    'position': 'bottom'
                },
                {
                    'title': 'Performance Charts',
                    'content': 'Visual charts help you understand trends in your review performance over time.',
                    'target': '.charts-section',
                    'position': 'top'
                },
                {
                    'title': 'Recent Activity',
                    'content': 'Stay updated with the latest reviews and team activity in real-time.',
                    'target': '.activity-feed',
                    'position': 'left'
                },
                {
                    'title': 'Customization',
                    'content': 'You can customize this dashboard by rearranging widgets and choosing what metrics to display.',
                    'target': '.dashboard-settings',
                    'position': 'bottom-left'
                }
            ]
        }
    }
    
    return tours.get(tour_type, {'title': 'Tour', 'steps': []})

def _create_default_layouts(user_id):
    """Create default dashboard layouts for a new user"""
    layouts = []
    
    # Executive Layout
    executive_layout = DashboardLayout(
        user_id=user_id,
        name='Executive Overview',
        description='High-level metrics and trends for executives',
        is_default=True,
        tags='executive,overview,metrics'
    )
    executive_layout.set_layout_data({
        'widgets': [
            {'type': 'metrics_card', 'position': {'x': 0, 'y': 0, 'w': 3, 'h': 2}},
            {'type': 'chart', 'position': {'x': 3, 'y': 0, 'w': 6, 'h': 4}},
            {'type': 'performance_summary', 'position': {'x': 9, 'y': 0, 'w': 3, 'h': 4}},
            {'type': 'recent_reviews', 'position': {'x': 0, 'y': 2, 'w': 6, 'h': 3}},
            {'type': 'team_activity', 'position': {'x': 6, 'y': 4, 'w': 6, 'h': 3}}
        ]
    })
    layouts.append(executive_layout)
    
    # Manager Layout
    manager_layout = DashboardLayout(
        user_id=user_id,
        name='Manager Dashboard',
        description='Operational view with team management focus',
        tags='manager,operations,team'
    )
    manager_layout.set_layout_data({
        'widgets': [
            {'type': 'quick_actions', 'position': {'x': 0, 'y': 0, 'w': 3, 'h': 2}},
            {'type': 'metrics_card', 'position': {'x': 3, 'y': 0, 'w': 6, 'h': 2}},
            {'type': 'activity_feed', 'position': {'x': 9, 'y': 0, 'w': 3, 'h': 5}},
            {'type': 'recent_reviews', 'position': {'x': 0, 'y': 2, 'w': 9, 'h': 3}},
            {'type': 'team_activity', 'position': {'x': 0, 'y': 5, 'w': 9, 'h': 2}}
        ]
    })
    layouts.append(manager_layout)
    
    # Agent Layout
    agent_layout = DashboardLayout(
        user_id=user_id,
        name='Agent Workspace',
        description='Review-focused layout for agents',
        tags='agent,reviews,responses'
    )
    agent_layout.set_layout_data({
        'widgets': [
            {'type': 'quick_actions', 'position': {'x': 0, 'y': 0, 'w': 4, 'h': 2}},
            {'type': 'notifications', 'position': {'x': 4, 'y': 0, 'w': 4, 'h': 2}},
            {'type': 'metrics_card', 'position': {'x': 8, 'y': 0, 'w': 4, 'h': 2}},
            {'type': 'recent_reviews', 'position': {'x': 0, 'y': 2, 'w': 12, 'h': 4}}
        ]
    })
    layouts.append(agent_layout)
    
    # Add all layouts to database
    for layout in layouts:
        db.session.add(layout)
    
    db.session.commit()
    return layouts

