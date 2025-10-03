import pytest
import tempfile
import os
from src.main import app
from src.models.user import db

@pytest.fixture
def client():
    """Create a test client for the Flask application."""
    # Create a temporary database file
    db_fd, app.config['DATABASE'] = tempfile.mkstemp()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{app.config['DATABASE']}"
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
        yield client
    
    os.close(db_fd)
    os.unlink(app.config['DATABASE'])

@pytest.fixture
def auth_headers():
    """Create authentication headers for testing."""
    # This would typically create a JWT token for testing
    return {'Authorization': 'Bearer test-token'}

@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        'email': 'test@example.com',
        'name': 'Test User'
    }

@pytest.fixture
def sample_review_data():
    """Sample review data for testing."""
    return {
        'reviewer_name': 'John Doe',
        'platform': 'Google',
        'rating': 5,
        'review_text': 'Great service!',
        'sentiment': 'Positive',
        'status': 'Pending'
    }

