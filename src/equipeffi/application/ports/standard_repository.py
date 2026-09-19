from typing import Any, Protocol


class StandardRepository(Protocol):
    def get_pack(self, device_type: str, pack_id: str | None = None) -> dict[str, Any]: ...

    def find(self, device_type: str, criteria: dict[str, Any]) -> list[dict[str, Any]]: ...
