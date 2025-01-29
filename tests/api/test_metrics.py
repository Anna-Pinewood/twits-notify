def test_metrics_endpoint(client):
    """Test metrics endpoint returns prometheus metrics."""
    # Make some requests to generate metrics
    client.get("/health")
    client.get("/summary")
    
    # Get metrics
    response = client.get("/metrics")
    
    assert response.status_code == 200
    metrics_text = response.text
    
    # Check if our custom metrics are present
    assert 'requests_total{' in metrics_text
    assert 'request_duration_seconds' in metrics_text
    assert 'endpoint="/health"' in metrics_text
    assert 'endpoint="/summary"' in metrics_text
