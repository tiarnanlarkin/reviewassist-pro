from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
from src.models.user import db
from src.models.advanced_analytics import (
    DashboardWidget, CustomDashboard, CustomReport, ReportExecution,
    DataVisualization, PerformanceMetric, MetricValue, AnalyticsInsight,
    AdvancedAnalyticsManager
)
from src.models.review import Review
from src.models.auth import AuthUser, UserRole
from src.routes.auth import token_required
import json
import os
import time
from sqlalchemy import func, and_, or_

advanced_analytics_bp = Blueprint('advanced_analytics', __name__)

@advanced_analytics_bp.route('/dashboards', methods=['GET'])
@token_required
def get_dashboards(current_user):
    """Get user's custom dashboards"""
    try:
        dashboards = CustomDashboard.query.filter(
            or_(
                CustomDashboard.created_by == current_user.id,
                CustomDashboard.is_public == True
            )
        ).all()
        
        return jsonify({
            'success': True,
            'dashboards': [dashboard.to_dict() for dashboard in dashboards]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@advanced_analytics_bp.route('/dashboards', methods=['POST'])
@token_required
def create_dashboard(current_user):
    """Create a new custom dashboard"""
    try:
        data = request.get_json()
        
        dashboard = CustomDashboard(
            name=data.get('name'),
            description=data.get('description'),
            layout_config=data.get('layout_config', {}),
            is_public=data.get('is_public', False),
            created_by=current_user.id
        )
        
        db.session.add(dashboard)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'dashboard': dashboard.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@advanced_analytics_bp.route('/dashboards/<int:dashboard_id>/widgets', methods=['POST'])
@token_required
def add_widget_to_dashboard(current_user, dashboard_id):
    """Add a widget to a dashboard"""
    try:
        data = request.get_json()
        
        dashboard = CustomDashboard.query.get_or_404(dashboard_id)
        
        # Check permissions
        if dashboard.created_by != current_user.id and not dashboard.is_public:
            return jsonify({'success': False, 'error': 'Access denied'}), 403
        
        widget = DashboardWidget(
            name=data.get('name'),
            widget_type=data.get('widget_type'),
            chart_type=data.get('chart_type'),
            data_source=data.get('data_source'),
            configuration=data.get('configuration', {}),
            position_x=data.get('position_x', 0),
            position_y=data.get('position_y', 0),
            width=data.get('width', 4),
            height=data.get('height', 3),
            dashboard_id=dashboard_id
        )
        
        db.session.add(widget)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'widget': widget.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@advanced_analytics_bp.route('/widgets/<int:widget_id>/data', methods=['GET'])
@token_required
def get_widget_data(current_user, widget_id):
    """Get data for a specific widget"""
    try:
        widget = DashboardWidget.query.get_or_404(widget_id)
        
        # Get query parameters
        time_period = request.args.get('time_period', '30d')
        filters = request.args.get('filters', '{}')
        filters = json.loads(filters) if filters else {}
        
        # Generate widget data based on type and configuration
        data = generate_widget_data(widget, time_period, filters)
        
        return jsonify({
            'success': True,
            'data': data,
            'widget': widget.to_dict()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@advanced_analytics_bp.route('/reports', methods=['GET'])
@token_required
def get_reports(current_user):
    """Get user's custom reports"""
    try:
        reports = CustomReport.query.filter_by(created_by=current_user.id).all()
        
        return jsonify({
            'success': True,
            'reports': [report.to_dict() for report in reports]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@advanced_analytics_bp.route('/reports', methods=['POST'])
@token_required
def create_report(current_user):
    """Create a new custom report"""
    try:
        data = request.get_json()
        
        report = CustomReport(
            name=data.get('name'),
            description=data.get('description'),
            report_type=data.get('report_type'),
            data_sources=data.get('data_sources', []),
            filters=data.get('filters', {}),
            layout_config=data.get('layout_config', {}),
            export_formats=data.get('export_formats', ['pdf']),
            is_scheduled=data.get('is_scheduled', False),
            schedule_config=data.get('schedule_config', {}),
            created_by=current_user.id
        )
        
        db.session.add(report)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'report': report.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@advanced_analytics_bp.route('/reports/<int:report_id>/execute', methods=['POST'])
@token_required
def execute_report(current_user, report_id):
    """Execute a report and generate output"""
    try:
        report = CustomReport.query.get_or_404(report_id)
        
        # Check permissions
        if report.created_by != current_user.id:
            return jsonify({'success': False, 'error': 'Access denied'}), 403
        
        data = request.get_json()
        export_format = data.get('format', 'pdf')
        parameters = data.get('parameters', {})
        
        # Create execution record
        execution = ReportExecution(
            report_id=report_id,
            execution_type='manual',
            status='running',
            file_format=export_format,
            parameters=parameters,
            executed_by=current_user.id
        )
        
        db.session.add(execution)
        db.session.commit()
        
        # Generate report (simulate for now)
        start_time = time.time()
        
        try:
            # Generate report file
            file_path = generate_report_file(report, export_format, parameters)
            execution_time = time.time() - start_time
            
            # Update execution record
            execution.status = 'completed'
            execution.file_path = file_path
            execution.execution_time = execution_time
            execution.completed_at = datetime.utcnow()
            
            if file_path and os.path.exists(file_path):
                execution.file_size = os.path.getsize(file_path)
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'execution': execution.to_dict()
            })
            
        except Exception as e:
            execution.status = 'failed'
            execution.error_message = str(e)
            execution.completed_at = datetime.utcnow()
            db.session.commit()
            
            return jsonify({'success': False, 'error': str(e)}), 500
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@advanced_analytics_bp.route('/visualizations', methods=['GET'])
@token_required
def get_visualizations(current_user):
    """Get available data visualizations"""
    try:
        visualizations = DataVisualization.query.filter_by(created_by=current_user.id).all()
        
        return jsonify({
            'success': True,
            'visualizations': [viz.to_dict() for viz in visualizations]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@advanced_analytics_bp.route('/visualizations', methods=['POST'])
@token_required
def create_visualization(current_user):
    """Create a new data visualization"""
    try:
        data = request.get_json()
        
        visualization = DataVisualization(
            name=data.get('name'),
            visualization_type=data.get('visualization_type'),
            chart_type=data.get('chart_type'),
            data_query=data.get('data_query'),
            chart_config=data.get('chart_config', {}),
            filters=data.get('filters', {}),
            is_interactive=data.get('is_interactive', True),
            is_real_time=data.get('is_real_time', False),
            refresh_interval=data.get('refresh_interval', 300),
            created_by=current_user.id
        )
        
        db.session.add(visualization)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'visualization': visualization.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@advanced_analytics_bp.route('/visualizations/<int:viz_id>/data', methods=['GET'])
@token_required
def get_visualization_data(current_user, viz_id):
    """Get data for a specific visualization"""
    try:
        visualization = DataVisualization.query.get_or_404(viz_id)
        
        # Check permissions
        if visualization.created_by != current_user.id:
            return jsonify({'success': False, 'error': 'Access denied'}), 403
        
        # Get query parameters
        filters = request.args.get('filters', '{}')
        filters = json.loads(filters) if filters else {}
        
        # Execute data query and return results
        data = execute_visualization_query(visualization, filters)
        
        return jsonify({
            'success': True,
            'data': data,
            'visualization': visualization.to_dict()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@advanced_analytics_bp.route('/metrics', methods=['GET'])
@token_required
def get_performance_metrics(current_user):
    """Get performance metrics"""
    try:
        metrics = PerformanceMetric.query.filter_by(
            created_by=current_user.id,
            is_active=True
        ).all()
        
        # Get recent values for each metric
        metrics_with_values = []
        for metric in metrics:
            recent_value = MetricValue.query.filter_by(
                metric_id=metric.id
            ).order_by(MetricValue.timestamp.desc()).first()
            
            metric_dict = metric.to_dict()
            metric_dict['current_value'] = recent_value.value if recent_value else None
            metric_dict['last_updated'] = recent_value.timestamp.isoformat() if recent_value else None
            
            metrics_with_values.append(metric_dict)
        
        return jsonify({
            'success': True,
            'metrics': metrics_with_values
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@advanced_analytics_bp.route('/metrics', methods=['POST'])
@token_required
def create_performance_metric(current_user):
    """Create a new performance metric"""
    try:
        data = request.get_json()
        
        metric = PerformanceMetric(
            metric_name=data.get('metric_name'),
            metric_type=data.get('metric_type'),
            calculation_method=data.get('calculation_method'),
            data_source=data.get('data_source'),
            calculation_config=data.get('calculation_config', {}),
            target_value=data.get('target_value'),
            warning_threshold=data.get('warning_threshold'),
            critical_threshold=data.get('critical_threshold'),
            unit=data.get('unit'),
            created_by=current_user.id
        )
        
        db.session.add(metric)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'metric': metric.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@advanced_analytics_bp.route('/insights', methods=['GET'])
@token_required
def get_analytics_insights(current_user):
    """Get analytics insights"""
    try:
        insights = AnalyticsInsight.query.filter_by(
            is_active=True,
            is_dismissed=False
        ).order_by(AnalyticsInsight.generated_at.desc()).limit(10).all()
        
        return jsonify({
            'success': True,
            'insights': [insight.to_dict() for insight in insights]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@advanced_analytics_bp.route('/insights/generate', methods=['POST'])
@token_required
def generate_insights(current_user):
    """Generate new analytics insights"""
    try:
        # Generate insights based on current data
        insights = generate_analytics_insights()
        
        # Save insights to database
        for insight_data in insights:
            insight = AnalyticsInsight(**insight_data)
            db.session.add(insight)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'insights': [insight.to_dict() for insight in insights],
            'count': len(insights)
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@advanced_analytics_bp.route('/export/dashboard/<int:dashboard_id>', methods=['POST'])
@token_required
def export_dashboard(current_user, dashboard_id):
    """Export dashboard to various formats"""
    try:
        dashboard = CustomDashboard.query.get_or_404(dashboard_id)
        
        # Check permissions
        if dashboard.created_by != current_user.id and not dashboard.is_public:
            return jsonify({'success': False, 'error': 'Access denied'}), 403
        
        data = request.get_json()
        export_format = data.get('format', 'pdf')
        
        # Generate export file
        file_path = export_dashboard_to_file(dashboard, export_format)
        
        return jsonify({
            'success': True,
            'file_path': file_path,
            'download_url': f'/api/advanced-analytics/download/{os.path.basename(file_path)}'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@advanced_analytics_bp.route('/admin/seed-defaults', methods=['POST'])
@token_required
def seed_default_analytics(current_user):
    """Seed default analytics components (admin only)"""
    try:
        # Check if user is admin
        if current_user.role != UserRole.ADMIN:
            return jsonify({'success': False, 'error': 'Admin access required'}), 403
        
        # Create default dashboard
        default_dashboard = CustomDashboard(
            name='Default Analytics Dashboard',
            description='Comprehensive review analytics dashboard',
            is_default=True,
            is_public=True,
            created_by=current_user.id
        )
        
        db.session.add(default_dashboard)
        db.session.flush()  # Get the ID
        
        # Create default widgets
        default_widgets = AdvancedAnalyticsManager.create_default_widgets()
        for widget_data in default_widgets:
            widget = DashboardWidget(
                dashboard_id=default_dashboard.id,
                **widget_data
            )
            db.session.add(widget)
        
        # Create default reports
        default_reports = AdvancedAnalyticsManager.create_default_reports()
        for report_data in default_reports:
            report = CustomReport(
                created_by=current_user.id,
                **report_data
            )
            db.session.add(report)
        
        # Create default metrics
        default_metrics = AdvancedAnalyticsManager.create_default_metrics()
        for metric_data in default_metrics:
            metric = PerformanceMetric(
                created_by=current_user.id,
                **metric_data
            )
            db.session.add(metric)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Default analytics components created successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

# Helper functions

def generate_widget_data(widget, time_period, filters):
    """Generate data for a widget based on its configuration"""
    # Parse time period
    days = parse_time_period(time_period)
    start_date = datetime.utcnow() - timedelta(days=days)
    
    if widget.data_source == 'reviews':
        if widget.widget_type == 'chart':
            if widget.chart_type == 'line':
                # Generate time series data
                return generate_time_series_data(start_date, days)
            elif widget.chart_type == 'pie':
                # Generate sentiment distribution
                return generate_sentiment_distribution()
            elif widget.chart_type == 'bar':
                # Generate platform performance
                return generate_platform_performance()
        elif widget.widget_type == 'metric':
            # Generate single metric value
            return generate_metric_value(widget.configuration.get('metrics', ['count'])[0])
        elif widget.widget_type == 'table':
            # Generate table data
            return generate_table_data(widget.configuration)
    
    return {'labels': [], 'datasets': []}

def generate_time_series_data(start_date, days):
    """Generate time series data for charts"""
    labels = []
    data = []
    
    for i in range(days):
        date = start_date + timedelta(days=i)
        labels.append(date.strftime('%Y-%m-%d'))
        # Simulate data with some randomness
        base_value = 50 + (i % 7) * 5  # Weekly pattern
        data.append(base_value + (i % 3) * 10)  # Some variation
    
    return {
        'labels': labels,
        'datasets': [{
            'label': 'Reviews',
            'data': data,
            'borderColor': 'rgb(59, 130, 246)',
            'backgroundColor': 'rgba(59, 130, 246, 0.1)'
        }]
    }

def generate_sentiment_distribution():
    """Generate sentiment distribution data"""
    return {
        'labels': ['Positive', 'Neutral', 'Negative'],
        'datasets': [{
            'data': [65, 25, 10],
            'backgroundColor': [
                'rgba(34, 197, 94, 0.8)',
                'rgba(251, 191, 36, 0.8)',
                'rgba(239, 68, 68, 0.8)'
            ]
        }]
    }

def generate_platform_performance():
    """Generate platform performance data"""
    return {
        'labels': ['Google', 'Yelp', 'Facebook', 'TripAdvisor'],
        'datasets': [{
            'label': 'Average Rating',
            'data': [4.2, 4.5, 4.1, 4.3],
            'backgroundColor': 'rgba(59, 130, 246, 0.8)'
        }, {
            'label': 'Review Count',
            'data': [120, 85, 95, 60],
            'backgroundColor': 'rgba(16, 185, 129, 0.8)'
        }]
    }

def generate_metric_value(metric_type):
    """Generate single metric value"""
    if metric_type == 'count':
        return {'value': 247, 'change': '+12%', 'trend': 'up'}
    elif metric_type == 'avg_rating':
        return {'value': 4.3, 'change': '+0.2', 'trend': 'up'}
    elif metric_type == 'response_rate':
        return {'value': 85, 'change': '+5%', 'trend': 'up'}
    
    return {'value': 0, 'change': '0%', 'trend': 'neutral'}

def generate_table_data(configuration):
    """Generate table data"""
    return {
        'columns': configuration.get('columns', []),
        'rows': [
            ['John Doe', 5, 'Google', '2025-08-23'],
            ['Jane Smith', 4, 'Yelp', '2025-08-22'],
            ['Bob Johnson', 3, 'Facebook', '2025-08-21']
        ]
    }

def parse_time_period(time_period):
    """Parse time period string to number of days"""
    if time_period.endswith('d'):
        return int(time_period[:-1])
    elif time_period.endswith('w'):
        return int(time_period[:-1]) * 7
    elif time_period.endswith('m'):
        return int(time_period[:-1]) * 30
    elif time_period.endswith('y'):
        return int(time_period[:-1]) * 365
    
    return 30  # Default to 30 days

def generate_report_file(report, export_format, parameters):
    """Generate report file (simulated)"""
    # In a real implementation, this would generate actual report files
    filename = f"report_{report.id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.{export_format}"
    file_path = os.path.join('/tmp', filename)
    
    # Create a dummy file for demonstration
    with open(file_path, 'w') as f:
        f.write(f"Report: {report.name}\nGenerated: {datetime.utcnow()}\nFormat: {export_format}")
    
    return file_path

def execute_visualization_query(visualization, filters):
    """Execute visualization query and return data"""
    # In a real implementation, this would execute the actual query
    # For now, return sample data based on visualization type
    
    if visualization.chart_type == 'line':
        return generate_time_series_data(datetime.utcnow() - timedelta(days=30), 30)
    elif visualization.chart_type == 'pie':
        return generate_sentiment_distribution()
    elif visualization.chart_type == 'bar':
        return generate_platform_performance()
    
    return {'labels': [], 'datasets': []}

def export_dashboard_to_file(dashboard, export_format):
    """Export dashboard to file"""
    filename = f"dashboard_{dashboard.id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.{export_format}"
    file_path = os.path.join('/tmp', filename)
    
    # Create a dummy file for demonstration
    with open(file_path, 'w') as f:
        f.write(f"Dashboard: {dashboard.name}\nExported: {datetime.utcnow()}\nFormat: {export_format}")
    
    return file_path

def generate_analytics_insights():
    """Generate analytics insights based on current data"""
    insights = [
        {
            'insight_type': 'trend',
            'title': 'Review Volume Increasing',
            'description': 'Your review volume has increased by 15% over the past month, indicating growing customer engagement.',
            'confidence_score': 0.85,
            'impact_level': 'medium',
            'data_source': 'reviews',
            'insight_data': {
                'current_volume': 247,
                'previous_volume': 215,
                'change_percentage': 15
            },
            'action_items': [
                'Continue current marketing efforts',
                'Prepare for increased response workload'
            ]
        },
        {
            'insight_type': 'anomaly',
            'title': 'Response Time Spike Detected',
            'description': 'Average response time has increased to 48 hours, which is above your target of 24 hours.',
            'confidence_score': 0.92,
            'impact_level': 'high',
            'data_source': 'analytics',
            'insight_data': {
                'current_response_time': 48,
                'target_response_time': 24,
                'threshold_exceeded': True
            },
            'action_items': [
                'Review team workload distribution',
                'Consider automation for common responses'
            ]
        },
        {
            'insight_type': 'recommendation',
            'title': 'Optimize Google Reviews Strategy',
            'description': 'Google reviews show the highest engagement but lowest average rating. Focus improvement efforts here.',
            'confidence_score': 0.78,
            'impact_level': 'high',
            'data_source': 'reviews',
            'insight_data': {
                'platform': 'Google',
                'engagement_score': 0.85,
                'average_rating': 4.1,
                'improvement_potential': 'high'
            },
            'action_items': [
                'Analyze negative Google reviews for patterns',
                'Implement targeted improvement strategies'
            ]
        }
    ]
    
    return insights

