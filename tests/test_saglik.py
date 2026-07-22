"""/health endpoint testi — deploy sonrası canlılık kontrolü."""

from __future__ import annotations


def test_health_200_saglikli(client):
    # Act
    yanit = client.get("/health")
    # Assert: 200 ve beklenen gövde
    assert yanit.status_code == 200
    assert yanit.json() == {"durum": "saglikli"}
