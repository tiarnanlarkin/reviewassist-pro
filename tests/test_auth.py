import pytest
import json

def test_register_user(client):
    """Test user registration."""
    response = client.post('/api/auth/register', 
                          json={
                              'email': 'test@example.com',
                              'password': 'TestPass123!',
                              'first_name': 'Test',
                              'last_name': 'User'
                          })
    assert response.status_code == 201
    data = json.loads(response.data)
    assert 'token' in data
    assert data['user']['email'] == 'test@example.com'

def test_login_user(client):
    """Test user login."""
    # First register a user
    client.post('/api/auth/register', 
                json={
                    'email': 'test@example.com',
                    'password': 'TestPass123!',
                    'first_name': 'Test',
                    'last_name': 'User'
                })
    
    # Then login
    response = client.post('/api/auth/login',
                          json={
                              'email': 'test@example.com',
                              'password': 'TestPass123!'
                          })
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'token' in data
    assert data['user']['email'] == 'test@example.com'

def test_invalid_login(client):
    """Test login with invalid credentials."""
    response = client.post('/api/auth/login',
                          json={
                              'email': 'nonexistent@example.com',
                              'password': 'wrongpassword'
                          })
    assert response.status_code == 401

def test_protected_route_without_token(client):
    """Test accessing protected route without token."""
    response = client.get('/api/auth/profile')
    assert response.status_code == 401

def test_protected_route_with_token(client):
    """Test accessing protected route with valid token."""
    # Register and login to get token
    client.post('/api/auth/register', 
                json={
                    'email': 'test@example.com',
                    'password': 'TestPass123!',
                    'first_name': 'Test',
                    'last_name': 'User'
                })
    
    login_response = client.post('/api/auth/login',
                                json={
                                    'email': 'test@example.com',
                                    'password': 'TestPass123!'
                                })
    token = json.loads(login_response.data)['token']
    
    # Access protected route
    response = client.get('/api/auth/profile',
                         headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 200

