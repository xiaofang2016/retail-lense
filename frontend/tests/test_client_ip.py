import httpx

from services import api_client
from services.client_ip import pick_client_ip


def test_pick_client_ip_uses_leftmost_public_hop():
    assert pick_client_ip("203.0.113.9") == "203.0.113.9"
    # CloudFront / ALB append their own address on the right (e.g. 15.158.x).
    assert pick_client_ip("8.8.8.8, 15.158.222.198") == "8.8.8.8"


def test_pick_client_ip_prefers_cloudfront_viewer_address():
    assert pick_client_ip("15.158.222.198", viewer_address="8.8.8.8:443") == "8.8.8.8"


def test_pick_client_ip_falls_back_to_private_when_local():
    assert pick_client_ip("127.0.0.1") == "127.0.0.1"
    assert pick_client_ip("", real_ip="10.0.1.4") == "10.0.1.4"


def test_send_sets_x_forwarded_for(monkeypatch):
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["xff"] = request.headers.get("x-forwarded-for", "")
        captured["client"] = request.headers.get("x-retaillen-client-ip", "")
        captured["ua"] = request.headers.get("user-agent", "")
        return httpx.Response(200, json={"ok": True})

    monkeypatch.setattr(api_client, "browser_ip", lambda: "203.0.113.9")
    monkeypatch.setattr(api_client, "browser_user_agent", lambda: "Mozilla/5.0")
    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport, base_url="http://backend") as client:
        api_client._send(client, "GET", "/health")
    assert captured["xff"] == "203.0.113.9"
    assert captured["client"] == "203.0.113.9"
    assert captured["ua"] == "Mozilla/5.0"
