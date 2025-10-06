import pytest
from src.main import create_app
from src.models.customer_success import HelpCategory, HelpArticle, SupportTicket, TicketMessage, LiveChatSession, ChatMessage, VideoTutorial, OnboardingProgress, CustomerHealthScore, CustomerHealthStatus, ArticleStatus
from src.models.auth import AuthUser, UserRole
from datetime import datetime

# The db fixture is now provided by conftest.py

def test_get_help_categories(client, db):
    response = client.get("/customer-success/help/categories")
    assert response.status_code == 200
    assert len(response.json["categories"]) == 1

def test_get_help_articles(client, db):
    response = client.get("/customer-success/help/articles")
    assert response.status_code == 200
    assert len(response.json["articles"]) == 1

def test_get_help_article(client, db):
    response = client.get("/customer-success/help/articles/test-article")
    assert response.status_code == 200
    assert response.json["article"]["title"] == "Test Article"

def test_create_support_ticket(client, db):
    user = db.session.query(AuthUser).first()
    response = client.post("/api/auth/login", json={"email": user.email, "password": "password"})
    token = response.json["access_token"]

    response = client.post("/customer-success/support/tickets", headers={"Authorization": f"Bearer {token}"}, json={"subject": "Test Ticket", "description": "Test description"})
    assert response.status_code == 201
    assert response.json["ticket"]["subject"] == "Test Ticket"

def test_get_support_tickets(client, db):
    user = db.session.query(AuthUser).first()
    response = client.post("/api/auth/login", json={"email": user.email, "password": "password"})
    token = response.json["access_token"]

    response = client.get("/customer-success/support/tickets", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert len(response.json["tickets"]) > 0

def test_start_chat_session(client, db):
    response = client.post("/customer-success/chat/sessions", json={"visitor_name": "Test Visitor", "visitor_email": "visitor@example.com", "subject": "Chat Inquiry"})
    assert response.status_code == 201
    assert response.json["session"]["visitor_name"] == "Test Visitor"

def test_send_chat_message(client, db):
    session_response = client.post("/customer-success/chat/sessions", json={"visitor_name": "Test Visitor", "visitor_email": "visitor@example.com", "subject": "Chat Inquiry"})
    session_id = session_response.json["session"]["session_id"]

    message_response = client.post(f"/customer-success/chat/sessions/{session_id}/messages", json={"sender_type": "visitor", "sender_name": "Test Visitor", "message": "Hello, I have a question."})
    assert message_response.status_code == 201
    assert message_response.json["message"]["message"] == "Hello, I have a question."

def test_get_chat_messages(client, db):
    session_response = client.post("/customer-success/chat/sessions", json={"visitor_name": "Test Visitor", "visitor_email": "visitor@example.com", "subject": "Chat Inquiry"})
    session_id = session_response.json["session"]["session_id"]

    client.post(f"/customer-success/chat/sessions/{session_id}/messages", json={"sender_type": "visitor", "sender_name": "Test Visitor", "message": "Hello, I have a question."})
    client.post(f"/customer-success/chat/sessions/{session_id}/messages", json={"sender_type": "agent", "sender_name": "Support Agent", "message": "How can I help you?"})

    messages_response = client.get(f"/customer-success/chat/sessions/{session_id}/messages")
    assert messages_response.status_code == 200
    assert len(messages_response.json["messages"]) == 2

def test_get_video_tutorials(client, db):
    response = client.get("/customer-success/tutorials/videos")
    assert response.status_code == 200
    assert len(response.json["videos"]) > 0

def test_update_video_progress(client, db):
    user = db.session.query(AuthUser).first()
    response = client.post("/api/auth/login", json={"email": user.email, "password": "password"})
    token = response.json["access_token"]

    video = db.session.query(VideoTutorial).first()
    response = client.post(f"/customer-success/tutorials/videos/{video.id}/progress", headers={"Authorization": f"Bearer {token}"}, json={"progress_seconds": 60, "completion_percentage": 20, "completed": False})
    assert response.status_code == 200
    assert response.json["progress"]["progress_seconds"] == 60

def test_admin_create_help_category(client, db):
    admin_user = db.session.query(AuthUser).filter_by(role=UserRole.ADMIN).first()
    response = client.post("/api/auth/login", json={"email": admin_user.email, "password": "password"})
    token = response.json["access_token"]

    new_category_data = {
        "name": "New Admin Category",
        "description": "Description for new admin category",
        "icon": "new-icon",
        "color": "#FFFFFF",
        "sort_order": 10,
        "is_active": True
    }
    response = client.post("/customer-success/admin/help/categories", headers={"Authorization": f"Bearer {token}"}, json=new_category_data)
    assert response.status_code == 201
    assert response.json["category"]["name"] == "New Admin Category"

def test_admin_update_help_category(client, db):
    admin_user = db.session.query(AuthUser).filter_by(role=UserRole.ADMIN).first()
    response = client.post("/api/auth/login", json={"email": admin_user.email, "password": "password"})
    token = response.json["access_token"]

    category = db.session.query(HelpCategory).filter_by(name="Test Category").first()
    updated_category_data = {
        "name": "Updated Test Category",
        "description": "Updated description",
        "is_active": False
    }
    response = client.put(f"/customer-success/admin/help/categories/{category.id}", headers={"Authorization": f"Bearer {token}"}, json=updated_category_data)
    assert response.status_code == 200
    assert response.json["category"]["name"] == "Updated Test Category"
    assert response.json["category"]["is_active"] == False

def test_admin_delete_help_category(client, db):
    admin_user = db.session.query(AuthUser).filter_by(role=UserRole.ADMIN).first()
    response = client.post("/api/auth/login", json={"email": admin_user.email, "password": "password"})
    token = response.json["access_token"]

    category = HelpCategory(name="Category to Delete", slug="category-to-delete")
    db.session.add(category)
    db.session.commit()

    response = client.delete(f"/customer-success/admin/help/categories/{category.id}", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 204
    assert db.session.query(HelpCategory).get(category.id) is None

def test_admin_create_help_article(client, db):
    admin_user = db.session.query(AuthUser).filter_by(role=UserRole.ADMIN).first()
    response = client.post("/api/auth/login", json={"email": admin_user.email, "password": "password"})
    token = response.json["access_token"]

    category = db.session.query(HelpCategory).first()
    new_article_data = {
        "title": "New Admin Article",
        "content": "Content for new admin article",
        "category_id": category.id,
        "status": "published",
        "featured": True
    }
    response = client.post("/customer-success/admin/help/articles", headers={"Authorization": f"Bearer {token}"}, json=new_article_data)
    assert response.status_code == 201
    assert response.json["article"]["title"] == "New Admin Article"
    assert response.json["article"]["status"] == "published"

def test_admin_update_help_article(client, db):
    admin_user = db.session.query(AuthUser).filter_by(role=UserRole.ADMIN).first()
    response = client.post("/api/auth/login", json={"email": admin_user.email, "password": "password"})
    token = response.json["access_token"]

    article = db.session.query(HelpArticle).filter_by(title="Test Article").first()
    updated_article_data = {
        "title": "Updated Test Article",
        "content": "Updated content",
        "status": "archived",
        "featured": False
    }
    response = client.put(f"/customer-success/admin/help/articles/{article.id}", headers={"Authorization": f"Bearer {token}"}, json=updated_article_data)
    assert response.status_code == 200
    assert response.json["article"]["title"] == "Updated Test Article"
    assert response.json["article"]["status"] == "archived"

def test_admin_delete_help_article(client, db):
    admin_user = db.session.query(AuthUser).filter_by(role=UserRole.ADMIN).first()
    response = client.post("/api/auth/login", json={"email": admin_user.email, "password": "password"})
    token = response.json["access_token"]

    category = db.session.query(HelpCategory).first()
    article = HelpArticle(title="Article to Delete", slug="article-to-delete", content="Content", category_id=category.id, author_id=admin_user.id)
    db.session.add(article)
    db.session.commit()

    response = client.delete(f"/customer-success/admin/help/articles/{article.id}", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 204
    assert db.session.query(HelpArticle).get(article.id) is None

def test_get_customer_health_score(client, db):
    user = db.session.query(AuthUser).first()
    response = client.post("/api/auth/login", json={"email": user.email, "password": "password"})
    token = response.json["access_token"]

    response = client.get("/customer-success/success/health-score", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json["success"] == True
    assert response.json["health_score"] is not None

def test_get_onboarding_progress(client, db):
    user = db.session.query(AuthUser).first()
    response = client.post("/api/auth/login", json={"email": user.email, "password": "password"})
    token = response.json["access_token"]

    # Create a sample onboarding step for the user
    onboarding_step = OnboardingProgress(user_id=user.id, step_name="Welcome Tour", step_category="setup", completed=False)
    db.session.add(onboarding_step)
    db.session.commit()

    response = client.get("/customer-success/success/onboarding-progress", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json["success"] == True
    assert len(response.json["onboarding_progress"]) > 0
    assert response.json["overall_completion"] == 0.0

def test_update_onboarding_progress(client, db):
    user = db.session.query(AuthUser).first()
    response = client.post("/api/auth/login", json={"email": user.email, "password": "password"})
    token = response.json["access_token"]

    onboarding_step = OnboardingProgress(user_id=user.id, step_name="Complete Profile", step_category="setup", completed=False)
    db.session.add(onboarding_step)
    db.session.commit()

    update_data = {"completed": True, "completion_percentage": 100}
    response = client.put(f"/customer-success/success/onboarding-progress/{onboarding_step.id}", headers={"Authorization": f"Bearer {token}"}, json=update_data)
    assert response.status_code == 200
    assert response.json["onboarding_progress"]["completed"] == True
    assert response.json["onboarding_progress"]["completion_percentage"] == 100

def test_admin_create_onboarding_step(client, db):
    admin_user = db.session.query(AuthUser).filter_by(role=UserRole.ADMIN).first()
    response = client.post("/api/auth/login", json={"email": admin_user.email, "password": "password"})
    token = response.json["access_token"]

    user = db.session.query(AuthUser).first()
    new_step_data = {
        "user_id": user.id,
        "step_name": "Admin Created Step",
        "step_category": "tutorial",
        "completed": False
    }
    response = client.post("/customer-success/admin/onboarding-progress", headers={"Authorization": f"Bearer {token}"}, json=new_step_data)
    assert response.status_code == 201
    assert response.json["onboarding_step"]["step_name"] == "Admin Created Step"

def test_admin_update_onboarding_step(client, db):
    admin_user = db.session.query(AuthUser).filter_by(role=UserRole.ADMIN).first()
    response = client.post("/api/auth/login", json={"email": admin_user.email, "password": "password"})
    token = response.json["access_token"]

    user = db.session.query(AuthUser).first()
    onboarding_step = OnboardingProgress(user_id=user.id, step_name="Step to Update", step_category="setup", completed=False)
    db.session.add(onboarding_step)
    db.session.commit()

    update_data = {"completed": True, "completion_percentage": 50}
    response = client.put(f"/customer-success/admin/onboarding-progress/{onboarding_step.id}", headers={"Authorization": f"Bearer {token}"}, json=update_data)
    assert response.status_code == 200
    assert response.json["onboarding_step"]["completed"] == True
    assert response.json["onboarding_step"]["completion_percentage"] == 50

def test_admin_delete_onboarding_step(client, db):
    admin_user = db.session.query(AuthUser).filter_by(role=UserRole.ADMIN).first()
    response = client.post("/api/auth/login", json={"email": admin_user.email, "password": "password"})
    token = response.json["access_token"]

    user = db.session.query(AuthUser).first()
    onboarding_step = OnboardingProgress(user_id=user.id, step_name="Step to Delete", step_category="setup", completed=False)
    db.session.add(onboarding_step)
    db.session.commit()

    response = client.delete(f"/customer-success/admin/onboarding-progress/{onboarding_step.id}", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 204
    assert db.session.query(OnboardingProgress).get(onboarding_step.id) is None

def test_admin_create_customer_health_score(client, db):
    admin_user = db.session.query(AuthUser).filter_by(role=UserRole.ADMIN).first()
    response = client.post("/api/auth/login", json={"email": admin_user.email, "password": "password"})
    token = response.json["access_token"]

    user = db.session.query(AuthUser).first()
    new_health_score_data = {
        "user_id": user.id,
        "overall_score": 85.5,
        "status": "healthy",
        "login_frequency_score": 90,
        "feature_adoption_score": 80
    }
    response = client.post("/customer-success/admin/success/health-score", headers={"Authorization": f"Bearer {token}"}, json=new_health_score_data)
    assert response.status_code == 201
    assert response.json["health_score"]["overall_score"] == 85.5

def test_admin_update_customer_health_score(client, db):
    admin_user = db.session.query(AuthUser).filter_by(role=UserRole.ADMIN).first()
    response = client.post("/api/auth/login", json={"email": admin_user.email, "password": "password"})
    token = response.json["access_token"]

    user = db.session.query(AuthUser).first()
    health_score = CustomerHealthScore(user_id=user.id, overall_score=70, status=CustomerHealthStatus.AT_RISK)

    db.session.add(health_score)
    db.session.commit()

    update_data = {"overall_score": 90, "status": "healthy"}
    response = client.put(f"/customer-success/admin/success/health-score/{health_score.id}", headers={"Authorization": f"Bearer {token}"}, json=update_data)
    assert response.status_code == 200
    assert response.json["health_score"]["overall_score"] == 90
    assert response.json["health_score"]["status"] == "healthy"

def test_admin_delete_customer_health_score(client, db):
    admin_user = db.session.query(AuthUser).filter_by(role=UserRole.ADMIN).first()
    response = client.post("/api/auth/login", json={"email": admin_user.email, "password": "password"})
    token = response.json["access_token"]

    user = db.session.query(AuthUser).first()
    health_score = CustomerHealthScore(user_id=user.id, overall_score=60, status=CustomerHealthStatus.CRITICAL)

    db.session.add(health_score)
    db.session.commit()

    response = client.delete(f"/customer-success/admin/success/health-score/{health_score.id}", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 204
    assert db.session.query(CustomerHealthScore).get(health_score.id) is None

def test_admin_trigger_health_score_calculation(client, db):
    admin_user = db.session.query(AuthUser).filter_by(role=UserRole.ADMIN).first()
    response = client.post("/api/auth/login", json={"email": admin_user.email, "password": "password"})
    token = response.json["access_token"]

    response = client.post("/customer-success/admin/success/calculate-health-scores", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json["success"] == True
    assert response.json["message"] == "Customer health scores calculation triggered"

