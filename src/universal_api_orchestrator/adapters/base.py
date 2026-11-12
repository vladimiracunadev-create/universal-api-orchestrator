from abc import ABC, abstractmethod
from typing import Any


class Adapter(ABC):
    @abstractmethod
    async def execute(
        self,
        system: dict[str, Any],
        operation: dict[str, Any],
        params: dict[str, Any],
        headers: dict[str, str],
    ) -> tuple[int | None, Any]: ...
