from app.model import Users

def test_new_user(test_client):
    user = Users(username='testuser', password='password123', email='test@test.com')
    assert user.username == 'testuser'