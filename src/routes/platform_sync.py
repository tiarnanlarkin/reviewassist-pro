from flask import Blueprint, request, jsonify, current_app
from flask_cors import cross_origin
import logging
from datetime import datetime, timedelta
from src.models.user import db
from src.models.auth import AuthUser
from src.models.review import Review, Analytics, ResponseTemplate
from src.models.integrations import Integration, IntegrationSyncLog
from src.routes.auth import token_required
from src.services.platform_apis import platform_manager, ReviewData, LocationData
from sqlalchemy import func
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

platform_sync_bp = Blueprint('platform_sync', __name__, url_prefix='/api/platform-sync')

@platform_sync_bp.route('/available-platforms', methods=['GET'])
@cross_origin()
@token_required
def get_available_platforms(current_user):
    """Get list of available platform integrations"""
    try:
        platforms = platform_manager.get_available_platforms()
        
        platform_info = []
        for platform in platforms:
            platform_info.append({
                'name': platform,
                'display_name': platform.title(),
                'supports_sync': True,
                'supports_response': platform in ['google'],  # Only Google supports responses
                'description': get_platform_description(platform)
            })
        
        return jsonify({
            'platforms': platform_info,
            'total_count': len(platform_info)
        })
        
    except Exception as e:
        logger.error(f"Error getting available platforms: {str(e)}")
        return jsonify({'error': 'Failed to get available platforms'}), 500

@platform_sync_bp.route('/sync-reviews', methods=['POST'])
@cross_origin()
@token_required
def sync_reviews(current_user):
    """Sync reviews from a specific platform"""
    try:
        data = request.get_json()
        platform = data.get('platform')
        location_id = data.get('location_id')
        limit = data.get('limit', 50)
        
        if not platform or not location_id:
            return jsonify({'error': 'Platform and location_id are required'}), 400
        
        # Check if user has integration configured
        integration = Integration.query.filter_by(
            user_id=current_user.id,
            platform=platform,
            is_active=True
        ).first()
        
        if not integration:
            return jsonify({'error': f'No active {platform} integration found'}), 400
        
        # Sync reviews from platform
        reviews_data = platform_manager.sync_reviews(platform, location_id, limit)
        
        # Save reviews to database
        saved_reviews = []
        new_count = 0
        updated_count = 0
        
        for review_data in reviews_data:
            # Check if review already exists
            existing_review = Review.query.filter_by(
                platform_review_id=review_data.platform_review_id,
                platform=review_data.platform
            ).first()
            
            if existing_review:
                # Update existing review
                existing_review.rating = review_data.rating
                existing_review.review_text = review_data.review_text
                existing_review.sentiment = review_data.sentiment
                existing_review.updated_at = datetime.utcnow()
                updated_count += 1
            else:
                # Create new review
                new_review = Review(
                    user_id=current_user.id,
                    platform=review_data.platform,
                    platform_review_id=review_data.platform_review_id,
                    reviewer_name=review_data.reviewer_name,
                    reviewer_avatar=review_data.reviewer_avatar,
                    rating=review_data.rating,
                    review_text=review_data.review_text,
                    review_date=review_data.review_date,
                    location_id=review_data.location_id,
                    location_name=review_data.location_name,
                    sentiment=review_data.sentiment or determine_sentiment(review_data.review_text, review_data.rating),
                    language=review_data.language,
                    verified=review_data.verified,
                    helpful_count=review_data.helpful_count,
                    photos=json.dumps(review_data.photos) if review_data.photos else None
                )
                
                # Add response if exists
                if review_data.response_text:
                    response = ReviewResponse(
                        review=new_review,
                        response_text=review_data.response_text,
                        response_date=review_data.response_date or datetime.utcnow(),
                        response_source='platform'
                    )
                    db.session.add(response)
                
                db.session.add(new_review)
                saved_reviews.append(new_review)
                new_count += 1
        
        # Create sync log
        sync_log = IntegrationSyncLog(
            integration_id=integration.id,
            sync_type='reviews',
            status='success',
            records_processed=len(reviews_data),
            records_created=new_count,
            records_updated=updated_count,
            sync_details=json.dumps({
                'platform': platform,
                'location_id': location_id,
                'limit': limit
            })
        )
        
        db.session.add(sync_log)
        db.session.commit()
        
        return jsonify({
            'message': 'Reviews synced successfully',
            'total_processed': len(reviews_data),
            'new_reviews': new_count,
            'updated_reviews': updated_count,
            'sync_log_id': sync_log.id
        })
        
    except Exception as e:
        logger.error(f"Error syncing reviews: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to sync reviews'}), 500

@platform_sync_bp.route('/sync-all', methods=['POST'])
@cross_origin()
@token_required
def sync_all_platforms(current_user):
    """Sync reviews from all configured platforms"""
    try:
        data = request.get_json()
        limit = data.get('limit', 50)
        
        # Get all active integrations for user
        integrations = Integration.query.filter_by(
            user_id=current_user.id,
            is_active=True
        ).all()
        
        if not integrations:
            return jsonify({'error': 'No active integrations found'}), 400
        
        # Build location configs
        location_configs = {}
        for integration in integrations:
            config = json.loads(integration.configuration) if integration.configuration else {}
            location_id = config.get('location_id')
            if location_id:
                location_configs[integration.platform] = location_id
        
        if not location_configs:
            return jsonify({'error': 'No location configurations found'}), 400
        
        # Sync from all platforms
        results = platform_manager.sync_all_platforms(location_configs, limit)
        
        total_processed = 0
        total_new = 0
        total_updated = 0
        platform_results = {}
        
        for platform, reviews_data in results.items():
            new_count = 0
            updated_count = 0
            
            for review_data in reviews_data:
                # Check if review already exists
                existing_review = Review.query.filter_by(
                    platform_review_id=review_data.platform_review_id,
                    platform=review_data.platform
                ).first()
                
                if existing_review:
                    # Update existing review
                    existing_review.rating = review_data.rating
                    existing_review.review_text = review_data.review_text
                    existing_review.sentiment = review_data.sentiment
                    existing_review.updated_at = datetime.utcnow()
                    updated_count += 1
                else:
                    # Create new review
                    new_review = Review(
                        user_id=current_user.id,
                        platform=review_data.platform,
                        platform_review_id=review_data.platform_review_id,
                        reviewer_name=review_data.reviewer_name,
                        reviewer_avatar=review_data.reviewer_avatar,
                        rating=review_data.rating,
                        review_text=review_data.review_text,
                        review_date=review_data.review_date,
                        location_id=review_data.location_id,
                        location_name=review_data.location_name,
                        sentiment=review_data.sentiment or determine_sentiment(review_data.review_text, review_data.rating),
                        language=review_data.language,
                        verified=review_data.verified,
                        helpful_count=review_data.helpful_count,
                        photos=json.dumps(review_data.photos) if review_data.photos else None
                    )
                    
                    # Add response if exists
                    if review_data.response_text:
                        response = ReviewResponse(
                            review=new_review,
                            response_text=review_data.response_text,
                            response_date=review_data.response_date or datetime.utcnow(),
                            response_source='platform'
                        )
                        db.session.add(response)
                    
                    db.session.add(new_review)
                    new_count += 1
            
            platform_results[platform] = {
                'processed': len(reviews_data),
                'new': new_count,
                'updated': updated_count
            }
            
            total_processed += len(reviews_data)
            total_new += new_count
            total_updated += updated_count
            
            # Create sync log for each platform
            integration = next((i for i in integrations if i.platform == platform), None)
            if integration:
                sync_log = IntegrationSyncLog(
                    integration_id=integration.id,
                    sync_type='reviews',
                    status='success',
                    records_processed=len(reviews_data),
                    records_created=new_count,
                    records_updated=updated_count,
                    sync_details=json.dumps({
                        'platform': platform,
                        'sync_type': 'bulk_sync'
                    })
                )
                db.session.add(sync_log)
        
        db.session.commit()
        
        return jsonify({
            'message': 'All platforms synced successfully',
            'total_processed': total_processed,
            'total_new': total_new,
            'total_updated': total_updated,
            'platform_results': platform_results
        })
        
    except Exception as e:
        logger.error(f"Error syncing all platforms: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to sync all platforms'}), 500

@platform_sync_bp.route('/location-info', methods=['POST'])
@cross_origin()
@token_required
def get_location_info(current_user):
    """Get location information from a platform"""
    try:
        data = request.get_json()
        platform = data.get('platform')
        location_id = data.get('location_id')
        
        if not platform or not location_id:
            return jsonify({'error': 'Platform and location_id are required'}), 400
        
        # Get location info from platform
        location_data = platform_manager.get_location_info(platform, location_id)
        
        if not location_data:
            return jsonify({'error': 'Location not found'}), 404
        
        return jsonify({
            'location': {
                'platform': location_data.platform,
                'platform_location_id': location_data.platform_location_id,
                'name': location_data.name,
                'address': location_data.address,
                'phone': location_data.phone,
                'website': location_data.website,
                'category': location_data.category,
                'rating': location_data.rating,
                'review_count': location_data.review_count,
                'photos': location_data.photos,
                'hours': location_data.hours
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting location info: {str(e)}")
        return jsonify({'error': 'Failed to get location info'}), 500

@platform_sync_bp.route('/post-response', methods=['POST'])
@cross_origin()
@token_required
def post_response_to_platform(current_user):
    """Post response to a review on a platform"""
    try:
        data = request.get_json()
        platform = data.get('platform')
        review_id = data.get('review_id')
        response_text = data.get('response_text')
        
        if not all([platform, review_id, response_text]):
            return jsonify({'error': 'Platform, review_id, and response_text are required'}), 400
        
        # Check if platform supports responses
        if platform not in ['google']:
            return jsonify({'error': f'{platform} does not support posting responses via API'}), 400
        
        # Check if user has integration configured
        integration = Integration.query.filter_by(
            user_id=current_user.id,
            platform=platform,
            is_active=True
        ).first()
        
        if not integration:
            return jsonify({'error': f'No active {platform} integration found'}), 400
        
        # Post response to platform
        success = platform_manager.post_response(platform, review_id, response_text)
        
        if success:
            # Update local review record if exists
            review = Review.query.filter_by(
                platform_review_id=review_id,
                platform=platform,
                user_id=current_user.id
            ).first()
            
            if review:
                # Check if response already exists
                existing_response = ReviewResponse.query.filter_by(review_id=review.id).first()
                
                if existing_response:
                    existing_response.response_text = response_text
                    existing_response.response_date = datetime.utcnow()
                    existing_response.updated_at = datetime.utcnow()
                else:
                    new_response = ReviewResponse(
                        review_id=review.id,
                        response_text=response_text,
                        response_date=datetime.utcnow(),
                        response_source='api'
                    )
                    db.session.add(new_response)
                
                review.has_response = True
                review.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            return jsonify({
                'message': 'Response posted successfully',
                'platform': platform,
                'review_id': review_id
            })
        else:
            return jsonify({'error': 'Failed to post response to platform'}), 500
        
    except Exception as e:
        logger.error(f"Error posting response: {str(e)}")
        return jsonify({'error': 'Failed to post response'}), 500

@platform_sync_bp.route('/sync-history', methods=['GET'])
@cross_origin()
@token_required
def get_sync_history(current_user):
    """Get synchronization history for user's integrations"""
    try:
        # Get user's integrations
        integrations = Integration.query.filter_by(user_id=current_user.id).all()
        integration_ids = [i.id for i in integrations]
        
        # Get sync logs
        sync_logs = IntegrationSyncLog.query.filter(
            IntegrationSyncLog.integration_id.in_(integration_ids)
        ).order_by(IntegrationSyncLog.created_at.desc()).limit(50).all()
        
        history = []
        for log in sync_logs:
            integration = next((i for i in integrations if i.id == log.integration_id), None)
            
            history.append({
                'id': log.id,
                'platform': integration.platform if integration else 'Unknown',
                'sync_type': log.sync_type,
                'status': log.status,
                'records_processed': log.records_processed,
                'records_created': log.records_created,
                'records_updated': log.records_updated,
                'error_message': log.error_message,
                'sync_date': log.created_at.isoformat(),
                'duration': log.duration_seconds,
                'details': json.loads(log.sync_details) if log.sync_details else {}
            })
        
        return jsonify({
            'sync_history': history,
            'total_count': len(history)
        })
        
    except Exception as e:
        logger.error(f"Error getting sync history: {str(e)}")
        return jsonify({'error': 'Failed to get sync history'}), 500

@platform_sync_bp.route('/sync-stats', methods=['GET'])
@cross_origin()
@token_required
def get_sync_stats(current_user):
    """Get synchronization statistics"""
    try:
        # Get user's integrations
        integrations = Integration.query.filter_by(user_id=current_user.id).all()
        integration_ids = [i.id for i in integrations]
        
        # Get sync statistics
        total_syncs = IntegrationSyncLog.query.filter(
            IntegrationSyncLog.integration_id.in_(integration_ids)
        ).count()
        
        successful_syncs = IntegrationSyncLog.query.filter(
            IntegrationSyncLog.integration_id.in_(integration_ids),
            IntegrationSyncLog.status == 'success'
        ).count()
        
        failed_syncs = IntegrationSyncLog.query.filter(
            IntegrationSyncLog.integration_id.in_(integration_ids),
            IntegrationSyncLog.status == 'error'
        ).count()
        
        # Get recent sync stats (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_syncs = IntegrationSyncLog.query.filter(
            IntegrationSyncLog.integration_id.in_(integration_ids),
            IntegrationSyncLog.created_at >= thirty_days_ago
        ).all()
        
        total_records_synced = sum(log.records_processed or 0 for log in recent_syncs)
        total_new_records = sum(log.records_created or 0 for log in recent_syncs)
        
        # Platform breakdown
        platform_stats = {}
        for integration in integrations:
            platform_logs = [log for log in recent_syncs if log.integration_id == integration.id]
            platform_stats[integration.platform] = {
                'total_syncs': len(platform_logs),
                'successful_syncs': len([log for log in platform_logs if log.status == 'success']),
                'records_synced': sum(log.records_processed or 0 for log in platform_logs),
                'new_records': sum(log.records_created or 0 for log in platform_logs)
            }
        
        return jsonify({
            'total_syncs': total_syncs,
            'successful_syncs': successful_syncs,
            'failed_syncs': failed_syncs,
            'success_rate': (successful_syncs / total_syncs * 100) if total_syncs > 0 else 0,
            'recent_stats': {
                'total_records_synced': total_records_synced,
                'total_new_records': total_new_records,
                'period_days': 30
            },
            'platform_stats': platform_stats
        })
        
    except Exception as e:
        logger.error(f"Error getting sync stats: {str(e)}")
        return jsonify({'error': 'Failed to get sync stats'}), 500

def get_platform_description(platform: str) -> str:
    """Get description for platform"""
    descriptions = {
        'google': 'Google My Business - Sync reviews and post responses directly to Google',
        'yelp': 'Yelp Fusion API - Collect reviews and business information from Yelp',
        'facebook': 'Facebook Graph API - Monitor Facebook page reviews and ratings',
        'tripadvisor': 'TripAdvisor API - Manage reviews for travel and hospitality businesses'
    }
    return descriptions.get(platform, f'{platform.title()} integration')

def determine_sentiment(review_text: str, rating: float) -> str:
    """Determine sentiment based on rating and text"""
    if rating >= 4:
        return 'positive'
    elif rating <= 2:
        return 'negative'
    else:
        return 'neutral'

