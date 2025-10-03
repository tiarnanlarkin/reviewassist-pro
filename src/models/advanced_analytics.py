from datetime import datetime, timedelta
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, JSON, ForeignKey
from sqlalchemy.orm import relationship
from src.models.user import db
import json

class DashboardWidget(db.Model):
    __tablename__ = 'dashboard_widgets'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    widget_type = Column(String(50), nullable=False)  # chart, metric, table, text
    chart_type = Column(String(50))  # line, bar, pie, doughnut, area
    data_source = Column(String(100), nullable=False)  # reviews, analytics, users
    configuration = Column(JSON)  # Widget-specific configuration
    position_x = Column(Integer, default=0)
    position_y = Column(Integer, default=0)
    width = Column(Integer, default=4)
    height = Column(Integer, default=3)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    dashboard_id = Column(Integer, ForeignKey('custom_dashboards.id'))
    dashboard = relationship("CustomDashboard", back_populates="widgets")
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'widget_type': self.widget_type,
            'chart_type': self.chart_type,
            'data_source': self.data_source,
            'configuration': self.configuration,
            'position': {
                'x': self.position_x,
                'y': self.position_y,
                'width': self.width,
                'height': self.height
            },
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class CustomDashboard(db.Model):
    __tablename__ = 'custom_dashboards'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    layout_config = Column(JSON)  # Grid layout configuration
    is_default = Column(Boolean, default=False)
    is_public = Column(Boolean, default=False)
    created_by = Column(Integer, ForeignKey('auth_users.id'))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    widgets = relationship("DashboardWidget", back_populates="dashboard", cascade="all, delete-orphan")
    creator = relationship("AuthUser", foreign_keys=[created_by])
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'layout_config': self.layout_config,
            'is_default': self.is_default,
            'is_public': self.is_public,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'widgets': [widget.to_dict() for widget in self.widgets]
        }

class CustomReport(db.Model):
    __tablename__ = 'custom_reports'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    report_type = Column(String(50), nullable=False)  # dashboard, table, chart, summary
    data_sources = Column(JSON)  # List of data sources
    filters = Column(JSON)  # Report filters
    layout_config = Column(JSON)  # Report layout configuration
    export_formats = Column(JSON)  # Supported export formats
    is_scheduled = Column(Boolean, default=False)
    schedule_config = Column(JSON)  # Scheduling configuration
    created_by = Column(Integer, ForeignKey('auth_users.id'))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    creator = relationship("AuthUser", foreign_keys=[created_by])
    executions = relationship("ReportExecution", back_populates="report", cascade="all, delete-orphan")
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'report_type': self.report_type,
            'data_sources': self.data_sources,
            'filters': self.filters,
            'layout_config': self.layout_config,
            'export_formats': self.export_formats,
            'is_scheduled': self.is_scheduled,
            'schedule_config': self.schedule_config,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class ReportExecution(db.Model):
    __tablename__ = 'report_executions'
    
    id = Column(Integer, primary_key=True)
    report_id = Column(Integer, ForeignKey('custom_reports.id'), nullable=False)
    execution_type = Column(String(50), nullable=False)  # manual, scheduled, api
    status = Column(String(50), default='pending')  # pending, running, completed, failed
    file_path = Column(String(255))  # Path to generated report file
    file_format = Column(String(20))  # pdf, xlsx, csv, pptx
    file_size = Column(Integer)  # File size in bytes
    execution_time = Column(Float)  # Execution time in seconds
    error_message = Column(Text)
    parameters = Column(JSON)  # Execution parameters
    executed_by = Column(Integer, ForeignKey('auth_users.id'))
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    
    # Relationships
    report = relationship("CustomReport", back_populates="executions")
    executor = relationship("AuthUser", foreign_keys=[executed_by])
    
    def to_dict(self):
        return {
            'id': self.id,
            'report_id': self.report_id,
            'execution_type': self.execution_type,
            'status': self.status,
            'file_path': self.file_path,
            'file_format': self.file_format,
            'file_size': self.file_size,
            'execution_time': self.execution_time,
            'error_message': self.error_message,
            'parameters': self.parameters,
            'executed_by': self.executed_by,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }

class DataVisualization(db.Model):
    __tablename__ = 'data_visualizations'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    visualization_type = Column(String(50), nullable=False)  # chart, graph, map, table
    chart_type = Column(String(50))  # line, bar, pie, scatter, heatmap
    data_query = Column(Text, nullable=False)  # SQL query or data source configuration
    chart_config = Column(JSON)  # Chart.js or similar configuration
    filters = Column(JSON)  # Available filters
    is_interactive = Column(Boolean, default=True)
    is_real_time = Column(Boolean, default=False)
    refresh_interval = Column(Integer, default=300)  # Refresh interval in seconds
    created_by = Column(Integer, ForeignKey('auth_users.id'))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    creator = relationship("AuthUser", foreign_keys=[created_by])
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'visualization_type': self.visualization_type,
            'chart_type': self.chart_type,
            'data_query': self.data_query,
            'chart_config': self.chart_config,
            'filters': self.filters,
            'is_interactive': self.is_interactive,
            'is_real_time': self.is_real_time,
            'refresh_interval': self.refresh_interval,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class PerformanceMetric(db.Model):
    __tablename__ = 'performance_metrics'
    
    id = Column(Integer, primary_key=True)
    metric_name = Column(String(100), nullable=False)
    metric_type = Column(String(50), nullable=False)  # kpi, benchmark, trend, ratio
    calculation_method = Column(String(50), nullable=False)  # sum, avg, count, ratio, custom
    data_source = Column(String(100), nullable=False)
    calculation_config = Column(JSON)  # Calculation configuration
    target_value = Column(Float)  # Target or benchmark value
    warning_threshold = Column(Float)  # Warning threshold
    critical_threshold = Column(Float)  # Critical threshold
    unit = Column(String(20))  # Unit of measurement
    is_active = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey('auth_users.id'))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    creator = relationship("AuthUser", foreign_keys=[created_by])
    values = relationship("MetricValue", back_populates="metric", cascade="all, delete-orphan")
    
    def to_dict(self):
        return {
            'id': self.id,
            'metric_name': self.metric_name,
            'metric_type': self.metric_type,
            'calculation_method': self.calculation_method,
            'data_source': self.data_source,
            'calculation_config': self.calculation_config,
            'target_value': self.target_value,
            'warning_threshold': self.warning_threshold,
            'critical_threshold': self.critical_threshold,
            'unit': self.unit,
            'is_active': self.is_active,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class MetricValue(db.Model):
    __tablename__ = 'metric_values'
    
    id = Column(Integer, primary_key=True)
    metric_id = Column(Integer, ForeignKey('performance_metrics.id'), nullable=False)
    value = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    period_start = Column(DateTime)
    period_end = Column(DateTime)
    context_data = Column(JSON)  # Additional context information
    
    # Relationships
    metric = relationship("PerformanceMetric", back_populates="values")
    
    def to_dict(self):
        return {
            'id': self.id,
            'metric_id': self.metric_id,
            'value': self.value,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'period_start': self.period_start.isoformat() if self.period_start else None,
            'period_end': self.period_end.isoformat() if self.period_end else None,
            'context_data': self.context_data
        }

class AnalyticsInsight(db.Model):
    __tablename__ = 'analytics_insights'
    
    id = Column(Integer, primary_key=True)
    insight_type = Column(String(50), nullable=False)  # trend, anomaly, prediction, recommendation
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    confidence_score = Column(Float)  # Confidence level (0-1)
    impact_level = Column(String(20))  # low, medium, high, critical
    data_source = Column(String(100))
    insight_data = Column(JSON)  # Supporting data and analysis
    action_items = Column(JSON)  # Recommended actions
    is_active = Column(Boolean, default=True)
    is_dismissed = Column(Boolean, default=False)
    generated_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
    
    def to_dict(self):
        return {
            'id': self.id,
            'insight_type': self.insight_type,
            'title': self.title,
            'description': self.description,
            'confidence_score': self.confidence_score,
            'impact_level': self.impact_level,
            'data_source': self.data_source,
            'insight_data': self.insight_data,
            'action_items': self.action_items,
            'is_active': self.is_active,
            'is_dismissed': self.is_dismissed,
            'generated_at': self.generated_at.isoformat() if self.generated_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None
        }

class AdvancedAnalyticsManager:
    """Manager class for advanced analytics operations"""
    
    @staticmethod
    def create_default_widgets():
        """Create default dashboard widgets"""
        default_widgets = [
            {
                'name': 'Review Volume Trend',
                'widget_type': 'chart',
                'chart_type': 'line',
                'data_source': 'reviews',
                'configuration': {
                    'metrics': ['count'],
                    'time_period': '30d',
                    'group_by': 'date'
                }
            },
            {
                'name': 'Sentiment Distribution',
                'widget_type': 'chart',
                'chart_type': 'pie',
                'data_source': 'reviews',
                'configuration': {
                    'metrics': ['sentiment'],
                    'time_period': '30d'
                }
            },
            {
                'name': 'Average Rating',
                'widget_type': 'metric',
                'data_source': 'reviews',
                'configuration': {
                    'metrics': ['avg_rating'],
                    'time_period': '30d',
                    'format': 'decimal'
                }
            },
            {
                'name': 'Response Rate',
                'widget_type': 'metric',
                'data_source': 'analytics',
                'configuration': {
                    'metrics': ['response_rate'],
                    'time_period': '30d',
                    'format': 'percentage'
                }
            },
            {
                'name': 'Platform Performance',
                'widget_type': 'chart',
                'chart_type': 'bar',
                'data_source': 'reviews',
                'configuration': {
                    'metrics': ['avg_rating', 'count'],
                    'group_by': 'platform',
                    'time_period': '30d'
                }
            },
            {
                'name': 'Recent Reviews',
                'widget_type': 'table',
                'data_source': 'reviews',
                'configuration': {
                    'columns': ['reviewer_name', 'rating', 'platform', 'created_at'],
                    'limit': 10,
                    'order_by': 'created_at desc'
                }
            }
        ]
        
        return default_widgets
    
    @staticmethod
    def create_default_reports():
        """Create default report templates"""
        default_reports = [
            {
                'name': 'Monthly Review Summary',
                'description': 'Comprehensive monthly review performance report',
                'report_type': 'dashboard',
                'data_sources': ['reviews', 'analytics'],
                'filters': {
                    'time_period': 'last_month',
                    'platforms': 'all'
                },
                'export_formats': ['pdf', 'xlsx'],
                'is_scheduled': True,
                'schedule_config': {
                    'frequency': 'monthly',
                    'day_of_month': 1,
                    'time': '09:00'
                }
            },
            {
                'name': 'Weekly Performance Report',
                'description': 'Weekly review metrics and trends',
                'report_type': 'summary',
                'data_sources': ['reviews', 'analytics'],
                'filters': {
                    'time_period': 'last_week'
                },
                'export_formats': ['pdf', 'csv'],
                'is_scheduled': True,
                'schedule_config': {
                    'frequency': 'weekly',
                    'day_of_week': 'monday',
                    'time': '08:00'
                }
            },
            {
                'name': 'Sentiment Analysis Report',
                'description': 'Detailed sentiment analysis and trends',
                'report_type': 'chart',
                'data_sources': ['reviews'],
                'filters': {
                    'time_period': 'last_quarter',
                    'include_sentiment': True
                },
                'export_formats': ['pdf', 'pptx']
            }
        ]
        
        return default_reports
    
    @staticmethod
    def create_default_metrics():
        """Create default performance metrics"""
        default_metrics = [
            {
                'metric_name': 'Customer Satisfaction Score',
                'metric_type': 'kpi',
                'calculation_method': 'avg',
                'data_source': 'reviews',
                'calculation_config': {
                    'field': 'rating',
                    'scale': 5
                },
                'target_value': 4.5,
                'warning_threshold': 4.0,
                'critical_threshold': 3.5,
                'unit': 'stars'
            },
            {
                'metric_name': 'Review Response Rate',
                'metric_type': 'kpi',
                'calculation_method': 'ratio',
                'data_source': 'reviews',
                'calculation_config': {
                    'numerator': 'responded_reviews',
                    'denominator': 'total_reviews'
                },
                'target_value': 0.9,
                'warning_threshold': 0.7,
                'critical_threshold': 0.5,
                'unit': 'percentage'
            },
            {
                'metric_name': 'Average Response Time',
                'metric_type': 'benchmark',
                'calculation_method': 'avg',
                'data_source': 'analytics',
                'calculation_config': {
                    'field': 'response_time_hours'
                },
                'target_value': 24,
                'warning_threshold': 48,
                'critical_threshold': 72,
                'unit': 'hours'
            },
            {
                'metric_name': 'Positive Sentiment Ratio',
                'metric_type': 'trend',
                'calculation_method': 'ratio',
                'data_source': 'reviews',
                'calculation_config': {
                    'numerator': 'positive_reviews',
                    'denominator': 'total_reviews'
                },
                'target_value': 0.8,
                'warning_threshold': 0.6,
                'critical_threshold': 0.4,
                'unit': 'percentage'
            }
        ]
        
        return default_metrics

