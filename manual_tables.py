# 手动补齐表格配置
# 用于存储从 Word 文档中提取的高质量表格数据
# 格式: {标准代号: {表格标题: 表格内容}}

# Word提取的表格文件路径
WORD_TABLE_FILES = {
    "JTG_F80_1": "JTG_F80_1-2017_tables.md",
    "TB10753": "TB10753-2018_tables.md",
    "TB10417": "TB10417-2018_tables.md",
}

MANUAL_TABLES = {
    # TB10417-2018 铁路隧道工程
    "TB10417": {
        # 表4.4.1 钢架规格允许偏差
        "表4.4.1钢架规格允许偏差": [
            ["序号", "项目", "允许偏差"],
            ["1", "截面尺寸", "+5mm"],
            ["2", "矢高", "±10mm"],
            ["3", "长度", "±20mm"],
            ["4", "重量", "±5%"],
        ],
        # 表4.4.2 喷射混凝土实测项目
        "表4.4.2喷射混凝土实测项目": [
            ["序号", "检查项目", "允许偏差", "检验方法和频率"],
            ["1", "混凝土强度(MPa)", "符合设计要求", "标准养护试件检验"],
            ["2", "喷层厚度(mm)", "平均厚度≥设计厚度；最小厚度≥0.5设计厚度且≥50", "凿孔检测或取芯检测，每10m检查一个断面"],
            ["3", "喷层表面平整度(mm)", "≤30", "2m靠尺检查"],
        ],
        # 表5.2.4 孔位中心位置、孔深允许偏差
        "表5.2.4孔位中心位置、孔深允许偏差": [
            ["序号", "项目", "允许偏差(mm)"],
            ["1", "孔间距", "±100"],
            ["2", "孔深", "不小于设计值"],
        ],
        # 表6.2.3 洞口开挖允许偏差
        "表6.2.3洞口开挖允许偏差": [
            ["序号", "项目", "允许偏差", "检验方法"],
            ["1", "平面位置", "±50mm", "测量"],
            ["2", "开挖断面", "不小于设计值", "测量"],
            ["3", "边仰坡坡度", "符合设计要求", "坡度尺检查"],
        ],
    },

    # TB10753-2018 高铁隧道工程
    "TB10753": {
        # 从Word提取的表格可以在这里添加
    },

    # JTG F80/1-2017 公路隧道工程
    "JTG_F80_1": {
        # 10.7 喷射混凝土实测项目
        "表10.7喷射混凝土实测项目": [
            ["项次", "检查项目", "规定值或允许偏差", "检查方法和频率"],
            ["1", "喷射混凝土强度(MPa)", "符合设计要求", "《公路工程质量检验评定标准》附录E"],
            ["2", "喷层厚度(mm)", "平均厚度≥设计厚度；最小厚度≥0.5设计厚度且≥50", "凿孔检测，每10m检查一个断面"],
            ["3", "喷层表面平整度(mm)", "≤30", "2m靠尺检查"],
        ],
        # 10.8 锚杆实测项目
        "表10.8锚杆实测项目": [
            ["项次", "检查项目", "规定值或允许偏差", "检查方法和频率"],
            ["1", "锚杆长度(m)", "符合设计要求", "尺量"],
            ["2", "锚杆间距(mm)", "±100", "尺量"],
            ["3", "锚杆拔力(kN)", "≥设计值", "拔力试验"],
        ],
    },
}


def get_manual_table(standard_code: str, table_title: str) -> list:
    """获取手动补齐的表格

    Args:
        standard_code: 标准代号，如 "TB10417", "TB10753", "JTG_F80_1"
        table_title: 表格标题

    Returns:
        表格二维列表，如果没有手动配置返回 None
    """
    standard_tables = MANUAL_TABLES.get(standard_code, {})
    return standard_tables.get(table_title)


def list_manual_tables(standard_code: str = None) -> dict:
    """列出所有手动补齐的表格

    Args:
        standard_code: 可选的过滤标准代号

    Returns:
        表格字典
    """
    if standard_code:
        return {standard_code: MANUAL_TABLES.get(standard_code, {})}
    return MANUAL_TABLES


def add_manual_table(standard_code: str, table_title: str, table_data: list) -> bool:
    """添加手动补齐的表格

    Args:
        standard_code: 标准代号
        table_title: 表格标题
        table_data: 表格二维列表

    Returns:
        是否成功
    """
    if standard_code not in MANUAL_TABLES:
        MANUAL_TABLES[standard_code] = {}

    MANUAL_TABLES[standard_code][table_title] = table_data
    return True


if __name__ == "__main__":
    # 测试
    print("手动补齐表格列表：")
    for std, tables in MANUAL_TABLES.items():
        print(f"\n{std}:")
        for title in tables.keys():
            rows = len(tables[title])
            print(f"  - {title} ({rows}行)")
