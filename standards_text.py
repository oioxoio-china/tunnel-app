# standards_text.py
"""
隧道工程检验批划分系统 - 规范标准查阅文本库
从DATA文件夹加载完整数据，支持PDF原汁原味显示
"""

# 导入DATA加载模块
try:
    from standards_data import (
        get_standard_data,
        get_all_chapters,
        get_chapter_content,
        get_chapter_tables,
        table_to_markdown,
        STANDARD_NAMES,
        STANDARD_FILES
    )
    DATA_LOADED = True
except ImportError:
    DATA_LOADED = False
    STANDARD_NAMES = {}
    STANDARD_FILES = {}

# =============================================================================
# 如果DATA加载失败，使用原有的静态文本
# =============================================================================
if not DATA_LOADED:
    # 从原文件加载（这里为了简洁省略，实际使用DATA加载）
    TB10417_TEXT = {}
    TB10753_TEXT = {}
    JTG_F80_1_TEXT = {}
else:
    # 从DATA文件夹加载数据
    # TB10417_TEXT 格式: {章节名: 内容}
    def _load_tb10417():
        data = get_standard_data("TB10417")
        chapters = data.get("chapters", {})
        # 转换为简单格式
        result = {}
        for ch, ch_data in chapters.items():
            result[ch] = ch_data.get("content", "")
        return result

    def _load_tb10753():
        data = get_standard_data("TB10753")
        chapters = data.get("chapters", {})
        result = {}
        for ch, ch_data in chapters.items():
            result[ch] = ch_data.get("content", "")
        return result

    def _load_jtg_f80_1():
        data = get_standard_data("JTG_F80_1")
        chapters = data.get("chapters", {})
        result = {}
        for ch, ch_data in chapters.items():
            result[ch] = ch_data.get("content", "")
        return result

    # 延迟加载
    TB10417_TEXT = {}
    TB10753_TEXT = {}
    JTG_F80_1_TEXT = {}

    def _ensure_loaded():
        global TB10417_TEXT, TB10753_TEXT, JTG_F80_1_TEXT
        if not TB10417_TEXT:
            TB10417_TEXT = _load_tb10417()
            TB10753_TEXT = _load_tb10753()
            JTG_F80_1_TEXT = _load_jtg_f80_1()

    # 提供加载函数
    def load_all_standards():
        """加载所有标准数据"""
        _ensure_loaded()

# =============================================================================
# 图表配置（保持原有格式）
# =============================================================================
STANDARD_CHARTS = {}

# =============================================================================
# 辅助函数
# =============================================================================
def get_standard_key(standard_type: str) -> str:
    """根据标准类型获取标准代号"""
    if "公路" in standard_type or "JTG" in standard_type:
        return "JTG_F80_1"
    elif "高铁" in standard_type or "TB10753" in standard_type:
        return "TB10753"
    else:
        return "TB10417"


def get_charts_for_chapter(standard_type: str, chapter: str) -> list:
    """获取章节对应的图表"""
    key = get_standard_key(standard_type)
    return STANDARD_CHARTS.get(key, {}).get(chapter, [])


def get_pdf_page(standard_type: str, chapter: str) -> int:
    """获取章节对应的PDF页码"""
    # 默认返回1，实际可能需要从配置获取
    return 1


def get_all_chapters_with_pages(standard_type: str) -> dict:
    """获取所有章节及其页码"""
    key = get_standard_key(standard_type)
    chapters = get_all_chapters(key)
    # 返回章节列表（不带页码，后续可扩展）
    return {ch: i+1 for i, ch in enumerate(chapters)}


# =============================================================================
# 新增：获取完整数据接口
# =============================================================================
def get_full_text_dict(standard_type: str) -> dict:
    """获取完整的条文字典"""
    key = get_standard_key(standard_type)

    if not DATA_LOADED:
        if key == "TB10417":
            return TB10417_TEXT
        elif key == "TB10753":
            return TB10753_TEXT
        else:
            return JTG_F80_1_TEXT

    _ensure_loaded()

    if key == "TB10417":
        return TB10417_TEXT
    elif key == "TB10753":
        return TB10753_TEXT
    else:
        return JTG_F80_1_TEXT


def get_tables_for_chapter(standard_type: str, chapter: str = None) -> list:
    """获取指定章节的表格"""
    key = get_standard_key(standard_type)
    return get_chapter_tables(key, chapter)


def get_full_content(standard_type: str) -> str:
    """获取标准的完整内容"""
    key = get_standard_key(standard_type)
    data = get_standard_data(key)
    return data.get("full_content", "")


# 测试
if __name__ == "__main__":
    if DATA_LOADED:
        print("从DATA文件夹加载数据...")
        load_all_standards()

        print(f"\nTB10417 章节数: {len(TB10417_TEXT)}")
        print(f"TB10753 章节数: {len(TB10753_TEXT)}")
        print(f"JTG_F80_1 章节数: {len(JTG_F80_1_TEXT)}")

        # 显示章节示例
        print("\nTB10417 章节示例:")
        for i, ch in enumerate(list(TB10417_TEXT.keys())[:10]):
            print(f"  {i+1}. {ch}")
    else:
        print("DATA加载失败，使用空数据")
