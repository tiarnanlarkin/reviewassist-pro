from flask import Blueprint, request, jsonify, current_app
from src.models.user import db
from src.models.integrations import (
    Integration, WebhookEndpoint, WebhookDelivery, APIKey, APIUsageLog,
    IntegrationSyncLog, IntegrationType, IntegrationStatus, WebhookEventType,
    APIKeyScope, IntegrationManager
)
from src.models.auth import AuthUser
from src.routes.auth import token_required
from datetime import datetime, timedelta
from sqlalchemy import func, desc
import json
import requests
import hashlib
import hmac
from functools import wraps

integrations_bp = Blueprint('integrations', __name__)

# API Key authentication decorator
def api_key_required(scopes=None):
    """Decorator to require API key authentication"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
            
            if not api_key:
                return jsonify({
                    'success': False,
                    'message': 'API key required'
                }), 401
            
            # Find and verify API key
            key_hash = hashlib.sha256(api_key.encode()).hexdigest()
            api_key_obj = APIKey.query.filter_by(key_hash=key_hash, is_active=True).first()
            
            if not api_key_obj or api_key_obj.is_expired():
                return jsonify({
                    'success': False,
                    'message': 'Invalid or expired API key'
                }), 401
            
            # Check scopes if required
            if scopes:
                user_scopes = api_key_obj.get_scopes()
                if not any(scope in user_scopes for scope in scopes):
                    return jsonify({
                        'success': False,
                        'message': 'Insufficient API key permissions'
                    }), 403
            
            # Update usage
            api_key_obj.total_requests += 1
            api_key_obj.last_used_at = datetime.utcnow()
            
            # Log API usage
            usage_log = APIUsageLog(
                api_key_id=api_key_obj.id,
                endpoint=request.endpoint,
                method=request.method,
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent', '')[:500]
            )
            db.session.add(usage_log)
            db.session.commit()
            
            # Add API key and user to request context
            request.api_key = api_key_obj
            request.current_user = api_key_obj.user
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Integration Management Routes

@integrations_bp.route('/integrations', methods=['GET'])
@token_required
def get_integrations(current_user):
    """Get all integrations for the current user"""
    try:
        integration_type = request.args.get('type')
        integrations = IntegrationManager.get_user_integrations(
            current_user.id, 
            IntegrationType(integration_type) if integration_type else None
        )
        
        return jsonify({
            'success': True,
            'data': [integration.to_dict() for integration in integrations]
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error fetching integrations: {str(e)}'
        }), 500

@integrations_bp.route('/integrations', methods=['POST'])
@token_required
def create_integration(current_user):
    """Create a new integration"""
    try:
        data = request.get_json()
        name = data.get('name')
        integration_type = data.get('integration_type')
        config_data = data.get('config_data', {})
        
        if not name or not integration_type:
            return jsonify({
                'success': False,
                'message': 'Name and integration type are required'
            }), 400
        
        try:
            integration_type_enum = IntegrationType(integration_type)
        except ValueError:
            return jsonify({
                'success': False,
                'message': 'Invalid integration type'
            }), 400
        
        integration = IntegrationManager.create_integration(
            current_user.id, name, integration_type_enum, config_data
        )
        
        return jsonify({
            'success': True,
            'data': integration.to_dict(),
            'message': 'Integration created successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error creating integration: {str(e)}'
        }), 500

@integrations_bp.route('/integrations/<int:integration_id>', methods=['PUT'])
@token_required
def update_integration(current_user, integration_id):
    """Update an integration"""
    try:
        integration = Integration.query.filter_by(
            id=integration_id, 
            user_id=current_user.id
        ).first()
        
        if not integration:
            return jsonify({
                'success': False,
                'message': 'Integration not found'
            }), 404
        
        data = request.get_json()
        
        if 'name' in data:
            integration.name = data['name']
        if 'config_data' in data:
            integration.set_config(data['config_data'])
        if 'status' in data:
            try:
                integration.status = IntegrationStatus(data['status'])
            except ValueError:
                return jsonify({
                    'success': False,
                    'message': 'Invalid status'
                }), 400
        
        integration.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': integration.to_dict(),
            'message': 'Integration updated successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error updating integration: {str(e)}'
        }), 500

@integrations_bp.route('/integrations/<int:integration_id>', methods=['DELETE'])
@token_required
def delete_integration(current_user, integration_id):
    """Delete an integration"""
    try:
        integration = Integration.query.filter_by(
            id=integration_id, 
            user_id=current_user.id
        ).first()
        
        if not integration:
            return jsonify({
                'success': False,
                'message': 'Integration not found'
            }), 404
        
        db.session.delete(integration)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Integration deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error deleting integration: {str(e)}'
        }), 500

@integrations_bp.route('/integrations/<int:integration_id>/test', methods=['POST'])
@token_required
def test_integration(current_user, integration_id):
    """Test an integration connection"""
    try:
        integration = Integration.query.filter_by(
            id=integration_id, 
            user_id=current_user.id
        ).first()
        
        if not integration:
            return jsonify({
                'success': False,
                'message': 'Integration not found'
            }), 404
        
        result = IntegrationManager.test_integration(integration_id)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error testing integration: {str(e)}'
        }), 500

@integrations_bp.route('/integrations/<int:integration_id>/sync', methods=['POST'])
@token_required
def sync_integration(current_user, integration_id):
    """Trigger integration sync"""
    try:
        integration = Integration.query.filter_by(
            id=integration_id, 
            user_id=current_user.id
        ).first()
        
        if not integration:
            return jsonify({
                'success': False,
                'message': 'Integration not found'
            }), 404
        
        result = IntegrationManager.sync_integration(integration_id, 'manual')
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error syncing integration: {str(e)}'
        }), 500

# Webhook Management Routes

@integrations_bp.route('/webhooks', methods=['GET'])
@token_required
def get_webhooks(current_user):
    """Get all webhook endpoints for the current user"""
    try:
        webhooks = WebhookEndpoint.query.filter_by(user_id=current_user.id).all()
        
        return jsonify({
            'success': True,
            'data': [webhook.to_dict() for webhook in webhooks]
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error fetching webhooks: {str(e)}'
        }), 500

@integrations_bp.route('/webhooks', methods=['POST'])
@token_required
def create_webhook(current_user):
    """Create a new webhook endpoint"""
    try:
        data = request.get_json()
        name = data.get('name')
        url = data.get('url')
        events = data.get('events', [])
        
        if not name or not url:
            return jsonify({
                'success': False,
                'message': 'Name and URL are required'
            }), 400
        
        # Validate events
        valid_events = [event.value for event in WebhookEventType]
        invalid_events = [event for event in events if event not in valid_events]
        if invalid_events:
            return jsonify({
                'success': False,
                'message': f'Invalid events: {invalid_events}'
            }), 400
        
        webhook = WebhookEndpoint(
            user_id=current_user.id,
            name=name,
            url=url,
            max_retries=data.get('max_retries', 3),
            retry_delay=data.get('retry_delay', 60)
        )
        webhook.set_events(events)
        
        db.session.add(webhook)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': webhook.to_dict(),
            'message': 'Webhook created successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error creating webhook: {str(e)}'
        }), 500

@integrations_bp.route('/webhooks/<int:webhook_id>', methods=['PUT'])
@token_required
def update_webhook(current_user, webhook_id):
    """Update a webhook endpoint"""
    try:
        webhook = WebhookEndpoint.query.filter_by(
            id=webhook_id, 
            user_id=current_user.id
        ).first()
        
        if not webhook:
            return jsonify({
                'success': False,
                'message': 'Webhook not found'
            }), 404
        
        data = request.get_json()
        
        if 'name' in data:
            webhook.name = data['name']
        if 'url' in data:
            webhook.url = data['url']
        if 'events' in data:
            webhook.set_events(data['events'])
        if 'is_active' in data:
            webhook.is_active = data['is_active']
        if 'max_retries' in data:
            webhook.max_retries = data['max_retries']
        if 'retry_delay' in data:
            webhook.retry_delay = data['retry_delay']
        
        webhook.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': webhook.to_dict(),
            'message': 'Webhook updated successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error updating webhook: {str(e)}'
        }), 500

@integrations_bp.route('/webhooks/<int:webhook_id>/test', methods=['POST'])
@token_required
def test_webhook(current_user, webhook_id):
    """Test a webhook endpoint"""
    try:
        webhook = WebhookEndpoint.query.filter_by(
            id=webhook_id, 
            user_id=current_user.id
        ).first()
        
        if not webhook:
            return jsonify({
                'success': False,
                'message': 'Webhook not found'
            }), 404
        
        # Send test payload
        test_payload = {
            'event_type': 'webhook.test',
            'timestamp': datetime.utcnow().isoformat(),
            'data': {
                'message': 'This is a test webhook delivery',
                'webhook_id': webhook_id
            }
        }
        
        payload_json = json.dumps(test_payload)
        signature = webhook.generate_signature(payload_json)
        
        headers = {
            'Content-Type': 'application/json',
            'X-Webhook-Signature': signature,
            'User-Agent': 'ReviewAssist-Webhook/1.0'
        }
        
        try:
            response = requests.post(
                webhook.url, 
                data=payload_json, 
                headers=headers, 
                timeout=10
            )
            
            return jsonify({
                'success': True,
                'message': 'Test webhook sent successfully',
                'response': {
                    'status_code': response.status_code,
                    'response_time_ms': int(response.elapsed.total_seconds() * 1000),
                    'headers': dict(response.headers)
                }
            })
            
        except requests.exceptions.RequestException as e:
            return jsonify({
                'success': False,
                'message': f'Webhook test failed: {str(e)}'
            }), 400
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error testing webhook: {str(e)}'
        }), 500

# API Key Management Routes

@integrations_bp.route('/api-keys', methods=['GET'])
@token_required
def get_api_keys(current_user):
    """Get all API keys for the current user"""
    try:
        api_keys = APIKey.query.filter_by(user_id=current_user.id).all()
        
        return jsonify({
            'success': True,
            'data': [api_key.to_dict() for api_key in api_keys]
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error fetching API keys: {str(e)}'
        }), 500

@integrations_bp.route('/api-keys', methods=['POST'])
@token_required
def create_api_key(current_user):
    """Create a new API key"""
    try:
        data = request.get_json()
        name = data.get('name')
        scopes = data.get('scopes', [])
        
        if not name:
            return jsonify({
                'success': False,
                'message': 'Name is required'
            }), 400
        
        # Validate scopes
        valid_scopes = [scope.value for scope in APIKeyScope]
        invalid_scopes = [scope for scope in scopes if scope not in valid_scopes]
        if invalid_scopes:
            return jsonify({
                'success': False,
                'message': f'Invalid scopes: {invalid_scopes}'
            }), 400
        
        api_key = APIKey(
            user_id=current_user.id,
            name=name,
            rate_limit_per_hour=data.get('rate_limit_per_hour', 1000),
            rate_limit_per_day=data.get('rate_limit_per_day', 10000),
            expires_at=datetime.fromisoformat(data['expires_at']) if data.get('expires_at') else None
        )
        api_key.set_scopes(scopes)
        
        db.session.add(api_key)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': api_key.to_dict(include_key=True),
            'message': 'API key created successfully. Save the key securely - it will not be shown again.'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error creating API key: {str(e)}'
        }), 500

@integrations_bp.route('/api-keys/<int:key_id>', methods=['PUT'])
@token_required
def update_api_key(current_user, key_id):
    """Update an API key"""
    try:
        api_key = APIKey.query.filter_by(
            id=key_id, 
            user_id=current_user.id
        ).first()
        
        if not api_key:
            return jsonify({
                'success': False,
                'message': 'API key not found'
            }), 404
        
        data = request.get_json()
        
        if 'name' in data:
            api_key.name = data['name']
        if 'scopes' in data:
            api_key.set_scopes(data['scopes'])
        if 'is_active' in data:
            api_key.is_active = data['is_active']
        if 'rate_limit_per_hour' in data:
            api_key.rate_limit_per_hour = data['rate_limit_per_hour']
        if 'rate_limit_per_day' in data:
            api_key.rate_limit_per_day = data['rate_limit_per_day']
        
        api_key.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': api_key.to_dict(),
            'message': 'API key updated successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error updating API key: {str(e)}'
        }), 500

@integrations_bp.route('/api-keys/<int:key_id>', methods=['DELETE'])
@token_required
def delete_api_key(current_user, key_id):
    """Delete an API key"""
    try:
        api_key = APIKey.query.filter_by(
            id=key_id, 
            user_id=current_user.id
        ).first()
        
        if not api_key:
            return jsonify({
                'success': False,
                'message': 'API key not found'
            }), 404
        
        db.session.delete(api_key)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'API key deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error deleting API key: {str(e)}'
        }), 500

# Public API Routes (using API key authentication)

@integrations_bp.route('/api/v1/reviews', methods=['GET'])
@api_key_required(['read:reviews'])
def api_get_reviews():
    """Public API: Get reviews"""
    try:
        from src.models.review import Review
        
        # Get query parameters
        limit = min(int(request.args.get('limit', 50)), 100)
        offset = int(request.args.get('offset', 0))
        platform = request.args.get('platform')
        rating = request.args.get('rating')
        
        # Build query
        query = Review.query
        
        if platform:
            query = query.filter(Review.platform == platform)
        if rating:
            query = query.filter(Review.rating == int(rating))
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        reviews = query.offset(offset).limit(limit).all()
        
        return jsonify({
            'success': True,
            'data': [review.to_dict() for review in reviews],
            'pagination': {
                'total': total,
                'limit': limit,
                'offset': offset,
                'has_more': offset + limit < total
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error fetching reviews: {str(e)}'
        }), 500

@integrations_bp.route('/api/v1/analytics/summary', methods=['GET'])
@api_key_required(['read:analytics'])
def api_get_analytics_summary():
    """Public API: Get analytics summary"""
    try:
        from src.models.review import Review
        from sqlalchemy import func
        
        # Calculate basic metrics
        total_reviews = Review.query.count()
        avg_rating = db.session.query(func.avg(Review.rating)).scalar() or 0
        
        # Platform breakdown
        platform_stats = db.session.query(
            Review.platform,
            func.count(Review.id).label('count'),
            func.avg(Review.rating).label('avg_rating')
        ).group_by(Review.platform).all()
        
        return jsonify({
            'success': True,
            'data': {
                'total_reviews': total_reviews,
                'average_rating': round(float(avg_rating), 2),
                'platform_breakdown': [
                    {
                        'platform': stat.platform,
                        'count': stat.count,
                        'average_rating': round(float(stat.avg_rating), 2)
                    }
                    for stat in platform_stats
                ]
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error fetching analytics: {str(e)}'
        }), 500

# Integration Templates and Documentation

@integrations_bp.route('/integration-types', methods=['GET'])
@token_required
def get_integration_types(current_user):
    """Get available integration types with configuration templates"""
    try:
        integration_templates = {
            'google_my_business': {
                'name': 'Google My Business',
                'description': 'Sync reviews from Google My Business listings',
                'config_fields': [
                    {'name': 'business_id', 'type': 'string', 'required': True, 'description': 'Google My Business location ID'},
                    {'name': 'api_key', 'type': 'password', 'required': True, 'description': 'Google API key'},
                    {'name': 'sync_frequency', 'type': 'number', 'required': False, 'description': 'Sync frequency in hours', 'default': 1}
                ],
                'features': ['Review sync', 'Response posting', 'Analytics'],
                'documentation_url': '/docs/integrations/google-my-business'
            },
            'yelp': {
                'name': 'Yelp',
                'description': 'Monitor and respond to Yelp reviews',
                'config_fields': [
                    {'name': 'business_id', 'type': 'string', 'required': True, 'description': 'Yelp business ID'},
                    {'name': 'api_key', 'type': 'password', 'required': True, 'description': 'Yelp Fusion API key'},
                    {'name': 'auto_respond', 'type': 'boolean', 'required': False, 'description': 'Enable automatic responses', 'default': False}
                ],
                'features': ['Review monitoring', 'Business info sync'],
                'documentation_url': '/docs/integrations/yelp'
            },
            'slack': {
                'name': 'Slack',
                'description': 'Send review notifications to Slack channels',
                'config_fields': [
                    {'name': 'webhook_url', 'type': 'url', 'required': True, 'description': 'Slack webhook URL'},
                    {'name': 'channel', 'type': 'string', 'required': False, 'description': 'Default channel name', 'default': '#reviews'},
                    {'name': 'notify_on_rating', 'type': 'number', 'required': False, 'description': 'Notify for ratings below this threshold', 'default': 3}
                ],
                'features': ['Real-time notifications', 'Custom channels', 'Rich formatting'],
                'documentation_url': '/docs/integrations/slack'
            },
            'webhook': {
                'name': 'Custom Webhook',
                'description': 'Send events to custom webhook endpoints',
                'config_fields': [
                    {'name': 'url', 'type': 'url', 'required': True, 'description': 'Webhook endpoint URL'},
                    {'name': 'secret', 'type': 'password', 'required': False, 'description': 'Webhook secret for signature verification'},
                    {'name': 'events', 'type': 'multiselect', 'required': True, 'description': 'Events to send', 'options': [event.value for event in WebhookEventType]}
                ],
                'features': ['Custom events', 'Signature verification', 'Retry logic'],
                'documentation_url': '/docs/integrations/webhooks'
            }
        }
        
        return jsonify({
            'success': True,
            'data': integration_templates
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error fetching integration types: {str(e)}'
        }), 500

