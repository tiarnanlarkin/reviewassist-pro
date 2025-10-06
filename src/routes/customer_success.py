from flask import Blueprint, request, jsonify, current_app
from datetime import datetime, timedelta
from src.models.user import db
from src.models.customer_success import (
    HelpArticle, HelpCategory, SupportTicket, TicketMessage, 
    LiveChatSession, ChatMessage, CustomerHealthScore, FeatureAdoption,
    OnboardingProgress, VideoTutorial, UserVideoProgress, CustomerSuccessMetric,
    TicketStatus, TicketPriority, ChatStatus, ArticleStatus, CustomerHealthStatus
)

from src.models.auth import AuthUser, UserRole
from src.routes.auth import token_required
import uuid
import random
from sqlalchemy import func, desc, asc

customer_success_bp = Blueprint('customer_success', __name__)

# Help Center Routes
@customer_success_bp.route('/help/categories', methods=['GET'])
def get_help_categories():
    """Get all help categories"""
    try:
        categories = HelpCategory.query.filter_by(is_active=True).order_by(HelpCategory.sort_order).all()
        return jsonify({
            'success': True,
            'categories': [category.to_dict() for category in categories]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@customer_success_bp.route('/help/articles', methods=['GET'])
def get_help_articles():
    """Get help articles with optional filtering"""
    try:
        query = HelpArticle.query.filter_by(status=ArticleStatus.PUBLISHED, is_active=True)

        
        # Filter by category
        category_id = request.args.get('category_id')
        if category_id:
            query = query.filter_by(category_id=category_id)
        
        # Search functionality
        search = request.args.get('search')
        if search:
            query = query.filter(
                db.or_(
                    HelpArticle.title.contains(search),
                    HelpArticle.content.contains(search),
                    HelpArticle.search_keywords.contains(search)
                )
            )
        
        # Featured articles
        featured = request.args.get('featured')
        if featured == 'true':
            query = query.filter_by(featured=True)
        
        # Pagination
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        
        articles = query.order_by(desc(HelpArticle.featured), desc(HelpArticle.view_count)).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'success': True,
            'articles': [article.to_dict() for article in articles.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': articles.total,
                'pages': articles.pages
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@customer_success_bp.route('/help/articles/<slug>', methods=['GET'])
def get_help_article(slug):
    """Get a specific help article by slug"""
    try:
        article = HelpArticle.query.filter_by(slug=slug, status=ArticleStatus.PUBLISHED).first()
        if not article:
            return jsonify({'success': False, 'error': 'Article not found'}), 404
        
        # Increment view count
        article.view_count += 1
        db.session.commit()
        
        return jsonify({
            'success': True,
            'article': article.to_dict()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@customer_success_bp.route('/help/articles/<int:article_id>/vote', methods=['POST'])
@token_required
def vote_help_article(current_user, article_id):
    """Vote on help article helpfulness"""
    try:
        data = request.get_json()
        helpful = data.get('helpful', True)
        
        article = HelpArticle.query.get_or_404(article_id)
        
        if helpful:
            article.helpful_votes += 1
        else:
            article.unhelpful_votes += 1
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'helpful_votes': article.helpful_votes,
            'unhelpful_votes': article.unhelpful_votes
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Support Ticket Routes
@customer_success_bp.route('/support/tickets', methods=['GET'])
@token_required
def get_support_tickets(current_user):
    """Get support tickets for current user"""
    try:
        query = SupportTicket.query.filter_by(user_id=current_user.id)
        
        # Filter by status
        status = request.args.get('status')
        if status:
            query = query.filter_by(status=TicketStatus(status))
        
        tickets = query.order_by(desc(SupportTicket.created_at)).all()
        
        return jsonify({
            'success': True,
            'tickets': [ticket.to_dict() for ticket in tickets]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@customer_success_bp.route('/support/tickets', methods=['POST'])
@token_required
def create_support_ticket(current_user):
    """Create a new support ticket"""
    try:
        data = request.get_json()
        
        # Generate ticket number
        ticket_number = f"TKT-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
        
        ticket = SupportTicket(
            ticket_number=ticket_number,
            user_id=current_user.id,
            subject=data.get('subject'),
            description=data.get('description'),
            priority=TicketPriority(data.get('priority', 'medium')),
            category=data.get('category'),
            customer_email=current_user.email,
            customer_name=f"{current_user.first_name} {current_user.last_name}"
        )
        
        db.session.add(ticket)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'ticket': ticket.to_dict()
        }), 201
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@customer_success_bp.route('/support/tickets/<int:ticket_id>/messages', methods=['GET'])
@token_required
def get_ticket_messages(current_user, ticket_id):
    """Get messages for a support ticket"""
    try:
        ticket = SupportTicket.query.filter_by(id=ticket_id, user_id=current_user.id).first()
        if not ticket:
            return jsonify({'success': False, 'error': 'Ticket not found'}), 404
        
        messages = TicketMessage.query.filter_by(ticket_id=ticket_id).order_by(TicketMessage.created_at).all()
        
        return jsonify({
            'success': True,
            'messages': [message.to_dict() for message in messages]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@customer_success_bp.route('/support/tickets/<int:ticket_id>/messages', methods=['POST'])
@token_required
def add_ticket_message(current_user, ticket_id):
    """Add a message to a support ticket"""
    try:
        ticket = SupportTicket.query.filter_by(id=ticket_id, user_id=current_user.id).first()
        if not ticket:
            return jsonify({'success': False, 'error': 'Ticket not found'}), 404
        
        data = request.get_json()
        
        message = TicketMessage(
            ticket_id=ticket_id,
            user_id=current_user.id,
            message=data.get('message'),
            is_internal=False
        )
        
        db.session.add(message)
        
        # Update ticket status if it was waiting for customer
        if ticket.status == TicketStatus.WAITING_FOR_CUSTOMER:
            ticket.status = TicketStatus.OPEN
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': message.to_dict()
        }), 201
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Live Chat Routes
@customer_success_bp.route('/chat/sessions', methods=['POST'])
def start_chat_session():
    """Start a new live chat session"""
    try:
        data = request.get_json()
        
        session = LiveChatSession(
            visitor_name=data.get('visitor_name'),
            visitor_email=data.get('visitor_email'),
            subject=data.get('subject'),
            visitor_info=data.get('visitor_info', {})
        )
        
        db.session.add(session)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'session': session.to_dict()
        }), 201
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@customer_success_bp.route('/chat/sessions/<session_id>/messages', methods=['GET'])
def get_chat_messages(session_id):
    """Get messages for a chat session"""
    try:
        messages = ChatMessage.query.filter_by(session_id=session_id).order_by(ChatMessage.created_at).all()
        
        return jsonify({
            'success': True,
            'messages': [message.to_dict() for message in messages]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@customer_success_bp.route('/chat/sessions/<session_id>/messages', methods=['POST'])
def send_chat_message(session_id):
    """Send a message in a chat session"""
    try:
        data = request.get_json()
        
        message = ChatMessage(
            session_id=session_id,
            sender_type=data.get('sender_type', 'visitor'),
            sender_name=data.get('sender_name'),
            message=data.get('message'),
            message_type=data.get('message_type', 'text')
        )
        
        db.session.add(message)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': message.to_dict()
        }), 201
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Customer Health & Success Tracking Routes
@customer_success_bp.route('/success/health-score', methods=['GET'])
@token_required
def get_customer_health_score(current_user):
    """Get customer health score for current user"""
    try:
        health_score = CustomerHealthScore.query.filter_by(user_id=current_user.id).first()
        
        if not health_score:
            # Calculate initial health score
            health_score = calculate_customer_health_score(current_user.id)
        
        return jsonify({
            'success': True,
            'health_score': health_score.to_dict() if health_score else None
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@customer_success_bp.route('/success/feature-adoption', methods=['GET'])
@token_required
def get_feature_adoption(current_user):
    """Get feature adoption data for current user"""
    try:
        adoptions = FeatureAdoption.query.filter_by(user_id=current_user.id).all()
        
        return jsonify({
            'success': True,
            'feature_adoption': [adoption.to_dict() for adoption in adoptions]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@customer_success_bp.route('/success/onboarding-progress', methods=['GET'])
@token_required
def get_onboarding_progress(current_user):
    """Get onboarding progress for current user"""
    try:
        progress = OnboardingProgress.query.filter_by(user_id=current_user.id).all()
        
        # Calculate overall completion percentage
        total_steps = len(progress) if progress else 0
        completed_steps = len([p for p in progress if p.completed]) if progress else 0
        overall_percentage = (completed_steps / total_steps * 100) if total_steps > 0 else 0
        
        return jsonify({
            'success': True,
            'onboarding_progress': [p.to_dict() for p in progress],
            'overall_completion': overall_percentage,
            'completed_steps': completed_steps,
            'total_steps': total_steps
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Video Tutorial Routes
@customer_success_bp.route('/tutorials/videos', methods=['GET'])
def get_video_tutorials():
    """Get video tutorials"""
    try:
        query = VideoTutorial.query.filter_by(is_active=True)

        
        # Filter by category
        category = request.args.get('category')
        if category:
            query = query.filter_by(category=category)
        
        # Filter by difficulty
        difficulty = request.args.get('difficulty')
        if difficulty:
            query = query.filter_by(difficulty_level=difficulty)
        
        # Featured videos
        featured = request.args.get('featured')
        if featured == 'true':
            query = query.filter_by(is_featured=True)
        
        videos = query.order_by(VideoTutorial.sort_order, desc(VideoTutorial.view_count)).all()
        
        return jsonify({
            'success': True,
            'videos': [video.to_dict() for video in videos]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@customer_success_bp.route('/tutorials/videos/<int:video_id>/progress', methods=['POST'])
@token_required
def update_video_progress(current_user, video_id):
    """Update user progress on a video tutorial"""
    try:
        data = request.get_json()
        
        progress = UserVideoProgress.query.filter_by(
            user_id=current_user.id, 
            video_id=video_id
        ).first()
        
        if not progress:
            progress = UserVideoProgress(
                user_id=current_user.id,
                video_id=video_id
            )
            db.session.add(progress)
        
        progress.progress_seconds = data.get('progress_seconds', 0)
        progress.completion_percentage = data.get('completion_percentage', 0)
        progress.completed = data.get('completed', False)
        progress.last_watched_at = datetime.utcnow()
        
        # Update video view count if first time watching
        if progress.progress_seconds == 0:
            video = VideoTutorial.query.get(video_id)
            if video:
                video.view_count += 1
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'progress': progress.to_dict()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Admin Routes for Customer Success Management
@customer_success_bp.route('/admin/help/articles', methods=['POST'])
@token_required
def create_help_article(current_user):
    """Create a new help article (admin only)"""
    try:
        if current_user.role != UserRole.ADMIN:
            return jsonify({'success': False, 'error': 'Admin access required'}), 403
        
        data = request.get_json()
        
        # Generate slug from title
        slug = data.get('title', '').lower().replace(' ', '-').replace('/', '-')
        
        article = HelpArticle(
            title=data.get('title'),
            slug=slug,
            content=data.get('content'),
            excerpt=data.get('excerpt'),
            category_id=data.get('category_id'),
            author_id=current_user.id,
            status=ArticleStatus(data.get('status', 'draft')),
            featured=data.get('featured', False),
            tags=data.get('tags', []),
            meta_description=data.get('meta_description'),
            search_keywords=data.get('search_keywords')
        )
        
        if article.status == ArticleStatus.PUBLISHED:
            article.published_at = datetime.utcnow()
        
        db.session.add(article)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'article': article.to_dict()
        }), 201
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@customer_success_bp.route('/admin/support/tickets', methods=['GET'])
@token_required
def get_all_support_tickets(current_user):
    """Get all support tickets (admin/manager only)"""
    try:
        if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
            return jsonify({'success': False, 'error': 'Admin or Manager access required'}), 403
        
        query = SupportTicket.query
        
        # Filter by status
        status = request.args.get('status')
        if status:
            query = query.filter_by(status=TicketStatus(status))
        
        # Filter by priority
        priority = request.args.get('priority')
        if priority:
            query = query.filter_by(priority=TicketPriority(priority))
        
        tickets = query.order_by(desc(SupportTicket.created_at)).all()
        
        return jsonify({
            'success': True,
            'tickets': [ticket.to_dict() for ticket in tickets]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@customer_success_bp.route('/admin/success/metrics', methods=['GET'])
@token_required
def get_customer_success_metrics(current_user):
    """Get customer success metrics (admin only)"""
    try:
        if current_user.role != UserRole.ADMIN:
            return jsonify({'success': False, 'error': 'Admin access required'}), 403
        
        # Calculate various metrics
        total_users = AuthUser.query.count()
        active_tickets = SupportTicket.query.filter(
            SupportTicket.status.in_([TicketStatus.OPEN, TicketStatus.IN_PROGRESS])
        ).count()
        
        # Average health score
        avg_health_score = db.session.query(func.avg(CustomerHealthScore.overall_score)).scalar() or 0
        
        # Feature adoption rate
        total_features = 10  # Assuming 10 main features
        avg_features_adopted = db.session.query(func.avg(CustomerHealthScore.features_used)).scalar() or 0
        adoption_rate = (avg_features_adopted / total_features * 100) if total_features > 0 else 0
        
        # Support satisfaction
        avg_satisfaction = db.session.query(func.avg(SupportTicket.satisfaction_rating)).scalar() or 0
        
        return jsonify({
            'success': True,
            'metrics': {
                'total_users': total_users,
                'active_tickets': active_tickets,
                'average_health_score': round(avg_health_score, 2),
                'feature_adoption_rate': round(adoption_rate, 2),
                'support_satisfaction': round(avg_satisfaction, 2),
                'calculated_at': datetime.utcnow().isoformat()
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Utility Functions
def calculate_customer_health_score(user_id):
    """Calculate customer health score for a user"""
    try:
        user = AuthUser.query.get(user_id)
        if not user:
            return None
        
        # Calculate various scores (simplified for demo)
        login_score = min(100, user.last_login_days_ago * 10) if hasattr(user, 'last_login_days_ago') else 50
        feature_score = random.randint(40, 90)  # Demo data
        support_score = random.randint(60, 100)  # Demo data
        billing_score = random.randint(80, 100)  # Demo data
        engagement_score = random.randint(50, 95)  # Demo data
        
        overall_score = (login_score + feature_score + support_score + billing_score + engagement_score) / 5
        
        # Determine status based on score
        if overall_score >= 80:
            status = CustomerHealthStatus.HEALTHY
        elif overall_score >= 60:
            status = CustomerHealthStatus.AT_RISK
        else:
            status = CustomerHealthStatus.CRITICAL
        
        # Check if health score already exists
        health_score = CustomerHealthScore.query.filter_by(user_id=user_id).first()
        if not health_score:
            health_score = CustomerHealthScore(user_id=user_id)
            db.session.add(health_score)
        
        health_score.overall_score = overall_score
        health_score.status = status
        health_score.login_frequency_score = login_score
        health_score.feature_adoption_score = feature_score
        health_score.support_interaction_score = support_score
        health_score.billing_health_score = billing_score
        health_score.engagement_score = engagement_score
        health_score.calculated_at = datetime.utcnow()
        
        db.session.commit()
        return health_score
        
    except Exception as e:
        print(f"Error calculating health score: {e}")
        return None

@customer_success_bp.route('/admin/seed-customer-success-data', methods=['POST'])
@token_required
def seed_customer_success_data(current_user):
    """Seed demo customer success data (admin only)"""
    try:
        if current_user.role != UserRole.ADMIN:
            return jsonify({'success': False, 'error': 'Admin access required'}), 403
        
        # Check if data already exists
        if HelpCategory.query.first():
            return jsonify({'success': True, 'message': 'Customer success data already exists'})
        
        # Create help categories
        categories = [
            {'name': 'Getting Started', 'slug': 'getting-started', 'icon': 'play-circle', 'color': '#10B981'},
            {'name': 'Account Management', 'slug': 'account-management', 'icon': 'user-circle', 'color': '#3B82F6'},
            {'name': 'Reviews & Responses', 'slug': 'reviews-responses', 'icon': 'chat-bubble-left-right', 'color': '#8B5CF6'},
            {'name': 'Analytics & Reports', 'slug': 'analytics-reports', 'icon': 'chart-bar', 'color': '#F59E0B'},
            {'name': 'Integrations', 'slug': 'integrations', 'icon': 'puzzle-piece', 'color': '#EF4444'},
            {'name': 'Billing & Subscriptions', 'slug': 'billing-subscriptions', 'icon': 'credit-card', 'color': '#06B6D4'}
        ]
        
        for i, cat_data in enumerate(categories):
            category = HelpCategory(
                name=cat_data['name'],
                slug=cat_data['slug'],
                description=f"Help articles for {cat_data['name'].lower()}",
                icon=cat_data['icon'],
                color=cat_data['color'],
                sort_order=i
            )
            db.session.add(category)
        
        db.session.commit()
        
        # Create sample help articles
        articles = [
            {
                'title': 'How to Get Started with ReviewAssist Pro',
                'slug': 'how-to-get-started',
                'content': 'Welcome to ReviewAssist Pro! This guide will help you get started...',
                'category_id': 1,
                'featured': True
            },
            {
                'title': 'Managing Your Account Settings',
                'slug': 'managing-account-settings',
                'content': 'Learn how to update your account settings and preferences...',
                'category_id': 2,
                'featured': False
            },
            {
                'title': 'Responding to Reviews Effectively',
                'slug': 'responding-to-reviews',
                'content': 'Best practices for responding to customer reviews...',
                'category_id': 3,
                'featured': True
            }
        ]
        
        for article_data in articles:
            article = HelpArticle(
                title=article_data['title'],
                slug=article_data['slug'],
                content=article_data['content'],
                excerpt=article_data['content'][:150] + '...',
                category_id=article_data['category_id'],
                author_id=current_user.id,
                status=ArticleStatus.PUBLISHED,
                featured=article_data['featured'],
                published_at=datetime.utcnow()
            )
            db.session.add(article)
        
        # Create sample video tutorials
        videos = [
            {
                'title': 'ReviewAssist Pro Overview',
                'description': 'A comprehensive overview of ReviewAssist Pro features',
                'video_url': 'https://example.com/video1',
                'category': 'Getting Started',
                'difficulty_level': 'beginner',
                'duration': 300,
                'is_featured': True
            },
            {
                'title': 'Setting Up Platform Integrations',
                'description': 'Learn how to connect your review platforms',
                'video_url': 'https://example.com/video2',
                'category': 'Integrations',
                'difficulty_level': 'intermediate',
                'duration': 450,
                'is_featured': False
            }
        ]
        
        for video_data in videos:
            video = VideoTutorial(**video_data)
            db.session.add(video)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Customer success data seeded successfully'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500




@customer_success_bp.route('/help/articles/<int:article_id>/related', methods=['GET'])
def get_related_articles(article_id):
    """Get related help articles based on tags and category"""
    try:
        article = HelpArticle.query.get_or_404(article_id)
        
        # Find articles with shared tags
        related_by_tags = HelpArticle.query.filter(
            HelpArticle.id != article_id,
            HelpArticle.status == ArticleStatus.PUBLISHED,
            HelpArticle.tags.op('&&')(article.tags)  # Overlap operator for JSONB
        ).limit(5).all()
        
        # Find articles in the same category
        related_by_category = HelpArticle.query.filter(
            HelpArticle.id != article_id,
            HelpArticle.category_id == article.category_id,
            HelpArticle.status == ArticleStatus.PUBLISHED
        ).limit(5).all()
        
        # Combine and de-duplicate results
        related_articles = {art.id: art for art in related_by_tags}
        for art in related_by_category:
            related_articles[art.id] = art
            
        return jsonify({
            'success': True,
            'related_articles': [art.to_dict() for art in related_articles.values()][:5]  # Limit to 5
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500



@customer_success_bp.route('/help/articles/popular', methods=['GET'])
def get_popular_articles():
    """Get most popular help articles based on view count"""
    try:
        popular_articles = HelpArticle.query.filter_by(status=ArticleStatus.PUBLISHED).order_by(desc(HelpArticle.view_count)).limit(5).all()
        return jsonify({
            'success': True,
            'popular_articles': [article.to_dict() for article in popular_articles]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500



@customer_success_bp.route("/admin/help/categories", methods=["POST"])
@token_required
def create_help_category(current_user):
    """Create a new help category (admin only)"""
    try:
        if current_user.role != UserRole.ADMIN:
            return jsonify({"success": False, "error": "Admin access required"}), 403
        
        data = request.get_json()
        
        slug = data.get("name", "").lower().replace(" ", "-").replace("/", "-")
        
        category = HelpCategory(
            name=data.get("name"),
            slug=slug,
            description=data.get("description"),
            icon=data.get("icon"),
            color=data.get("color"),
            sort_order=data.get("sort_order", 0),
            is_active=data.get("is_active", True)
        )
        
        db.session.add(category)
        db.session.commit()
        
        return jsonify({"success": True, "category": category.to_dict()}), 201
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@customer_success_bp.route("/admin/help/categories/<int:category_id>", methods=["PUT"])
@token_required
def update_help_category(current_user, category_id):
    """Update an existing help category (admin only)"""
    try:
        if current_user.role != UserRole.ADMIN:
            return jsonify({"success": False, "error": "Admin access required"}), 403
        
        category = HelpCategory.query.get_or_404(category_id)
        data = request.get_json()
        
        category.name = data.get("name", category.name)
        category.slug = data.get("slug", category.slug)
        category.description = data.get("description", category.description)
        category.icon = data.get("icon", category.icon)
        category.color = data.get("color", category.color)
        category.sort_order = data.get("sort_order", category.sort_order)
        category.is_active = data.get("is_active", category.is_active)
        
        db.session.commit()
        
        return jsonify({"success": True, "category": category.to_dict()})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@customer_success_bp.route("/admin/help/categories/<int:category_id>", methods=["DELETE"])
@token_required
def delete_help_category(current_user, category_id):
    """Delete a help category (admin only)"""
    try:
        if current_user.role != UserRole.ADMIN:
            return jsonify({"success": False, "error": "Admin access required"}), 403
        
        category = HelpCategory.query.get_or_404(category_id)
        db.session.delete(category)
        db.session.commit()
        
        return jsonify({"success": True, "message": "Category deleted successfully"}), 204
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500



@customer_success_bp.route("/admin/help/articles/<int:article_id>", methods=["PUT"])
@token_required
def update_help_article(current_user, article_id):
    """Update an existing help article (admin only)"""
    try:
        if current_user.role != UserRole.ADMIN:
            return jsonify({"success": False, "error": "Admin access required"}), 403
        
        article = HelpArticle.query.get_or_404(article_id)
        data = request.get_json()
        
        article.title = data.get("title", article.title)
        article.slug = data.get("slug", article.slug)
        article.content = data.get("content", article.content)
        article.excerpt = data.get("excerpt", article.excerpt)
        article.category_id = data.get("category_id", article.category_id)
        article.status = ArticleStatus(data.get("status", article.status.value))
        article.featured = data.get("featured", article.featured)
        article.tags = data.get("tags", article.tags)
        article.meta_description = data.get("meta_description", article.meta_description)
        article.search_keywords = data.get("search_keywords", article.search_keywords)
        
        if article.status == ArticleStatus.PUBLISHED and not article.published_at:
            article.published_at = datetime.utcnow()
        elif article.status != ArticleStatus.PUBLISHED:
            article.published_at = None
            
        db.session.commit()
        
        return jsonify({"success": True, "article": article.to_dict()})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@customer_success_bp.route("/admin/help/articles/<int:article_id>", methods=["DELETE"])
@token_required
def delete_help_article(current_user, article_id):
    """Delete a help article (admin only)"""
    try:
        if current_user.role != UserRole.ADMIN:
            return jsonify({"success": False, "error": "Admin access required"}), 403
        
        article = HelpArticle.query.get_or_404(article_id)
        db.session.delete(article)
        db.session.commit()
        
        return jsonify({"success": True, "message": "Article deleted successfully"}), 204
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500



@customer_success_bp.route("/admin/tutorials/videos", methods=["POST"])
@token_required
def create_video_tutorial(current_user):
    """Create a new video tutorial (admin only)"""
    try:
        if current_user.role != UserRole.ADMIN:
            return jsonify({"success": False, "error": "Admin access required"}), 403
        
        data = request.get_json()
        
        video = VideoTutorial(
            title=data.get("title"),
            description=data.get("description"),
            video_url=data.get("video_url"),
            thumbnail_url=data.get("thumbnail_url"),
            duration=data.get("duration"),
            category=data.get("category"),
            difficulty_level=data.get("difficulty_level"),
            tags=data.get("tags", []),
            is_published=data.get("is_published", False),
            is_featured=data.get("is_featured", False),
            sort_order=data.get("sort_order", 0)
        )
        
        db.session.add(video)
        db.session.commit()
        
        return jsonify({"success": True, "video": video.to_dict()}), 201
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@customer_success_bp.route("/admin/tutorials/videos/<int:video_id>", methods=["PUT"])
@token_required
def update_video_tutorial(current_user, video_id):
    """Update an existing video tutorial (admin only)"""
    try:
        if current_user.role != UserRole.ADMIN:
            return jsonify({"success": False, "error": "Admin access required"}), 403
        
        video = VideoTutorial.query.get_or_404(video_id)
        data = request.get_json()
        
        video.title = data.get("title", video.title)
        video.description = data.get("description", video.description)
        video.video_url = data.get("video_url", video.video_url)
        video.thumbnail_url = data.get("thumbnail_url", video.thumbnail_url)
        video.duration = data.get("duration", video.duration)
        video.category = data.get("category", video.category)
        video.difficulty_level = data.get("difficulty_level", video.difficulty_level)
        video.tags = data.get("tags", video.tags)
        video.is_published = data.get("is_published", video.is_published)
        video.is_featured = data.get("is_featured", video.is_featured)
        video.sort_order = data.get("sort_order", video.sort_order)
        
        db.session.commit()
        
        return jsonify({"success": True, "video": video.to_dict()})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@customer_success_bp.route("/admin/tutorials/videos/<int:video_id>", methods=["DELETE"])
@token_required
def delete_video_tutorial(current_user, video_id):
    """Delete a video tutorial (admin only)"""
    try:
        if current_user.role != UserRole.ADMIN:
            return jsonify({"success": False, "error": "Admin access required"}), 403
        
        video = VideoTutorial.query.get_or_404(video_id)
        db.session.delete(video)
        db.session.commit()
        
        return jsonify({"success": True, "message": "Video tutorial deleted successfully"}), 204
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500



@customer_success_bp.route("/admin/support/tickets/<int:ticket_id>/messages/<int:message_id>", methods=["PUT"])
@token_required
def update_ticket_message(current_user, ticket_id, message_id):
    """Update a ticket message (admin only)"""
    try:
        if current_user.role != UserRole.ADMIN:
            return jsonify({"success": False, "error": "Admin access required"}), 403
        
        message = TicketMessage.query.filter_by(id=message_id, ticket_id=ticket_id).first_or_404()
        data = request.get_json()
        
        message.message = data.get("message", message.message)
        message.is_internal = data.get("is_internal", message.is_internal)
        message.attachments = data.get("attachments", message.attachments)
        
        db.session.commit()
        
        return jsonify({"success": True, "message": message.to_dict()})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@customer_success_bp.route("/admin/support/tickets/<int:ticket_id>/messages/<int:message_id>", methods=["DELETE"])
@token_required
def delete_ticket_message(current_user, ticket_id, message_id):
    """Delete a ticket message (admin only)"""
    try:
        if current_user.role != UserRole.ADMIN:
            return jsonify({"success": False, "error": "Admin access required"}), 403
        
        message = TicketMessage.query.filter_by(id=message_id, ticket_id=ticket_id).first_or_404()
        db.session.delete(message)
        db.session.commit()
        
        return jsonify({"success": True, "message": "Ticket message deleted successfully"}), 204
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500



@customer_success_bp.route("/admin/chat/sessions", methods=["GET"])
@token_required
def get_all_chat_sessions(current_user):
    """Get all live chat sessions (admin/manager only)"""
    try:
        if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
            return jsonify({"success": False, "error": "Admin access required"}), 403
        
        sessions = LiveChatSession.query.order_by(desc(LiveChatSession.started_at)).all()
        
        return jsonify({
            "success": True,
            "sessions": [session.to_dict() for session in sessions]
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@customer_success_bp.route("/admin/chat/sessions/<session_id>", methods=["PUT"])
@token_required
def update_chat_session(current_user, session_id):
    """Update a live chat session (admin/manager only)"""
    try:
        if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
            return jsonify({"success": False, "error": "Admin access required"}), 403
        
        session = LiveChatSession.query.filter_by(session_id=session_id).first_or_404()
        data = request.get_json()
        
        session.status = ChatStatus(data.get("status", session.status.value))
        session.agent_id = data.get("agent_id", session.agent_id)
        session.subject = data.get("subject", session.subject)
        session.visitor_name = data.get("visitor_name", session.visitor_name)
        session.visitor_email = data.get("visitor_email", session.visitor_email)
        session.visitor_info = data.get("visitor_info", session.visitor_info)
        session.ended_at = data.get("ended_at", session.ended_at)
        session.rating = data.get("rating", session.rating)
        session.feedback = data.get("feedback", session.feedback)
        
        db.session.commit()
        
        return jsonify({"success": True, "session": session.to_dict()})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@customer_success_bp.route("/admin/chat/sessions/<session_id>", methods=["DELETE"])
@token_required
def delete_chat_session(current_user, session_id):
    """Delete a live chat session (admin only)"""
    try:
        if current_user.role != UserRole.ADMIN:
            return jsonify({"success": False, "error": "Admin access required"}), 403
        
        session = LiveChatSession.query.filter_by(session_id=session_id).first_or_404()
        db.session.delete(session)
        db.session.commit()
        
        return jsonify({"success": True, "message": "Chat session deleted successfully"}), 204
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500



@customer_success_bp.route("/success/onboarding-progress/<int:progress_id>", methods=["PUT"])
@token_required
def update_onboarding_progress(current_user, progress_id):
    """Update a specific onboarding progress step for the current user"""
    try:
        data = request.get_json()
        
        progress_step = OnboardingProgress.query.filter_by(id=progress_id, user_id=current_user.id).first_or_404()
        
        progress_step.completed = data.get("completed", progress_step.completed)
        progress_step.completion_percentage = data.get("completion_percentage", progress_step.completion_percentage)
        progress_step.time_spent = data.get("time_spent", progress_step.time_spent)
        progress_step.attempts = data.get("attempts", progress_step.attempts)
        progress_step.skipped = data.get("skipped", progress_step.skipped)
        
        if progress_step.completed and not progress_step.completed_at:
            progress_step.completed_at = datetime.utcnow()
        elif not progress_step.completed:
            progress_step.completed_at = None
            
        db.session.commit()
        
        return jsonify({"success": True, "onboarding_progress": progress_step.to_dict()})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@customer_success_bp.route("/admin/onboarding-progress", methods=["POST"])
@token_required
def create_onboarding_step(current_user):
    """Create a new onboarding step (admin only)"""
    try:
        if current_user.role != UserRole.ADMIN:
            return jsonify({"success": False, "error": "Admin access required"}), 403
        
        data = request.get_json()
        
        onboarding_step = OnboardingProgress(
            user_id=data.get("user_id"),
            step_name=data.get("step_name"),
            step_category=data.get("step_category"),
            completed=data.get("completed", False),
            completion_percentage=data.get("completion_percentage", 0),
            time_spent=data.get("time_spent", 0),
            attempts=data.get("attempts", 0),
            skipped=data.get("skipped", False)
        )
        
        if onboarding_step.completed:
            onboarding_step.completed_at = datetime.utcnow()
            
        db.session.add(onboarding_step)
        db.session.commit()
        
        return jsonify({"success": True, "onboarding_step": onboarding_step.to_dict()}), 201
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@customer_success_bp.route("/admin/onboarding-progress/<int:progress_id>", methods=["PUT"])
@token_required
def admin_update_onboarding_progress(current_user, progress_id):
    """Update an onboarding progress step (admin only)"""
    try:
        if current_user.role != UserRole.ADMIN:
            return jsonify({"success": False, "error": "Admin access required"}), 403
        
        progress_step = OnboardingProgress.query.get_or_404(progress_id)
        data = request.get_json()
        
        progress_step.user_id = data.get("user_id", progress_step.user_id)
        progress_step.step_name = data.get("step_name", progress_step.step_name)
        progress_step.step_category = data.get("step_category", progress_step.step_category)
        progress_step.completed = data.get("completed", progress_step.completed)
        progress_step.completion_percentage = data.get("completion_percentage", progress_step.completion_percentage)
        progress_step.time_spent = data.get("time_spent", progress_step.time_spent)
        progress_step.attempts = data.get("attempts", progress_step.attempts)
        progress_step.skipped = data.get("skipped", progress_step.skipped)
        
        if progress_step.completed and not progress_step.completed_at:
            progress_step.completed_at = datetime.utcnow()
        elif not progress_step.completed:
            progress_step.completed_at = None
            
        db.session.commit()
        
        return jsonify({"success": True, "onboarding_step": progress_step.to_dict()})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@customer_success_bp.route("/admin/onboarding-progress/<int:progress_id>", methods=["DELETE"])
@token_required
def delete_onboarding_step(current_user, progress_id):
    """Delete an onboarding step (admin only)"""
    try:
        if current_user.role != UserRole.ADMIN:
            return jsonify({"success": False, "error": "Admin access required"}), 403
        
        onboarding_step = OnboardingProgress.query.get_or_404(progress_id)
        db.session.delete(onboarding_step)
        db.session.commit()
        
        return jsonify({"success": True, "message": "Onboarding step deleted successfully"}), 204
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500



@customer_success_bp.route("/admin/success/health-score", methods=["POST"])
@token_required
def create_customer_health_score(current_user):
    """Create a new customer health score (admin only)"""
    try:
        if current_user.role != UserRole.ADMIN:
            return jsonify({"success": False, "error": "Admin access required"}), 403
        
        data = request.get_json()
        
        health_score = CustomerHealthScore(
            user_id=data.get("user_id"),
            organization_id=data.get("organization_id"),
            overall_score=data.get("overall_score"),
            status=CustomerHealthStatus(data.get("status")),
            login_frequency_score=data.get("login_frequency_score", 0),
            feature_adoption_score=data.get("feature_adoption_score", 0),
            support_interaction_score=data.get("support_interaction_score", 0),
            billing_health_score=data.get("billing_health_score", 0),
            engagement_score=data.get("engagement_score", 0),
            days_since_last_login=data.get("days_since_last_login", 0),
            total_logins=data.get("total_logins", 0),
            features_used=data.get("features_used", 0),
            support_tickets_count=data.get("support_tickets_count", 0),
            satisfaction_rating=data.get("satisfaction_rating"),
            risk_factors=data.get("risk_factors", []),
            recommendations=data.get("recommendations", []),
            calculated_at=datetime.utcnow()
        )
        
        db.session.add(health_score)
        db.session.commit()
        
        return jsonify({"success": True, "health_score": health_score.to_dict()}), 201
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@customer_success_bp.route("/admin/success/health-score/<int:health_score_id>", methods=["PUT"])
@token_required
def update_customer_health_score_admin(current_user, health_score_id):
    """Update a customer health score (admin only)"""
    try:
        if current_user.role != UserRole.ADMIN:
            return jsonify({"success": False, "error": "Admin access required"}), 403
        
        health_score = CustomerHealthScore.query.get_or_404(health_score_id)
        data = request.get_json()
        
        health_score.user_id = data.get("user_id", health_score.user_id)
        health_score.organization_id = data.get("organization_id", health_score.organization_id)
        health_score.overall_score = data.get("overall_score", health_score.overall_score)
        health_score.status = CustomerHealthStatus(data.get("status", health_score.status.value))
        health_score.login_frequency_score = data.get("login_frequency_score", health_score.login_frequency_score)
        health_score.feature_adoption_score = data.get("feature_adoption_score", health_score.feature_adoption_score)
        health_score.support_interaction_score = data.get("support_interaction_score", health_score.support_interaction_score)
        health_score.billing_health_score = data.get("billing_health_score", health_score.billing_health_score)
        health_score.engagement_score = data.get("engagement_score", health_score.engagement_score)
        health_score.days_since_last_login = data.get("days_since_last_login", health_score.days_since_last_login)
        health_score.total_logins = data.get("total_logins", health_score.total_logins)
        health_score.features_used = data.get("features_used", health_score.features_used)
        health_score.support_tickets_count = data.get("support_tickets_count", health_score.support_tickets_count)
        health_score.satisfaction_rating = data.get("satisfaction_rating", health_score.satisfaction_rating)
        health_score.risk_factors = data.get("risk_factors", health_score.risk_factors)
        health_score.recommendations = data.get("recommendations", health_score.recommendations)
        health_score.calculated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({"success": True, "health_score": health_score.to_dict()})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@customer_success_bp.route("/admin/success/health-score/<int:health_score_id>", methods=["DELETE"])
@token_required
def delete_customer_health_score(current_user, health_score_id):
    """Delete a customer health score (admin only)"""
    try:
        if current_user.role != UserRole.ADMIN:
            return jsonify({"success": False, "error": "Admin access required"}), 403
        
        health_score = CustomerHealthScore.query.get_or_404(health_score_id)
        db.session.delete(health_score)
        db.session.commit()
        
        return jsonify({"success": True, "message": "Customer health score deleted successfully"}), 204
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@customer_success_bp.route("/admin/success/feature-adoption", methods=["POST"])
@token_required
def create_feature_adoption(current_user):
    """Create a new feature adoption record (admin only)"""
    try:
        if current_user.role != UserRole.ADMIN:
            return jsonify({"success": False, "error": "Admin access required"}), 403
        
        data = request.get_json()
        
        feature_adoption = FeatureAdoption(
            user_id=data.get("user_id"),
            organization_id=data.get("organization_id"),
            feature_name=data.get("feature_name"),
            first_used_at=datetime.fromisoformat(data["first_used_at"]) if "first_used_at" in data else datetime.utcnow(),
            last_used_at=datetime.fromisoformat(data["last_used_at"]) if "last_used_at" in data else datetime.utcnow(),
            usage_count=data.get("usage_count", 1),
            time_to_adoption=data.get("time_to_adoption"),
            is_power_user=data.get("is_power_user", False)
        )
        
        db.session.add(feature_adoption)
        db.session.commit()
        
        return jsonify({"success": True, "feature_adoption": feature_adoption.to_dict()}), 201
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@customer_success_bp.route("/admin/success/feature-adoption/<int:adoption_id>", methods=["PUT"])
@token_required
def update_feature_adoption(current_user, adoption_id):
    """Update a feature adoption record (admin only)"""
    try:
        if current_user.role != UserRole.ADMIN:
            return jsonify({"success": False, "error": "Admin access required"}), 403
        
        feature_adoption = FeatureAdoption.query.get_or_404(adoption_id)
        data = request.get_json()
        
        feature_adoption.user_id = data.get("user_id", feature_adoption.user_id)
        feature_adoption.organization_id = data.get("organization_id", feature_adoption.organization_id)
        feature_adoption.feature_name = data.get("feature_name", feature_adoption.feature_name)
        feature_adoption.first_used_at = datetime.fromisoformat(data["first_used_at"]) if "first_used_at" in data else feature_adoption.first_used_at
        feature_adoption.last_used_at = datetime.fromisoformat(data["last_used_at"]) if "last_used_at" in data else feature_adoption.last_used_at
        feature_adoption.usage_count = data.get("usage_count", feature_adoption.usage_count)
        feature_adoption.time_to_adoption = data.get("time_to_adoption", feature_adoption.time_to_adoption)
        feature_adoption.is_power_user = data.get("is_power_user", feature_adoption.is_power_user)
        
        db.session.commit()
        
        return jsonify({"success": True, "feature_adoption": feature_adoption.to_dict()})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@customer_success_bp.route("/admin/success/feature-adoption/<int:adoption_id>", methods=["DELETE"])
@token_required
def delete_feature_adoption(current_user, adoption_id):
    """Delete a feature adoption record (admin only)"""
    try:
        if current_user.role != UserRole.ADMIN:
            return jsonify({"success": False, "error": "Admin access required"}), 403
        
        feature_adoption = FeatureAdoption.query.get_or_404(adoption_id)
        db.session.delete(feature_adoption)
        db.session.commit()
        
        return jsonify({"success": True, "message": "Feature adoption record deleted successfully"}), 204
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500



@customer_success_bp.route("/admin/success/calculate-health-scores", methods=["POST"])
@token_required
def trigger_health_score_calculation(current_user):
    """Trigger calculation of all customer health scores (admin only)"""
    try:
        if current_user.role != UserRole.ADMIN:
            return jsonify({"success": False, "error": "Admin access required"}), 403
        
        users = AuthUser.query.all()
        for user in users:
            calculate_customer_health_score(user.id)
            
        return jsonify({"success": True, "message": "Customer health scores calculation triggered"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
