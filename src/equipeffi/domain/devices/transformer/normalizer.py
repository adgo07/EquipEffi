from typing import Any

from ...common.models import DeviceDraft


class TransformerNormalizer:
    """变压器标准化入口；暂不迁移旧清洗规则。"""

    def normalize(self, draft: DeviceDraft) -> DeviceDraft:
        return draft

    def normalize_values(self, values: dict[str, Any]) -> dict[str, Any]:
        return dict(values)
