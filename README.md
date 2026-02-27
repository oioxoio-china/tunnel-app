# 隧道工程检验批划分系统 Pro

🚇 隧道工程施工质量验收标准检验批划分工具

## 功能特点

- 支持铁路隧道（TB 10417-2018）、高速铁路隧道（TB 10753-2018）、公路隧道（JTG F80/1-2017）三种标准
- 检验批自动计算和划分
- 原版 PDF 在线阅览（支持书签导航）
- 统计看板可视化

## 安装部署

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动应用

```bash
# 方式一：直接运行
python -m streamlit run streamlit_app.py

# 方式二：使用启动脚本（Windows）
启动.bat
```

### 3. 访问应用

浏览器打开：http://localhost:8501

## 文件说明

```
deploy/
├── streamlit_app.py      # 主应用
├── default_config.py    # 配置文件
├── standards_text.py    # 标准文本配置
├── standards_data.py    # 标准数据加载
├── manual_tables.py     # 手动表格配置
├── *.pdf               # 标准规范 PDF 文件
├── requirements.txt     # Python 依赖
└── README.md          # 说明文档
```

## 使用说明

1. 选择隧道类型（铁路/高铁/公路）
2. 配置参数（围岩等级、开挖方式等）
3. 自动生成检验批划分表
4. 可导出 Excel 表格
5. 支持 PDF 原版查阅

## 技术栈

- Streamlit - Web 框架
- Pandas - 数据处理
- Matplotlib - 图表绘制
- PyMuPDF/PDF.js - PDF 渲染

## 版本

v18.2 - 高铁铁路规范对齐版
