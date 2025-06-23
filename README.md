# 智析平台 - AI数据分析平台

<div align="center">
  <img src="https://img.shields.io/badge/Python-3.8+-blue.svg" alt="Python Version">
  <img src="https://img.shields.io/badge/Flask-2.3.3-green.svg" alt="Flask Version">
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License">
</div>

## 📋 项目简介

智析平台是一个基于AI驱动的数据分析平台，集成了阿里云大模型API，提供智能对话、文档问答、数据治理和自动化分析报告等功能。项目采用现代化毛玻璃设计风格，提供优雅的用户体验。

## ✨ 主要功能

### 🤖 AI智能对话
- ✅ **普通模式**：标准AI对话，支持自定义人设和初始提示
- ✅ **知识库模式**：基于上传文档的智能问答
- ✅ **多会话管理**：支持创建、切换和删除多个对话会话
- ✅ **历史记录**：自动保存对话历史，支持会话恢复

### 📊 数据治理工具
- ✅ **智能Excel处理**：自动识别和处理合并单元格
- ✅ **复杂表头解析**：智能识别多层表头结构
- ✅ **AI辅助处理**：自然语言指令处理数据
- ✅ **数据预览**：实时预览处理结果
- ✅ **批量下载**：一键下载处理后的文件

### 📈 智能分析报告
- ✅ **自动数据统计**：基础统计、数值分析、分类统计
- ✅ **AI分析报告**：自动生成专业的数据分析报告
- ✅ **数据可视化**：自动生成多种图表（柱状图、散点图、热力图）
- ✅ **报告导出**：生成完整的HTML分析报告

### 📁 文件支持
- ✅ **文档格式**：TXT、PDF、DOCX、MD
- ✅ **数据格式**：Excel (XLSX/XLS)、CSV
- ✅ **智能编码检测**：自动识别文件编码格式

## 🛠️ 技术栈

### 后端技术
- **框架**：Flask 2.3.3
- **数据处理**：pandas、openpyxl、numpy
- **可视化**：matplotlib、seaborn
- **AI集成**：阿里云大模型API
- **文件处理**：PyPDF2、python-docx

### 前端技术
- **界面风格**：现代毛玻璃透明设计
- **交互特效**：CSS动画、粒子背景
- **响应式设计**：适配各种屏幕尺寸
- **字体**：Inter + 中文字体优化

## 📦 安装配置

### 环境要求
- Python 3.8+
- pip 包管理器

### 1. 克隆项目
```bash
git clone <your-repository-url>
cd 联通
```

### 2. 创建虚拟环境
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
```

### 3. 安装依赖
```bash
pip install -r requirements.txt
```

### 4. 环境变量配置
创建 `.env` 文件并配置：
```env
# 阿里云大模型API配置
API_KEY=your_alibaba_cloud_api_key
API_URL=https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation

# Flask配置
FLASK_ENV=development
FLASK_DEBUG=True
SECRET_KEY=your_secret_key
```

### 5. 启动应用
```bash
python app.py
```

访问 `http://localhost:5000` 即可使用平台。

## 🔧 项目结构

```
智析平台/
├── app.py                 # 主应用程序
├── requirements.txt       # 依赖包列表
├── .env                  # 环境变量配置
├── templates/            # HTML模板
│   └── index.html        # 主页面模板
├── static/              # 静态资源
│   ├── css/
│   │   └── style.css    # 样式文件
│   ├── js/
│   │   └── main.js      # 前端交互逻辑
│   └── images/          # 图片资源
├── uploads/             # 临时文件上传目录
├── processed/           # 处理后的Excel文件
├── analysis/            # 数据分析结果
│   ├── *.xlsx          # 分析数据
│   ├── *.html          # 分析报告
│   └── images_*/       # 可视化图表
└── charts/              # 图表缓存目录
```

## 🚀 使用指南

### AI对话功能
1. 选择对话模式（普通模式/知识库模式）
2. 上传文档（知识库模式）或设置初始提示（普通模式）
3. 开始与AI对话
4. 支持多会话管理和历史记录

### 数据治理功能
1. 点击"智能数据治理"工具
2. 上传Excel文件
3. 系统自动处理合并单元格和复杂表头
4. 可选：使用AI指令进一步处理数据
5. 下载处理后的文件

### 数据分析功能
1. 点击"智能分析报告"工具
2. 上传数据文件（Excel/CSV）
3. 系统自动进行数据统计和分析
4. 查看AI生成的分析报告
5. 下载完整的HTML报告

## 🎨 UI特色

### 毛玻璃设计
- 现代半透明毛玻璃效果
- 动态粒子背景动画
- 柔和的阴影和渐变
- 流畅的交互动画

### 响应式布局
- 适配PC、平板、手机等设备
- 侧边栏可折叠设计
- 智能内容适配

### 交互体验
- 流畅的页面切换动画
- 实时反馈和状态提示
- 拖拽上传文件支持
- 快捷键操作支持

## 📊 API接口

### 主要API端点
- `POST /api/chat` - AI对话接口
- `POST /api/upload` - 文件上传接口
- `GET /api/sessions` - 获取会话列表
- `POST /api/process_excel` - Excel处理接口
- `POST /api/data_analysis` - 数据分析接口

详细API文档请参考代码注释。

## 🔒 安全考虑

- 文件上传大小限制：16MB
- 支持的文件类型白名单验证
- 临时文件自动清理
- 文件名安全处理
- API密钥环境变量保护

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 📝 更新日志

### v2.0.0 (2025-06-23)
- ✨ 完整重构项目架构
- 🎨 新增毛玻璃现代UI设计
- 📊 增强数据处理和分析功能
- 🤖 集成阿里云大模型API
- 📱 优化响应式设计

### v1.0.0 (2025-06-12)
- 🎉 项目初始版本
- 基础AI对话功能
- Excel数据处理功能


## 📞 联系方式

📧 Email: zwan0569@student.monash.edu


---

<div align="center">
  <p>Made with ❤️ by zwan0569@student.monash.edu</p>
  <p>⭐ 如果这个项目对您有帮助，请给我们一个星标！</p>
</div> 