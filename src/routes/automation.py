from flask import Blueprint, request, jsonify
from src.models.user import db
from src.models.automation import (
    Workflow, WorkflowTask, AutomationRule, ScheduledReport, AlertRule,
    WorkflowStatus, TaskStatus, TriggerType, ActionType,
    WorkflowEngine, AutomationRuleEngine
)
from src.models.auth import AuthUser
from src.routes.auth import token_required
from datetime import datetime, timedelta
from sqlalchemy import func, and_, or_, desc
import json

automation_bp = Blueprint('automation', __name__)

# Workflow Management Routes

@automation_bp.route('/workflows', methods=['GET'])
@token_required
def get_workflows(current_user):
    """Get all workflows for the current user"""
    try:
        workflows = Workflow.query.filter_by(created_by=current_user.id).all()
        return jsonify({
            'success': True,
            'data': [workflow.to_dict() for workflow in workflows]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@automation_bp.route('/workflows', methods=['POST'])
@token_required
def create_workflow(current_user):
    """Create a new workflow"""
    try:
        data = request.get_json()
        
        workflow = Workflow(
            name=data['name'],
            description=data.get('description'),
            trigger_type=TriggerType(data['trigger_type']),
            trigger_config=data['trigger_config'],
            actions=data['actions'],
            conditions=data.get('conditions'),
            max_executions=data.get('max_executions'),
            created_by=current_user.id
        )
        
        # Calculate next execution if it's a scheduled workflow
        if workflow.trigger_type == TriggerType.SCHEDULE:
            workflow.next_execution = WorkflowEngine._calculate_next_execution(workflow)
        
        db.session.add(workflow)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': workflow.to_dict()
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@automation_bp.route('/workflows/<int:workflow_id>', methods=['PUT'])
@token_required
def update_workflow(current_user, workflow_id):
    """Update an existing workflow"""
    try:
        workflow = Workflow.query.filter_by(
            id=workflow_id, 
            created_by=current_user.id
        ).first_or_404()
        
        data = request.get_json()
        
        workflow.name = data.get('name', workflow.name)
        workflow.description = data.get('description', workflow.description)
        workflow.status = WorkflowStatus(data.get('status', workflow.status.value))
        workflow.trigger_config = data.get('trigger_config', workflow.trigger_config)
        workflow.actions = data.get('actions', workflow.actions)
        workflow.conditions = data.get('conditions', workflow.conditions)
        workflow.max_executions = data.get('max_executions', workflow.max_executions)
        workflow.updated_at = datetime.utcnow()
        
        # Recalculate next execution if trigger config changed
        if 'trigger_config' in data and workflow.trigger_type == TriggerType.SCHEDULE:
            workflow.next_execution = WorkflowEngine._calculate_next_execution(workflow)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': workflow.to_dict()
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@automation_bp.route('/workflows/<int:workflow_id>', methods=['DELETE'])
@token_required
def delete_workflow(current_user, workflow_id):
    """Delete a workflow"""
    try:
        workflow = Workflow.query.filter_by(
            id=workflow_id, 
            created_by=current_user.id
        ).first_or_404()
        
        db.session.delete(workflow)
        db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@automation_bp.route('/workflows/<int:workflow_id>/execute', methods=['POST'])
@token_required
def execute_workflow(current_user, workflow_id):
    """Manually execute a workflow"""
    try:
        workflow = Workflow.query.filter_by(
            id=workflow_id, 
            created_by=current_user.id
        ).first_or_404()
        
        success = WorkflowEngine.execute_workflow(workflow_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Workflow executed successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Workflow execution failed or conditions not met'
            }), 400
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@automation_bp.route('/workflows/<int:workflow_id>/tasks', methods=['GET'])
@token_required
def get_workflow_tasks(current_user, workflow_id):
    """Get tasks for a specific workflow"""
    try:
        workflow = Workflow.query.filter_by(
            id=workflow_id, 
            created_by=current_user.id
        ).first_or_404()
        
        tasks = WorkflowTask.query.filter_by(workflow_id=workflow_id).order_by(
            desc(WorkflowTask.created_at)
        ).limit(50).all()
        
        return jsonify({
            'success': True,
            'data': [task.to_dict() for task in tasks]
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Automation Rules Routes

@automation_bp.route('/rules', methods=['GET'])
@token_required
def get_automation_rules(current_user):
    """Get all automation rules for the current user"""
    try:
        rules = AutomationRule.query.filter_by(created_by=current_user.id).all()
        return jsonify({
            'success': True,
            'data': [rule.to_dict() for rule in rules]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@automation_bp.route('/rules', methods=['POST'])
@token_required
def create_automation_rule(current_user):
    """Create a new automation rule"""
    try:
        data = request.get_json()
        
        rule = AutomationRule(
            name=data['name'],
            description=data.get('description'),
            trigger_event=data['trigger_event'],
            conditions=data['conditions'],
            actions=data['actions'],
            cooldown_minutes=data.get('cooldown_minutes', 0),
            priority=data.get('priority', 100),
            created_by=current_user.id
        )
        
        db.session.add(rule)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': rule.to_dict()
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@automation_bp.route('/rules/<int:rule_id>', methods=['PUT'])
@token_required
def update_automation_rule(current_user, rule_id):
    """Update an automation rule"""
    try:
        rule = AutomationRule.query.filter_by(
            id=rule_id, 
            created_by=current_user.id
        ).first_or_404()
        
        data = request.get_json()
        
        rule.name = data.get('name', rule.name)
        rule.description = data.get('description', rule.description)
        rule.is_active = data.get('is_active', rule.is_active)
        rule.trigger_event = data.get('trigger_event', rule.trigger_event)
        rule.conditions = data.get('conditions', rule.conditions)
        rule.actions = data.get('actions', rule.actions)
        rule.cooldown_minutes = data.get('cooldown_minutes', rule.cooldown_minutes)
        rule.priority = data.get('priority', rule.priority)
        rule.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': rule.to_dict()
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@automation_bp.route('/rules/<int:rule_id>', methods=['DELETE'])
@token_required
def delete_automation_rule(current_user, rule_id):
    """Delete an automation rule"""
    try:
        rule = AutomationRule.query.filter_by(
            id=rule_id, 
            created_by=current_user.id
        ).first_or_404()
        
        db.session.delete(rule)
        db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Scheduled Reports Routes

@automation_bp.route('/scheduled-reports', methods=['GET'])
@token_required
def get_scheduled_reports(current_user):
    """Get all scheduled reports for the current user"""
    try:
        reports = ScheduledReport.query.filter_by(created_by=current_user.id).all()
        return jsonify({
            'success': True,
            'data': [report.to_dict() for report in reports]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@automation_bp.route('/scheduled-reports', methods=['POST'])
@token_required
def create_scheduled_report(current_user):
    """Create a new scheduled report"""
    try:
        data = request.get_json()
        
        report = ScheduledReport(
            name=data['name'],
            description=data.get('description'),
            report_type=data['report_type'],
            report_format=data['report_format'],
            filters=data.get('filters'),
            schedule_type=data['schedule_type'],
            schedule_config=data['schedule_config'],
            delivery_method=data.get('delivery_method', 'download'),
            delivery_config=data.get('delivery_config'),
            created_by=current_user.id
        )
        
        # Calculate next generation time
        report.next_generation = calculate_next_schedule_time(
            report.schedule_type, 
            report.schedule_config
        )
        
        db.session.add(report)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': report.to_dict()
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@automation_bp.route('/scheduled-reports/<int:report_id>', methods=['PUT'])
@token_required
def update_scheduled_report(current_user, report_id):
    """Update a scheduled report"""
    try:
        report = ScheduledReport.query.filter_by(
            id=report_id, 
            created_by=current_user.id
        ).first_or_404()
        
        data = request.get_json()
        
        report.name = data.get('name', report.name)
        report.description = data.get('description', report.description)
        report.is_active = data.get('is_active', report.is_active)
        report.report_type = data.get('report_type', report.report_type)
        report.report_format = data.get('report_format', report.report_format)
        report.filters = data.get('filters', report.filters)
        report.schedule_type = data.get('schedule_type', report.schedule_type)
        report.schedule_config = data.get('schedule_config', report.schedule_config)
        report.delivery_method = data.get('delivery_method', report.delivery_method)
        report.delivery_config = data.get('delivery_config', report.delivery_config)
        report.updated_at = datetime.utcnow()
        
        # Recalculate next generation if schedule changed
        if 'schedule_config' in data or 'schedule_type' in data:
            report.next_generation = calculate_next_schedule_time(
                report.schedule_type, 
                report.schedule_config
            )
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': report.to_dict()
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@automation_bp.route('/scheduled-reports/<int:report_id>', methods=['DELETE'])
@token_required
def delete_scheduled_report(current_user, report_id):
    """Delete a scheduled report"""
    try:
        report = ScheduledReport.query.filter_by(
            id=report_id, 
            created_by=current_user.id
        ).first_or_404()
        
        db.session.delete(report)
        db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Alert Rules Routes

@automation_bp.route('/alerts', methods=['GET'])
@token_required
def get_alert_rules(current_user):
    """Get all alert rules for the current user"""
    try:
        alerts = AlertRule.query.filter_by(created_by=current_user.id).all()
        return jsonify({
            'success': True,
            'data': [alert.to_dict() for alert in alerts]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@automation_bp.route('/alerts', methods=['POST'])
@token_required
def create_alert_rule(current_user):
    """Create a new alert rule"""
    try:
        data = request.get_json()
        
        alert = AlertRule(
            name=data['name'],
            description=data.get('description'),
            metric_type=data['metric_type'],
            threshold_config=data['threshold_config'],
            severity=data.get('severity', 'medium'),
            alert_frequency=data.get('alert_frequency', 'immediate'),
            notification_channels=data['notification_channels'],
            notification_config=data.get('notification_config'),
            created_by=current_user.id
        )
        
        db.session.add(alert)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': alert.to_dict()
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@automation_bp.route('/alerts/<int:alert_id>', methods=['PUT'])
@token_required
def update_alert_rule(current_user, alert_id):
    """Update an alert rule"""
    try:
        alert = AlertRule.query.filter_by(
            id=alert_id, 
            created_by=current_user.id
        ).first_or_404()
        
        data = request.get_json()
        
        alert.name = data.get('name', alert.name)
        alert.description = data.get('description', alert.description)
        alert.is_active = data.get('is_active', alert.is_active)
        alert.metric_type = data.get('metric_type', alert.metric_type)
        alert.threshold_config = data.get('threshold_config', alert.threshold_config)
        alert.severity = data.get('severity', alert.severity)
        alert.alert_frequency = data.get('alert_frequency', alert.alert_frequency)
        alert.notification_channels = data.get('notification_channels', alert.notification_channels)
        alert.notification_config = data.get('notification_config', alert.notification_config)
        alert.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': alert.to_dict()
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@automation_bp.route('/alerts/<int:alert_id>', methods=['DELETE'])
@token_required
def delete_alert_rule(current_user, alert_id):
    """Delete an alert rule"""
    try:
        alert = AlertRule.query.filter_by(
            id=alert_id, 
            created_by=current_user.id
        ).first_or_404()
        
        db.session.delete(alert)
        db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Utility Routes

@automation_bp.route('/templates', methods=['GET'])
@token_required
def get_workflow_templates(current_user):
    """Get predefined workflow templates"""
    templates = [
        {
            'id': 'auto_response',
            'name': 'Auto Response Generation',
            'description': 'Automatically generate AI responses for new reviews',
            'trigger_type': 'event',
            'trigger_config': {
                'event': 'new_review',
                'conditions': {
                    'rating_threshold': 3,
                    'platforms': ['Google', 'Yelp']
                }
            },
            'actions': [
                {
                    'type': 'generate_response',
                    'config': {
                        'tone': 'professional',
                        'auto_publish': False
                    }
                }
            ]
        },
        {
            'id': 'weekly_report',
            'name': 'Weekly Performance Report',
            'description': 'Generate and email weekly performance reports',
            'trigger_type': 'schedule',
            'trigger_config': {
                'type': 'cron',
                'expression': '0 9 * * 1',  # Every Monday at 9 AM
                'timezone': 'UTC'
            },
            'actions': [
                {
                    'type': 'generate_report',
                    'config': {
                        'report_type': 'weekly',
                        'format': 'pdf',
                        'email_recipients': []
                    }
                }
            ]
        },
        {
            'id': 'urgent_review_alert',
            'name': 'Urgent Review Alert',
            'description': 'Send alerts for low-rated reviews requiring immediate attention',
            'trigger_type': 'event',
            'trigger_config': {
                'event': 'new_review',
                'conditions': {
                    'rating_max': 2,
                    'sentiment': 'Negative'
                }
            },
            'actions': [
                {
                    'type': 'send_notification',
                    'config': {
                        'channels': ['email', 'in_app'],
                        'priority': 'high',
                        'message_template': 'urgent_review'
                    }
                }
            ]
        }
    ]
    
    return jsonify({
        'success': True,
        'data': templates
    })

@automation_bp.route('/dashboard', methods=['GET'])
@token_required
def get_automation_dashboard(current_user):
    """Get automation dashboard data"""
    try:
        # Get workflow statistics
        total_workflows = Workflow.query.filter_by(created_by=current_user.id).count()
        active_workflows = Workflow.query.filter_by(
            created_by=current_user.id,
            status=WorkflowStatus.ACTIVE
        ).count()
        
        # Get recent tasks
        recent_tasks = WorkflowTask.query.join(Workflow).filter(
            Workflow.created_by == current_user.id
        ).order_by(desc(WorkflowTask.created_at)).limit(10).all()
        
        # Get automation rules statistics
        total_rules = AutomationRule.query.filter_by(created_by=current_user.id).count()
        active_rules = AutomationRule.query.filter_by(
            created_by=current_user.id,
            is_active=True
        ).count()
        
        # Get scheduled reports
        scheduled_reports = ScheduledReport.query.filter_by(
            created_by=current_user.id,
            is_active=True
        ).count()
        
        # Get alert rules
        alert_rules = AlertRule.query.filter_by(
            created_by=current_user.id,
            is_active=True
        ).count()
        
        return jsonify({
            'success': True,
            'data': {
                'statistics': {
                    'total_workflows': total_workflows,
                    'active_workflows': active_workflows,
                    'total_rules': total_rules,
                    'active_rules': active_rules,
                    'scheduled_reports': scheduled_reports,
                    'alert_rules': alert_rules
                },
                'recent_tasks': [task.to_dict() for task in recent_tasks]
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Utility functions

def calculate_next_schedule_time(schedule_type, schedule_config):
    """Calculate the next scheduled execution time"""
    if schedule_type == 'interval':
        interval_minutes = schedule_config.get('interval_minutes', 60)
        return datetime.utcnow() + timedelta(minutes=interval_minutes)
    elif schedule_type == 'cron':
        # For demo purposes, calculate next daily execution
        # In production, use a proper cron parser like croniter
        return datetime.utcnow() + timedelta(days=1)
    else:
        return None

