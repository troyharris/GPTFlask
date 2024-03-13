def test_development_config(test_client):
    test_client.application.config.from_object('app.config.DevelopmentConfig')
    assert test_client.application.config['DEBUG'] is True

def test_production_config(test_client):
    test_client.application.config.from_object('app.config.ProductionConfig')
    assert test_client.application.config['DEBUG'] is False
