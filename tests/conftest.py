
import pytest
from src.main import create_app
from src.models.user import db as _db
from src.models.auth import AuthUser, UserRole
from src.models.customer_success import HelpCategory, HelpArticle, VideoTutorial, ArticleStatus

@pytest.fixture(scope="module")
def app():
    app = create_app("config.TestConfig")
    with app.app_context():
        _db.create_all()
        # Create a user
        user = AuthUser(email="test@example.com", first_name="Test", last_name="User", role=UserRole.ADMIN)

        user.set_password("password")
        _db.session.add(user)
        _db.session.commit()

        # Create a help category
        category = HelpCategory(name="Test Category", slug="test-category")
        _db.session.add(category)
        _db.session.commit()

        # Create a help article
        article = HelpArticle(title="Test Article", slug="test-article", content="Test content", category_id=category.id, author_id=user.id, status=ArticleStatus.PUBLISHED, is_active=True)


        _db.session.add(article)
        _db.session.commit()

        # Create a video tutorial
        video = VideoTutorial(title="Test Video", description="Test Description", video_url="http://example.com/video.mp4", category="General", difficulty_level="easy", is_active=True)

        _db.session.add(video)
        _db.session.commit()

        yield app
        _db.session.remove()
        _db.drop_all()

@pytest.fixture(scope="module")
def client(app):
    return app.test_client()

@pytest.fixture(scope="module")
def db(app):
    return _db

