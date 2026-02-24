"""
隧道工程检验批划分系统 Pro v16.9 (极致分项对齐版)
==========================================
优化内容：
1. 【完美对齐】公路规范下，2、洞口工程精确输出7个分项；4、洞身衬砌精确输出11个分项，杜绝任何冗余子项！
2. 架构升级：将庞大的标准文本、默认工程配置剥离至 standards_text.py 和 default_config.py，主代码极度轻量。
3. 归口逻辑：车行横通道作为独立的单位工程，原汁原味地划入其专属的1-6分部。
4. 全量恢复：100% 恢复 v15.0 中 Plotly、Matplotlib 的高级美化和交互（阴影、进度条文字、悬停提示等）。

作者: 编码助手
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
import copy
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import streamlit.components.v1 as components

# =============================================================================
# [核心引入] 导入外部静态配置，为代码大幅瘦身
# =============================================================================
try:
    from standards_text import TB10417_TEXT, JTG_F80_1_TEXT, TB10753_TEXT
    from default_config import RAILWAY_DIVISIONS, HIGHWAY_DIVISIONS, HIGH_SPEED_RAILWAY_DIVISIONS, ZK_DATA, YK_DATA, AK_DATA, BK_DATA, HTD_DATA
except ImportError:
    st.error("⚠️ 缺失依赖文件！请确保当前目录下存在 `standards_text.py` 和 `default_config.py` 文件。")
    st.stop()

# =============================================================================
# 0. 页面与样式配置
# =============================================================================
st.set_page_config(page_title="隧道工程检验批划分系统 Pro v16.9", page_icon="🚇", layout="wide", initial_sidebar_state="expanded")

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
    .bg-blue { background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); }
    .bg-green { background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%); }
    .bg-purple { background: linear-gradient(135deg, #c471ed 0%, #f64f59 100%); }
    .bg-orange { background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); }
    h3 { margin-top: 1.5rem !important; margin-bottom: 1rem !important; color: #2c3e50;}
    .standard-text { font-size: 1.05rem; line-height: 1.8; color: #333; background: #fff; padding: 30px; border-radius: 10px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); white-space: pre-wrap; font-family: 'Microsoft YaHei', sans-serif;}
    .highlight { background-color: #ffeaa7; padding: 2px 4px; border-radius: 3px; font-weight: bold;}
    .stForm { background: #f8f9fa; padding: 20px; border-radius: 10px; margin-bottom: 20px; }
    .nav-section { background: #f8f9fa; padding: 10px; border-radius: 10px; margin: 10px 0; }
    .nav-title { font-size: 16px; font-weight: bold; color: #2c3e50; margin-bottom: 8px; padding-left: 5px; }
    </style>
""", unsafe_allow_html=True)

# 中文字体修复 - 更全面的字体支持
import matplotlib.font_manager as fm
import matplotlib as mpl
import os
import warnings
warnings.filterwarnings('ignore')

# 尝试从系统字体目录获取更多中文字体
try:
    font_paths = [
        r'C:\Windows\Fonts',  # Windows
        r'/usr/share/fonts',   # Linux
        r'/System/Library/Fonts',  # macOS
    ]
    for font_path in font_paths:
        if os.path.exists(font_path):
            for f in os.listdir(font_path):
                if f.endswith(('.ttf', '.otf')):
                    try:
                        fm.fontManager.addfont(os.path.join(font_path, f))
                    except:
                        pass
except:
    pass

# 获取所有可用中文字体
chinese_fonts = []
for font in fm.fontManager.ttflist:
    font_name = font.name.lower()
    # 检查多种中文字体名称
    if any(name in font_name for name in ['simHei', 'SimHei', 'simsun', 'SimSun', 'Microsoft YaHei', 'microsoft yahei', 
                                           'wenquanyi', 'WenQuanYi', 'noto sans cjk', 'noto sans sc', 
                                           'droid sans fallback', 'source han sans', 'pingFang', 'STHeiti',
                                           'FangSong', 'KaiTi', 'YouYuan', 'YuWei', 'Ma Shan Zheng']):
        chinese_fonts.append(font.name)

# 去重并保持顺序
chinese_fonts = list(dict.fromkeys(chinese_fonts))

# 完整的备选字体列表
all_fonts = [
    'Microsoft YaHei', 'SimHei', 'SimSun', 'WenQuanYi Zen Hei', 'WenQuanYi Micro Hei',
    'Arial Unicode MS', 'Noto Sans CJK SC', 'Noto Sans CJK TC', 'Noto Sans SC',
    'Source Han Sans SC', 'PingFang SC', 'PingFang TC', 'STHeiti', 'STSong',
    'FangSong', 'FangSong_GB2312', 'KaiTi', 'KaiTi_GB2312', 'YouYuan',
    'YuWei', 'Ma Shan Zheng', 'SimKai', 'SimFang', 'SimLi'
]

# 合并可用字体，优先使用找到的中文字体
available_fonts = chinese_fonts + [f for f in all_fonts if f not in chinese_fonts]

# 设置 matplotlib 字体
if available_fonts:
    plt.rcParams['font.sans-serif'] = available_fonts
    plt.rcParams['font.family'] = 'sans-serif'

# 修复负号显示问题
plt.rcParams['axes.unicode_minus'] = False

# 打印调试信息（可选）
# print(f"可用中文字体: {chinese_fonts}")
# print(f"设置字体: {plt.rcParams['font.sans-serif'][:3]}")

# =============================================================================
# 1. 数据结构定义
# =============================================================================
@dataclass
class TunnelSegment:
    name: str; method: str; length: float; start_mileage: float; end_mileage: float
    frame_spacing: float = 0.8; frames_per_ring: int = 2; steps: int = 2
    trolley_length: float = 12.0; advance_per_cycle: float = 1.6; lining_type: str = ""

@dataclass
class Tunnel:
    id: str; name: str; total_length: float; start_mileage: float; end_mileage: float
    start_label: str; end_label: str; is_main_line: bool; trolley_length: float = 12.0; direction: str = "正向"
    segments: List[TunnelSegment] = field(default_factory=list)

@dataclass
class Project:
    name: str; created_at: str; tunnels: List[Tunnel] = field(default_factory=list)

# =============================================================================
# 2. 工具函数 & 解析器
# =============================================================================
def parse_mileage(km_str: str) -> float:
    try:
        km_str = str(km_str).strip().upper().replace('K', '')
        if '+' in km_str:
            parts = km_str.split('+'); return int(''.join(filter(lambda x: x.isdigit() or x == '-', parts[0]))) * 1000 + float(parts[1])
        return float(km_str)
    except Exception: return 0.0

def format_mileage(meters: float) -> str:
    if pd.isna(meters): return "K0+000.000"
    sign = "-" if meters < 0 else ""
    return f"{sign}K{int(abs(meters) / 1000)}+{abs(meters) % 1000:.3f}"

def export_project_to_json(project: Project) -> str: return json.dumps(asdict(project), ensure_ascii=False, indent=2)

def import_project_from_json(json_str: str) -> Optional[Project]:
    try:
        data = json.loads(json_str); tunnels = []
        for t_data in data.get('tunnels', []):
            segments = [TunnelSegment(**s) for s in t_data.get('segments', [])]
            t_data_clean = {k:v for k,v in t_data.items() if k != 'segments'}
            tunnels.append(Tunnel(segments=segments, **t_data_clean))
        return Project(name=data['name'], created_at=data.get('created_at', datetime.now().strftime("%Y-%m-%d")), tunnels=tunnels)
    except Exception as e: st.error(f"文件解析失败: {e}"); return None

def parse_segments_from_raw(raw_data: str, trolley_len: float) -> List[TunnelSegment]:
    segments = []
    for line in raw_data.strip().split('\n'):
        parts = line.replace('，', ',').replace('；', ',').replace(';', ',').split(',')
        if len(parts) < 4: continue
        m1, m2 = parse_mileage(parts[0]), parse_mileage(parts[1])
        start, end = min(m1, m2), max(m1, m2)
        name, method = parts[2].replace('（', '(').split('(')[0], parts[3].strip()
        length = end - start
        if '明挖' in method: steps, advance, frames = 1, length, 1; method='明挖'
        elif 'CD' in method: steps, advance, frames = 4, 0.8, 1; method='CD法'
        else: steps, advance, frames = 2, 1.6, 2; method='台阶法'
        segments.append(TunnelSegment(name, method, length, start, end, advance/frames if frames else 0, frames, steps, trolley_len, advance, name))
    return sorted(segments, key=lambda x: x.start_mileage)

@st.cache_data(ttl=3600)
def create_demo_project() -> Project:
    t_zk = Tunnel("ZK", "ZK左线", 0, 0, 0, "", "", True, 12.0, "正向", parse_segments_from_raw(ZK_DATA, 12.0))
    t_yk = Tunnel("YK", "YK右线", 0, 0, 0, "", "", True, 12.0, "正向", parse_segments_from_raw(YK_DATA, 12.0))
    t_ak = Tunnel("AK", "A匝道", 0, 0, 0, "", "", False, 9.0, "正向", parse_segments_from_raw(AK_DATA, 9.0))
    t_bk = Tunnel("BK", "B匝道", 0, 0, 0, "", "", False, 9.0, "正向", parse_segments_from_raw(BK_DATA, 9.0))
    t_htd = Tunnel("HTD1", "1#车行横通道", 0, 0, 0, "", "", False, 9.0, "正向", parse_segments_from_raw(HTD_DATA, 9.0))
    for t in [t_zk, t_yk, t_ak, t_bk, t_htd]:
        if t.segments:
            t.start_mileage, t.end_mileage = min(s.start_mileage for s in t.segments), max(s.end_mileage for s in t.segments)
            t.total_length, t.start_label, t.end_label = t.end_mileage - t.start_mileage, format_mileage(t.start_mileage), format_mileage(t.end_mileage)
    return Project(name="泸州老旧改造配套项目(全线)", created_at=datetime.now().strftime("%Y-%m-%d"), tunnels=[t_zk, t_yk, t_ak, t_bk, t_htd])

# =============================================================================
# 3. 图表渲染引擎
# =============================================================================
def draw_enhanced_profile(segments: List[TunnelSegment], tunnel_name: str, direction: str):
    if not segments: return None
    min_m, max_m = min(min(s.start_mileage, s.end_mileage) for s in segments), max(max(s.start_mileage, s.end_mileage) for s in segments)
    total_len = max_m - min_m
    if total_len <= 0: return None
    colors = {'明挖': '#FF9F43', 'CD法': '#48DBFB', '台阶法': '#1DD1A1', '洞口': '#10AC84', '其他': '#54A0FF'}
    fig, ax = plt.subplots(figsize=(14, 3.5), dpi=120)
    ax.set_facecolor('#F8F9FA')
    for seg in segments:
        l = abs(seg.end_mileage - seg.start_mileage)
        if l <= 0: continue
        start_x = min(seg.start_mileage, seg.end_mileage)
        rect = patches.Rectangle((start_x, 0), l, 1, linewidth=1.5, edgecolor='white', facecolor=colors.get(seg.method, '#A4B0BE'), alpha=0.95)
        ax.add_patch(rect)
        if l > total_len * 0.04: ax.text(start_x + l/2, 0.5, f"{seg.method}\n{l:.1f}m", ha='center', va='center', color='white', fontweight='bold', fontsize=10)
    ax.set_xlim(min_m - total_len*0.05, max_m + total_len*0.05); ax.set_ylim(-0.5, 2); ax.set_yticks([])
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False); ax.spines['left'].set_visible(False)
    ax.spines['bottom'].set_linewidth(1.5); ax.spines['bottom'].set_color('#2C3E50'); ax.tick_params(axis='x', colors='#2C3E50', labelsize=10)
    ax.set_title(f"【{tunnel_name}】 施工工法纵断面展示 (方向: {direction})", pad=15, fontsize=14, fontweight='bold', color='#2C3E50')
    ticks = np.linspace(min_m, max_m, 6); ax.set_xticks(ticks); ax.set_xticklabels([format_mileage(t) for t in ticks])
    plt.tight_layout(); return fig

def render_plotly_profile(segments: List[TunnelSegment], tunnel_name: str, direction: str):
    try: import plotly.graph_objects as go
    except ImportError: return None
    if not segments: return None
    df = pd.DataFrame([{'Task': tunnel_name, 'Start': min(s.start_mileage, s.end_mileage), 'Finish': max(s.start_mileage, s.end_mileage), 'Method': s.method, 'Length': s.length, 'Name': s.name, 'StartStr': format_mileage(min(s.start_mileage, s.end_mileage)), 'EndStr': format_mileage(max(s.start_mileage, s.end_mileage))} for s in segments])
    colors = {'明挖': '#FF9F43', 'CD法': '#48DBFB', '台阶法': '#1DD1A1', '洞口': '#10AC84', '其他': '#54A0FF'}
    fig = go.Figure()
    for _, row in df.iterrows():
        fig.add_trace(go.Bar(x=[row['Length']], y=[row['Task']], orientation='h', base=[row['Start']], marker_color=colors.get(row['Method'], '#A4B0BE'), name=row['Method'], text=f"{row['Method']} ({row['Length']:.1f}m)", textposition='inside', insidetextanchor='middle', textfont=dict(color='white', size=12, family="Microsoft YaHei"), hovertemplate=f"<b>部位</b>: {row['Name']}<br><b>工法</b>: {row['Method']}<br><b>里程</b>: {row['StartStr']} ~ {row['EndStr']}<br><b>长度</b>: {row['Length']:.1f}m<extra></extra>"))
    fig.update_layout(title=dict(text=f"<b>{tunnel_name}</b> 施工工法交互式纵断面图", font=dict(size=18)), xaxis_title="里程桩号 (m)", barmode='overlay', height=250, showlegend=True, plot_bgcolor='white', paper_bgcolor='#F8F9FA', margin=dict(l=20, r=20, t=50, b=20), hoverlabel=dict(bgcolor="white", font_size=13, font_family="Microsoft YaHei"))
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='LightGray', tickformat='.1f'); fig.update_yaxes(showticklabels=False)
    return fig

def render_plotly_dashboard(df_sum: pd.DataFrame, df_detail: pd.DataFrame):
    try: import plotly.express as px
    except ImportError: return None, None, None, None
    fig1 = px.bar(df_sum, x='隧道', y='合计', title="各隧道检验批总量对比", text='合计', color_discrete_sequence=['#4facfe'])
    fig1.update_traces(textposition='outside'); fig1.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
    cols_to_sum = [c for c in df_sum.columns if c not in ['隧道', '合计']]; total_series = df_sum[cols_to_sum].sum().reset_index(); total_series.columns = ['分部工程', '数量']
    fig2 = px.pie(total_series, values='数量', names='分部工程', title="全项目分部工程占比", hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
    fig2.update_traces(textposition='inside', textinfo='percent+label')
    df_melted = df_sum.melt(id_vars=['隧道'], value_vars=cols_to_sum, var_name='分部工程', value_name='数量')
    fig3 = px.bar(df_melted, x='隧道', y='数量', color='分部工程', title="各隧道分部工程详细构成", barmode='stack', color_discrete_sequence=px.colors.qualitative.Set2)
    fig3.update_layout(plot_bgcolor='rgba(0,0,0,0)')
    df_subitem_chart = df_detail.groupby('分项工程')['检验批编号'].count().reset_index(); df_subitem_chart.columns = ['分项工程', '频次']
    fig4 = px.bar(df_subitem_chart.sort_values(by='频次', ascending=True).tail(10), x='频次', y='分项工程', orientation='h', title="分项工程验收频次排行 (TOP 10)", color='频次', color_continuous_scale='Sunset')
    fig4.update_layout(plot_bgcolor='rgba(0,0,0,0)')
    return fig1, fig2, fig3, fig4

# =============================================================================
# 4. 检验批智能计算器 (针对公路规范精准适配 7+11项)
# =============================================================================
def _generate_batch_code(tunnel_id: str, div_code: str, item_code: str, seq: int) -> str: return f"{tunnel_id}-{div_code}-{item_code}-{seq:03d}"

def _add_batch(results, tunnel_name, tunnel_id, d, i, seq, remark, start=0, end=0, cycle_num="", div_config=None):
    # 安全检查：确保div和item都存在
    if d not in div_config: return
    if i not in div_config[d].get('items', {}): return
    if div_config[d]['items'][i].get('name') == '-': return
    mileage_str = "K0+000" if start==0 and end==0 else f"{format_mileage(start)}~{format_mileage(end)}"
    batch = {
        '检验批编号': _generate_batch_code(tunnel_id, d, i, seq), '隧道': tunnel_name,
        '分部工程': div_config[d]['name'], '分项工程': div_config[d]['items'][i]['name'],
        '具体部位': remark, '里程范围': mileage_str, '长度': round(abs(end - start), 3) if start!=0 or end!=0 else 0.0,
        '循环数': cycle_num, '主控项目条文': div_config[d]['items'][i]['main'], '一般项目条文': div_config[d]['items'][i]['gen'], '备注': remark
    }
    results['divisions'][d]['items'][i]['batches'].append(batch); results['all_batches'].append(batch)

def _calculate_cycles_and_rings(tunnel: Tunnel) -> Tuple[int, int, int, int]:
    cd_cycles = tj_cycles = 0
    for seg in tunnel.segments:
        if seg.method not in ['CD法', '台阶法']: continue
        cycles = math.ceil(seg.length / seg.advance_per_cycle) if seg.advance_per_cycle > 0 else 0
        if seg.method == 'CD法': cd_cycles += cycles
        else: tj_cycles += cycles
    return cd_cycles, tj_cycles, cd_cycles + tj_cycles, math.ceil(tunnel.total_length / tunnel.trolley_length) if tunnel.trolley_length > 0 else 0

def _calculate_portal_batches(results, tunnel: Tunnel, div_config: dict, is_highway: bool):
    _add_batch(results, tunnel.name, tunnel.id, '01', '01', 1, '进洞口-总体/装饰', div_config=div_config)
    _add_batch(results, tunnel.name, tunnel.id, '01', '01', 2, '出洞口-总体/装饰', div_config=div_config)
    
    if is_highway:
        # 公路规范：洞口工程严格输出这7项
        if '02' in div_config:
            for ic in div_config['02']['items'].keys():
                _add_batch(results, tunnel.name, tunnel.id, '02', ic, 1, '进洞口', div_config=div_config)
                _add_batch(results, tunnel.name, tunnel.id, '02', ic, 2, '出洞口', div_config=div_config)
        # 公路规范：超前支护（超前锚杆、超前小导管、管棚）在洞口生成
        if '03' in div_config:
            for ic in div_config['03']['items'].keys():
                _add_batch(results, tunnel.name, tunnel.id, '03', ic, 1, '进洞口', div_config=div_config)
                _add_batch(results, tunnel.name, tunnel.id, '03', ic, 2, '出洞口', div_config=div_config)
    else:
        # 铁路规范：传统逻辑
        for d, i_codes in [('02', ['01','04']), ('03', ['01','02','03'])]:
            if d in div_config:
                for ic in i_codes:
                    _add_batch(results, tunnel.name, tunnel.id, d, ic, 1, '进洞口', div_config=div_config)
                    _add_batch(results, tunnel.name, tunnel.id, d, ic, 2, '出洞口', div_config=div_config)
        if '02' in div_config:
            for idx, sub_item in enumerate(['防护', '明洞防水层', '明洞浇筑']):
                if '02' in div_config['02']['items']:
                    _add_batch(results, tunnel.name, tunnel.id, '02', '02', idx+1, f'进洞口-{sub_item}', div_config=div_config)
                    _add_batch(results, tunnel.name, tunnel.id, '02', '02', idx+4, f'出洞口-{sub_item}', div_config=div_config)
            for idx, sub_item in enumerate(['模板/防排水', '钢筋', '混凝土']):
                if '03' in div_config['02']['items']:
                    _add_batch(results, tunnel.name, tunnel.id, '02', '03', idx+1, f'进洞口-{sub_item}', div_config=div_config)
                    _add_batch(results, tunnel.name, tunnel.id, '02', '03', idx+4, f'出洞口-{sub_item}', div_config=div_config)

def _calculate_excavation_and_support_batches(results, tunnel: Tunnel, cd_cycles: int, tj_cycles: int, div_config: dict, is_highway: bool):
    dir_sign = 1 if tunnel.direction == "正向" else -1; seq_counter = 1
    for seg in tunnel.segments:
        if seg.method not in ['CD法', '台阶法']: continue
        cycles = math.ceil(seg.length / seg.advance_per_cycle) if seg.advance_per_cycle > 0 else 0
        ic_exc = '01' if seg.method == 'CD法' else '02'
        step_names = ['左上','右上','左下','右下'] if seg.method == 'CD法' else ['上台阶','下台阶']
        seg_start = min(seg.start_mileage, seg.end_mileage) if dir_sign == 1 else max(seg.start_mileage, seg.end_mileage)
        seg_end = max(seg.start_mileage, seg.end_mileage) if dir_sign == 1 else min(seg.start_mileage, seg.end_mileage)
        for c in range(cycles):
            start = seg_start + c * seg.advance_per_cycle * dir_sign; end = start + seg.advance_per_cycle * dir_sign
            if dir_sign == 1: end = min(end, seg_end)
            else: end = max(end, seg_end)
            for s_idx, s_name in enumerate(step_names):
                seq = seq_counter; seq_counter += 1
                if '04' in div_config: _add_batch(results, tunnel.name, tunnel.id, '04', ic_exc, seq, f"{seg.name}-{s_name}", start, end, c+1, div_config=div_config)
                if '05' in div_config:
                    for ic_sup in div_config['05']['items'].keys():
                        _add_batch(results, tunnel.name, tunnel.id, '05', ic_sup, seq, f"{seg.name}-{s_name}", start, end, c+1, div_config=div_config)

def _calculate_lining_and_auxiliary_batches(results, tunnel: Tunnel, rings: int, div_config: dict, is_highway: bool):
    if tunnel.trolley_length <= 0: return
    dir_sign = 1 if tunnel.direction == "正向" else -1
    base_t_start = min(tunnel.start_mileage, tunnel.end_mileage) if dir_sign == 1 else max(tunnel.start_mileage, tunnel.end_mileage)
    base_t_end = max(tunnel.start_mileage, tunnel.end_mileage) if dir_sign == 1 else min(tunnel.start_mileage, tunnel.end_mileage)
    for r in range(rings):
        start = base_t_start + r * tunnel.trolley_length * dir_sign; end = min(start + tunnel.trolley_length, base_t_end) if dir_sign == 1 else max(start - tunnel.trolley_length, base_t_end)
        if is_highway:
            # 公路规范：衬砌部分直接输出字典里的 仰拱,仰拱回填,衬砌钢筋,混凝土衬砌，无衍生子项
            if '06' in div_config:
                for ic in div_config['06']['items'].keys():
                    _add_batch(results, tunnel.name, tunnel.id, '06', ic, r+1, '洞身衬砌-二衬部分', start, end, r+1, div_config=div_config)
        else:
            if '06' in div_config:
                for idx, sub_item in enumerate(['施工', '钢筋', '混凝土']):
                    seq = r * 3 + idx + 1
                    if '01' in div_config['06']['items']: _add_batch(results, tunnel.name, tunnel.id, '06', '01', seq, f'仰拱-{sub_item}', start, end, r+1, div_config=div_config)
                    if '02' in div_config['06']['items']: _add_batch(results, tunnel.name, tunnel.id, '06', '02', seq, f'拱墙-{sub_item}', start, end, r+1, div_config=div_config)
        
        if '07' in div_config:
            for ic in div_config['07']['items'].keys(): _add_batch(results, tunnel.name, tunnel.id, '07', ic, r+1, '防排水', start, end, r+1, div_config=div_config)
        if '08' in div_config:
            for ic in div_config['08']['items'].keys(): _add_batch(results, tunnel.name, tunnel.id, '08', ic, r+1, '路面/附属', start, end, r+1, div_config=div_config)

def _generate_subitem_summary(results, tunnel: Tunnel, cd_cycles: int, tj_cycles: int, total_cycles: int, rings: int, div_config: dict):
    subitem_res = []
    total = 0
    for d_code, d_data in results['divisions'].items():
        d_total = 0
        for i_code, i_data in d_data['items'].items():
            count = len(i_data['batches'])
            if count == 0: continue
            name, rule = i_data['name'], div_config[d_code]['items'][i_code]['formula']
            calc_base = "-"
            if '洞口' in rule: calc_base = "2 个洞口"; calc_str = f"{calc_base} × 1 批/洞口 = {count} 批"
            elif 'CD法' in name: calc_base = f"{cd_cycles} 循环"; calc_str = f"{calc_base} × 4 步/循环 = {count} 批"
            elif '台阶法' in name: calc_base = f"{tj_cycles} 循环"; calc_str = f"{calc_base} × 2 步/循环 = {count} 批"
            elif '循环' in rule: calc_base = f"{total_cycles} 循环"; calc_str = f"{calc_base} × 4 批/循环 = {count} 批"
            elif '环数×3' in rule: calc_base = f"{rings} 衬砌环"; calc_str = f"{calc_base} × 3 批/环 = {count} 批"
            elif '环数' in rule or '每环' in rule: calc_base = f"{rings} 衬砌环"; calc_str = f"{calc_base} × 1 批/环 = {count} 批"
            else: calc_str = f"按部位或基数累加 = {count} 批"
            subitem_res.append({'隧道': tunnel.name, '分部工程': d_data['name'], '分项工程': name, '计算基数(循环/环/洞口)': calc_base, '检验批计算式': calc_str, '检验批数量': count})
            d_total += count; total += count
        results['summary'][d_data['name']] = results['summary'].get(d_data['name'], 0) + d_total
    results['summary']['合计'] = total
    return subitem_res

def calculate_single_tunnel(tunnel: Tunnel, base_div_config: dict, is_highway: bool, is_high_speed: bool = False) -> Tuple[Dict, List]:
    div_config = copy.deepcopy(base_div_config)
    results = {'tunnel_name': tunnel.name, 'divisions': {}, 'summary': {}, 'all_batches': []}
    for d_code, d_info in div_config.items():
        results['divisions'][d_code] = {'name': d_info['name'], 'items': {}, 'total_batches': 0}
        for i_code, i_info in d_info['items'].items():
            results['divisions'][d_code]['items'][i_code] = {'name': i_info['name'], 'batches': [], 'count': 0}
    
    cd_cycles, tj_cycles, total_cycles, rings = _calculate_cycles_and_rings(tunnel)
    _calculate_portal_batches(results, tunnel, div_config, is_highway or is_high_speed)
    _calculate_excavation_and_support_batches(results, tunnel, cd_cycles, tj_cycles, div_config, is_highway or is_high_speed)
    _calculate_lining_and_auxiliary_batches(results, tunnel, rings, div_config, is_highway or is_high_speed)
    subitem_res = _generate_subitem_summary(results, tunnel, cd_cycles, tj_cycles, total_cycles, rings, div_config)
    return results, subitem_res

@st.cache_data(ttl=3600, show_spinner=False)
def calculate_project_batches(project: Project, standard_type: str) -> Tuple[int, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    is_highway = "公路" in standard_type
    is_high_speed = "高铁" in standard_type
    base_div_config = HIGHWAY_DIVISIONS if is_highway else (HIGH_SPEED_RAILWAY_DIVISIONS if is_high_speed else RAILWAY_DIVISIONS)
    grand_total = 0; summary_list = []; all_batches_flat = []; subitem_summary_flat = []
    
    for tunnel in project.tunnels:
        tunnel_res, subitem_res = calculate_single_tunnel(tunnel, base_div_config, is_highway, is_high_speed)
        sum_dict = {'隧道': tunnel.name}
        sum_dict.update(tunnel_res['summary']); summary_list.append(sum_dict)
        grand_total += tunnel_res['summary']['合计']
        all_batches_flat.extend(tunnel_res['all_batches']); subitem_summary_flat.extend(subitem_res)
    
    return grand_total, pd.DataFrame(summary_list).fillna(0), pd.DataFrame(subitem_summary_flat), pd.DataFrame(all_batches_flat)

# =============================================================================
# 5. PDF 渲染器
# =============================================================================
def render_pdf_viewer(pdf_bytes: bytes, filename: str):
    if len(pdf_bytes) / (1024 * 1024) > 15:
        st.warning(f"⚠️ 文件大于15MB，在线预览已禁用。"); st.download_button("📥 下载文件", data=pdf_bytes, file_name=filename, mime="application/pdf"); return
    with st.spinner("正在加载PDF预览..."):
        base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
        components.html(f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="850px" style="border:none;border-radius:8px;"></iframe>', height=900)

def get_pdf_bytes(standard_type: str) -> Optional[bytes]:
    import sys
    app_dir = os.path.dirname(os.path.abspath(sys.argv[0])) if hasattr(sys, 'argv') else os.getcwd()
    if "公路" in standard_type:
        target_file = "JTG_F80_1-2017.pdf"
    elif "高铁" in standard_type:
        target_file = "TB10753-2018.pdf"
    else:
        target_file = "TB10417-2018.pdf"
    for p in [target_file, os.path.join(app_dir, target_file), os.path.join(os.path.dirname(__file__), target_file)]:
        if os.path.exists(p): return open(p, "rb").read()
    return None

# =============================================================================
# 6. 主程序 GUI
# =============================================================================
def main():
    if 'projects' not in st.session_state: st.session_state.projects = [create_demo_project()]
    if 'current_project_index' not in st.session_state: st.session_state.current_project_index = 0
    if 'standard_type' not in st.session_state: st.session_state.standard_type = "公路隧道 (JTG F80/1-2017)"
    if 'last_result' not in st.session_state: st.session_state.last_result = None
    if 'current_page' not in st.session_state: st.session_state.current_page = "📋 参数配置"
    
    try: current_project = st.session_state.projects[st.session_state.current_project_index]
    except IndexError: st.session_state.current_project_index = 0; current_project = st.session_state.projects[0]

    with st.sidebar:
        st.title("🏗️ 工程管理")
        project_names = [p.name for p in st.session_state.projects]
        selected_idx = st.selectbox("当前工作工程:", range(len(project_names)), format_func=lambda x: project_names[x], index=st.session_state.current_project_index)
        st.session_state.current_project_index = selected_idx
        
        new_proj_name = st.text_input("📝 重命名工程:", current_project.name)
        if new_proj_name and new_proj_name != current_project.name: current_project.name = new_proj_name; st.rerun()
            
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            if st.button("➕ 新建工程", use_container_width=True):
                st.session_state.projects.append(Project(name=f"新建工程_{len(project_names)+1}", created_at=datetime.now().strftime("%Y-%m-%d"), tunnels=[Tunnel("T1", "一号隧道", 100, 0, 100, "K0", "K100", True, 12.0, "正向", [TunnelSegment("首段", "台阶法", 100, 0, 100)])]))
                st.session_state.current_project_index = len(st.session_state.projects) - 1; st.rerun()
        with col_p2:
            if st.button("🗑️ 删除工程", use_container_width=True) and len(st.session_state.projects) > 1:
                st.session_state.projects.pop(selected_idx); st.session_state.current_project_index = 0; st.rerun()
                
        with st.expander("📂 数据导入/导出", expanded=False):
            st.download_button("📤 导出当前工程 (.json)", export_project_to_json(current_project), f"{current_project.name}.json", "application/json", use_container_width=True)
            uploaded_file = st.file_uploader("📥 导入工程配置", type=['json'])
            if uploaded_file and st.button("✅ 确认导入", use_container_width=True):
                imported_proj = import_project_from_json(uploaded_file.getvalue().decode("utf-8"))
                if imported_proj: st.session_state.projects.append(imported_proj); st.session_state.current_project_index = len(st.session_state.projects) - 1; st.rerun()
        
        st.markdown("---")
        st.markdown('<div class="nav-section"><div class="nav-title">📐 应用规范标准</div>', unsafe_allow_html=True)
        selected_standard = st.radio("规范", ["铁路隧道 (TB 10417-2018)", "公路隧道 (JTG F80/1-2017)", "高铁隧道 (TB 10753-2018)"], index=0 if "铁路" in st.session_state.standard_type else 1, label_visibility="collapsed", key="standard_selector")
        if selected_standard != st.session_state.standard_type:
            st.session_state.standard_type = selected_standard
            st.session_state.last_result = None
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown('<div class="nav-section"><div class="nav-title">🛠️ 功能模块</div>', unsafe_allow_html=True)
        page_options = ["📋 参数配置", "📊 检验批计算", "📉 统计看板", "📖 标准查阅"]
        page = st.radio("模块", page_options, index=page_options.index(st.session_state.current_page), label_visibility="collapsed", key="page_selector")
        if page != st.session_state.current_page:
            st.session_state.current_page = page
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    if page == "📋 参数配置":
        st.subheader(f"📋 参数配置 - {current_project.name} | 选用规范: {st.session_state.standard_type}")
        if not current_project.tunnels:
            st.warning("无隧道数据。"); return
        
        c1, c2, c3 = st.columns([3, 1, 1])
        with c1: target_tunnel = next(t for t in current_project.tunnels if t.name == st.selectbox("选择要编辑的隧道/通道:", [t.name for t in current_project.tunnels]))
        with c2:
            st.write(""); st.write("")
            if st.button("➕ 新增隧道", use_container_width=True):
                current_project.tunnels.append(Tunnel(f"T{len(current_project.tunnels)+1}", "新建隧道", 100, 0, 100, "K0", "K1", True, 12.0, "正向", [TunnelSegment("新建段落", "台阶法", 100, 0, 100)]))
                st.rerun()
        with c3:
            st.write(""); st.write("")
            if st.button("🗑️ 删除当前隧道", use_container_width=True) and len(current_project.tunnels) > 1:
                current_project.tunnels.remove(target_tunnel); st.rerun()
        
        tab1, tab2 = st.tabs(["📊 Matplotlib版本", "🎨 Plotly交互版"])
        with tab1:
            fig = draw_enhanced_profile(target_tunnel.segments, target_tunnel.name, target_tunnel.direction)
            if fig: st.pyplot(fig); plt.close(fig)
        with tab2:
            plotly_fig = render_plotly_profile(target_tunnel.segments, target_tunnel.name, target_tunnel.direction)
            if plotly_fig: st.plotly_chart(plotly_fig, use_container_width=True)
        
        st.markdown("---")
        col_basic, col_seg = st.columns([1, 4])
        with col_basic:
            st.markdown("##### 2. 基础信息")
            with st.form("basic_info"):
                new_id = st.text_input("隧道ID", target_tunnel.id)
                new_name = st.text_input("名称", target_tunnel.name)
                new_dir = st.radio("掘进方向", ["正向", "反向"], index=0 if target_tunnel.direction == "正向" else 1)
                st_val = min(s.start_mileage for s in target_tunnel.segments) if target_tunnel.segments else 0.0
                ed_val = max(s.end_mileage for s in target_tunnel.segments) if target_tunnel.segments else 100.0
                st.text_input("总体起点桩号 (自动更新)", format_mileage(st_val), disabled=True)
                st.text_input("总体终点桩号 (自动更新)", format_mileage(ed_val), disabled=True)
                is_main = st.checkbox("设为隧道主线 (取消即为辅助通道)", value=target_tunnel.is_main_line)
                new_trolley = st.number_input("二衬台车长度(m)", value=float(target_tunnel.trolley_length), step=0.1)
                if st.form_submit_button("💾 保存基础信息"):
                    target_tunnel.id = new_id; target_tunnel.name = new_name; target_tunnel.direction = "正向" if "正向" in new_dir else "反向"
                    target_tunnel.trolley_length = new_trolley; target_tunnel.is_main_line = is_main; st.success("更新成功!"); st.rerun()
        
        with col_seg:
            st.markdown("##### 3. 施工段落表")
            expected_columns = ["部位名称", "工法", "起始桩号", "长度(m)", "终止桩号", "衬砌类型", "榀数/环", "榀距(m)", "进尺(m)", "步骤数"]
            df_seg = pd.DataFrame([{ "部位名称": s.name, "工法": s.method, "起始桩号": format_mileage(s.start_mileage), "长度(m)": float(s.length), "终止桩号": format_mileage(s.end_mileage), "衬砌类型": s.lining_type, "榀数/环": int(s.frames_per_ring), "榀距(m)": float(s.frame_spacing), "进尺(m)": float(s.advance_per_cycle), "步骤数": int(s.steps) } for s in target_tunnel.segments]) if target_tunnel.segments else pd.DataFrame(columns=expected_columns)
            edited_df = st.data_editor(df_seg, num_rows="dynamic", use_container_width=True, height=400, column_config={"工法": st.column_config.SelectboxColumn(options=["明挖", "CD法", "台阶法", "洞口", "其他"]), "终止桩号": st.column_config.TextColumn(disabled=True), "进尺(m)": st.column_config.NumberColumn(disabled=True), "步骤数": st.column_config.NumberColumn(disabled=True)})
            
            if st.button("💾 保存段落 & 触发智能连缀推算", type="primary", use_container_width=True):
                new_segs = []; dir_sign = 1 if target_tunnel.direction == "正向" else -1; prev_end_m = None
                for idx, row in edited_df.iterrows():
                    start_str = str(row.get('起始桩号', "")); start_m = parse_mileage(start_str) if start_str and prev_end_m is None else prev_end_m if prev_end_m is not None else target_tunnel.start_mileage
                    length = float(row.get('长度(m)', 100.0)); length = 100.0 if length <= 0.001 else length
                    end_m = start_m + (length * dir_sign); prev_end_m = end_m
                    method = str(row.get('工法', "台阶法")); frames = int(row.get('榀数/环', 2)); spacing = float(row.get('榀距(m)', 0.8))
                    advance = round(frames * spacing, 3) if frames > 0 and spacing > 0 else 1.6
                    steps = 4 if 'CD' in method else 2 if '台阶' in method else 1
                    new_segs.append(TunnelSegment(str(row.get('部位名称', f"段落_{idx+1}")), method, length, start_m, end_m, advance_per_cycle=advance, lining_type=str(row.get('衬砌类型', "")), steps=steps, frames_per_ring=frames, frame_spacing=spacing, trolley_length=target_tunnel.trolley_length))
                target_tunnel.segments = new_segs
                if new_segs:
                    target_tunnel.start_mileage = new_segs[0].start_mileage if dir_sign == 1 else new_segs[-1].end_mileage
                    target_tunnel.end_mileage = new_segs[-1].end_mileage if dir_sign == 1 else new_segs[0].start_mileage
                    target_tunnel.total_length = sum(s.length for s in new_segs)
                st.success("✅ 智能连缀计算完成!"); st.rerun()

    elif page == "📊 检验批计算":
        st.markdown(f"<h2>📊 检验批计算 - {current_project.name}</h2>", unsafe_allow_html=True)
        st.info(f"📌 **当前依据规范**：{st.session_state.standard_type}。提示：已精准对齐 2、洞口工程（7项）、4、洞身衬砌（11项）以及 6、路面 等规范分项内容。")
        with st.spinner("🚀 正在执行智能计算..."):
            total, df_sum, df_subitem, df_detail = calculate_project_batches(current_project, st.session_state.standard_type)
            st.session_state.last_result = (total, df_sum, df_subitem, df_detail)
        
        if "铁路" in st.session_state.standard_type:
            m2_title, m2_val = "初期支护占比", df_sum["05 初期支护"].sum() / total if total > 0 and "05 初期支护" in df_sum else 0
            m3_title, m3_val = "洞身开挖", df_sum["04 洞身开挖"].sum() if "04 洞身开挖" in df_sum else 0
            m4_title, m4_val = "衬砌工程", df_sum["06 衬砌工程"].sum() if "06 衬砌工程" in df_sum else 0
        else:
            m2_title, m2_val = "洞身衬砌占比(含初支)", df_sum["4、洞身衬砌"].sum() / total if total > 0 and "4、洞身衬砌" in df_sum else 0
            m3_title, m3_val = "洞身开挖", df_sum["3、洞身开挖"].sum() if "3、洞身开挖" in df_sum else 0
            m4_title, m4_val = "防排水", df_sum["5、防排水"].sum() if "5、防排水" in df_sum else 0

        c1, c2, c3, c4 = st.columns(4)
        with c1: st.markdown(f'<div class="metric-card bg-blue"><div class="metric-title">全线检验批总数</div><div class="metric-value">{total:,}</div></div>', unsafe_allow_html=True)
        with c2: st.markdown(f'<div class="metric-card bg-green"><div class="metric-title">{m2_title}</div><div class="metric-value">{m2_val:.1%}</div></div>', unsafe_allow_html=True)
        with c3: st.markdown(f'<div class="metric-card bg-purple"><div class="metric-title">{m3_title}</div><div class="metric-value">{m3_val:,}</div></div>', unsafe_allow_html=True)
        with c4: st.markdown(f'<div class="metric-card bg-orange"><div class="metric-title">{m4_title}</div><div class="metric-value">{m4_val:,}</div></div>', unsafe_allow_html=True)
        
        segment_stats = []
        for tunnel in current_project.tunnels:
            for seg in tunnel.segments:
                if seg.method in ['CD法', '台阶法']: cycles = math.ceil(seg.length / seg.advance_per_cycle) if seg.advance_per_cycle > 0 else 0; steps = 4 if seg.method == 'CD法' else 2
                elif seg.method == '明挖': cycles = 1; steps = 1
                else: cycles = 0; steps = 0
                div_04 = cycles * steps if seg.method in ['CD法', '台阶法'] else 0
                div_05 = cycles * steps * 4 if seg.method in ['CD法', '台阶法'] else 0
                total_batches = div_04 + div_05
                if seg.method == 'CD法': formula = f"{cycles}循环×4步×1批={div_04}批 | {cycles}循环×4步×4项={div_05}批"
                elif seg.method == '台阶法': formula = f"{cycles}循环×2步×1批={div_04}批 | {cycles}循环×2步×4项={div_05}批"
                else: formula = "-"
                
                col_04_name = '04 洞身开挖' if "铁路" in st.session_state.standard_type else '3、洞身开挖'
                col_05_name = '05 初期支护' if "铁路" in st.session_state.standard_type else '4、洞身衬砌(支护项)'
                
                segment_stats.append({'隧道/通道': tunnel.name, '部位名称': seg.name, '施工工法': seg.method, '段落长度(m)': round(seg.length, 3), '起点里程': format_mileage(min(seg.start_mileage, seg.end_mileage)), '终点里程': format_mileage(max(seg.start_mileage, seg.end_mileage)), '进尺(m)': seg.advance_per_cycle, '循环数': cycles if seg.method in ['CD法', '台阶法'] else '-', col_04_name: div_04, col_05_name: div_05, '检验批总数': total_batches, '计算说明': formula})
        
        st.markdown("### 1. 分部工程汇总表")
        st.dataframe(df_sum, use_container_width=True)
        st.markdown("### 2. 隧道段落统计表 (含辅助通道)")
        st.dataframe(pd.DataFrame(segment_stats), use_container_width=True)
        st.markdown("### 3. 分部分项汇总表 (带基数与计算说明)")
        st.dataframe(df_subitem, use_container_width=True)
        
        c_d1, c_d2, c_d3 = st.columns(3)
        with c_d1: st.download_button("📥 导出分部汇总表", df_sum.to_csv(index=False, float_format='%.3f').encode('utf-8-sig'), "分部汇总.csv", "text/csv", use_container_width=True)
        with c_d2: st.download_button("📥 导出分部分项表", df_subitem.to_csv(index=False).encode('utf-8-sig'), "分部分项汇总.csv", "text/csv", use_container_width=True)
        with c_d3: st.download_button("📥 导出详细明细表", df_detail.to_csv(index=False, float_format='%.3f').encode('utf-8-sig'), "明细.csv", "text/csv", use_container_width=True)

    elif page == "📉 统计看板":
        st.markdown(f"<h2>📉 项目质量管控数据看板 ({st.session_state.standard_type})</h2>", unsafe_allow_html=True)
        with st.spinner("🚀 正在准备可视化数据..."):
            total, df_sum, df_subitem, df_detail = calculate_project_batches(current_project, st.session_state.standard_type)
        try: import plotly.express as px; plotly_available = True
        except ImportError: st.warning("⚠️ 未检测到 Plotly 库，已降级为 Matplotlib 静态图表。"); plotly_available = False
        if plotly_available:
            fig1, fig2, fig3, fig4 = render_plotly_dashboard(df_sum, df_detail)
            if fig1:
                col1, col2 = st.columns(2)
                with col1: st.plotly_chart(fig1, use_container_width=True)
                with col2: st.plotly_chart(fig2, use_container_width=True)
                col3, col4 = st.columns(2)
                with col3: st.plotly_chart(fig3, use_container_width=True)
                with col4: st.plotly_chart(fig4, use_container_width=True)
        else:
            fig1, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6), dpi=120)
            bars = ax1.bar(df_sum['隧道'], df_sum['合计'], color='#3498db', width=0.5)
            ax1.set_title("各隧道检验批总量对比", pad=20, fontsize=14, fontweight='bold')
            for bar in bars: ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + (bar.get_height()*0.02), f"{int(bar.get_height()):,}", ha='center', va='bottom')
            cols_to_sum = [c for c in df_sum.columns if c not in ['隧道', '合计']]; total_series = df_sum[cols_to_sum].sum()
            ax2.pie(total_series, labels=total_series.index, autopct='%1.1f%%', startangle=140, pctdistance=0.85, colors=['#4E79A7', '#F28E2B', '#E15759', '#76B7B2', '#59A14F', '#EDC948', '#B07AA1'])
            ax2.add_artist(plt.Circle((0, 0), 0.65, fc='white'))
            ax2.set_title("全项目分部工程占比", pad=20, fontsize=14, fontweight='bold')
            plt.tight_layout(); st.pyplot(fig1); plt.close(fig1)

    elif page == "📖 标准查阅":
        st.markdown(f"<h2>📖 隧道工程施工质量验收标准查阅</h2>", unsafe_allow_html=True)
        st.info(f"💡 当前查阅标准：**{st.session_state.standard_type}**。可在左侧边栏进行切换。")
        full_text_dict = JTG_F80_1_TEXT if "公路" in st.session_state.standard_type else TB10417_TEXT
        tab1, tab2, tab3 = st.tabs(["📚 全文在线阅读", "🔍 全局智能检索", "📄 原版 PDF 阅览"])
        with tab1:
            selected_chapter = st.selectbox("📌 选择章节快速跳转:", list(full_text_dict.keys()))
            st.markdown(f"<div class='standard-text'>{full_text_dict[selected_chapter]}</div>", unsafe_allow_html=True)
        with tab2:
            search_query = st.text_input("🔍 输入检索词 (如: 洞身开挖, 喷射混凝土, 检验批)")
            if search_query:
                found = False
                for chapter, content in full_text_dict.items():
                    if search_query in content:
                        found = True
                        st.markdown(f"#### 📍 【{chapter}】")
                        for p in content.replace(search_query, f"<span class='highlight'>{search_query}</span>").split('\n'):
                            if f"<span class='highlight'>{search_query}</span>" in p: st.markdown(f"<div class='standard-text' style='margin-bottom: 10px; padding: 15px;'>{p}</div>", unsafe_allow_html=True)
                if not found: st.warning(f"未检索到包含「{search_query}」的条款。")
        with tab3:
            target_pdf_name = "JTG_F80_1-2017.pdf" if "公路" in st.session_state.standard_type else "TB10417-2018.pdf"
            st.write(f"📖 **原版 PDF 在线阅览:** `{target_pdf_name}`")
            pdf_bytes = get_pdf_bytes(st.session_state.standard_type)
            if pdf_bytes: render_pdf_viewer(pdf_bytes, target_pdf_name)
            else:
                st.warning(f"⚠️ 系统未能找到内置的 PDF 文件 `{target_pdf_name}`。")
                uploaded_pdf = st.file_uploader("📥 手动上传 PDF 规范进行阅览", type=['pdf'])
                if uploaded_pdf: render_pdf_viewer(uploaded_pdf.read(), uploaded_pdf.name)

if __name__ == "__main__":
    main()