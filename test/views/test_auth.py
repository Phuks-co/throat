from test.fixtures import client

# This is intended as a sample first test, not a real test of login
# functionality. All it does is check that somewhere in the login page
# is the string "password".
def test_login(client):
    """The login page mentions passwords."""
    rv = client.get("/login")
    assert b"password" in rv.data
