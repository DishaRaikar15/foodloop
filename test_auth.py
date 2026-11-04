from backend.auth import register_user, login_user

# Register a test student
user, message = register_user(
    name="Test Student",
    email="teststudent@foodloop.com",
    password="test12345",
    role="student"
)

print("Registration:", message)

# Test login
logged_in_user = login_user(
    "teststudent@foodloop.com",
    "test12345"
)

if logged_in_user:
    print("Login successful!")
    print("User:", logged_in_user)
else:
    print("Login failed!")