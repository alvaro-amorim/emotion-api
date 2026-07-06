def test_index_serves_web_interface(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Audio Emotion API" in response.text
    assert "/static/styles.css" in response.text
    assert "/static/app.js" in response.text
