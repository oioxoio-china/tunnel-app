# standards_data.py
"""
从DATA文件夹加载标准文本数据
提供标准条文、表格等数据
"""

import os
import re
from pathlib import Path

# DATA文件夹路径
DATA_DIR = Path(__file__).parent / "DATA"

# 标准文件映射
STANDARD_FILES = {
    "TB10417": "TB10417.md",
    "TB10753": "TB10753.md",
    "JTG_F80_1": "JTG_F80_1.md",
}

# 标准名称映射
STANDARD_NAMES = {
    "TB10417": "铁路隧道工程 (TB 10417-2018)",
    "TB10753": "高速铁路隧道 (TB 10753-2018)",
    "JTG_F80_1": "公路隧道 (JTG F80/1-2017)",
}


def load_markdown_content(md_file: str) -> str:
    """加载Markdown文件内容"""
    md_path = DATA_DIR / md_file
    if not md_path.exists():
        return ""

    with open(md_path, 'r', encoding='utf-8') as f:
        return f.read()


def parse_chapters(md_content: str) -> dict:
    """解析Markdown内容，提取章节和表格

    Returns:
        {
            "章节标题": {
                "content": "条文内容",
                "tables": [(表格标题, 表格数据), ...]
            },
            ...
        }
    """
    chapters = {}
    current_chapter = None
    current_content = []
    current_tables = []

    lines = md_content.split('\n')

    for i, line in enumerate(lines):
        line = line.strip()

        # 检测章节标题 (## 开头)
        if line.startswith('## '):
            # 保存上一章
            if current_chapter:
                chapters[current_chapter] = {
                    "content": '\n\n'.join(current_content),
                    "tables": current_tables
                }

            # 开始新章节
            current_chapter = line[3:].strip()
            current_content = []
            current_tables = []

        # 检测表格 (### 表格)
        elif line.startswith('### ') and '表' in line:
            # 提取表格
            table_lines = []
            j = i + 1
            while j < len(lines):
                tline = lines[j].strip()
                if tline.startswith('|') and '---' not in tline:
                    table_lines.append(tline)
                elif tline.startswith('|') and '---' in tline:
                    pass  # 跳过分隔行
                elif not tline:
                    break
                elif not tline.startswith('|'):
                    break
                j += 1

            if table_lines:
                # 解析表格
                table_data = []
                for tline in table_lines:
                    cells = [c.strip() for c in tline.split('|')[1:-1]]
                    if cells and any(c for c in cells):
                        table_data.append(cells)

                if table_data and current_chapter:
                    table_title = line[4:].strip() if len(line) > 4 else "表格"
                    current_tables.append((table_title, table_data))

    # 保存最后一章
    if current_chapter:
        chapters[current_chapter] = {
            "content": '\n\n'.join(current_content),
            "tables": current_tables
        }

    return chapters


def get_chapter_content(standard_code: str, chapter: str = None) -> str:
    """获取指定章节的内容"""
    md_file = STANDARD_FILES.get(standard_code)
    if not md_file:
        return ""

    content = load_markdown_content(md_file)

    if not chapter:
        return content  # 返回全文

    chapters = parse_chapters(content)
    chapter_data = chapters.get(chapter, {})
    return chapter_data.get("content", "")


def get_chapter_tables(standard_code: str, chapter: str = None) -> list:
    """获取指定章节的表格"""
    md_file = STANDARD_FILES.get(standard_code)
    if not md_file:
        return []

    content = load_markdown_content(md_file)
    chapters = parse_chapters(content)

    if chapter:
        chapter_data = chapters.get(chapter, {})
        return chapter_data.get("tables", [])

    # 返回所有表格
    all_tables = []
    for ch_data in chapters.values():
        all_tables.extend(ch_data.get("tables", []))

    return all_tables


def get_all_chapters(standard_code: str) -> list:
    """获取所有章节列表"""
    md_file = STANDARD_FILES.get(standard_code)
    if not md_file:
        return []

    content = load_markdown_content(md_file)
    chapters = parse_chapters(content)

    return list(chapters.keys())


def table_to_markdown(table: list) -> str:
    """将表格转换为Markdown格式"""
    if not table:
        return ""

    md = ""
    for i, row in enumerate(table):
        cells = [str(cell) if cell else "" for cell in row]

        if i == 0:
            md += "| " + " | ".join(cells) + " |\n"
            md += "| " + " | ".join(["---"] * len(cells)) + " |\n"
        else:
            md += "| " + " | ".join(cells) + " |\n"

    return md


# 导出统一接口
def get_standard_data(standard_code: str) -> dict:
    """获取标准完整数据"""
    md_file = STANDARD_FILES.get(standard_code)
    if not md_file:
        return {}

    content = load_markdown_content(md_file)
    chapters = parse_chapters(content)

    return {
        "full_content": content,
        "chapters": chapters,
        "chapter_list": list(chapters.keys())
    }


if __name__ == "__main__":
    # 测试
    print("加载标准数据...")

    for code, name in STANDARD_NAMES.items():
        print(f"\n{name}:")
        chapters = get_all_chapters(code)
        print(f"  章节数量: {len(chapters)}")

        # 获取表格数量
        tables = get_chapter_tables(code)
        print(f"  表格数量: {len(tables)}")

        # 显示章节示例
        print("  章节示例:")
        for ch in chapters[:5]:
            print(f"    - {ch}")
