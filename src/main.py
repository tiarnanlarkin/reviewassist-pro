import os
from datetime import datetime, timedelta
from flask import Flask, send_from_directory
from flask_cors import CORS
from src.models.user import db, User
from src.models.review import Review
from src.models.realtime import RealtimeNotification, UserActivity, LiveMetrics, ConnectedUser
from src.models.subscription import SubscriptionPlan, PlanFeature, UserSubscription, FeatureUsage
from src.routes.user import user_bp
from src.routes.review import review_bp
from src.routes.auth import auth_bp
from src.routes.subscription import subscription_bp
from src.models.integrations import Integration, WebhookEndpoint, APIKey, IntegrationSyncLog
from src.routes.integrations import integrations_bp
from src.models.onboarding import (
    UserOnboarding, UserTourProgress, DashboardLayout, UserPreferences,
    FeatureAnnouncement, UserAnnouncementView, OnboardingManager
)
from src.routes.onboarding import onboarding_bp
from src.models.advanced_analytics import (
    DashboardWidget, CustomDashboard, CustomReport, ReportExecution,
    DataVisualization, PerformanceMetric, MetricValue, AnalyticsInsight
)
from src.routes.advanced_analytics import advanced_analytics_bp
from src.routes.payments import payments_bp
from src.models.auth import AuthUser, UserRole
from src.routes.realtime import socketio

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
app.config['SECRET_KEY'] = 'reviewassist_pro_enhanced_secret_key_2025'

# Enable CORS for all routes
CORS(app, origins="*")

# Initialize SocketIO with the app
socketio.init_app(app, cors_allowed_origins="*", async_mode='threading')

# Register blueprints
app.register_blueprint(user_bp, url_prefix='/api')
app.register_blueprint(review_bp, url_prefix='/api')
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(subscription_bp, url_prefix='/api/subscription')
app.register_blueprint(integrations_bp, url_prefix='/api/integrations')
app.register_blueprint(onboarding_bp, url_prefix='/api/onboarding')
app.register_blueprint(advanced_analytics_bp, url_prefix='/api/advanced-analytics')
app.register_blueprint(payments_bp, url_prefix='/api/payments')

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'database', 'app.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db.init_app(app)

with app.app_context():
    # Create database directory if it doesn't exist
    db_dir = os.path.join(os.path.dirname(__file__), 'database')
    os.makedirs(db_dir, exist_ok=True)
    
    # Create all tables
    db.create_all()
    
    print("Starting ReviewAssist Pro Enhanced with real-time features...")

def seed_demo_data():
    """Seed the database with demo data"""
    try:
        # Check if data already exists
        if Review.query.first():
            return
        
        # Sample reviews data
        reviews_data = [
            {
                'reviewer_name': 'John Smith',
                'platform': 'Google',
                'rating': 5,
                'review_text': 'Excellent service! The team was professional and delivered exactly what we needed. Highly recommend!',
                'sentiment': 'Positive',
                'status': 'Responded',
                'response_time': '2.1h',
                'created_at': datetime.utcnow() - timedelta(days=1)
            },
            {
                'reviewer_name': 'Sarah Johnson',
                'platform': 'Yelp',
                'rating': 4,
                'review_text': 'Great experience overall. The staff was friendly and helpful. Minor delay in delivery but worth the wait.',
                'sentiment': 'Positive',
                'status': 'Responded',
                'response_time': '1.8h',
                'created_at': datetime.utcnow() - timedelta(days=2)
            },
            {
                'reviewer_name': 'Mike Wilson',
                'platform': 'Facebook',
                'rating': 2,
                'review_text': 'Service was below expectations. Had to wait too long and the final result was not what was promised.',
                'sentiment': 'Negative',
                'status': 'Urgent',
                'response_time': '4.2h',
                'created_at': datetime.utcnow() - timedelta(hours=6)
            }
        ]
        
        for review_data in reviews_data:
            review = Review(**review_data)
            db.session.add(review)
        
        # Add more sample reviews for better demo
        import random
        platforms = ['Google', 'Yelp', 'Facebook', 'TripAdvisor']
        sentiments = ['Positive', 'Negative', 'Neutral']
        statuses = ['Responded', 'Pending', 'Urgent']
        
        for i in range(244):  # Add 244 more to reach 247 total
            review = Review(
                reviewer_name=f'Customer {i+4}',
                platform=random.choice(platforms),
                rating=random.randint(1, 5),
                review_text=f'Sample review text {i+4}',
                sentiment=random.choice(sentiments),
                status=random.choice(statuses),
                response_time=f'{random.uniform(0.5, 8.0):.1f}h',
                created_at=datetime.utcnow() - timedelta(days=random.randint(0, 30))
            )
            db.session.add(review)
        
        db.session.commit()
        print("Demo data seeded successfully!")
        
    except Exception as e:
        print(f"Error seeding demo data: {e}")

def seed_auth_data():
    """Seed authentication data"""
    try:
        # Check if auth users already exist
        if AuthUser.query.first():
            return
        
        # Create demo users
        demo_users = [
            {
                'email': 'admin@reviewassist.com',
                'password': 'Admin123!',
                'first_name': 'Admin',
                'last_name': 'User',
                'role': UserRole.ADMIN
            },
            {
                'email': 'manager@reviewassist.com',
                'password': 'Manager123!',
                'first_name': 'Manager',
                'last_name': 'User',
                'role': UserRole.MANAGER
            },
            {
                'email': 'agent@reviewassist.com',
                'password': 'Agent123!',
                'first_name': 'Agent',
                'last_name': 'User',
                'role': UserRole.AGENT
            }
        ]
        
        for user_data in demo_users:
            user = AuthUser(
                email=user_data['email'],
                first_name=user_data['first_name'],
                last_name=user_data['last_name'],
                role=user_data['role']
            )
            user.set_password(user_data['password'])
            db.session.add(user)
        
        db.session.commit()
        print("Authentication data seeded successfully!")
    except Exception as e:
        print(f"Error seeding auth data: {e}")

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    static_folder_path = app.static_folder
    if static_folder_path is None:
        return "Static folder not configured", 404

    if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
        return send_from_directory(static_folder_path, path)
    else:
        index_path = os.path.join(static_folder_path, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(static_folder_path, 'index.html')
        else:
            return "index.html not found", 404

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return {
        'status': 'healthy',
        'app': 'ReviewAssist Pro Enhanced',
        'version': '2.0.0',
        'demo_mode': os.getenv('DEMO_MODE', 'false')
    }

if __name__ == '__main__':
    with app.app_context():
        # Seed demo data
        seed_demo_data()
        seed_auth_data()
    
    print("Starting ReviewAssist Pro Enhanced with real-time features...")
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)

