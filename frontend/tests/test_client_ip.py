import httpx

from services import api_client
from services.client_ip import pick_client_ip


def test_pick_client_ip_uses_alb_appended_hop():
    assert pick_client_ip("203.0.113.9") == "203.0.113.9"
    # Client-supplied spoof on the left; ALB appends the real peer on the right.
    assert pick_client_ip("1.2.3.4, 8.8.8.8") == "8.8.8.8"


def test_pick_client_ip_falls_back_to_private_when_local():
    assert pick_client_ip("127.0.0.1") == "127.0.0.1"
    assert pick_client_ip("", real_ip="10.0.1.4") == "10.0.1.4"


def test_send_sets_x_forwarded_for(monkeypatch):
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["xff"] = request.headers.get("x-forwarded-for", "")
        captured["ua"] = request.headers.get("user-agent", "")
        return httpx.Response(200, json={"ok": True})

    monkeypatch.setattr(api_client, "browser_ip", lambda: "203.0.113.9")
    monkeypatch.setattr(api_client, "browser_user_agent", lambda: "Mozilla/5.0")
    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport, base_url="http://backend") as client:
        api_client._send(client, "GET", "/health")
    assert captured["xff"] == "203.0.113.9"
    assert captured["ua"] == "Mozilla/5.0"
