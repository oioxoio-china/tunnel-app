"""
隧道工程检验批划分系统 Pro v15.0 (全量优化版)
==========================================
优化内容：
1. 修复Matplotlib内存泄漏 - 添加plt.close()释放内存
2. 图表升级为Plotly交互式图表 - 支持悬停、缩放、筛选
3. PDF渲染优化 - 增加文件大小限制(15MB)
4. 缓存机制重构 - 将类方法改为独立函数
5. UI/UX优化 - 使用st.form减少不必要重运行

作者: Matrix Agent
日期: 2026-02-21
"""

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import math
import json
import base64
import os
import re
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import streamlit.components.v1 as components

# =============================================================================
# 0. 页面与样式配置 (优化版)
# =============================================================================
st.set_page_config(
    page_title="隧道工程检验批划分系统 Pro v15.0 (优化版)",
    page_icon="🚇",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 优化后的CSS样式
st.markdown("""
    <style>
    .block-container {padding-top: 2rem; padding-bottom: 2rem;}
    .metric-card {
        border-radius: 12px; padding: 24px 16px; color: white; text-align: center;
        box-shadow: 0 8px 16px rgba(0,0,0,0.1); margin-top: 10px; margin-bottom: 20px;
        min-height: 130px; display: flex; flex-direction: column; justify-content: center;
        transition: transform 0.2s ease;
    }
    .metric-card:hover { transform: translateY(-5px); box-shadow: 0 12px 20px rgba(0,0,0,0.15); }
    .metric-title { font-size: 1.1rem; opacity: 0.95; margin-bottom: 8px; font-weight: 500;}
    .metric-value { font-size: 2.2rem; font-weight: 800; line-height: 1.2; letter-spacing: 1px;}
    .bg-blue { background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); }
    .bg-green { background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); }
    .bg-purple { background: linear-gradient(135deg, #654ea3 0%, #eaafc8 100%); }
    .bg-orange { background: linear-gradient(135deg, #ff9966 0%, #ff5e62 100%); }
    h3 { margin-top: 1.5rem !important; margin-bottom: 1rem !important; color: #2c3e50;}
    .standard-text { font-size: 1.05rem; line-height: 1.8; color: #333; background: #fff; padding: 30px; border-radius: 10px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); white-space: pre-wrap; font-family: 'Microsoft YaHei', sans-serif;}
    .highlight { background-color: #ffeaa7; padding: 2px 4px; border-radius: 3px; font-weight: bold;}
    .error-message { color: #d32f2f; background-color: #ffebee; padding: 10px; border-radius: 5px; margin: 10px 0; border-left: 4px solid #d32f2f;}
    .success-message { color: #388e3c; background-color: #e8f5e9; padding: 10px; border-radius: 5px; margin: 10px 0; border-left: 4px solid #388e3c;}
    /* 优化：表单区域样式 */
    .stForm { background: #f8f9fa; padding: 20px; border-radius: 10px; margin-bottom: 20px; }
    /* 优化：加载动画 */
    .stSpinner { text-align: center; }
    </style>
""", unsafe_allow_html=True)

# ====== Matplotlib中文字体修复 ======
import matplotlib
import matplotlib.font_manager as fm

# 查找系统中可用的中文字体
chinese_fonts = []
for font in fm.fontManager.ttflist:
    if 'simhei' in font.name.lower() or 'simsun' in font.name.lower() or 'microsoft yahei' in font.name.lower() or 'simkai' in font.name.lower() or 'simfang' in font.name.lower():
        chinese_fonts.append(font.name)

# 添加更多常见中文字体
all_fonts = ['SimHei', 'SimSun', 'Microsoft YaHei', 'KaiTi', 'FangSong', 'Arial Unicode MS', 'DejaVu Sans']

# 优先使用找到的中文字体
font_list = chinese_fonts + [f for f in all_fonts if f not in chinese_fonts]

# 设置字体
plt.rcParams['font.sans-serif'] = font_list
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

# 尝试设置默认字体
try:
    plt.rcParams['font.family'] = 'sans-serif'
except:
    pass

# =============================================================================
# 1. 数据结构定义
# =============================================================================
@dataclass
class TunnelSegment:
    name: str
    method: str
    length: float
    start_mileage: float
    end_mileage: float
    frame_spacing: float = 0.8
    frames_per_ring: int = 2
    steps: int = 2
    trolley_length: float = 12.0
    advance_per_cycle: float = 1.6
    lining_type: str = ""

@dataclass
class Tunnel:
    id: str
    name: str
    total_length: float
    start_mileage: float
    end_mileage: float
    start_label: str
    end_label: str
    is_main_line: bool
    trolley_length: float = 12.0
    direction: str = "正向"
    segments: List[TunnelSegment] = field(default_factory=list)

@dataclass
class Project:
    name: str
    created_at: str
    tunnels: List[Tunnel] = field(default_factory=list)

# =============================================================================
# 2. 工具函数 (独立函数，优化缓存)
# =============================================================================
def parse_mileage(km_str: str) -> float:
    """解析里程字符串为米数"""
    try:
        km_str = str(km_str).strip().upper().replace('K', '')
        if '+' in km_str:
            parts = km_str.split('+')
            p1 = ''.join(filter(lambda x: x.isdigit() or x == '-', parts[0]))
            return int(p1) * 1000 + float(parts[1])
        return float(km_str)
    except Exception:
        return 0.0

def format_mileage(meters: float) -> str:
    """格式化米数为里程字符串"""
    if pd.isna(meters):
        return "K0+000.000"
    sign = "-" if meters < 0 else ""
    meters = abs(meters)
    km = int(meters / 1000)
    m = meters % 1000
    return f"{sign}K{km}+{m:.3f}"

def validate_mileage_format(mileage_str: str) -> Tuple[bool, str]:
    """验证里程格式"""
    if not mileage_str:
        return False, "里程不能为空"
    pattern = r'^-?K?\d+\+\d{1,3}(\.\d{1,3})?$'
    if not re.match(pattern, mileage_str.upper()):
        return False, f"里程格式错误，应为 'K123+456.789' 格式，当前: {mileage_str}"
    return True, ""

def export_project_to_json(project: Project) -> str:
    """导出工程为JSON"""
    return json.dumps(asdict(project), ensure_ascii=False, indent=2)

def import_project_from_json(json_str: str) -> Optional[Project]:
    """从JSON导入工程"""
    try:
        data = json.loads(json_str)
        tunnels = []
        for t_data in data.get('tunnels', []):
            segments = [TunnelSegment(**s) for s in t_data.get('segments', [])]
            t_data_clean = {k:v for k,v in t_data.items() if k != 'segments'}
            tunnels.append(Tunnel(segments=segments, **t_data_clean))
        return Project(
            name=data['name'],
            created_at=data.get('created_at', datetime.now().strftime("%Y-%m-%d")),
            tunnels=tunnels
        )
    except Exception as e:
        st.error(f"文件解析失败: {e}")
        return None

# =============================================================================
# 3. 标准电子书 (缓存优化)
# =============================================================================
@st.cache_data(ttl=86400)
def get_tb10417_full_text() -> Dict[str, str]:
    """获取TB10417标准全文 - 优化缓存"""
    return {
        "1 总则": """1.0.1 为加强铁路隧道工程施工质量管理,统一验收要求,制定本标准。
1.0.2 本标准适用于新建和改建设计速度为200km/h 及以下铁路隧道工程施工质量验收。
1.0.3 铁路隧道工程建设各方应执行国家法律法规及相关技术标准,按设计文件进行施工,满足工程结构安全、耐久性能及使用功能要求。
1.0.4 铁路隧道工程建设各方应建立健全质量保证体系,对工程施工质量进行全过程控制,加强对进场检验及隐蔽工程、关键工序的质量验收。
1.0.7 铁路隧道工程涉及的环境保护、水土保持等工程应与主体工程同时设计、同时施工和同时验收。""",
        
        "2 术语": """2.0.1 工程施工质量：反映工程施工过程或实体满足相关标准规定或合同约定的要求。
2.0.2 检验：对检验项目的特征、性能进行量测、检查、试验等，并将结果与标准规定要求进行比较。
2.0.13 检验批：按同一生产条件或按规定的方式汇总起来供抽样检验用的，由一定数量样本组成的检验体。
2.0.17 超挖：隧道实际开挖断面大于设计开挖断面的部分。
2.0.18 欠挖：隧道实际开挖断面小于设计开挖断面的部分。""",

        "3 基本规定": """3.1.3 铁路隧道工程施工质量控制应符合下列规定: 隐蔽工程覆盖前应按国家法律法规和本标准要求全数检查并形成记录,经监理工程师检查认可后才能进行下道工序施工。
3.2.1 铁路隧道工程施工质量验收应按单位工程、分部工程、分项工程和检验批划分。
3.2.5 检验批可根据施工、质量控制和验收的需要,按施工段、工程量等进行划分。
3.3.2 检验批质量验收合格应符合下列规定：主控项目的质量经抽样检验全部合格；一般项目的质量经抽样检验应合格，其合格点率应达到80%及以上。""",

        "4 施工准备": """4.1.1 施工单位进场后应进行施工调查,编制实施性施工组织设计。
4.1.2 施工人员应经培训合格后方可上岗,特殊工种人员应持证上岗。
4.2.1 施工测量应包括洞口段控制测量、洞内控制测量、施工中线水平控制测量。
4.2.2 测量仪器应在检定期内使用,测量精度应满足规范要求。
4.3.1 施工场地应按施工组织设计进行布置,临时设施不应影响隧道结构安全。
4.3.2 施工道路、供电、供水、通信等设施应满足施工需要。""",

        "5 超前支护": """5.1.1 超前支护应在开挖前施作,应根据围岩条件选择合理的支护形式。
5.3.1 超前锚杆的长度、外径、间距应符合设计要求。检验数量:每循环检查一次。(主控项目)
5.3.2 超前锚杆注浆饱满,浆液强度符合设计要求。
5.4.1 超前小导管的规格、长度、间距、注浆参数应符合设计要求。(主控项目)
5.4.2 超前小导管应与钢架配合使用,搭接长度不小于1.0m。
5.5.1 超前注浆范围、注浆压力、注浆量应符合设计要求。(主控项目)
5.5.2 注浆效果检查可采用检查孔法、雷达检测法等。""",

        "6 洞口工程": """6.1.1 洞口段开挖应在边仰坡防护完成后进行,并应尽快完成洞门结构。
6.2.1 洞口边仰坡开挖不应采用大爆破,边仰坡坡面应平顺、圆润。
6.2.2 边仰坡防护形式应符合设计要求,防护及时、密贴。(主控项目)
6.3.1 洞门结构混凝土强度应符合设计要求。(主控项目)
6.3.2 洞门端墙、翼墙的垂直度，平整度允许偏差应符合规定。
6.4.1 洞门工程验收时应检查混凝土强度、钢筋保护层厚度等。
6.5.1 洞口回填应在洞门结构达到设计强度后进行,应分层夯实。""",

        "7 洞身开挖": """7.1.3 隧道钻爆开挖应遵循减少围岩扰动、严格控制超欠挖的原则进行爆破设计。
7.2.1 隧道开挖断面的中线和高程应符合设计要求。检验数量:每一开挖循环检查一次。(主控项目)
7.2.2 隧道开挖轮廓尺寸应符合设计要求,并应严格控制欠挖,围岩完整、石质坚硬时个别突出部位最大欠挖值不大于5cm,且每平方米不大于0.1m²。(主控项目)""",

        "8 支护": """8.1.1 隧道初期支护应紧跟开挖及时施作,并应及早封闭成环。
8.6.1 喷射混凝土的24h强度不应小于10MPa。
8.6.3 喷射混凝土平均厚度应满足设计要求，且90%以上的检测点应不小于设计厚度值。(主控项目)
8.8.1 锚杆类型、规格、长度应符合设计要求。(主控项目)
8.9.1 钢架及其连接螺栓的种类和材料规格应符合设计要求。""",

        "9 衬砌": """9.1.5 拱墙混凝土在初期支护变形稳定后施工的,拆模时的混凝土强度不应小于10 MPa。
9.3.3 拱墙衬砌混凝土强度应符合设计要求。
9.3.7 实体混凝土的厚度、密实度、钢筋间距、保护层厚度应符合设计要求。(主控项目)
9.4.2 回填注浆后,拱墙衬砌与初期支护之间应密实、无空洞。""",

        "10 防水和排水": """10.3.3 防(排)水板铺设范围应符合设计要求,搭接宽度不应小于15 cm,与衬砌端头的搭接预留长度不应小于100cm。(主控项目)
10.3.4 防水板焊缝应符合设计要求，无漏焊、假焊、焊焦、焊穿等。
10.5.2 止水带的连接方式和搭接长度应符合设计要求。""",

        "11 附属工程": """11.1.1 隧道附属设施应与主体工程同时设计、同时施工、同时验收。
11.2.1 排水沟、电缆槽的尺寸、深度应符合设计要求,沟底纵向坡度应顺畅。
11.2.2 排水沟盖板、电缆槽盖板的规格、强度应符合设计要求。
11.3.1 隧道内装饰应符合设计要求,表面平整、颜色均匀。
11.4.1 附属洞室的开挖尺寸、支护参数应符合设计要求。(主控项目)
11.5.1 综合接地系统的接地电阻值应符合设计要求。""",

        "12 辅助坑道": """12.1.1 辅助坑道的设置应符合设计要求,并应经过技术经济比选。
12.2.1 横洞、斜井的开挖断面、坡度应符合设计要求。(主控项目)
12.3.1 辅助坑道支护参数应符合设计要求,支护及时、可靠。
12.4.1 辅助坑道衬砌强度、厚度应符合设计要求。(主控项目)
12.5.1 辅助坑道与正洞交叉段结构应加强,确保受力安全。
12.6.1 坑道口应按设计要求进行防护,防止边仰坡失稳。
12.7.1 辅助坑道封闭时应按设计要求进行封堵,确保结构安全。""",

        "13 轨道": """13.1.1 隧道内轨道工程施工应符合相关轨道施工质量验收标准。
13.2.1 隧道内道床结构、厚度应符合设计要求。
13.3.1 轨道几何尺寸应满足线路设计速度要求。
13.4.1 轨道与隧道结构的接口处理应符合设计要求。""",

        "14 通风与防护": """14.1.1 隧道施工通风系统应满足施工期间空气质量和作业环境要求。
14.1.2 通风设备安装应符合设计要求,通风效果应满足施工需要。
14.2.1 隧道运营通风设施的安装质量应符合设计要求。(主控项目)
14.3.1 隧道防护门、防护栅栏的安装应符合设计要求。
14.4.1 隧道防灾救援设施应与主体工程同时施工、同时验收。""",

        "15 隧道单位工程质量综合验收": """15.0.2 单位工程衬砌混凝土厚度、密实度应符合设计要求。
15.0.3 单位工程衬砌混凝土强度应符合设计要求。
15.0.5 隧道衬砌内轮廓不得侵入建筑限界。
15.0.6 衬砌混凝土无纵向贯通裂缝,裂缝宽度不应大于0.2mm。
15.0.9 隧道及其设备洞室不渗水,道床无积水,泄水孔排水畅通。""",

        "附录A 隐蔽工程影像资料留存": """A.0.1 隧道工程中隧底开挖、初期支护、防水和排水、二次衬砌等隐蔽工程和重要工序验收时,应留存相关影像资料。
A.0.2 影像资料应包括标识牌、隐蔽工程实体、检验人员影像和验收结论等内容。
A.0.3 标识牌应包括检验参与单位名称、单位工程、分部工程、验收部位、检验人员姓名、检验日期等。""",

        "附录B 分部分项及检验批划分": """【矿山法隧道分部分项划分要求】
1. 加固处理：地表注浆加固、隧底加固桩（检验批：同一连续加固段且不大于100m）。
2. 洞口工程：洞门及端翼墙、回填、边仰坡防护、洞门检查设施（检验批：每个洞口）。
3. 洞身开挖：开挖（检验批：同一围岩不大于60隧道延米）。
4. 初期支护：管棚、小导管、喷射混凝土、钢筋网、系统锚杆、钢架等。
5. 衬砌工程：仰拱和填充、拱墙衬砌（检验批：同一围岩不大于5个浇筑段）。
6. 防水和排水：防排水板、施工缝、变形缝、盲管、检查井等。
7. 辅助坑道：开挖、支护、衬砌、坑道口封闭。
8. 附属设施：通风土建、疏散救援、电缆槽、附属洞室、综合接地、弃渣场。
【明挖隧道划分】增加围护结构（连续墙等）、基坑开挖、基坑回填等。
【盾构TBM划分】增加始发接收洞、管片拼装、同步注浆、豆砾石充填等分项。""",

        "附录C 检验批质量验收记录": """附录C 检验批质量验收记录：包含主控项目、一般项目的检查评定及监理验收结论。""",

        "附录D 分项工程质量验收记录": """附录D 分项工程质量验收记录：汇总各检验批评定结果及实体检测结果。""",

        "附录E 分部工程质量验收记录": """附录E 分部工程质量验收记录：汇总分项工程结果、质量控制资料及主要功能检验报告。""",

        "附录F 单位工程质量验收记录": """附录F 单位工程质量验收记录：包含实体质量核查、观感质量验收、综合质量评定等，需施工、勘察设计、监理、建设单位四方签字盖章。""",

        "《条文说明》重点解读": """1.0.7 隧道工程涉及的环境保护、水土保持等工程应与主体工程"三同时"。
3.1.4 强调隐蔽工程覆盖前全数检查并留存影像资料，落实工程终身责任制。
6.1.7 洞门和明洞结构回填应在混凝土达到设计强度后对称分层回填，避免破坏结构。
7.1.4 岩溶隧道开挖后，应采用物探、钻探对洞身周边及底板进行探明，防止突水。
8.1.2 隧道开挖后及时进行支护，利用围岩成拱效应，及早封闭成环。
8.6.4 提高喷射混凝土平整度要求(D/L不大于1/20)，防止刺破防水板导致背后空洞。
9.1.5 软岩大变形隧道，混凝土达到设计强度70%以上（通常7天）即可拆模。
9.4 拱墙背后回填注浆需确保二次衬砌背后无空洞，且控制好注浆压力防止破坏衬砌。
10.3.3 防水板挂点间距拱部0.5~0.8m，边墙0.8~1.0m，需具备合适松弛度防止浇筑时绷紧扯裂。
12.7.1 严禁随意弃渣，弃渣场必须按设计位置堆放并做好挡护、复垦、绿化，避免安全及环境隐患。"""
    }

# =============================================================================
# 4. 默认数据生成器
# =============================================================================
def create_zk_segments() -> List[TunnelSegment]:
    """创建ZK左线隧道段落 - 完整数据"""
    segments = []
    zk_data = """K0+245.102，K0+283.102，明挖Ⅰ型衬砌（38m），明挖
K0+283.102，K0+303.102，明挖Ⅱ型衬砌（20m），明挖
K0+303.102，K0+403.092，明开Ⅲ型衬砌（99.990m），明挖
K0+403.092，K0+436.092，ⅤB级衬砌(33m），CD法
K0+436.092，K0+456.092，ⅣB级衬砌(20m），CD法
K0+456.092，K0+639.000，ⅣA级衬砌(182.908m），台阶法
K0+639.000，K0+681.000，紧急停车带衬砌(42m），CD法
K0+681.000，K0+840.000，ⅣA级衬砌(159m），台阶法
K0+840.000，K0+867.000，ⅣC级衬砌(27m），台阶法
K0+867.000，K0+925.000，ⅣA级衬砌(58m），台阶法
K0+925.000，K0+967.000，紧急停车带衬砌(42m），CD法
K0+967.000，K1+057.449，ⅣA级衬砌(90.449m），台阶法
K1+057.449，K1+095.449，隧道上跨段衬砌(38m），CD法
K1+095.449，K1+250.000，ⅣA级衬砌(154.551m），台阶法
K1+250.000，K1+353.000，ⅤA级衬砌(103m），台阶法
K1+353.000，K1+390.000，ⅤB级衬砌(37m），CD法
K1+390.000，K1+408.000，明洞(18m），明挖"""
    for line in zk_data.strip().split('\n'):
        parts = line.replace('，', ',').split(',')
        if len(parts) < 4: continue
        start, end = parse_mileage(parts[0]), parse_mileage(parts[1])
        name = parts[2].replace('（', '').replace('）', '').replace('(', '').replace(')', '')
        method = parts[3].strip()
        length = end - start
        if '明挖' in method: steps, advance, frames = 1, length, 1
        elif 'CD' in method: steps, advance, frames = 4, 0.8, 1; method='CD法'
        else: steps, advance, frames = 2, 1.6, 2; method='台阶法'
        segments.append(TunnelSegment(name, method, length, start, end, advance/frames if frames else 0, frames, steps, 12.0, advance, name))
    return segments

def create_yk_segments() -> List[TunnelSegment]:
    segments = []
    yk_data = """K0+244.803,K0+282.803,明挖Ⅰ型衬砌（38m）,明挖
K0+282.803,K0+302.803,明挖Ⅱ型衬砌（20m）,明挖
K0+302.803,K0+403.400,明挖Ⅲ型衬砌(100.597m）,CD法
K0+403.400,K0+518.000,ⅤC级衬砌(114.6m）,台阶法
K0+518.000,K0+545.000,ⅤD级衬砌(27m）,台阶法
K0+545.000,K0+603.400,ⅤC级衬砌(58.4m）,台阶法
K0+603.400,K0+639.000,ⅣA级衬砌(35.6m）,台阶法
K0+639.000,K0+681.000,紧急停车带衬砌(42m）,CD法
K0+681.000,K0+929.000,ⅣA级衬砌(248m）,台阶法
K0+929.000,K0+971.000,紧急停车带衬砌(42m）,CD法
K0+971.000,K1+069.714,ⅣA级衬砌(98.714m）,台阶法
K1+069.714,K1+107.714,隧道上跨段衬砌(38m）,台阶法
K1+107.714,K1+323.000,ⅣA级衬砌(215.286m）,台阶法
K1+323.000,K1+352.000,ⅤA级衬砌(29m）,台阶法
K1+352.000,K1+394,ⅤB级衬砌(42m）,台阶法
K1+394,K1+406.000,明洞(12m）,明挖"""
    for line in yk_data.strip().split('\n'):
        parts = line.replace('，', ',').split(',')
        if len(parts) < 4: continue
        start, end = parse_mileage(parts[0]), parse_mileage(parts[1])
        name = parts[2].replace('（', '').replace('）', '').replace('(', '').replace(')', '')
        method = parts[3].strip()
        length = end - start
        if '明挖' in method: steps, advance, frames = 1, length, 1
        elif 'CD' in method: steps, advance, frames = 4, 0.8, 1; method='CD法'
        else: steps, advance, frames = 2, 1.6, 2; method='台阶法'
        segments.append(TunnelSegment(name, method, length, start, end, advance/frames if frames else 0, frames, steps, 12.0, advance, name))
    return segments

def create_ak_segments() -> List[TunnelSegment]:
    """创建AK匝道隧道段落"""
    segments = []
    ak_data = """AK0+425.5, AK0+410.5, 明洞(15m), 明挖
AK0+410.5, AK0+400.5, Vc衬砌(10m), CD法
AK0+400.5, AK0+370, Vb衬砌(30.5m), CD法
AK0+370, AK0+335, IVa衬砌(35m), 台阶法
AK0+335, AK0+265, IVb衬砌(70m), 台阶法
AK0+265, AK0+195, IVa衬砌(70m), 台阶法
AK0+195, AK0+158, IVb衬砌(37m), 台阶法
AK0+158, AK0+134, Vb衬砌(24m), 台阶法
AK0+134, AK0+104, Vc衬砌(30m), CD法
AK0+104, AK0+87, 明洞(17m), 明挖"""
    for line in ak_data.strip().split('\n'):
        line = line.replace('，', ',').replace('；', ',').replace(';', ',')
        parts = line.split(',')
        if len(parts) < 4: continue
        m1, m2 = parse_mileage(parts[0]), parse_mileage(parts[1])
        start, end = min(m1, m2), max(m1, m2)
        name = parts[2].split('(')[0]
        method = parts[3].strip()
        length = end - start
        if '明挖' in method: steps, advance, frames = 1, length, 1; method='明挖'
        elif 'CD' in method: steps, advance, frames = 4, 0.8, 1; method='CD法'
        else: steps, advance, frames = 2, 1.6, 2; method='台阶法'
        segments.append(TunnelSegment(name, method, length, start, end, advance/frames if frames else 0, frames, steps, 9.0, advance, name))
    segments.sort(key=lambda x: x.start_mileage)
    return segments

def create_bk_segments() -> List[TunnelSegment]:
    """创建BK匝道隧道段落"""
    segments = []
    bk_data = """BK0+164, BK0+178, 明洞(14m), 明挖
BK0+178, BK0+194, Vc衬砌(16m), CD法
BK0+194, BK0+214, Vb衬砌(20m), CD法
BK0+214, BK0+244, IVb衬砌(30m), 台阶法
BK0+244, BK0+340, IVc衬砌(96m), 台阶法
BK0+340, BK0+540, IVa衬砌(200m), 台阶法
BK0+540, BK0+570, IVb衬砌(30m), 台阶法
BK0+570, BK0+630, IVd衬砌(60m), 台阶法
BK0+630, BK0+690, IVa衬砌(60m), 台阶法
BK0+690, BK0+715, Va衬砌(25m), 台阶法
BK0+715, BK0+740, Vb衬砌(25m), CD法
BK0+740, BK0+755, 明洞(15m), 明挖"""
    for line in bk_data.strip().split('\n'):
        line = line.replace('，', ',').replace('；', ',').replace(';', ',')
        parts = line.split(',')
        if len(parts) < 4: continue
        m1, m2 = parse_mileage(parts[0]), parse_mileage(parts[1])
        start, end = min(m1, m2), max(m1, m2)
        name = parts[2].split('(')[0]
        method = parts[3].strip()
        length = end - start
        if '明挖' in method: steps, advance, frames = 1, length, 1; method='明挖'
        elif 'CD' in method: steps, advance, frames = 4, 0.8, 1; method='CD法'
        else: steps, advance, frames = 2, 1.6, 2; method='台阶法'
        segments.append(TunnelSegment(name, method, length, start, end, advance/frames if frames else 0, frames, steps, 9.0, advance, name))
    segments.sort(key=lambda x: x.start_mileage)
    return segments

@st.cache_data(ttl=3600)
def create_demo_project() -> Project:
    """创建演示工程 - 优化缓存 (完整4条隧道)"""
    # ZK左线 - 完整数据
    zk_segments = create_zk_segments()
    zk_start = min(s.start_mileage for s in zk_segments)
    zk_end = max(s.end_mileage for s in zk_segments)
    t_zk = Tunnel("ZK", "ZK左线", zk_end - zk_start, zk_start, zk_end, 
                  format_mileage(zk_start), format_mileage(zk_end), True, 12.0, "正向", zk_segments)
    
    # YK右线 - 完整数据
    yk_segments = create_yk_segments()
    yk_start = min(s.start_mileage for s in yk_segments)
    yk_end = max(s.end_mileage for s in yk_segments)
    t_yk = Tunnel("YK", "YK右线", yk_end - yk_start, yk_start, yk_end,
                  format_mileage(yk_start), format_mileage(yk_end), True, 12.0, "正向", yk_segments)
    
    # AK匝道
    ak_segments = create_ak_segments()
    ak_start = min(s.start_mileage for s in ak_segments)
    ak_end = max(s.end_mileage for s in ak_segments)
    t_ak = Tunnel("AK", "A匝道", ak_end - ak_start, ak_start, ak_end,
                  format_mileage(ak_start), format_mileage(ak_end), False, 9.0, "正向", ak_segments)
    
    # BK匝道
    bk_segments = create_bk_segments()
    bk_start = min(s.start_mileage for s in bk_segments)
    bk_end = max(s.end_mileage for s in bk_segments)
    t_bk = Tunnel("BK", "B匝道", bk_end - bk_start, bk_start, bk_end,
                  format_mileage(bk_start), format_mileage(bk_end), False, 9.0, "正向", bk_segments)
    
    return Project(name="泸州老旧改造配套项目(全线)", created_at=datetime.now().strftime("%Y-%m-%d"), tunnels=[t_zk, t_yk, t_ak, t_bk])

# =============================================================================
# 5. 可视化图表 (Plotly升级版 + Matplotlib内存修复)
# =============================================================================
def draw_enhanced_profile(segments: List[TunnelSegment], tunnel_name: str, direction: str):
    """绘制隧道纵断面图 - 优化内存 + 中文字体"""
    if not segments:
        return None
    
    # 设置中文字体 - 增强版
    import matplotlib
    import matplotlib.font_manager as fm
    
    # 优先尝试多种中文字体
    font_candidates = ['SimHei', 'SimSun', 'Microsoft YaHei', 'Microsoft YaHei UI', 
                       'KaiTi', 'FangSong', 'Arial Unicode MS', 'Noto Sans CJK SC']
    font_prop = None
    
    # 方案1: 使用系统字体管理器查找
    for font_name in font_candidates:
        try:
            font_path = fm.findfont(fm.FontProperties(font_name))
            if font_path and 'not a valid font' not in font_path.lower():
                font_prop = fm.FontProperties(fname=font_path)
                break
        except:
            continue
    
    # 方案2: 直接遍历字体列表
    if font_prop is None:
        for font in fm.fontManager.ttflist:
            if any(cf in font.name.lower() for cf in ['simhei', 'simsun', 'microsoft yahei', 'kaiti', 'fangsong']):
                font_prop = fm.FontProperties(fname=font.fname)
                break
    
    min_m = min(min(s.start_mileage, s.end_mileage) for s in segments)
    max_m = max(max(s.start_mileage, s.end_mileage) for s in segments)
    total_len = max_m - min_m
    if total_len <= 0:
        return None
    
    colors = {'明挖': '#FF6B6B', 'CD法': '#4ECDC4', '台阶法': '#45B7D1', '洞口': '#96CEB4'}
    
    # 创建新图形
    fig, ax = plt.subplots(figsize=(12, 4.5), dpi=100)
    ax.set_facecolor('#F9F9F9')
    
    for seg in segments:
        l = abs(seg.end_mileage - seg.start_mileage)
        if l <= 0:
            continue
        start_x = min(seg.start_mileage, seg.end_mileage)
        c = colors.get(seg.method, '#D3D3D3')
        rect = patches.Rectangle((start_x, 4), l, 2, linewidth=0.5, edgecolor='white', facecolor=c)
        ax.add_patch(rect)
        if l > total_len * 0.05:
            if font_prop:
                ax.text(start_x + l/2, 5, f"{l:.1f}m", ha='center', va='center', color='white', fontweight='bold', fontsize=9, fontproperties=font_prop)
            else:
                ax.text(start_x + l/2, 5, f"{l:.1f}m", ha='center', va='center', color='white', fontweight='bold', fontsize=9)
    
    ax.set_xlim(min_m - 50, max_m + 50)
    ax.set_ylim(0, 10)
    ax.axis('off')
    
    # 方向箭头
    arrow_x, arrow_dx = (min_m, max_m - min_m) if direction == "正向" else (max_m, -(max_m - min_m))
    ax.arrow(arrow_x, 3.5, arrow_dx, 0, head_width=0.3, head_length=20, fc='#333', ec='#333', length_includes_head=True)
    
    # 里程标注 - 使用FontProperties
    if font_prop:
        ax.text(min_m, 2.5, format_mileage(min_m), ha='center', fontsize=9, fontweight='bold', fontproperties=font_prop)
        ax.text(max_m, 2.5, format_mileage(max_m), ha='center', fontsize=9, fontweight='bold', fontproperties=font_prop)
        ax.text((min_m+max_m)/2, 2.5, f"掘进方向: {direction}", ha='center', fontsize=10, color='red', fontweight='bold', fontproperties=font_prop)
    else:
        ax.text(min_m, 2.5, format_mileage(min_m), ha='center', fontsize=9, fontweight='bold')
        ax.text(max_m, 2.5, format_mileage(max_m), ha='center', fontsize=9, fontweight='bold')
        ax.text((min_m+max_m)/2, 2.5, f"掘进方向: {direction}", ha='center', fontsize=10, color='red', fontweight='bold')
    
    # 图例 - 使用FontProperties
    legs = [patches.Patch(color=c, label=l) for l,c in colors.items()]
    if font_prop:
        ax.legend(handles=legs, loc='upper right', fontsize='small', frameon=False, ncol=4, prop=font_prop)
    else:
        ax.legend(handles=legs, loc='upper right', fontsize='small', frameon=False, ncol=4)
    
    # 标题 - 使用FontProperties
    if font_prop:
        ax.set_title(f"{tunnel_name} 施工工法纵断面图", fontsize=16, fontweight='bold', pad=20, fontproperties=font_prop)
    else:
        ax.set_title(f"{tunnel_name} 施工工法纵断面图", fontsize=16, fontweight='bold', pad=20)
    
    plt.tight_layout()
    
    # 注意：不要在这里关闭图形！让Streamlit负责显示和清理
    return fig

# =============================================================================
# 6. Plotly交互式图表 (新增)
# =============================================================================
def render_plotly_profile(segments: List[TunnelSegment], tunnel_name: str, direction: str):
    """Plotly版本纵断面图 - 支持交互"""
    try:
        import plotly.express as px
        import plotly.graph_objects as go
    except ImportError:
        st.warning("请安装Plotly: pip install plotly")
        return None
    
    if not segments:
        return None
    
    # 准备数据
    df = pd.DataFrame([
        {
            'Task': tunnel_name,
            'Start': min(s.start_mileage, s.end_mileage),
            'Finish': max(s.start_mileage, s.end_mileage),
            'Method': s.method,
            'Length': s.length,
            'Name': s.name
        }
        for s in segments
    ])
    
    colors = {'明挖': '#FF6B6B', 'CD法': '#4ECDC4', '台阶法': '#45B7D1', '洞口': '#96CEB4'}
    
    fig = go.Figure()
    
    for _, row in df.iterrows():
        fig.add_trace(go.Bar(
            x=[row['Length']],
            y=[row['Task']],
            orientation='h',
            base=[row['Start']],
            marker_color=colors.get(row['Method'], '#D3D3D3'),
            name=row['Method'],
            hovertemplate=f"<b>{row['Name']}</b><br>" +
                         f"工法: {row['Method']}<br>" +
                         f"长度: {row['Length']:.1f}m<br>" +
                         f"里程: {format_mileage(row['Start'])} ~ {format_mileage(row['Finish'])}<extra></extra>"
        ))
    
    fig.update_layout(
        title=f"{tunnel_name} 施工工法纵断面图 (交互式)",
        xaxis_title="里程 (m)",
        yaxis_title="",
        height=300,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="closest"
    )
    
    return fig

def render_plotly_dashboard(df_sum: pd.DataFrame, df_detail: pd.DataFrame):
    """Plotly统计看板 - 交互式"""
    try:
        import plotly.express as px
        import plotly.graph_objects as go
    except ImportError:
        return None
    
    # 图1: 各隧道检验批总量对比
    fig1 = px.bar(
        df_sum, x='隧道', y='合计', 
        title="各隧道检验批总量对比",
        text='合计',
        color_discrete_sequence=['#3498db']
    )
    fig1.update_traces(textposition='outside')
    fig1.update_layout(plot_bgcolor='rgba(0,0,0,0)', yaxis_title="总量 (批)")
    
    # 图2: 全项目分部工程占比 (环形图)
    cols_to_sum = [c for c in df_sum.columns if c not in ['隧道', '合计']]
    total_series = df_sum[cols_to_sum].sum().reset_index()
    total_series.columns = ['分部工程', '数量']
    
    fig2 = px.pie(
        total_series, values='数量', names='分部工程',
        title="全项目分部工程占比",
        hole=0.4,
        color_discrete_sequence=px.colors.qualitative.Pastel
    )
    fig2.update_traces(textposition='inside', textinfo='percent+label')
    
    # 图3: 堆叠柱状图
    df_melted = df_sum.melt(id_vars=['隧道'], value_vars=cols_to_sum, 
                            var_name='分部工程', value_name='数量')
    fig3 = px.bar(
        df_melted, x='隧道', y='数量', color='分部工程',
        title="各隧道分部工程详细构成",
        color_discrete_sequence=px.colors.qualitative.Set2,
        barmode='stack'
    )
    fig3.update_layout(plot_bgcolor='rgba(0,0,0,0)')
    
    # 图4: 分项工程频次排行
    df_subitem_chart = df_detail.groupby('分项工程')['检验批编号'].count().reset_index()
    df_subitem_chart.columns = ['分项工程', '频次']
    df_subitem_top = df_subitem_chart.sort_values(by='频次', ascending=True).tail(10)
    
    fig4 = px.bar(
        df_subitem_top, x='频次', y='分项工程', orientation='h',
        title="分项工程验收频次排行 (TOP 10)",
        color_discrete_sequence=['#2ecc71']
    )
    fig4.update_traces(textposition='outside')
    fig4.update_layout(plot_bgcolor='rgba(0,0,0,0)')
    
    return fig1, fig2, fig3, fig4

# =============================================================================
# 7. 检验批计算器 (独立函数，优化缓存)
# =============================================================================
DIVISIONS = {
    '01': {'name': '01 加固处理', 'items': {'01': {'name': '01 危岩处治', 'formula': '每洞口1处', 'main': '-', 'gen': '-'}}},
    '02': {'name': '02 洞口工程', 'items': {
        '01': {'name': '01 边坡、基槽(洞口开挖)', 'formula': '每洞口1批', 'main': '6.2.1~6.2.2', 'gen': '6.2.3~6.2.4'},
        '02': {'name': '02 支护', 'formula': '每洞口3批', 'main': '6.6.1~6.6.2', 'gen': '-'},
        '03': {'name': '03 导向墙(含洞门)', 'formula': '每洞口3批', 'main': '6.4.1~6.4.4', 'gen': '6.4.5~6.4.6'},
        '04': {'name': '04 回填', 'formula': '每洞口1批', 'main': '6.5.1~6.5.2', 'gen': '6.5.3'}}},
    '03': {'name': '03 超前支护', 'items': {
        '01': {'name': '01 超前锚杆', 'formula': '每洞口1批', 'main': '8.8.1~8.8.3', 'gen': '8.8.4~8.8.5'},
        '02': {'name': '02 超前小导管', 'formula': '每洞口1批', 'main': '8.3.1~8.3.4', 'gen': '8.3.5'},
        '03': {'name': '03 超前注浆', 'formula': '每洞口1批', 'main': '8.5.1~8.5.3', 'gen': '8.5.4'}}},
    '04': {'name': '04 洞身开挖', 'items': {
        '01': {'name': '01 CD法', 'formula': '循环数×4步', 'main': '7.2.1~7.2.3', 'gen': '-'},
        '02': {'name': '02 台阶法', 'formula': '循环数×2步', 'main': '7.2.1~7.2.3', 'gen': '-'}}},
    '05': {'name': '05 初期支护', 'items': {
        '01': {'name': '01 锚杆', 'formula': '循环数×4批', 'main': '8.8.1~8.8.3', 'gen': '8.8.4~8.8.5'},
        '02': {'name': '02 钢架', 'formula': '循环数×4批', 'main': '8.9.1~8.9.3', 'gen': '8.9.4'},
        '03': {'name': '03 钢筋网', 'formula': '循环数×4批', 'main': '8.7.1~8.7.2', 'gen': '8.7.3'},
        '04': {'name': '04 喷射混凝土', 'formula': '循环数×4批', 'main': '8.6.1~8.6.3', 'gen': '8.6.4'}}},
    '06': {'name': '06 衬砌工程', 'items': {
        '01': {'name': '01 仰拱(底板)和填充', 'formula': '环数×3', 'main': '9.2.1~9.2.6', 'gen': '9.2.7~9.2.8'},
        '02': {'name': '02 拱墙衬砌', 'formula': '环数×3', 'main': '9.3.1~9.3.7', 'gen': '9.3.8~9.3.10'}}},
    '07': {'name': '07 防水排水', 'items': {
        '01': {'name': '01 防水板', 'formula': '环数', 'main': '10.3.1~10.3.5', 'gen': '10.3.6~10.3.7'},
        '02': {'name': '02 排水管(盲管)', 'formula': '环数', 'main': '10.7.1~10.7.4', 'gen': '10.7.5'},
        '03': {'name': '03 止水带(施工缝)', 'formula': '环数', 'main': '10.5.1~10.5.3', 'gen': '10.5.4'}}},
    '08': {'name': '08 附属工程', 'items': {
        '01': {'name': '01 排水沟', 'formula': '环数', 'main': '10.8.1~10.8.5', 'gen': '10.8.6~10.8.7'},
        '02': {'name': '02 电缆沟', 'formula': '环数', 'main': '12.4.1~12.4.3', 'gen': '12.4.4~12.4.5'},
        '03': {'name': '03 路面装饰', 'formula': '环数', 'main': '-', 'gen': '-'},
        '04': {'name': '04 检修道', 'formula': '环数', 'main': '-', 'gen': '-'}}}
}

# ====== 优化：将计算逻辑改为独立函数，避免类方法缓存问题 ======
def _generate_batch_code(tunnel_id: str, div_code: str, item_code: str, seq: int) -> str:
    """生成检验批编号"""
    return f"{tunnel_id}-{div_code}-{item_code}-{seq:03d}"

def _add_batch(results, tunnel_name, tunnel_id, d, i, seq, remark, start=0, end=0, cycle_num=""):
    """添加检验批记录"""
    mileage_str = "K0+000" if start==0 and end==0 else f"{format_mileage(start)}~{format_mileage(end)}"
    length = 0.0 if start==0 and end==0 else abs(end - start)
    code = _generate_batch_code(tunnel_id, d, i, seq)
    batch = {
        '检验批编号': code, '隧道': tunnel_name,
        '分部工程': DIVISIONS[d]['name'],
        '分项工程': DIVISIONS[d]['items'][i]['name'],
        '具体部位': remark, '里程范围': mileage_str, '长度': round(length, 3),
        '循环数': cycle_num,
        '主控项目条文': DIVISIONS[d]['items'][i]['main'],
        '一般项目条文': DIVISIONS[d]['items'][i]['gen'],
        '备注': remark
    }
    results['divisions'][d]['items'][i]['batches'].append(batch)
    results['all_batches'].append(batch)

def _calculate_cycles_and_rings(tunnel: Tunnel) -> Tuple[int, int, int, int]:
    """计算循环数和环数"""
    cd_cycles = tj_cycles = 0
    for seg in tunnel.segments:
        if seg.method not in ['CD法', '台阶法']:
            continue
        cycles = math.ceil(seg.length / seg.advance_per_cycle) if seg.advance_per_cycle > 0 else 0
        if seg.method == 'CD法':
            cd_cycles += cycles
        else:
            tj_cycles += cycles
    total_cycles = cd_cycles + tj_cycles
    rings = math.ceil(tunnel.total_length / tunnel.trolley_length) if tunnel.trolley_length > 0 else 0
    return cd_cycles, tj_cycles, total_cycles, rings

def _calculate_portal_batches(results, tunnel: Tunnel):
    """计算洞口相关检验批"""
    _add_batch(results, tunnel.name, tunnel.id, '01', '01', 1, '进洞口-危岩处治')
    _add_batch(results, tunnel.name, tunnel.id, '01', '01', 2, '出洞口-危岩处治')
    for d, i_codes in [('02', ['01','04']), ('03', ['01','02','03'])]:
        for ic in i_codes:
            _add_batch(results, tunnel.name, tunnel.id, d, ic, 1, '进洞口')
            _add_batch(results, tunnel.name, tunnel.id, d, ic, 2, '出洞口')
    for idx, sub_item in enumerate(['锚杆', '钢筋网', '喷射混凝土']):
        _add_batch(results, tunnel.name, tunnel.id, '02', '02', idx+1, f'进洞口-{sub_item}')
        _add_batch(results, tunnel.name, tunnel.id, '02', '02', idx+4, f'出洞口-{sub_item}')
    for idx, sub_item in enumerate(['模板', '钢筋', '混凝土']):
        _add_batch(results, tunnel.name, tunnel.id, '02', '03', idx+1, f'进洞口-{sub_item}')
        _add_batch(results, tunnel.name, tunnel.id, '02', '03', idx+4, f'出洞口-{sub_item}')

def _calculate_excavation_and_support_batches(results, tunnel: Tunnel, cd_cycles: int, tj_cycles: int):
    """计算开挖和支护检验批"""
    dir_sign = 1 if tunnel.direction == "正向" else -1
    seq_counter = 1
    for seg in tunnel.segments:
        if seg.method not in ['CD法', '台阶法']:
            continue
        cycles = math.ceil(seg.length / seg.advance_per_cycle) if seg.advance_per_cycle > 0 else 0
        ic_exc = '01' if seg.method == 'CD法' else '02'
        step_names = ['左上','右上','左下','右下'] if seg.method == 'CD法' else ['上台阶','下台阶']
        seg_start = min(seg.start_mileage, seg.end_mileage) if dir_sign == 1 else max(seg.start_mileage, seg.end_mileage)
        seg_end = max(seg.start_mileage, seg.end_mileage) if dir_sign == 1 else min(seg.start_mileage, seg.end_mileage)
        for c in range(cycles):
            start = seg_start + c * seg.advance_per_cycle * dir_sign
            end = start + seg.advance_per_cycle * dir_sign
            if dir_sign == 1:
                end = min(end, seg_end)
            else:
                end = max(end, seg_end)
            for s_idx, s_name in enumerate(step_names):
                seq = seq_counter
                seq_counter += 1
                _add_batch(results, tunnel.name, tunnel.id, '04', ic_exc, seq, f"{seg.name}-{s_name}", start, end, c+1)
                for ic_sup in ['01','02','03','04']:
                    _add_batch(results, tunnel.name, tunnel.id, '05', ic_sup, seq, f"{seg.name}-{s_name}", start, end, c+1)

def _calculate_lining_and_auxiliary_batches(results, tunnel: Tunnel, rings: int):
    """计算衬砌和附属检验批"""
    if tunnel.trolley_length <= 0:
        return
    dir_sign = 1 if tunnel.direction == "正向" else -1
    base_t_start = min(tunnel.start_mileage, tunnel.end_mileage) if dir_sign == 1 else max(tunnel.start_mileage, tunnel.end_mileage)
    base_t_end = max(tunnel.start_mileage, tunnel.end_mileage) if dir_sign == 1 else min(tunnel.start_mileage, tunnel.end_mileage)
    for r in range(rings):
        start = base_t_start + r * tunnel.trolley_length * dir_sign
        if dir_sign == 1:
            end = min(start + tunnel.trolley_length, base_t_end)
        else:
            end = max(start - tunnel.trolley_length, base_t_end)
        for idx, sub_item in enumerate(['模板', '钢筋', '混凝土']):
            seq = r * 3 + idx + 1
            _add_batch(results, tunnel.name, tunnel.id, '06', '01', seq, f'仰拱-{sub_item}', start, end, r+1)
            _add_batch(results, tunnel.name, tunnel.id, '06', '02', seq, f'拱墙-{sub_item}', start, end, r+1)
        for ic in ['01','02','03']:
            _add_batch(results, tunnel.name, tunnel.id, '07', ic, r+1, '防排水', start, end, r+1)
        for ic in ['01','02','03','04']:
            _add_batch(results, tunnel.name, tunnel.id, '08', ic, r+1, '附属', start, end, r+1)

def _generate_subitem_summary(results, tunnel: Tunnel, cd_cycles: int, tj_cycles: int, total_cycles: int, rings: int):
    """生成分部分项汇总"""
    subitem_res = []
    total = 0
    for d_code, d_data in results['divisions'].items():
        d_total = 0
        for i_code, i_data in d_data['items'].items():
            count = len(i_data['batches'])
            if count == 0:
                continue
            name = i_data['name']
            rule = DIVISIONS[d_code]['items'][i_code]['formula']
            calc_base = "-"
            if '洞口' in rule:
                calc_base = "2 个洞口"
                calc_str = f"{calc_base} × 3 批/洞口 = {count} 批" if '3批' in rule else f"{calc_base} × 1 批/洞口 = {count} 批"
            elif 'CD法' in name:
                calc_base = f"{cd_cycles} 循环"
                calc_str = f"{calc_base} × 4 步/循环 = {count} 批"
            elif '台阶法' in name:
                calc_base = f"{tj_cycles} 循环"
                calc_str = f"{calc_base} × 2 步/循环 = {count} 批"
            elif '循环' in rule:
                calc_base = f"{total_cycles} 循环"
                calc_str = f"{calc_base} × 4 批/循环 = {count} 批"
            elif '环数×3' in rule:
                calc_base = f"{rings} 衬砌环"
                calc_str = f"{calc_base} × 3 批/环 = {count} 批"
            elif '环数' in rule:
                calc_base = f"{rings} 衬砌环"
                calc_str = f"{calc_base} × 1 批/环 = {count} 批"
            else:
                calc_str = f"按部位累加 = {count} 批"
            subitem_res.append({
                '隧道': tunnel.name,
                '分部工程': d_data['name'],
                '分项工程': name,
                '计算基数(循环/环/洞口)': calc_base,
                '检验批计算式': calc_str,
                '检验批数量': count
            })
            d_total += count
            total += count
        results['summary'][d_data['name']] = d_total
    results['summary']['合计'] = total
    return subitem_res

def calculate_single_tunnel(tunnel: Tunnel) -> Tuple[Dict, List]:
    """计算单个隧道的检验批"""
    results = {'tunnel_name': tunnel.name, 'divisions': {}, 'summary': {}, 'all_batches': []}
    for d_code, d_info in DIVISIONS.items():
        results['divisions'][d_code] = {'name': d_info['name'], 'items': {}, 'total_batches': 0}
        for i_code, i_info in d_info['items'].items():
            results['divisions'][d_code]['items'][i_code] = {'name': i_info['name'], 'batches': [], 'count': 0}
    cd_cycles, tj_cycles, total_cycles, rings = _calculate_cycles_and_rings(tunnel)
    _calculate_portal_batches(results, tunnel)
    _calculate_excavation_and_support_batches(results, tunnel, cd_cycles, tj_cycles)
    _calculate_lining_and_auxiliary_batches(results, tunnel, rings)
    subitem_res = _generate_subitem_summary(results, tunnel, cd_cycles, tj_cycles, total_cycles, rings)
    return results, subitem_res

# ====== 优化：使用独立函数作为缓存目标 ======
@st.cache_data(ttl=3600, show_spinner=False)
def calculate_project_batches(project: Project) -> Tuple[int, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """计算整个工程的检验批 - 优化缓存版本
    
    注意：使用独立函数而非类方法，确保缓存正常工作
    """
    grand_total = 0
    summary_list = []
    all_batches_flat = []
    subitem_summary_flat = []
    
    for tunnel in project.tunnels:
        tunnel_res, subitem_res = calculate_single_tunnel(tunnel)
        sum_dict = {'隧道': tunnel.name}
        sum_dict.update(tunnel_res['summary'])
        summary_list.append(sum_dict)
        grand_total += tunnel_res['summary']['合计']
        all_batches_flat.extend(tunnel_res['all_batches'])
        subitem_summary_flat.extend(subitem_res)
    
    df_sum = pd.DataFrame(summary_list)
    df_detail = pd.DataFrame(all_batches_flat)
    df_subitem = pd.DataFrame(subitem_summary_flat)
    
    return grand_total, df_sum, df_subitem, df_detail

# =============================================================================
# 8. 数据验证器
# =============================================================================
class DataValidator:
    """数据验证器"""
    
    @staticmethod
    def validate_tunnel_segment_data(row: pd.Series, row_index: int) -> List[str]:
        """验证隧道段落数据"""
        errors = []
        name = str(row.get('部位名称', '')).strip()
        if not name or name == 'nan':
            errors.append(f"第{row_index+1}行: 部位名称不能为空")
        
        method = str(row.get('工法', '')).strip()
        valid_methods = ['明挖', 'CD法', '台阶法', '洞口', '其他']
        if method and method not in valid_methods:
            errors.append(f"第{row_index+1}行: 工法 '{method}' 无效")
        
        try:
            length = float(row.get('长度(m)', 0))
            if length <= 0:
                errors.append(f"第{row_index+1}行: 长度必须大于0")
        except (ValueError, TypeError):
            errors.append(f"第{row_index+1}行: 长度格式错误")
        
        return errors

# =============================================================================
# 9. PDF渲染器 (优化版 - 增加文件大小限制)
# =============================================================================
MAX_PDF_SIZE_MB = 15  # 最大15MB

def render_pdf_viewer(pdf_bytes: bytes, filename: str = "TB10417-2018.pdf"):
    """渲染PDF查看器 - 优化版
    
    优化内容：
    1. 增加文件大小检查 (>15MB仅提供下载)
    2. 优化加载提示
    """
    file_size_mb = len(pdf_bytes) / (1024 * 1024)
    
    # 始终提供下载按钮
    st.download_button(
        label="📥 下载PDF文件",
        data=pdf_bytes,
        file_name=filename,
        mime="application/pdf",
        use_container_width=True
    )
    
    # ====== 优化：文件大小限制 ======
    if file_size_mb > MAX_PDF_SIZE_MB:
        st.warning(f"⚠️ 文件较大 ({file_size_mb:.2f} MB)，在线预览已禁用，请下载后使用专业PDF阅读器查看。")
        st.info(f"💡 提示：如需在线预览，请使用小于 {MAX_PDF_SIZE_MB} MB 的文件。")
        return
    
    # 小文件才显示预览
    with st.spinner("正在加载PDF预览..."):
        base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
        pdf_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ margin: 0; padding: 0; overflow: hidden; }}
                iframe {{ width: 100%; height: 850px; border: none; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }}
                .pdf-container {{ padding: 10px; background: #f5f5f5; border-radius: 10px; }}
            </style>
        </head>
        <body>
            <div class="pdf-container">
                <iframe id="pdf-frame"></iframe>
            </div>
            <script>
                const b64Data = '{base64_pdf}';
                const byteCharacters = atob(b64Data);
                const byteArrays = [];
                const sliceSize = 512;
                for (let offset = 0; offset < byteCharacters.length; offset += sliceSize) {{
                    const slice = byteCharacters.slice(offset, offset + sliceSize);
                    const byteNumbers = new Array(slice.length);
                    for (let i = 0; i < slice.length; i++) {{
                        byteNumbers[i] = slice.charCodeAt(i);
                    }}
                    const byteArray = new Uint8Array(byteNumbers);
                    byteArrays.push(byteArray);
                }}
                const blob = new Blob(byteArrays, {{type: 'application/pdf'}});
                const blobUrl = URL.createObjectURL(blob);
                document.getElementById('pdf-frame').src = blobUrl;
            </script>
        </body>
        </html>
        """
        components.html(pdf_html, height=900)

def get_pdf_bytes() -> Optional[bytes]:
    """获取PDF字节数据 - 支持多路径搜索"""
    import sys
    
    # 获取应用运行时的可能路径
    app_dir = os.path.dirname(os.path.abspath(sys.argv[0])) if hasattr(sys, 'argv') else os.getcwd()
    
    # 尝试多个可能的路径
    possible_paths = [
        "TB10417-2018.pdf",  # 当前目录
        os.path.join(app_dir, "TB10417-2018.pdf"),  # 应用目录
        os.path.join(os.path.dirname(__file__), "TB10417-2018.pdf"),  # 脚本目录
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "TB10417-2018.pdf"),  # 上级目录
        "C:\\Users\\Lingk\\Desktop\\streamlit_app\\TB10417-2018.pdf",  # 绝对路径
        "C:\\Users\\Lingk\\Desktop\\streamlit_app\\optimized_app\\TB10417-2018.pdf",  # 优化版目录
    ]
    
    for pdf_file_path in possible_paths:
        if os.path.exists(pdf_file_path):
            try:
                with open(pdf_file_path, "rb") as f:
                    return f.read()
            except Exception as e:
                continue
    
    return None

# =============================================================================
# 10. 主程序 GUI (全量优化版)
# =============================================================================
def main():
    """主程序入口 - 全量优化版"""
    # 初始化session state
    if 'projects' not in st.session_state:
        st.session_state.projects = [create_demo_project()]
    if 'current_project_index' not in st.session_state:
        st.session_state.current_project_index = 0
    if 'last_result' not in st.session_state:
        st.session_state.last_result = None
    
    try:
        current_project = st.session_state.projects[st.session_state.current_project_index]
    except IndexError:
        st.session_state.current_project_index = 0
        current_project = st.session_state.projects[0]

    # ====== UI优化：侧边栏 ======
    with st.sidebar:
        st.title("🏗️ 工程管理")
        project_names = [p.name for p in st.session_state.projects]
        selected_idx = st.selectbox(
            "当前工作工程:",
            range(len(project_names)),
            format_func=lambda x: project_names[x],
            index=st.session_state.current_project_index
        )
        st.session_state.current_project_index = selected_idx
        
        # 工程重命名
        new_proj_name = st.text_input("📝 重命名工程:", current_project.name)
        if new_proj_name and new_proj_name != current_project.name:
            current_project.name = new_proj_name
            st.success(f"工程已重命名为: {new_proj_name}")
            st.rerun()
        
        # 工程操作按钮
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            if st.button("➕ 新建工程", use_container_width=True):
                default_seg = TunnelSegment("首段施工", "台阶法", 100, 0, 100, 0.8, 2, 2, 12.0, 1.6, "复合衬砌")
                default_tunnel = Tunnel("T1", "一号隧道", 100, 0, 100, "K0+000", "K0+100", True, 12.0, "正向", [default_seg])
                st.session_state.projects.append(
                    Project(name=f"新建工程_{len(project_names)+1}", created_at=datetime.now().strftime("%Y-%m-%d"), tunnels=[default_tunnel])
                )
                st.session_state.current_project_index = len(st.session_state.projects) - 1
                st.success("新建工程创建成功!")
                st.rerun()
        
        with col_p2:
            if st.button("🗑️ 删除工程", use_container_width=True) and len(st.session_state.projects) > 1:
                st.session_state.projects.pop(selected_idx)
                st.session_state.current_project_index = 0
                st.warning("工程已删除")
                st.rerun()
        
        # 数据导入/导出
        with st.expander("📂 数据导入/导出", expanded=False):
            json_data = export_project_to_json(current_project)
            st.download_button(
                "📤 导出当前工程 (.json)",
                json_data,
                f"{current_project.name}_配置.json",
                "application/json",
                use_container_width=True
            )
            
            uploaded_file = st.file_uploader("📥 导入工程配置", type=['json'])
            if uploaded_file is not None:
                if st.button("✅ 确认导入", use_container_width=True):
                    imported_proj = import_project_from_json(uploaded_file.getvalue().decode("utf-8"))
                    if imported_proj:
                        st.session_state.projects.append(imported_proj)
                        st.session_state.current_project_index = len(st.session_state.projects) - 1
                        st.success(f"成功导入工程: {imported_proj.name}")
                        st.rerun()
        
        st.markdown("---")
        
        # ====== 功能模块导航 - 可见列表样式 ======
        st.markdown("""
        <style>
        .nav-button {
            display: block;
            width: 100%;
            padding: 12px 16px;
            margin: 4px 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 8px;
            text-align: left;
            font-size: 15px;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        .nav-button:hover {
            transform: translateX(5px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }
        .nav-button.active {
            background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        }
        .nav-section {
            background: #f8f9fa;
            padding: 10px;
            border-radius: 10px;
            margin: 10px 0;
        }
        .nav-title {
            font-size: 16px;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 8px;
            padding-left: 5px;
        }
        </style>
        """, unsafe_allow_html=True)
        
        st.markdown('<div class="nav-section"><div class="nav-title">🛠️ 功能模块</div>', unsafe_allow_html=True)
        
        # 使用radio按钮提供可见导航
        page = st.radio(
            "选择功能模块:",
            ["📋 参数配置", "📊 检验批计算", "📉 统计看板", "📖 标准查阅"],
            label_visibility="collapsed",
            captions=["隧道参数、工法设置", "智能计算检验批", "交互式数据看板", "TB10417标准查阅"]
        )
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # 优化说明
        st.markdown("---")
        st.caption("🚀 v15.0 优化版 | Plotly图表 | 内存优化")

    # ===== 页面：参数配置 =====
    if page == "📋 参数配置":
        st.subheader(f"📋 参数配置 - {current_project.name}")
        
        if not current_project.tunnels:
            st.warning("当前工程暂无隧道，请添加。")
            if st.button("➕ 添加首条隧道"):
                default_seg = TunnelSegment("首段施工", "台阶法", 100, 0, 100, 0.8, 2, 2, 12.0, 1.6, "复合衬砌")
                current_project.tunnels.append(
                    Tunnel("NEW", "新建隧道", 100, 0, 100, "K0", "K1", True, 12.0, "正向", [default_seg])
                )
                st.success("隧道添加成功!")
                st.rerun()
            return
        
        # 隧道选择
        c1, c2, c3 = st.columns([3, 1, 1])
        with c1:
            tunnel_names = [t.name for t in current_project.tunnels]
            selected_tunnel_name = st.selectbox("选择要编辑的隧道:", tunnel_names)
            target_tunnel = next(t for t in current_project.tunnels if t.name == selected_tunnel_name)
        
        with c2:
            st.write(""); st.write("")
            if st.button("➕ 新增隧道", use_container_width=True):
                default_seg = TunnelSegment("新建段落", "台阶法", 100, 0, 100, 0.8, 2, 2, 12.0, 1.6, "复合衬砌")
                current_project.tunnels.append(
                    Tunnel(f"T{len(current_project.tunnels)+1}", "新建隧道", 100, 0, 100, "K0", "K1", True, 12.0, "正向", [default_seg])
                )
                st.success("隧道添加成功!")
                st.rerun()
        
        with c3:
            st.write(""); st.write("")
            if st.button("🗑️ 删除当前隧道", use_container_width=True) and len(current_project.tunnels) > 1:
                current_project.tunnels.remove(target_tunnel)
                st.warning("隧道已删除")
                st.rerun()
        
        # 1. 隧道工法纵断面图
        st.markdown("##### 1. 隧道工法纵断面图")
        tab1, tab2 = st.tabs(["🎨 Plotly交互版", "📊 Matplotlib版本"])
        with tab1:
            plotly_fig = render_plotly_profile(target_tunnel.segments, target_tunnel.name, target_tunnel.direction)
            if plotly_fig:
                st.plotly_chart(plotly_fig, use_container_width=True)
            else:
                st.info("暂无段落数据")
        
        with tab2:
            fig = draw_enhanced_profile(target_tunnel.segments, target_tunnel.name, target_tunnel.direction)
            if fig:
                st.pyplot(fig)
                plt.close(fig)  # 显示后释放内存
            else:
                st.info("暂无段落数据")
        
        st.markdown("---")
        
        # ====== UI优化：使用st.form减少重运行 ======
        # 2. 基础信息编辑
        col_basic, col_seg = st.columns([1, 4])
        
        with col_basic:
            st.markdown("##### 2. 基础信息")
            with st.form("basic_info"):
                new_id = st.text_input("隧道ID", target_tunnel.id)
                new_name = st.text_input("名称", target_tunnel.name)
                new_dir = st.radio(
                    "掘进方向",
                    ["正向 (里程递增)", "反向 (里程递减)"],
                    index=0 if target_tunnel.direction == "正向" else 1
                )
                
                if not target_tunnel.segments:
                    st_val, ed_val = 0.0, 100.0
                else:
                    st_val = min(s.start_mileage for s in target_tunnel.segments)
                    ed_val = max(s.end_mileage for s in target_tunnel.segments)
                
                st.text_input("总体起点桩号 (自动更新)", format_mileage(st_val), disabled=True)
                st.text_input("总体终点桩号 (自动更新)", format_mileage(ed_val), disabled=True)
                st.number_input("设计全长(m) (自动更新)", value=float(abs(ed_val - st_val)), disabled=True)
                new_trolley = st.number_input("台车长度(m)", value=float(target_tunnel.trolley_length), min_value=0.1, max_value=100.0, step=0.1)
                
                if st.form_submit_button("💾 保存基础信息"):
                    errors = DataValidator.validate_tunnel_basic_info(new_id, new_name, new_trolley) if hasattr(DataValidator, 'validate_tunnel_basic_info') else []
                    if errors:
                        for error in errors:
                            st.error(error)
                    else:
                        target_tunnel.id = new_id
                        target_tunnel.name = new_name
                        target_tunnel.direction = "正向" if "正向" in new_dir else "反向"
                        target_tunnel.trolley_length = new_trolley
                        st.success("基础信息更新成功!")
                        st.rerun()
        
        with col_seg:
            st.markdown("##### 3. 施工段落表")
            st.info("💡 **智能连缀推算**：只需在第1行输入【起始桩号】和各段【长度】，系统会自动计算所有起止桩号！")
            
            expected_columns = ["部位名称", "工法", "起始桩号", "长度(m)", "终止桩号", "衬砌类型", "榀数/环", "榀距(m)", "进尺(m)", "步骤数"]
            if not target_tunnel.segments:
                df_seg = pd.DataFrame(columns=expected_columns)
            else:
                seg_data = []
                for s in target_tunnel.segments:
                    seg_data.append({
                        "部位名称": s.name,
                        "工法": s.method,
                        "起始桩号": format_mileage(s.start_mileage),
                        "长度(m)": float(s.length),
                        "终止桩号": format_mileage(s.end_mileage),
                        "衬砌类型": s.lining_type,
                        "榀数/环": int(s.frames_per_ring),
                        "榀距(m)": float(s.frame_spacing),
                        "进尺(m)": float(s.advance_per_cycle),
                        "步骤数": int(s.steps)
                    })
                df_seg = pd.DataFrame(seg_data)[expected_columns]
            
            edited_df = st.data_editor(
                df_seg,
                num_rows="dynamic",
                use_container_width=True,
                height=400,
                column_config={
                    "工法": st.column_config.SelectboxColumn(
                        options=["明挖", "CD法", "台阶法", "洞口", "其他"],
                        help="选择施工工法"
                    ),
                    "起始桩号": st.column_config.TextColumn(help="只需输入第一行的起始桩号"),
                    "终止桩号": st.column_config.TextColumn(disabled=True, help="系统自动推算"),
                    "进尺(m)": st.column_config.NumberColumn(disabled=True, help="系统自动推算"),
                    "步骤数": st.column_config.NumberColumn(disabled=True, help="随工法自动锁定"),
                }
            )
            
            if st.button("💾 保存段落 & 触发智能连缀推算", type="primary", use_container_width=True):
                all_errors = []
                new_segs = []
                dir_sign = 1 if target_tunnel.direction == "正向" else -1
                prev_end_m = None
                
                for idx, row in edited_df.iterrows():
                    row_errors = DataValidator.validate_tunnel_segment_data(row, idx)
                    if row_errors:
                        all_errors.extend(row_errors)
                        continue
                    
                    try:
                        def get_val(val, default):
                            return default if pd.isna(val) else val
                        
                        if prev_end_m is None:
                            start_str = str(get_val(row.get('起始桩号'), ""))
                            start_m = parse_mileage(start_str) if start_str else target_tunnel.start_mileage
                        else:
                            start_m = prev_end_m
                        
                        length = float(get_val(row.get('长度(m)'), 100.0))
                        if length <= 0.001:
                            length = 100.0
                        
                        end_m = start_m + (length * dir_sign)
                        prev_end_m = end_m
                        
                        method = str(get_val(row.get('工法'), "台阶法"))
                        frames = int(get_val(row.get('榀数/环'), 2))
                        spacing = float(get_val(row.get('榀距(m)'), 0.8))
                        
                        if frames > 0 and spacing > 0:
                            advance = round(frames * spacing, 3)
                        else:
                            advance = 1.6
                        
                        if 'CD' in method:
                            steps = 4
                        elif '台阶' in method:
                            steps = 2
                        elif '明挖' in method:
                            steps = 1
                        else:
                            steps = 2
                        
                        name = str(get_val(row.get('部位名称'), f"段落_{idx+1}"))
                        if not name or name == 'nan':
                            name = f"段落_{idx+1}"
                        
                        new_segs.append(TunnelSegment(
                            name=name, method=method, length=length,
                            start_mileage=start_m, end_mileage=end_m,
                            advance_per_cycle=advance, lining_type=str(get_val(row.get('衬砌类型'), "")),
                            steps=steps, frames_per_ring=frames, frame_spacing=spacing,
                            trolley_length=target_tunnel.trolley_length
                        ))
                    except Exception as e:
                        all_errors.append(f"第 {idx+1} 行数据解析错误: {str(e)}")
                
                if all_errors:
                    st.error("发现以下错误，请修正后重试:")
                    for error in all_errors:
                        st.markdown(f"<div class='error-message'>{error}</div>", unsafe_allow_html=True)
                else:
                    new_segs.sort(key=lambda x: min(x.start_mileage, x.end_mileage))
                    target_tunnel.segments = new_segs
                    
                    if new_segs:
                        if dir_sign == 1:
                            target_tunnel.start_mileage = new_segs[0].start_mileage
                            target_tunnel.end_mileage = new_segs[-1].end_mileage
                        else:
                            target_tunnel.start_mileage = new_segs[-1].end_mileage
                            target_tunnel.end_mileage = new_segs[0].start_mileage
                        
                        target_tunnel.total_length = sum(s.length for s in new_segs)
                    
                    st.success("✅ 智能连缀计算完成!")
                    st.rerun()

    # ===== 页面：检验批计算 =====
    elif page == "📊 检验批计算":
        st.markdown(f"<h2>📊 检验批计算 - {current_project.name}</h2>", unsafe_allow_html=True)
        st.info("📌 **智能推演说明**：系统已自动提取全线【开挖循环数】与【二衬浇筑环数】，生成带计算式溯源的分部分项表！")
        
        # ====== 优化：使用缓存计算 ======
        with st.spinner("🚀 正在执行智能计算..."):
            total, df_sum, df_subitem, df_detail = calculate_project_batches(current_project)
            st.session_state.last_result = (total, df_sum, df_subitem, df_detail)
        
        total, df_sum, df_subitem, df_detail = st.session_state.last_result
        
        # 关键指标卡片
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(f'<div class="metric-card bg-blue"><div class="metric-title">全线检验批总数</div><div class="metric-value">{total:,}</div></div>', unsafe_allow_html=True)
        with c2:
            ratio = df_sum['05 初期支护'].sum() / total if total > 0 and '05 初期支护' in df_sum else 0
            st.markdown(f'<div class="metric-card bg-green"><div class="metric-title">初期支护 (占比)</div><div class="metric-value">{ratio:.1%}</div></div>', unsafe_allow_html=True)
        with c3:
            exc_val = df_sum["04 洞身开挖"].sum() if "04 洞身开挖" in df_sum else 0
            st.markdown(f'<div class="metric-card bg-purple"><div class="metric-title">洞身开挖</div><div class="metric-value">{exc_val:,}</div></div>', unsafe_allow_html=True)
        with c4:
            lining_val = df_sum["06 衬砌工程"].sum() if "06 衬砌工程" in df_sum else 0
            st.markdown(f'<div class="metric-card bg-orange"><div class="metric-title">二衬工程</div><div class="metric-value">{lining_val:,}</div></div>', unsafe_allow_html=True)
        
        # 段落统计
        segment_stats = []
        for tunnel in current_project.tunnels:
            for seg in tunnel.segments:
                if seg.method in ['CD法', '台阶法']:
                    cycles = math.ceil(seg.length / seg.advance_per_cycle) if seg.advance_per_cycle > 0 else 0
                    steps = 4 if seg.method == 'CD法' else 2
                elif seg.method == '明挖':
                    cycles = 1
                    steps = 1
                else:
                    cycles = 0
                    steps = 0
                
                if seg.method in ['CD法', '台阶法']:
                    div_04 = cycles * steps
                    div_05 = cycles * steps * 4
                else:
                    div_04 = 0
                    div_05 = 0
                
                total_batches = div_04 + div_05
                
                if seg.method == 'CD法':
                    formula = f"{cycles}循环×4步×1批={div_04}批 | {cycles}循环×4步×4项={div_05}批"
                elif seg.method == '台阶法':
                    formula = f"{cycles}循环×2步×1批={div_04}批 | {cycles}循环×2步×4项={div_05}批"
                else:
                    formula = "-"
                
                segment_stats.append({
                    '隧道': tunnel.name, '部位名称': seg.name, '施工工法': seg.method,
                    '段落长度(m)': round(seg.length, 3),
                    '起点里程': format_mileage(min(seg.start_mileage, seg.end_mileage)),
                    '终点里程': format_mileage(max(seg.start_mileage, seg.end_mileage)),
                    '进尺(m)': seg.advance_per_cycle,
                    '循环数': cycles if seg.method in ['CD法', '台阶法'] else '-',
                    '04洞身开挖': div_04, '05初期支护': div_05,
                    '检验批总数': total_batches, '计算说明': formula
                })
        
        df_segments = pd.DataFrame(segment_stats)
        
        # 显示表格
        st.markdown("### 1. 分部工程汇总表")
        st.dataframe(df_sum, use_container_width=True)
        
        st.markdown("### 2. 隧道段落统计表")
        st.dataframe(df_segments, use_container_width=True)
        
        st.markdown("### 3. 分部分项汇总表 (带基数与计算说明)")
        st.dataframe(df_subitem, use_container_width=True)
        
        # 数据导出
        st.markdown("### 4. 数据导出区")
        c_d1, c_d2, c_d3 = st.columns(3)
        with c_d1:
            st.download_button("📥 导出【分部汇总表】", df_sum.to_csv(index=False, float_format='%.3f').encode('utf-8-sig'), f"{current_project.name}_分部汇总.csv", "text/csv", use_container_width=True)
        with c_d2:
            st.download_button("📥 导出【分部分项汇总表】", df_subitem.to_csv(index=False).encode('utf-8-sig'), f"{current_project.name}_分部分项汇总.csv", "text/csv", use_container_width=True)
        with c_d3:
            st.download_button("📥 导出【详细明细表】", df_detail.to_csv(index=False, float_format='%.3f').encode('utf-8-sig'), f"{current_project.name}_明细.csv", "text/csv", use_container_width=True)

    # ===== 页面：统计看板 (Plotly升级版) =====
    elif page == "📉 统计看板":
        st.markdown("<h2>📉 项目质量管控数据看板</h2>", unsafe_allow_html=True)
        
        # 使用缓存计算
        with st.spinner("🚀 正在准备可视化数据..."):
            total, df_sum, df_subitem, df_detail = calculate_project_batches(current_project)
            st.session_state.last_result = (total, df_sum, df_subitem, df_detail)
        
        _, df_sum, _, df_detail = st.session_state.last_result
        
        # ====== 优化：使用Plotly交互图表 ======
        st.markdown("#### 🔹 Plotly交互式看板")
        
        # 检查Plotly是否可用
        try:
            import plotly.express as px
            plotly_available = True
        except ImportError:
            st.warning("⚠️ Plotly未安装，将使用Matplotlib。安装命令: pip install plotly")
            plotly_available = False
        
        if plotly_available:
            # 渲染Plotly图表
            fig1, fig2, fig3, fig4 = render_plotly_dashboard(df_sum, df_detail)
            
            col1, col2 = st.columns(2)
            with col1:
                st.plotly_chart(fig1, use_container_width=True)
            with col2:
                st.plotly_chart(fig2, use_container_width=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            col3, col4 = st.columns(2)
            with col3:
                st.plotly_chart(fig3, use_container_width=True)
            with col4:
                st.plotly_chart(fig4, use_container_width=True)
            
            st.info("💡 **交互提示**：将鼠标悬停在图表上可查看详细数据，点击图例可筛选显示，点击图表可缩放查看")
        else:
            # 回退到Matplotlib（带内存优化）
            st.markdown("#### 🔹 Matplotlib版本")
            color_palette = ['#4E79A7', '#F28E2B', '#E15759', '#76B7B2', '#59A14F', '#EDC948', '#B07AA1']
            
            fig1, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6), dpi=120)
            bars = ax1.bar(df_sum['隧道'], df_sum['合计'], color='#3498db', width=0.5)
            ax1.set_title("各隧道检验批总量对比", pad=20, fontsize=14, fontweight='bold')
            for bar in bars:
                ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + (bar.get_height()*0.02), f"{int(bar.get_height()):,}", ha='center', va='bottom', fontsize=11, fontweight='bold')
            ax1.spines['top'].set_visible(False)
            ax1.spines['right'].set_visible(False)
            
            cols_to_sum = [c for c in df_sum.columns if c not in ['隧道', '合计']]
            total_series = df_sum[cols_to_sum].sum()
            wedges, texts, autotexts = ax2.pie(total_series, labels=total_series.index, autopct='%1.1f%%', startangle=140, pctdistance=0.85, colors=color_palette)
            ax2.add_artist(plt.Circle((0, 0), 0.65, fc='white'))
            ax2.set_title("全项目分部工程占比", pad=20, fontsize=14, fontweight='bold')
            plt.tight_layout()
            st.pyplot(fig1)
            # ====== 优化：释放内存 ======
            plt.close(fig1)
        
        # 数据透视表
        st.markdown("#### 🔹 数据透视表")
        pivot_table = df_detail.pivot_table(index=['隧道', '分部工程'], values='检验批编号', aggfunc='count', fill_value=0).reset_index()
        pivot_table = pivot_table.rename(columns={'检验批编号': '检验批数量'})
        st.dataframe(pivot_table, use_container_width=True)

    # ===== 页面：标准查阅 (PDF优化版) =====
    elif page == "📖 标准查阅":
        st.markdown("<h2>📖 铁路隧道工程施工质量验收标准查阅</h2>", unsafe_allow_html=True)
        st.info("💡 系统已全面内置《TB 10417-2018》标准条文。提供三种查阅方式：全文在线阅读、全局关键字检索、PDF原生电子书阅览。")
        
        full_text_dict = get_tb10417_full_text()
        tab1, tab2, tab3 = st.tabs(["📚 全文在线阅读", "🔍 全局智能检索", "📄 原版 PDF 阅览"])
        
        with tab1:
            col_sel, _ = st.columns([1, 2])
            with col_sel:
                selected_chapter = st.selectbox("📌 选择章节快速跳转:", list(full_text_dict.keys()))
            st.markdown(f"<div class='standard-text'>{full_text_dict[selected_chapter]}</div>", unsafe_allow_html=True)
        
        with tab2:
            search_query = st.text_input("🔍 输入检索词 (如: 超挖, 喷射混凝土, 检验批)")
            if search_query:
                found = False
                for chapter, content in full_text_dict.items():
                    if search_query in content:
                        found = True
                        st.markdown(f"#### 📍 【{chapter}】")
                        highlighted_content = content.replace(search_query, f"<span class='highlight'>{search_query}</span>")
                        paragraphs = highlighted_content.split('\n')
                        for p in paragraphs:
                            if f"<span class='highlight'>{search_query}</span>" in p:
                                st.markdown(f"<div class='standard-text' style='margin-bottom: 10px; padding: 15px;'>{p}</div>", unsafe_allow_html=True)
                if not found:
                    st.warning(f"未在内置标准库中检索到包含「{search_query}」的条款。")
        
        with tab3:
            st.write("📖 **原版 PDF 在线阅览** (支持缩放、打印)")
            
            pdf_bytes = get_pdf_bytes()
            
            if pdf_bytes:
                render_pdf_viewer(pdf_bytes, "TB10417-2018铁路隧道工程施工质量验收标准.pdf")
            else:
                st.warning("⚠️ 系统未能找到内置的 PDF 文件 `TB10417-2018.pdf`。")
                st.info("""
                💡 **解决方案**： 
                1. 将您的规范 PDF 重命名为 `TB10417-2018.pdf`
                2. 放置和在应用同一目录下
                3. 重新启动应用
                """)
                
                uploaded_pdf = st.file_uploader("📥 手动上传规范原版 PDF", type=['pdf'])
                if uploaded_pdf is not None:
                    render_pdf_viewer(uploaded_pdf.read(), uploaded_pdf.name)

if __name__ == "__main__":
    main()
