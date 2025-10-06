"""
AI Features Routes for ReviewAssist Pro
Provides endpoints for advanced AI capabilities
"""

from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
import json
import logging
from datetime import datetime, timedelta
from src.models.user import db
from src.models.auth import AuthUser
from src.models.review import Review, Analytics, ResponseTemplate
from src.routes.auth import token_required
from src.services.ai_engine import (
    ai_engine, ResponseTone, BusinessType, EmotionType, 
    ReviewAspect, SentimentAnalysis, ReviewCategory, SmartResponse
)
from sqlalchemy import func, desc

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ai_features_bp = Blueprint('ai_features', __name__)

@ai_features_bp.route('/api/ai/analyze-sentiment', methods=['POST'])
@cross_origin()
@token_required
def analyze_sentiment(current_user):
    """Analyze sentiment of review text with advanced AI"""
    try:
        data = request.get_json()
        review_text = data.get('review_text', '')
        business_type = data.get('business_type', 'general')
        
        if not review_text:
            return jsonify({'error': 'Review text is required'}), 400
        
        # Perform sentiment analysis
        sentiment = ai_engine.analyze_sentiment(review_text, business_type)
        
        return jsonify({
            'sentiment_analysis': {
                'overall_sentiment': sentiment.overall_sentiment,
                'confidence': sentiment.confidence,
                'emotion': sentiment.emotion.value,
                'aspects': {aspect.value: score for aspect, score in sentiment.aspects.items()},
                'keywords': sentiment.keywords,
                'urgency_score': sentiment.urgency_score
            }
        })
        
    except Exception as e:
        logger.error(f"Error in sentiment analysis: {e}")
        return jsonify({'error': 'Failed to analyze sentiment'}), 500

@ai_features_bp.route('/api/ai/categorize-review', methods=['POST'])
@cross_origin()
@token_required
def categorize_review(current_user):
    """Categorize review with intelligent AI classification"""
    try:
        data = request.get_json()
        review_text = data.get('review_text', '')
        business_type = data.get('business_type', 'general')
        
        if not review_text:
            return jsonify({'error': 'Review text is required'}), 400
        
        # Perform review categorization
        category = ai_engine.categorize_review(review_text, business_type)
        
        return jsonify({
            'categorization': {
                'primary_category': category.primary_category,
                'secondary_categories': category.secondary_categories,
                'priority_score': category.priority_score,
                'department': category.department,
                'tags': category.tags
            }
        })
        
    except Exception as e:
        logger.error(f"Error in review categorization: {e}")
        return jsonify({'error': 'Failed to categorize review'}), 500

@ai_features_bp.route('/api/ai/generate-response', methods=['POST'])
@cross_origin()
@token_required
def generate_smart_response(current_user):
    """Generate intelligent, context-aware response to review"""
    try:
        data = request.get_json()
        review_text = data.get('review_text', '')
        business_name = data.get('business_name', 'Our Business')
        business_type = data.get('business_type', 'general')
        tone = data.get('tone', 'professional')
        customer_name = data.get('customer_name')
        
        if not review_text:
            return jsonify({'error': 'Review text is required'}), 400
        
        # First analyze sentiment
        sentiment = ai_engine.analyze_sentiment(review_text, business_type)
        
        # Generate smart response
        response_tone = ResponseTone(tone) if tone in [t.value for t in ResponseTone] else ResponseTone.PROFESSIONAL
        
        smart_response = ai_engine.generate_smart_response(
            review_text=review_text,
            sentiment=sentiment,
            business_name=business_name,
            business_type=business_type,
            tone=response_tone,
            customer_name=customer_name
        )
        
        return jsonify({
            'smart_response': {
                'response_text': smart_response.response_text,
                'tone': smart_response.tone.value,
                'confidence': smart_response.confidence,
                'personalization_elements': smart_response.personalization_elements,
                'suggested_actions': smart_response.suggested_actions,
                'quality_score': smart_response.quality_score
            },
            'sentiment_analysis': {
                'overall_sentiment': sentiment.overall_sentiment,
                'emotion': sentiment.emotion.value,
                'urgency_score': sentiment.urgency_score
            }
        })
        
    except Exception as e:
        logger.error(f"Error generating smart response: {e}")
        return jsonify({'error': 'Failed to generate response'}), 500

@ai_features_bp.route('/api/ai/bulk-analyze', methods=['POST'])
@cross_origin()
@token_required
def bulk_analyze_reviews(current_user):
    """Bulk analyze multiple reviews with AI"""
    try:
        data = request.get_json()
        reviews = data.get('reviews', [])
        business_type = data.get('business_type', 'general')
        
        if not reviews:
            return jsonify({'error': 'Reviews list is required'}), 400
        
        results = []
        
        for review_data in reviews[:50]:  # Limit to 50 reviews per request
            review_text = review_data.get('text', '')
            review_id = review_data.get('id')
            
            if not review_text:
                continue
            
            # Analyze sentiment and categorize
            sentiment = ai_engine.analyze_sentiment(review_text, business_type)
            category = ai_engine.categorize_review(review_text, business_type)
            
            results.append({
                'review_id': review_id,
                'sentiment_analysis': {
                    'overall_sentiment': sentiment.overall_sentiment,
                    'confidence': sentiment.confidence,
                    'emotion': sentiment.emotion.value,
                    'urgency_score': sentiment.urgency_score,
                    'keywords': sentiment.keywords
                },
                'categorization': {
                    'primary_category': category.primary_category,
                    'priority_score': category.priority_score,
                    'department': category.department,
                    'tags': category.tags
                }
            })
        
        return jsonify({
            'bulk_analysis': results,
            'summary': {
                'total_analyzed': len(results),
                'average_sentiment': sum(r['sentiment_analysis']['overall_sentiment'] for r in results) / len(results) if results else 0,
                'high_priority_count': sum(1 for r in results if r['categorization']['priority_score'] > 0.7),
                'urgent_reviews': sum(1 for r in results if r['sentiment_analysis']['urgency_score'] > 0.7)
            }
        })
        
    except Exception as e:
        logger.error(f"Error in bulk analysis: {e}")
        return jsonify({'error': 'Failed to perform bulk analysis'}), 500

@ai_features_bp.route('/api/ai/competitor-analysis', methods=['POST'])
@cross_origin()
@token_required
def analyze_competitors(current_user):
    """Analyze competitor performance and identify opportunities"""
    try:
        data = request.get_json()
        our_reviews = data.get('our_reviews', [])
        competitor_data = data.get('competitors', [])
        
        if not our_reviews or not competitor_data:
            return jsonify({'error': 'Review data and competitor data required'}), 400
        
        # Perform competitor analysis
        insights = ai_engine.analyze_competitors(our_reviews, competitor_data)
        
        competitor_insights = []
        for insight in insights:
            competitor_insights.append({
                'competitor_name': insight.competitor_name,
                'sentiment_comparison': insight.sentiment_comparison,
                'volume_comparison': insight.volume_comparison,
                'strengths': insight.strengths,
                'weaknesses': insight.weaknesses,
                'opportunities': insight.opportunities
            })
        
        return jsonify({
            'competitor_analysis': competitor_insights,
            'summary': {
                'total_competitors': len(competitor_insights),
                'sentiment_advantage': sum(1 for i in insights if i.sentiment_comparison > 0),
                'volume_advantage': sum(1 for i in insights if i.volume_comparison > 1),
                'key_opportunities': [opp for insight in insights for opp in insight.opportunities[:2]]
            }
        })
        
    except Exception as e:
        logger.error(f"Error in competitor analysis: {e}")
        return jsonify({'error': 'Failed to analyze competitors'}), 500

@ai_features_bp.route('/api/ai/predictive-insights', methods=['POST'])
@cross_origin()
@token_required
def generate_predictive_insights(current_user):
    """Generate predictive insights and forecasts"""
    try:
        data = request.get_json()
        historical_data = data.get('historical_data', [])
        
        if len(historical_data) < 10:
            return jsonify({'error': 'Insufficient historical data for predictions (minimum 10 data points)'}), 400
        
        # Generate predictive insights
        insights = ai_engine.generate_predictive_insights(historical_data)
        
        predictive_insights = []
        for insight in insights:
            predictive_insights.append({
                'prediction_type': insight.prediction_type,
                'forecast_value': insight.forecast_value,
                'confidence': insight.confidence,
                'time_horizon': insight.time_horizon,
                'contributing_factors': insight.contributing_factors,
                'recommended_actions': insight.recommended_actions
            })
        
        return jsonify({
            'predictive_insights': predictive_insights,
            'summary': {
                'total_insights': len(predictive_insights),
                'high_confidence_predictions': sum(1 for i in insights if i.confidence > 0.7),
                'immediate_actions': sum(len(i.recommended_actions) for i in insights),
                'forecast_horizon': '30-90 days'
            }
        })
        
    except Exception as e:
        logger.error(f"Error generating predictive insights: {e}")
        return jsonify({'error': 'Failed to generate predictive insights'}), 500

@ai_features_bp.route('/api/ai/pattern-detection', methods=['POST'])
@cross_origin()
@token_required
def detect_patterns(current_user):
    """Detect patterns and anomalies in review data"""
    try:
        data = request.get_json()
        reviews = data.get('reviews', [])
        
        if not reviews:
            return jsonify({'error': 'Reviews data is required'}), 400
        
        # Detect patterns
        patterns = ai_engine.detect_review_patterns(reviews)
        
        return jsonify({
            'pattern_analysis': patterns,
            'insights': {
                'total_reviews_analyzed': len(reviews),
                'pattern_confidence': 0.8,  # Simplified
                'anomalies_detected': len(patterns.get('anomalies', [])),
                'trending_keywords': patterns.get('keyword_patterns', {}).get('top_keywords', [])[:5]
            }
        })
        
    except Exception as e:
        logger.error(f"Error in pattern detection: {e}")
        return jsonify({'error': 'Failed to detect patterns'}), 500

@ai_features_bp.route('/api/ai/business-insights', methods=['POST'])
@cross_origin()
@token_required
def generate_business_insights(current_user):
    """Generate comprehensive business insights from review data"""
    try:
        data = request.get_json()
        reviews = data.get('reviews', [])
        business_data = data.get('business_data', {})
        
        if not reviews:
            return jsonify({'error': 'Reviews data is required'}), 400
        
        # Generate business insights
        insights = ai_engine.generate_business_insights(reviews, business_data)
        
        return jsonify({
            'business_insights': insights,
            'analysis_metadata': {
                'reviews_analyzed': len(reviews),
                'analysis_date': datetime.utcnow().isoformat(),
                'confidence_level': 'high' if len(reviews) > 50 else 'medium',
                'data_quality': 'good'
            }
        })
        
    except Exception as e:
        logger.error(f"Error generating business insights: {e}")
        return jsonify({'error': 'Failed to generate business insights'}), 500

@ai_features_bp.route('/api/ai/response-templates', methods=['GET'])
@cross_origin()
@token_required
def get_response_templates(current_user):
    """Get available response templates and tones"""
    try:
        templates = {
            'business_types': [bt.value for bt in BusinessType],
            'response_tones': [rt.value for rt in ResponseTone],
            'emotion_types': [et.value for et in EmotionType],
            'review_aspects': [ra.value for ra in ReviewAspect],
            'templates': ai_engine.response_templates
        }
        
        return jsonify(templates)
        
    except Exception as e:
        logger.error(f"Error getting response templates: {e}")
        return jsonify({'error': 'Failed to get response templates'}), 500

@ai_features_bp.route('/api/ai/smart-suggestions', methods=['POST'])
@cross_origin()
@token_required
def get_smart_suggestions(current_user):
    """Get AI-powered suggestions for review management"""
    try:
        data = request.get_json()
        context = data.get('context', 'general')
        review_data = data.get('review_data', {})
        
        suggestions = []
        
        # Generate context-specific suggestions
        if context == 'response_improvement':
            suggestions = [
                {
                    'type': 'response_tone',
                    'suggestion': 'Consider using a more empathetic tone for negative reviews',
                    'confidence': 0.8,
                    'impact': 'high'
                },
                {
                    'type': 'personalization',
                    'suggestion': 'Include customer name and specific details mentioned in review',
                    'confidence': 0.9,
                    'impact': 'medium'
                }
            ]
        elif context == 'sentiment_improvement':
            suggestions = [
                {
                    'type': 'service_quality',
                    'suggestion': 'Focus on staff training to improve service quality scores',
                    'confidence': 0.7,
                    'impact': 'high'
                },
                {
                    'type': 'response_time',
                    'suggestion': 'Respond to reviews within 24 hours to show engagement',
                    'confidence': 0.9,
                    'impact': 'medium'
                }
            ]
        else:
            suggestions = [
                {
                    'type': 'general',
                    'suggestion': 'Implement regular review monitoring and response workflows',
                    'confidence': 0.8,
                    'impact': 'high'
                }
            ]
        
        return jsonify({
            'smart_suggestions': suggestions,
            'context': context,
            'total_suggestions': len(suggestions)
        })
        
    except Exception as e:
        logger.error(f"Error getting smart suggestions: {e}")
        return jsonify({'error': 'Failed to get smart suggestions'}), 500

@ai_features_bp.route('/api/ai/dashboard-insights', methods=['GET'])
@cross_origin()
@token_required
def get_dashboard_insights(current_user):
    """Get AI-powered insights for dashboard display"""
    try:
        # Get recent reviews for analysis
        recent_reviews = Review.query.filter_by(user_id=current_user.id)\
            .order_by(desc(Review.created_at))\
            .limit(100)\
            .all()
        
        if not recent_reviews:
            return jsonify({
                'dashboard_insights': {
                    'summary': 'No reviews available for analysis',
                    'insights': [],
                    'recommendations': []
                }
            })
        
        # Convert to format for AI analysis
        review_data = []
        for review in recent_reviews:
            review_data.append({
                'text': review.content,
                'sentiment': review.sentiment_score or 0,
                'rating': review.rating,
                'platform': review.platform.value if review.platform else 'unknown',
                'date': review.created_at.isoformat()
            })
        
        # Generate insights
        patterns = ai_engine.detect_review_patterns(review_data)
        
        # Create dashboard-friendly insights
        insights = {
            'summary': f"Analyzed {len(recent_reviews)} recent reviews",
            'key_metrics': {
                'average_sentiment': patterns.get('sentiment_patterns', {}).get('average', 0),
                'sentiment_trend': patterns.get('sentiment_patterns', {}).get('trend', 'stable'),
                'top_keywords': [kw[0] for kw in patterns.get('keyword_patterns', {}).get('top_keywords', [])[:5]],
                'anomalies_count': len(patterns.get('anomalies', []))
            },
            'insights': [
                f"Sentiment trend is {patterns.get('sentiment_patterns', {}).get('trend', 'stable')}",
                f"Found {len(patterns.get('anomalies', []))} anomalies requiring attention",
                f"Top concern areas: {', '.join([kw[0] for kw in patterns.get('keyword_patterns', {}).get('top_keywords', [])[:3]])}",
            ],
            'recommendations': [
                "Monitor recent sentiment changes closely",
                "Focus on addressing top keyword concerns",
                "Implement proactive response strategies"
            ]
        }
        
        return jsonify({'dashboard_insights': insights})
        
    except Exception as e:
        logger.error(f"Error getting dashboard insights: {e}")
        return jsonify({'error': 'Failed to get dashboard insights'}), 500

