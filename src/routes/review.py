from flask import Blueprint, request, jsonify, send_file
from src.models.review import db, Review, Analytics, ResponseTemplate, Platform, Sentiment, ResponseStatus
from datetime import datetime, timedelta, date
import csv
import io
import os
import openai
from sqlalchemy import func, and_, or_

review_bp = Blueprint('review', __name__)

# Configure OpenAI (using environment variables)
openai.api_key = os.getenv('OPENAI_API_KEY')
openai.api_base = os.getenv('OPENAI_API_BASE', 'https://api.openai.com/v1')

@review_bp.route('/reviews', methods=['GET'])
def get_reviews():
    """Get reviews with filtering and pagination"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        platform = request.args.get('platform')
        rating = request.args.get('rating', type=int)
        sentiment = request.args.get('sentiment')
        search = request.args.get('search')
        status = request.args.get('status')
        
        query = Review.query
        
        # Apply filters
        if platform and platform != 'All Platforms':
            query = query.filter(Review.platform == Platform(platform))
        
        if rating:
            query = query.filter(Review.rating == rating)
            
        if sentiment and sentiment != 'All Sentiments':
            query = query.filter(Review.sentiment == Sentiment(sentiment))
            
        if status and status != 'All Statuses':
            query = query.filter(Review.response_status == ResponseStatus(status))
            
        if search:
            query = query.filter(or_(
                Review.content.contains(search),
                Review.reviewer_name.contains(search)
            ))
        
        # Order by review date descending
        query = query.order_by(Review.review_date.desc())
        
        # Paginate
        reviews = query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        return jsonify({
            'reviews': [review.to_dict() for review in reviews.items],
            'total': reviews.total,
            'pages': reviews.pages,
            'current_page': page,
            'per_page': per_page
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@review_bp.route('/reviews/<int:review_id>/response', methods=['POST'])
def generate_ai_response(review_id):
    """Generate AI response for a specific review"""
    try:
        review = Review.query.get_or_404(review_id)
        data = request.get_json()
        tone = data.get('tone', 'professional')
        
        # Create prompt based on review content and tone
        prompt = f"""
        Generate a professional response to this customer review:
        
        Platform: {review.platform.value}
        Rating: {review.rating}/5 stars
        Review: "{review.content}"
        Sentiment: {review.sentiment.value}
        
        Response tone should be: {tone}
        
        Guidelines:
        - Be genuine and personalized
        - Address specific points mentioned in the review
        - Thank the customer for their feedback
        - For positive reviews: express gratitude and invite them back
        - For negative reviews: apologize, show empathy, and offer to resolve issues
        - Keep response concise but meaningful (2-3 sentences)
        - Use a {tone} tone throughout
        """
        
        # In demo mode, return a sample response
        if os.getenv('DEMO_MODE', 'true').lower() == 'true':
            if review.sentiment == Sentiment.POSITIVE:
                response_content = f"Thank you so much for your wonderful {review.rating}-star review! We're delighted to hear about your positive experience. We look forward to welcoming you back to our establishment soon!"
            elif review.sentiment == Sentiment.NEGATIVE:
                response_content = f"We sincerely apologize for not meeting your expectations during your recent visit. Your feedback is invaluable to us, and we would love the opportunity to make things right. Please contact us directly so we can address your concerns personally."
            else:
                response_content = f"Thank you for taking the time to share your feedback with us. We appreciate your {review.rating}-star review and the constructive points you've raised. We're always working to improve our service and hope to exceed your expectations on your next visit."
        else:
            # Use actual OpenAI API
            try:
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are a professional customer service representative responding to online reviews."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=200,
                    temperature=0.7
                )
                response_content = response.choices[0].message.content.strip()
            except Exception as api_error:
                return jsonify({'error': f'AI service error: {str(api_error)}'}), 500
        
        return jsonify({
            'response': response_content,
            'tone': tone,
            'review_id': review_id
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@review_bp.route('/reviews/<int:review_id>/response', methods=['PUT'])
def save_response(review_id):
    """Save the AI-generated response"""
    try:
        review = Review.query.get_or_404(review_id)
        data = request.get_json()
        response_content = data.get('response')
        
        if not response_content:
            return jsonify({'error': 'Response content is required'}), 400
        
        # Calculate response time
        response_time = None
        if review.review_date:
            response_time = (datetime.utcnow() - review.review_date).total_seconds() / 3600
        
        # Update review
        review.response_content = response_content
        review.response_date = datetime.utcnow()
        review.response_status = ResponseStatus.RESPONDED
        review.response_time_hours = response_time
        
        db.session.commit()
        
        return jsonify({
            'message': 'Response saved successfully',
            'review': review.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@review_bp.route('/reviews/bulk-response', methods=['POST'])
def bulk_generate_responses():
    """Generate AI responses for multiple reviews"""
    try:
        data = request.get_json()
        review_ids = data.get('review_ids', [])
        tone = data.get('tone', 'professional')
        
        if not review_ids:
            return jsonify({'error': 'No review IDs provided'}), 400
        
        results = []
        for review_id in review_ids:
            try:
                review = Review.query.get(review_id)
                if not review:
                    results.append({'review_id': review_id, 'error': 'Review not found'})
                    continue
                
                # Generate response (simplified for bulk operation)
                if review.sentiment == Sentiment.POSITIVE:
                    response_content = f"Thank you for your {review.rating}-star review! We're thrilled you had a great experience."
                elif review.sentiment == Sentiment.NEGATIVE:
                    response_content = f"We apologize for not meeting your expectations. We'd love to make this right - please contact us directly."
                else:
                    response_content = f"Thank you for your feedback. We appreciate your {review.rating}-star review and will continue improving."
                
                results.append({
                    'review_id': review_id,
                    'response': response_content,
                    'success': True
                })
                
            except Exception as e:
                results.append({'review_id': review_id, 'error': str(e)})
        
        return jsonify({'results': results})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@review_bp.route('/analytics/dashboard', methods=['GET'])
def get_dashboard_analytics():
    """Get dashboard analytics data"""
    try:
        # Calculate current period stats
        total_reviews = Review.query.count()
        
        # Average rating
        avg_rating = db.session.query(func.avg(Review.rating)).scalar() or 0
        
        # Response rate
        responded_count = Review.query.filter(Review.response_status == ResponseStatus.RESPONDED).count()
        response_rate = (responded_count / total_reviews * 100) if total_reviews > 0 else 0
        
        # Average response time
        avg_response_time = db.session.query(func.avg(Review.response_time_hours)).filter(
            Review.response_time_hours.isnot(None)
        ).scalar() or 0
        
        # New reviews this week
        week_ago = datetime.utcnow() - timedelta(days=7)
        new_reviews_week = Review.query.filter(Review.review_date >= week_ago).count()
        
        # Sentiment distribution
        sentiment_stats = db.session.query(
            Review.sentiment,
            func.count(Review.id)
        ).group_by(Review.sentiment).all()
        
        sentiment_data = {
            'positive': 0,
            'neutral': 0,
            'negative': 0
        }
        
        for sentiment, count in sentiment_stats:
            if sentiment == Sentiment.POSITIVE:
                sentiment_data['positive'] = count
            elif sentiment == Sentiment.NEUTRAL:
                sentiment_data['neutral'] = count
            elif sentiment == Sentiment.NEGATIVE:
                sentiment_data['negative'] = count
        
        # Platform distribution
        platform_stats = db.session.query(
            Review.platform,
            func.avg(Review.rating)
        ).group_by(Review.platform).all()
        
        platform_data = {}
        for platform, avg_rating_platform in platform_stats:
            platform_data[platform.value] = round(avg_rating_platform, 1)
        
        return jsonify({
            'total_reviews': total_reviews,
            'average_rating': round(avg_rating, 1),
            'response_rate': round(response_rate, 1),
            'avg_response_time_hours': round(avg_response_time, 1),
            'new_reviews_week': new_reviews_week,
            'sentiment_distribution': sentiment_data,
            'platform_performance': platform_data
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@review_bp.route('/analytics/trends', methods=['GET'])
def get_trends_data():
    """Get trends data for charts"""
    try:
        # Get last 6 months of data
        months_ago = datetime.utcnow() - timedelta(days=180)
        
        # Monthly sentiment trends
        monthly_sentiment = db.session.query(
            func.date_trunc('month', Review.review_date).label('month'),
            Review.sentiment,
            func.count(Review.id).label('count')
        ).filter(
            Review.review_date >= months_ago
        ).group_by(
            func.date_trunc('month', Review.review_date),
            Review.sentiment
        ).all()
        
        # Process data for frontend
        trends_data = {}
        for month, sentiment, count in monthly_sentiment:
            month_str = month.strftime('%b')
            if month_str not in trends_data:
                trends_data[month_str] = {'positive': 0, 'neutral': 0, 'negative': 0}
            
            if sentiment == Sentiment.POSITIVE:
                trends_data[month_str]['positive'] = count
            elif sentiment == Sentiment.NEUTRAL:
                trends_data[month_str]['neutral'] = count
            elif sentiment == Sentiment.NEGATIVE:
                trends_data[month_str]['negative'] = count
        
        return jsonify({'trends': trends_data})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@review_bp.route('/export/csv', methods=['GET'])
def export_reviews_csv():
    """Export reviews to CSV"""
    try:
        # Get filters from query parameters
        platform = request.args.get('platform')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        query = Review.query
        
        if platform and platform != 'All Platforms':
            query = query.filter(Review.platform == Platform(platform))
        
        if start_date:
            query = query.filter(Review.review_date >= datetime.fromisoformat(start_date))
        
        if end_date:
            query = query.filter(Review.review_date <= datetime.fromisoformat(end_date))
        
        reviews = query.order_by(Review.review_date.desc()).all()
        
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'ID', 'Platform', 'Reviewer Name', 'Rating', 'Content', 
            'Sentiment', 'Response Status', 'Review Date', 'Response Date',
            'Response Content', 'Response Time (Hours)'
        ])
        
        # Write data
        for review in reviews:
            writer.writerow([
                review.id,
                review.platform.value if review.platform else '',
                review.reviewer_name,
                review.rating,
                review.content,
                review.sentiment.value if review.sentiment else '',
                review.response_status.value if review.response_status else '',
                review.review_date.isoformat() if review.review_date else '',
                review.response_date.isoformat() if review.response_date else '',
                review.response_content or '',
                review.response_time_hours or ''
            ])
        
        # Create file-like object
        output.seek(0)
        
        # Create a BytesIO object for the response
        csv_data = io.BytesIO()
        csv_data.write(output.getvalue().encode('utf-8'))
        csv_data.seek(0)
        
        return send_file(
            csv_data,
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'reviews_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@review_bp.route('/templates', methods=['GET'])
def get_response_templates():
    """Get all response templates"""
    try:
        templates = ResponseTemplate.query.filter(ResponseTemplate.is_active == True).all()
        return jsonify({
            'templates': [template.to_dict() for template in templates]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@review_bp.route('/seed-data', methods=['POST'])
def seed_sample_data():
    """Seed the database with sample data for demo purposes"""
    try:
        # Clear existing data
        Review.query.delete()
        ResponseTemplate.query.delete()
        
        # Sample reviews
        sample_reviews = [
            {
                'platform': Platform.GOOGLE,
                'reviewer_name': 'John D.',
                'rating': 5,
                'content': 'Excellent service! The staff was very helpful and professional. The food was outstanding and the atmosphere was perfect for our anniversary dinner.',
                'sentiment': Sentiment.POSITIVE,
                'response_status': ResponseStatus.RESPONDED,
                'review_date': datetime.utcnow() - timedelta(days=2),
                'response_date': datetime.utcnow() - timedelta(days=1, hours=22),
                'response_content': 'Thank you so much for your wonderful 5-star review! We\'re delighted to hear about your positive experience. We look forward to welcoming you back to Demo Restaurant soon!',
                'response_time_hours': 1.2
            },
            {
                'platform': Platform.YELP,
                'reviewer_name': 'Sarah M.',
                'rating': 3,
                'content': 'Good experience overall. Food was great, service could be faster. The wait time was a bit long but the quality made up for it.',
                'sentiment': Sentiment.NEUTRAL,
                'response_status': ResponseStatus.PENDING,
                'review_date': datetime.utcnow() - timedelta(days=1),
            },
            {
                'platform': Platform.FACEBOOK,
                'reviewer_name': 'Mike R.',
                'rating': 2,
                'content': 'Disappointing experience. The food was cold when it arrived and the service was inattentive. Expected much better based on the reviews.',
                'sentiment': Sentiment.NEGATIVE,
                'response_status': ResponseStatus.URGENT,
                'review_date': datetime.utcnow() - timedelta(days=3),
            }
        ]
        
        for review_data in sample_reviews:
            review = Review(**review_data)
            db.session.add(review)
        
        # Sample response templates
        templates = [
            {
                'name': 'Positive Review Template',
                'description': 'For 4-5 star reviews with positive sentiment',
                'template_content': 'Thank you so much for your {rating}-star review! We\'re thrilled to hear you had such a positive experience. Your feedback means the world to us, and we can\'t wait to welcome you back soon!',
                'sentiment_type': Sentiment.POSITIVE,
                'rating_range_min': 4,
                'rating_range_max': 5
            },
            {
                'name': 'Constructive Feedback Template',
                'description': 'For 2-3 star reviews with improvement suggestions',
                'template_content': 'Thank you for taking the time to share your feedback. We appreciate your {rating}-star review and the constructive points you\'ve raised. We\'re always working to improve our service and hope to exceed your expectations on your next visit.',
                'sentiment_type': Sentiment.NEUTRAL,
                'rating_range_min': 2,
                'rating_range_max': 3
            },
            {
                'name': 'Service Recovery Template',
                'description': 'For 1-2 star reviews requiring immediate attention',
                'template_content': 'We sincerely apologize for not meeting your expectations during your recent visit. Your feedback is invaluable to us, and we would love the opportunity to make things right. Please contact us directly at [contact info] so we can address your concerns personally.',
                'sentiment_type': Sentiment.NEGATIVE,
                'rating_range_min': 1,
                'rating_range_max': 2
            }
        ]
        
        for template_data in templates:
            template = ResponseTemplate(**template_data)
            db.session.add(template)
        
        db.session.commit()
        
        return jsonify({'message': 'Sample data seeded successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

