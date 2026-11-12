from universal_api_orchestrator.normalizer import normalize


def test_normalize_with_jmespath():
    payload = {"data": {"user": {"id": 7, "name": "Ada"}}}
    result = normalize(payload, {"user_id": "data.user.id", "name": "data.user.name"})
    assert result == {"user_id": 7, "name": "Ada"}
