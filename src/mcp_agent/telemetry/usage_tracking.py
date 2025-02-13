from mcp_agent.config import get_settings


def send_usage_data():
    config = get_settings()
    if not config.usage_telemetry.enabled:
        print("Usage tracking disabled")
        return

    # TODO: saqadri - implement usage tracking
    # data = {"installation_id": str(uuid.uuid4()), "version": "0.1.0"}
    # try:
    #     requests.post("https://telemetry.example.com/usage", json=data, timeout=2)
    # except:
    #     pass
