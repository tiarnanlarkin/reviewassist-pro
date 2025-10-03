from src.models.user import db
from datetime import datetime
import enum

class Platform(enum.Enum):
    GOOGLE = "Google"
    YELP = "Yelp"
    FACEBOOK = "Facebook"
    TRIPADVISOR = "TripAdvisor"

class Sentiment(enum.Enum):
    POSITIVE = "Positive"
    NEUTRAL = "Neutral"
    NEGATIVE = "Negative"

class ResponseStatus(enum.Enum):
    PENDING = "Pending"
    RESPONDED = "Responded"
    URGENT = "Urgent"

class Review(db.Model):
    __tablename__ = 'reviews'
    
    id = db.Column(db.Integer, primary_key=True)
    platform = db.Column(db.Enum(Platform), nullable=False)
    reviewer_name = db.Column(db.String(100), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1-5 stars
    content = db.Column(db.Text, nullable=False)
    sentiment = db.Column(db.Enum(Sentiment), nullable=False)
    response_status = db.Column(db.Enum(ResponseStatus), default=ResponseStatus.PENDING)
    review_date = db.Column(db.DateTime, nullable=False)
    response_date = db.Column(db.DateTime, nullable=True)
    response_content = db.Column(db.Text, nullable=True)
    response_time_hours = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'platform': self.platform.value if self.platform else None,
            'reviewer_name': self.reviewer_name,
            'rating': self.rating,
            'content': self.content,
            'sentiment': self.sentiment.value if self.sentiment else None,
            'response_status': self.response_status.value if self.response_status else None,
            'review_date': self.review_date.isoformat() if self.review_date else None,
            'response_date': self.response_date.isoformat() if self.response_date else None,
            'response_content': self.response_content,
            'response_time_hours': self.response_time_hours,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Analytics(db.Model):
    __tablename__ = 'analytics'
    
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    total_reviews = db.Column(db.Integer, default=0)
    average_rating = db.Column(db.Float, default=0.0)
    response_rate = db.Column(db.Float, default=0.0)
    avg_response_time_hours = db.Column(db.Float, default=0.0)
    positive_sentiment_count = db.Column(db.Integer, default=0)
    neutral_sentiment_count = db.Column(db.Integer, default=0)
    negative_sentiment_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'date': self.date.isoformat() if self.date else None,
            'total_reviews': self.total_reviews,
            'average_rating': self.average_rating,
            'response_rate': self.response_rate,
            'avg_response_time_hours': self.avg_response_time_hours,
            'positive_sentiment_count': self.positive_sentiment_count,
            'neutral_sentiment_count': self.neutral_sentiment_count,
            'negative_sentiment_count': self.negative_sentiment_count,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class ResponseTemplate(db.Model):
    __tablename__ = 'response_templates'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    template_content = db.Column(db.Text, nullable=False)
    sentiment_type = db.Column(db.Enum(Sentiment), nullable=False)
    rating_range_min = db.Column(db.Integer, default=1)
    rating_range_max = db.Column(db.Integer, default=5)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'template_content': self.template_content,
            'sentiment_type': self.sentiment_type.value if self.sentiment_type else None,
            'rating_range_min': self.rating_range_min,
            'rating_range_max': self.rating_range_max,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

