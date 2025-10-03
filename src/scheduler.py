import threading
import time
import logging
from datetime import datetime, timedelta
from sqlalchemy import create_engine, func, or_
from sqlalchemy.orm import sessionmaker
from src.models.user import db
from src.models.automation import (
    Workflow, WorkflowTask, AutomationRule, ScheduledReport, AlertRule,
    WorkflowStatus, TaskStatus, TriggerType, WorkflowEngine, AutomationRuleEngine
)
from src.models.review import Review
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AutomationScheduler:
    def __init__(self, app=None):
        self.app = app
        self.running = False
        self.scheduler_thread = None
        self.check_interval = 60  # Check every minute
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize the scheduler with Flask app context"""
        self.app = app
        
        # Create database engine for scheduler
        database_path = os.path.join(os.path.dirname(__file__), 'database', 'app.db')
        self.engine = create_engine(f'sqlite:///{database_path}')
        self.Session = sessionmaker(bind=self.engine)
    
    def start(self):
        """Start the background scheduler"""
        if self.running:
            logger.warning("Scheduler is already running")
            return
        
        self.running = True
        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        logger.info("Automation scheduler started")
    
    def stop(self):
        """Stop the background scheduler"""
        self.running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        logger.info("Automation scheduler stopped")
    
    def _run_scheduler(self):
        """Main scheduler loop"""
        logger.info("Scheduler loop started")
        
        while self.running:
            try:
                with self.app.app_context():
                    session = self.Session()
                    try:
                        # Check for scheduled workflows
                        self._check_scheduled_workflows(session)
                        
                        # Check for pending tasks
                        self._process_pending_tasks(session)
                        
                        # Check for scheduled reports
                        self._check_scheduled_reports(session)
                        
                        # Check alert rules
                        self._check_alert_rules(session)
                        
                        # Clean up old completed tasks
                        self._cleanup_old_tasks(session)
                        
                        session.commit()
                        
                    except Exception as e:
                        logger.error(f"Error in scheduler loop: {e}")
                        session.rollback()
                    finally:
                        session.close()
                
                # Sleep for the check interval
                time.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Critical error in scheduler: {e}")
                time.sleep(self.check_interval)
    
    def _check_scheduled_workflows(self, session):
        """Check for workflows that need to be executed"""
        now = datetime.utcnow()
        
        # Find workflows that are due for execution
        due_workflows = session.query(Workflow).filter(
            Workflow.status == WorkflowStatus.ACTIVE,
            Workflow.trigger_type == TriggerType.SCHEDULE,
            Workflow.next_execution <= now
        ).all()
        
        for workflow in due_workflows:
            try:
                logger.info(f"Executing scheduled workflow: {workflow.name}")
                
                # Execute the workflow
                success = WorkflowEngine.execute_workflow(workflow.id)
                
                if success:
                    logger.info(f"Workflow {workflow.name} executed successfully")
                else:
                    logger.warning(f"Workflow {workflow.name} execution failed or skipped")
                
            except Exception as e:
                logger.error(f"Error executing workflow {workflow.name}: {e}")
    
    def _process_pending_tasks(self, session):
        """Process pending workflow tasks"""
        now = datetime.utcnow()
        
        # Find tasks that are ready to be executed
        pending_tasks = session.query(WorkflowTask).filter(
            WorkflowTask.status == TaskStatus.PENDING,
            WorkflowTask.scheduled_at <= now
        ).limit(10).all()  # Process up to 10 tasks at a time
        
        for task in pending_tasks:
            try:
                logger.info(f"Processing task {task.task_id} for workflow {task.workflow_id}")
                WorkflowEngine._execute_task(task)
                
            except Exception as e:
                logger.error(f"Error processing task {task.task_id}: {e}")
    
    def _check_scheduled_reports(self, session):
        """Check for scheduled reports that need to be generated"""
        now = datetime.utcnow()
        
        # Find reports that are due for generation
        due_reports = session.query(ScheduledReport).filter(
            ScheduledReport.is_active == True,
            ScheduledReport.next_generation <= now
        ).all()
        
        for report in due_reports:
            try:
                logger.info(f"Generating scheduled report: {report.name}")
                
                # Create a workflow task for report generation
                task = WorkflowTask(
                    workflow_id=None,  # Not associated with a specific workflow
                    action_type='generate_report',
                    action_config={
                        'report_type': report.report_type,
                        'format': report.report_format,
                        'filters': report.filters,
                        'delivery_method': report.delivery_method,
                        'delivery_config': report.delivery_config
                    },
                    scheduled_at=now
                )
                
                session.add(task)
                
                # Update report tracking
                report.last_generated = now
                report.generation_count += 1
                report.next_generation = self._calculate_next_report_time(report)
                
                logger.info(f"Scheduled report {report.name} queued for generation")
                
            except Exception as e:
                logger.error(f"Error scheduling report {report.name}: {e}")
    
    def _check_alert_rules(self, session):
        """Check alert rules and trigger notifications if needed"""
        now = datetime.utcnow()
        
        # Find active alert rules that haven't been checked recently
        alert_rules = session.query(AlertRule).filter(
            AlertRule.is_active == True,
            or_(
                AlertRule.last_check.is_(None),
                AlertRule.last_check <= now - timedelta(minutes=5)  # Check every 5 minutes
            )
        ).all()
        
        for rule in alert_rules:
            try:
                logger.debug(f"Checking alert rule: {rule.name}")
                
                # Check if alert conditions are met
                should_alert = self._evaluate_alert_rule(rule, session)
                
                if should_alert:
                    logger.info(f"Alert rule triggered: {rule.name}")
                    
                    # Create notification task
                    task = WorkflowTask(
                        workflow_id=None,
                        action_type='send_notification',
                        action_config={
                            'alert_rule_id': rule.id,
                            'channels': rule.notification_channels,
                            'config': rule.notification_config,
                            'severity': rule.severity
                        },
                        scheduled_at=now
                    )
                    
                    session.add(task)
                    
                    # Update rule tracking
                    rule.last_triggered = now
                    rule.trigger_count += 1
                
                # Update last check time
                rule.last_check = now
                
            except Exception as e:
                logger.error(f"Error checking alert rule {rule.name}: {e}")
    
    def _evaluate_alert_rule(self, rule, session):
        """Evaluate if an alert rule should be triggered"""
        try:
            threshold_config = rule.threshold_config
            metric_type = rule.metric_type
            
            if metric_type == 'rating_drop':
                # Check for significant rating drops
                recent_avg = self._get_recent_average_rating(session, days=1)
                previous_avg = self._get_recent_average_rating(session, days=7, offset_days=1)
                
                if recent_avg and previous_avg:
                    drop_threshold = threshold_config.get('drop_threshold', 0.5)
                    if previous_avg - recent_avg >= drop_threshold:
                        return True
            
            elif metric_type == 'review_volume':
                # Check for unusual review volume
                recent_count = self._get_recent_review_count(session, hours=1)
                threshold = threshold_config.get('volume_threshold', 10)
                
                if recent_count >= threshold:
                    return True
            
            elif metric_type == 'negative_sentiment':
                # Check for high negative sentiment
                negative_ratio = self._get_recent_negative_ratio(session, hours=24)
                threshold = threshold_config.get('negative_ratio_threshold', 0.3)
                
                if negative_ratio >= threshold:
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error evaluating alert rule {rule.name}: {e}")
            return False
    
    def _get_recent_average_rating(self, session, days=1, offset_days=0):
        """Get average rating for recent period"""
        end_date = datetime.utcnow() - timedelta(days=offset_days)
        start_date = end_date - timedelta(days=days)
        
        result = session.query(func.avg(Review.rating)).filter(
            Review.created_at >= start_date,
            Review.created_at <= end_date
        ).scalar()
        
        return float(result) if result else None
    
    def _get_recent_review_count(self, session, hours=1):
        """Get review count for recent period"""
        start_time = datetime.utcnow() - timedelta(hours=hours)
        
        count = session.query(Review).filter(
            Review.created_at >= start_time
        ).count()
        
        return count
    
    def _get_recent_negative_ratio(self, session, hours=24):
        """Get ratio of negative reviews in recent period"""
        start_time = datetime.utcnow() - timedelta(hours=hours)
        
        total_reviews = session.query(Review).filter(
            Review.created_at >= start_time
        ).count()
        
        if total_reviews == 0:
            return 0
        
        negative_reviews = session.query(Review).filter(
            Review.created_at >= start_time,
            Review.sentiment == 'Negative'
        ).count()
        
        return negative_reviews / total_reviews
    
    def _calculate_next_report_time(self, report):
        """Calculate next report generation time"""
        if report.schedule_type == 'interval':
            interval_hours = report.schedule_config.get('interval_hours', 24)
            return datetime.utcnow() + timedelta(hours=interval_hours)
        elif report.schedule_type == 'cron':
            # For demo purposes, schedule daily
            # In production, use a proper cron parser
            return datetime.utcnow() + timedelta(days=1)
        else:
            return None
    
    def _cleanup_old_tasks(self, session):
        """Clean up old completed tasks"""
        cutoff_date = datetime.utcnow() - timedelta(days=7)  # Keep tasks for 7 days
        
        old_tasks = session.query(WorkflowTask).filter(
            WorkflowTask.status.in_([TaskStatus.COMPLETED, TaskStatus.FAILED]),
            WorkflowTask.completed_at < cutoff_date
        ).all()
        
        for task in old_tasks:
            session.delete(task)
        
        if old_tasks:
            logger.info(f"Cleaned up {len(old_tasks)} old tasks")

# Global scheduler instance
scheduler = AutomationScheduler()

def init_scheduler(app):
    """Initialize and start the scheduler"""
    scheduler.init_app(app)
    scheduler.start()
    return scheduler

def stop_scheduler():
    """Stop the scheduler"""
    scheduler.stop()

