"""Configuración pytest del proyecto hospital."""

def pytest_configure(config):
    config.addinivalue_line("markers", "integration: requiere API Docker en localhost:8000")
