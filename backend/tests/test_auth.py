def test_register_login(client):
    r=client.post('/api/v1/auth/register',json={'email':'test@example.com','password':'password123'})
    assert r.status_code==200 and 'access_token' in r.json()
    r=client.post('/api/v1/auth/login',json={'email':'test@example.com','password':'password123'})
    assert r.status_code==200
