from typing import Any

import jmespath


def normalize(payload: Any, mapping: dict[str, str] | None) -> Any:
    if not mapping:
        return payload
    return {key: jmespath.search(expression, payload) for key, expression in mapping.items()}
