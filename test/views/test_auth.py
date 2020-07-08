from test.fixtures import client

def test_login(client):
    rv = client.get("/login")
    assert b"password" in rv.data
