from ...domain.common.models import DeviceDraft, RawDeviceRecord


class CleaningService:
    """清洗流程编排入口；具体规则由设备定义提供。"""

    def clean(self, record: RawDeviceRecord) -> DeviceDraft:
        return DeviceDraft(
            record_id=record.record_id,
            device_type=record.device_type,
            raw_values=dict(record.values),
            normalized_values=dict(record.values),
        )
