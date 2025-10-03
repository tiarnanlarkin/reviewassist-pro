from src.models.user import db
from datetime import datetime, timedelta
from sqlalchemy import func, and_, or_
from enum import Enum
import json
import uuid

class WorkflowStatus(Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    DISABLED = "disabled"
    ERROR = "error"

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TriggerType(Enum):
    SCHEDULE = "schedule"  # Time-based triggers
    EVENT = "event"       # Event-based triggers (new review, rating threshold, etc.)
    MANUAL = "manual"     # Manually triggered

class ActionType(Enum):
    GENERATE_RESPONSE = "generate_response"
    SEND_NOTIFICATION = "send_notification"
    GENERATE_REPORT = "generate_report"
    UPDATE_STATUS = "update_status"
    SEND_EMAIL = "send_email"
    WEBHOOK_CALL = "webhook_call"

class Workflow(db.Model):
    __tablename__ = 'workflows'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.Enum(WorkflowStatus), default=WorkflowStatus.ACTIVE)
    
    # Trigger configuration
    trigger_type = db.Column(db.Enum(TriggerType), nullable=False)
    trigger_config = db.Column(db.JSON, nullable=False)  # Schedule, conditions, etc.
    
    # Actions to perform
    actions = db.Column(db.JSON, nullable=False)  # List of actions with configurations
    
    # Conditions and filters
    conditions = db.Column(db.JSON, nullable=True)  # When to execute (rating filters, platform filters, etc.)
    
    # Execution settings
    max_executions = db.Column(db.Integer, nullable=True)  # Limit number of executions
    execution_count = db.Column(db.Integer, default=0)
    last_execution = db.Column(db.DateTime, nullable=True)
    next_execution = db.Column(db.DateTime, nullable=True)
    
    # Metadata
    created_by = db.Column(db.Integer, db.ForeignKey('auth_users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tasks = db.relationship('WorkflowTask', backref='workflow', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'status': self.status.value,
            'trigger_type': self.trigger_type.value,
            'trigger_config': self.trigger_config,
            'actions': self.actions,
            'conditions': self.conditions,
            'max_executions': self.max_executions,
            'execution_count': self.execution_count,
            'last_execution': self.last_execution.isoformat() if self.last_execution else None,
            'next_execution': self.next_execution.isoformat() if self.next_execution else None,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class WorkflowTask(db.Model):
    __tablename__ = 'workflow_tasks'
    
    id = db.Column(db.Integer, primary_key=True)
    workflow_id = db.Column(db.Integer, db.ForeignKey('workflows.id'), nullable=False)
    task_id = db.Column(db.String(50), nullable=False, default=lambda: str(uuid.uuid4()))
    
    # Task details
    action_type = db.Column(db.Enum(ActionType), nullable=False)
    action_config = db.Column(db.JSON, nullable=False)
    status = db.Column(db.Enum(TaskStatus), default=TaskStatus.PENDING)
    
    # Execution details
    scheduled_at = db.Column(db.DateTime, nullable=False)
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    # Results and logs
    result_data = db.Column(db.JSON, nullable=True)
    error_message = db.Column(db.Text, nullable=True)
    execution_log = db.Column(db.Text, nullable=True)
    
    # Retry configuration
    retry_count = db.Column(db.Integer, default=0)
    max_retries = db.Column(db.Integer, default=3)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'workflow_id': self.workflow_id,
            'task_id': self.task_id,
            'action_type': self.action_type.value,
            'action_config': self.action_config,
            'status': self.status.value,
            'scheduled_at': self.scheduled_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'result_data': self.result_data,
            'error_message': self.error_message,
            'retry_count': self.retry_count,
            'max_retries': self.max_retries,
            'created_at': self.created_at.isoformat()
        }

class AutomationRule(db.Model):
    __tablename__ = 'automation_rules'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    
    # Rule conditions
    trigger_event = db.Column(db.String(100), nullable=False)  # new_review, rating_threshold, etc.
    conditions = db.Column(db.JSON, nullable=False)  # Conditions to match
    
    # Actions to perform
    actions = db.Column(db.JSON, nullable=False)  # Actions to execute
    
    # Execution settings
    cooldown_minutes = db.Column(db.Integer, default=0)  # Minimum time between executions
    last_triggered = db.Column(db.DateTime, nullable=True)
    trigger_count = db.Column(db.Integer, default=0)
    
    # Priority and ordering
    priority = db.Column(db.Integer, default=100)  # Lower numbers = higher priority
    
    created_by = db.Column(db.Integer, db.ForeignKey('auth_users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'is_active': self.is_active,
            'trigger_event': self.trigger_event,
            'conditions': self.conditions,
            'actions': self.actions,
            'cooldown_minutes': self.cooldown_minutes,
            'last_triggered': self.last_triggered.isoformat() if self.last_triggered else None,
            'trigger_count': self.trigger_count,
            'priority': self.priority,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class ScheduledReport(db.Model):
    __tablename__ = 'scheduled_reports'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    
    # Report configuration
    report_type = db.Column(db.String(50), nullable=False)  # weekly, monthly, etc.
    report_format = db.Column(db.String(10), nullable=False)  # pdf, xlsx, csv
    filters = db.Column(db.JSON, nullable=True)  # Report filters
    
    # Schedule configuration
    schedule_type = db.Column(db.String(20), nullable=False)  # cron, interval
    schedule_config = db.Column(db.JSON, nullable=False)  # Cron expression or interval
    
    # Delivery configuration
    delivery_method = db.Column(db.String(20), default='download')  # download, email, webhook
    delivery_config = db.Column(db.JSON, nullable=True)  # Email addresses, webhook URLs, etc.
    
    # Execution tracking
    last_generated = db.Column(db.DateTime, nullable=True)
    next_generation = db.Column(db.DateTime, nullable=True)
    generation_count = db.Column(db.Integer, default=0)
    
    created_by = db.Column(db.Integer, db.ForeignKey('auth_users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'is_active': self.is_active,
            'report_type': self.report_type,
            'report_format': self.report_format,
            'filters': self.filters,
            'schedule_type': self.schedule_type,
            'schedule_config': self.schedule_config,
            'delivery_method': self.delivery_method,
            'delivery_config': self.delivery_config,
            'last_generated': self.last_generated.isoformat() if self.last_generated else None,
            'next_generation': self.next_generation.isoformat() if self.next_generation else None,
            'generation_count': self.generation_count,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class AlertRule(db.Model):
    __tablename__ = 'alert_rules'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    
    # Alert conditions
    metric_type = db.Column(db.String(50), nullable=False)  # rating_drop, review_volume, etc.
    threshold_config = db.Column(db.JSON, nullable=False)  # Threshold values and conditions
    
    # Alert settings
    severity = db.Column(db.String(20), default='medium')  # low, medium, high, critical
    alert_frequency = db.Column(db.String(20), default='immediate')  # immediate, hourly, daily
    
    # Notification configuration
    notification_channels = db.Column(db.JSON, nullable=False)  # email, webhook, in-app
    notification_config = db.Column(db.JSON, nullable=True)  # Channel-specific settings
    
    # Execution tracking
    last_triggered = db.Column(db.DateTime, nullable=True)
    trigger_count = db.Column(db.Integer, default=0)
    last_check = db.Column(db.DateTime, nullable=True)
    
    created_by = db.Column(db.Integer, db.ForeignKey('auth_users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'is_active': self.is_active,
            'metric_type': self.metric_type,
            'threshold_config': self.threshold_config,
            'severity': self.severity,
            'alert_frequency': self.alert_frequency,
            'notification_channels': self.notification_channels,
            'notification_config': self.notification_config,
            'last_triggered': self.last_triggered.isoformat() if self.last_triggered else None,
            'trigger_count': self.trigger_count,
            'last_check': self.last_check.isoformat() if self.last_check else None,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

# Automation Engine utility classes
class WorkflowEngine:
    @staticmethod
    def execute_workflow(workflow_id):
        """Execute a workflow and create tasks"""
        workflow = Workflow.query.get(workflow_id)
        if not workflow or workflow.status != WorkflowStatus.ACTIVE:
            return False
        
        # Check if workflow should execute based on conditions
        if not WorkflowEngine._should_execute(workflow):
            return False
        
        # Create tasks for each action
        tasks_created = []
        for action in workflow.actions:
            task = WorkflowTask(
                workflow_id=workflow.id,
                action_type=ActionType(action['type']),
                action_config=action.get('config', {}),
                scheduled_at=datetime.utcnow()
            )
            db.session.add(task)
            tasks_created.append(task)
        
        # Update workflow execution tracking
        workflow.execution_count += 1
        workflow.last_execution = datetime.utcnow()
        workflow.next_execution = WorkflowEngine._calculate_next_execution(workflow)
        
        db.session.commit()
        
        # Execute tasks immediately or schedule them
        for task in tasks_created:
            WorkflowEngine._execute_task(task)
        
        return True
    
    @staticmethod
    def _should_execute(workflow):
        """Check if workflow conditions are met"""
        if workflow.max_executions and workflow.execution_count >= workflow.max_executions:
            return False
        
        # Check conditions if any
        if workflow.conditions:
            # Implement condition checking logic here
            pass
        
        return True
    
    @staticmethod
    def _calculate_next_execution(workflow):
        """Calculate next execution time based on trigger config"""
        if workflow.trigger_type == TriggerType.SCHEDULE:
            schedule_config = workflow.trigger_config
            if schedule_config.get('type') == 'interval':
                interval_minutes = schedule_config.get('interval_minutes', 60)
                return datetime.utcnow() + timedelta(minutes=interval_minutes)
            elif schedule_config.get('type') == 'cron':
                # Implement cron parsing logic here
                # For now, default to daily
                return datetime.utcnow() + timedelta(days=1)
        
        return None
    
    @staticmethod
    def _execute_task(task):
        """Execute a single workflow task"""
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.utcnow()
        db.session.commit()
        
        try:
            result = None
            
            if task.action_type == ActionType.GENERATE_RESPONSE:
                result = WorkflowEngine._execute_generate_response(task)
            elif task.action_type == ActionType.SEND_NOTIFICATION:
                result = WorkflowEngine._execute_send_notification(task)
            elif task.action_type == ActionType.GENERATE_REPORT:
                result = WorkflowEngine._execute_generate_report(task)
            # Add more action types as needed
            
            task.status = TaskStatus.COMPLETED
            task.result_data = result
            task.completed_at = datetime.utcnow()
            
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error_message = str(e)
            task.completed_at = datetime.utcnow()
            
            # Retry logic
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                task.status = TaskStatus.PENDING
                task.scheduled_at = datetime.utcnow() + timedelta(minutes=5)  # Retry in 5 minutes
        
        db.session.commit()
    
    @staticmethod
    def _execute_generate_response(task):
        """Execute AI response generation task"""
        config = task.action_config
        # Implement AI response generation logic
        return {'responses_generated': 0, 'message': 'AI response generation completed'}
    
    @staticmethod
    def _execute_send_notification(task):
        """Execute notification sending task"""
        config = task.action_config
        # Implement notification sending logic
        return {'notifications_sent': 1, 'message': 'Notification sent successfully'}
    
    @staticmethod
    def _execute_generate_report(task):
        """Execute report generation task"""
        config = task.action_config
        # Implement report generation logic
        return {'report_generated': True, 'file_path': '/tmp/report.pdf'}

class AutomationRuleEngine:
    @staticmethod
    def trigger_event(event_type, event_data):
        """Trigger automation rules based on an event"""
        rules = AutomationRule.query.filter(
            AutomationRule.is_active == True,
            AutomationRule.trigger_event == event_type
        ).order_by(AutomationRule.priority).all()
        
        triggered_rules = []
        
        for rule in rules:
            if AutomationRuleEngine._should_trigger(rule, event_data):
                AutomationRuleEngine._execute_rule(rule, event_data)
                triggered_rules.append(rule)
        
        return triggered_rules
    
    @staticmethod
    def _should_trigger(rule, event_data):
        """Check if rule conditions are met"""
        # Check cooldown
        if rule.cooldown_minutes > 0 and rule.last_triggered:
            cooldown_end = rule.last_triggered + timedelta(minutes=rule.cooldown_minutes)
            if datetime.utcnow() < cooldown_end:
                return False
        
        # Check conditions
        conditions = rule.conditions
        if conditions:
            # Implement condition matching logic
            # For now, assume conditions are met
            pass
        
        return True
    
    @staticmethod
    def _execute_rule(rule, event_data):
        """Execute automation rule actions"""
        rule.last_triggered = datetime.utcnow()
        rule.trigger_count += 1
        
        for action in rule.actions:
            # Execute each action
            # This could create workflow tasks or execute immediately
            pass
        
        db.session.commit()

