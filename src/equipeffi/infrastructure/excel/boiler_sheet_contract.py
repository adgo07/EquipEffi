"""锅炉19列载体投影；构建、读取、结构校验共用，不含业务算法。"""
COLUMNS = (
    ("A", "序号", "", None, "convenience"), ("B", "设备名称", "", "device_name", "input"),
    ("C", "型号", "", "model", "input"), ("D", "数量", "台", "quantity", "input"),
    ("E", "安装位置", "", "location", "input"), ("F", "锅炉类别", "", "category_id", "input"),
    ("G", "能源/燃料品种", "", "fuel", "input"), ("H", "额定容量（蒸汽t/h；热水MW）", "", "rated_capacity", "input"),
    ("I", "额定压力", "MPa", "rated_pressure_mpa", "input"),
    ("J", "收到基低位发热量", "kJ/kg", "qnet_kj_kg", "input"), ("K", "干燥无灰基挥发分", "%", "vdaf_pct", "input"),
    ("L", "热效率", "%", "efficiency_pct", "input"),
    ("M", "一级热效率限值", "%", "grade_1", "result"), ("N", "二级热效率限值", "%", "grade_2", "result"),
    ("O", "三级热效率限值（低热值生物质填设计值）", "%", "design_limit_pct", "conditional_input"),
    ("P", "评价结论", "", "conclusion", "result"), ("Q", "铭牌照片", "", "photo", "input"),
    ("R", "填表备注", "", "user_note", "input"), ("S", "自动备注", "", "messages", "result"))
INPUT_COLUMNS = frozenset("BCDEFGHIJKLOQR")
RESULT_COLUMNS = frozenset("MNPS")


def column_letter(number):
    """一基列号→OOXML列名，运行时不依赖openpyxl。"""
    result = ""
    while number:
        number, remainder = divmod(number - 1, 26)
        result = chr(65 + remainder) + result
    return result
