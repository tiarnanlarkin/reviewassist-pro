from src.models.user import db
from datetime import datetime, timedelta
from sqlalchemy import func, and_, or_
from enum import Enum
import json

class ReportType(Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    CUSTOM = "custom"

class MetricType(Enum):
    REVIEW_COUNT = "review_count"
    AVERAGE_RATING = "average_rating"
    RESPONSE_RATE = "response_rate"
    RESPONSE_TIME = "response_time"
    SENTIMENT_SCORE = "sentiment_score"
    PLATFORM_PERFORMANCE = "platform_performance"

class AdvancedAnalytics(db.Model):
    __tablename__ = 'advanced_analytics'
    
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    metric_type = db.Column(db.Enum(MetricType), nullable=False)
    platform = db.Column(db.String(50), nullable=True)  # Google, Yelp, Facebook, etc.
    value = db.Column(db.Float, nullable=False)
    additional_data = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'date': self.date.isoformat(),
            'metric_type': self.metric_type.value,
            'platform': self.platform,
            'value': self.value,
            'additional_data': self.additional_data,
            'created_at': self.created_at.isoformat()
        }

class ReportTemplate(db.Model):
    __tablename__ = 'report_templates'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    report_type = db.Column(db.Enum(ReportType), nullable=False)
    metrics = db.Column(db.JSON, nullable=False)  # List of metrics to include
    filters = db.Column(db.JSON, nullable=True)  # Default filters
    visualization_config = db.Column(db.JSON, nullable=True)  # Chart configurations
    is_active = db.Column(db.Boolean, default=True)
    created_by = db.Column(db.Integer, db.ForeignKey('auth_users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'report_type': self.report_type.value,
            'metrics': self.metrics,
            'filters': self.filters,
            'visualization_config': self.visualization_config,
            'is_active': self.is_active,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class GeneratedReport(db.Model):
    __tablename__ = 'generated_reports'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(300), nullable=False)
    report_type = db.Column(db.Enum(ReportType), nullable=False)
    date_range_start = db.Column(db.Date, nullable=False)
    date_range_end = db.Column(db.Date, nullable=False)
    filters_applied = db.Column(db.JSON, nullable=True)
    data_snapshot = db.Column(db.JSON, nullable=False)  # Report data at generation time
    file_path = db.Column(db.String(500), nullable=True)  # Path to generated PDF/Excel
    file_type = db.Column(db.String(10), nullable=False)  # pdf, xlsx, csv
    generated_by = db.Column(db.Integer, db.ForeignKey('auth_users.id'), nullable=False)
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=True)  # Auto-cleanup old reports
    download_count = db.Column(db.Integer, default=0)
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'report_type': self.report_type.value,
            'date_range_start': self.date_range_start.isoformat(),
            'date_range_end': self.date_range_end.isoformat(),
            'filters_applied': self.filters_applied,
            'file_type': self.file_type,
            'generated_by': self.generated_by,
            'generated_at': self.generated_at.isoformat(),
            'download_count': self.download_count
        }

class PerformanceBenchmark(db.Model):
    __tablename__ = 'performance_benchmarks'
    
    id = db.Column(db.Integer, primary_key=True)
    metric_name = db.Column(db.String(100), nullable=False)
    industry_average = db.Column(db.Float, nullable=True)
    top_quartile = db.Column(db.Float, nullable=True)
    bottom_quartile = db.Column(db.Float, nullable=True)
    our_current_value = db.Column(db.Float, nullable=False)
    our_previous_value = db.Column(db.Float, nullable=True)
    benchmark_date = db.Column(db.Date, nullable=False)
    data_source = db.Column(db.String(200), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'metric_name': self.metric_name,
            'industry_average': self.industry_average,
            'top_quartile': self.top_quartile,
            'bottom_quartile': self.bottom_quartile,
            'our_current_value': self.our_current_value,
            'our_previous_value': self.our_previous_value,
            'benchmark_date': self.benchmark_date.isoformat(),
            'data_source': self.data_source,
            'notes': self.notes
        }

class PredictiveInsight(db.Model):
    __tablename__ = 'predictive_insights'
    
    id = db.Column(db.Integer, primary_key=True)
    insight_type = db.Column(db.String(50), nullable=False)  # trend, forecast, anomaly, etc.
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    confidence_score = db.Column(db.Float, nullable=False)  # 0-1 confidence level
    predicted_value = db.Column(db.Float, nullable=True)
    predicted_date = db.Column(db.Date, nullable=True)
    supporting_data = db.Column(db.JSON, nullable=True)
    action_recommendations = db.Column(db.JSON, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'insight_type': self.insight_type,
            'title': self.title,
            'description': self.description,
            'confidence_score': self.confidence_score,
            'predicted_value': self.predicted_value,
            'predicted_date': self.predicted_date.isoformat() if self.predicted_date else None,
            'supporting_data': self.supporting_data,
            'action_recommendations': self.action_recommendations,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat()
        }

# Analytics utility functions
class AnalyticsEngine:
    @staticmethod
    def calculate_trend(data_points, periods=7):
        """Calculate trend direction and strength"""
        if len(data_points) < 2:
            return {'direction': 'stable', 'strength': 0, 'change_percent': 0}
        
        recent_avg = sum(data_points[-periods:]) / min(len(data_points), periods)
        previous_avg = sum(data_points[:-periods]) / max(1, len(data_points) - periods)
        
        if previous_avg == 0:
            change_percent = 0
        else:
            change_percent = ((recent_avg - previous_avg) / previous_avg) * 100
        
        if abs(change_percent) < 5:
            direction = 'stable'
        elif change_percent > 0:
            direction = 'increasing'
        else:
            direction = 'decreasing'
        
        strength = min(abs(change_percent) / 10, 1.0)  # Normalize to 0-1
        
        return {
            'direction': direction,
            'strength': strength,
            'change_percent': round(change_percent, 2)
        }
    
    @staticmethod
    def detect_anomalies(data_points, threshold=2.0):
        """Detect anomalies using standard deviation"""
        if len(data_points) < 3:
            return []
        
        mean_val = sum(data_points) / len(data_points)
        variance = sum((x - mean_val) ** 2 for x in data_points) / len(data_points)
        std_dev = variance ** 0.5
        
        anomalies = []
        for i, value in enumerate(data_points):
            z_score = abs(value - mean_val) / std_dev if std_dev > 0 else 0
            if z_score > threshold:
                anomalies.append({
                    'index': i,
                    'value': value,
                    'z_score': z_score,
                    'severity': 'high' if z_score > 3 else 'medium'
                })
        
        return anomalies
    
    @staticmethod
    def forecast_next_period(data_points, periods_ahead=1):
        """Simple linear regression forecast"""
        if len(data_points) < 3:
            return None
        
        n = len(data_points)
        x_values = list(range(n))
        y_values = data_points
        
        # Calculate linear regression
        x_mean = sum(x_values) / n
        y_mean = sum(y_values) / n
        
        numerator = sum((x_values[i] - x_mean) * (y_values[i] - y_mean) for i in range(n))
        denominator = sum((x_values[i] - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return y_mean
        
        slope = numerator / denominator
        intercept = y_mean - slope * x_mean
        
        # Forecast
        forecast_x = n + periods_ahead - 1
        forecast_y = slope * forecast_x + intercept
        
        return max(0, forecast_y)  # Ensure non-negative forecast
    
    @staticmethod
    def calculate_correlation(data1, data2):
        """Calculate correlation coefficient between two datasets"""
        if len(data1) != len(data2) or len(data1) < 2:
            return 0
        
        n = len(data1)
        mean1 = sum(data1) / n
        mean2 = sum(data2) / n
        
        numerator = sum((data1[i] - mean1) * (data2[i] - mean2) for i in range(n))
        
        sum_sq1 = sum((data1[i] - mean1) ** 2 for i in range(n))
        sum_sq2 = sum((data2[i] - mean2) ** 2 for i in range(n))
        
        denominator = (sum_sq1 * sum_sq2) ** 0.5
        
        if denominator == 0:
            return 0
        
        return numerator / denominator

