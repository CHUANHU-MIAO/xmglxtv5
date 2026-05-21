# 项目管理系统 V5.0.1 - 部署总览

## 📋 项目简介

项目管理系统 V5.0.1 是一个综合性的工程项目管理平台，提供完整的项目全生命周期管理功能，包括项目管理、投资估算、能耗计算、财务分析等核心功能。系统采用 Flask 框架开发，支持 Web 端和桌面端两种使用模式，适用于各类工程项目的管理需求。

### 系统特点

- **全流程管理**：从项目立项到结款结算的完整生命周期管理
- **多维度分析**：投资估算、能耗计算、财务分析一体化
- **灵活部署**：支持 Web 端和桌面端两种部署方式
- **数据安全**：基于设备指纹的授权机制，保障系统安全
- **易于使用**：直观的用户界面，支持数据导入导出

---

## 🏗️ 系统架构

### 组件概览

| 组件 | 部署位置 | 端口 | 授权模式 | 说明 |
|------|----------|------|----------|------|
| Web系统 | 客户公司本地（Windows/Ubuntu） | 5005 | 买断制 | 完整的项目管理系统，永久授权 |
| 桌面端工具 | 个人电脑（Windows/Ubuntu桌面） | - | 订阅制 | 轻量级测算工具，需订阅账号 |
| 订阅管理后台 | 云服务器（Ubuntu） | 5001 | - | 用户认证、订阅管理、设备绑定 |

### 技术栈

**Web 系统**
- 后端框架：Flask 3.0.0
- 数据库：SQLite
- ORM：Flask-SQLAlchemy 3.1.1
- 用户认证：Flask-Login 0.6.3
- 表单验证：Flask-WTF 1.2.1
- 数据处理：openpyxl 3.1.2, xlrd 2.0.1
- 加密算法：cryptography 41.0.7
- Web服务器：gunicorn 22.0.0

**桌面端工具**
- GUI框架：PyQt5
- 核心计算：自定义计算引擎
- 订阅验证：HTTP API 调用

**订阅管理系统**
- 后端框架：Flask
- 数据库：SQLite
- RESTful API：标准化接口设计

---

## 📁 项目结构

```
项目管理系统-暂存/
├── license_generator.py          # 授权生成工具（管理端使用）
├── private_key.pem               # RSA私钥（请勿外泄）
├── public_key.pem                 # RSA公钥
├── Windows部署.md                  # Windows部署指南
├── Windows部署.txt                 # Windows部署指南（纯文本版）
├── ubantu部署.md                   # Ubuntu部署指南
├── ubantu部署.txt                  # Ubuntu部署指南（纯文本版）
├── README_DEPLOY.md               # 本文件（部署总览）
├── README_DEPLOY.txt              # 本文件（纯文本版）
├── 客户系统/                       # 客户公司部署的Web系统
│   ├── app.py                     # 启动入口（端口5005）
│   ├── license_manager.py         # 授权验证模块
│   ├── requirements.txt           # Python依赖包
│   ├── core/                      # 核心计算模块
│   │   ├── energy/                # 能耗计算
│   │   │   ├── calculator.py      # 能耗计算引擎
│   │   │   └── factors.py         # 能耗因子定义
│   │   ├── finance/               # 财务计算
│   │   │   └── calculator.py      # 财务分析引擎
│   │   ├── investment/            # 投资估算
│   │   │   └── calculator.py      # 投资计算引擎
│   │   └── tests/                 # 单元测试
│   ├── web/                       # Web应用
│   │   ├── app.py                 # Flask应用工厂
│   │   ├── config.py              # 配置文件（版本：V5.0.1）
│   │   ├── extensions.py          # Flask扩展初始化
│   │   ├── models.py              # 数据库模型
│   │   ├── utils.py               # 工具函数
│   │   ├── blueprints/            # 蓝图模块
│   │   │   ├── auth.py            # 认证蓝图（登录/登出）
│   │   │   ├── projects.py        # 项目管理蓝图
│   │   │   ├── admin.py           # 管理员功能蓝图
│   │   │   ├── files.py           # 文件管理蓝图
│   │   │   └── estimation.py      # 估算功能蓝图
│   │   ├── services/              # 业务逻辑层
│   │   │   ├── project_service.py # 项目服务
│   │   │   └── finance_service.py # 财务服务
│   │   ├── static/                # 静态资源
│   │   │   ├── style.css          # 样式文件
│   │   │   └── app.js             # JavaScript文件
│   │   └── templates/             # 模板文件
│   │       ├── base.html          # 基础模板
│   │       ├── login.html         # 登录页面
│   │       ├── index.html         # 首页
│   │       ├── admin_projects.html    # 项目管理页面
│   │       ├── admin_operations.html  # 经营管理页面
│   │       ├── admin_users.html       # 用户管理页面
│   │       ├── project_add.html       # 项目添加页面
│   │       ├── project_edit.html      # 项目编辑页面
│   │       ├── project_detail.html    # 项目详情页面
│   │       ├── investment_estimate.html # 投资估算页面
│   │       ├── energy_estimate.html     # 能耗估算页面
│   │       ├── finance_normal.html     # 财务分析页面
│   │       ├── finance_bond.html       # 债券融资页面
│   │       └── file_viewer.html        # 文件查看页面
│   └── desktop/                   # 桌面端工具
│       ├── calculator_tool.py     # 桌面应用入口
│       ├── config.json            # 配置文件
│       └── requirements.txt       # 桌面端依赖
└── 订阅管理系统/                    # 订阅管理后台
    ├── server.py                  # 启动入口（端口5001）
    ├── config.py                  # 配置文件
    ├── models.py                  # 数据模型
    ├── routes/                    # API路由
    │   ├── auth.py                # 认证路由
    │   ├── subscription.py        # 订阅路由
    │   ├── device.py              # 设备路由
    │   └── admin.py               # 管理员路由
    └── services/                  # 业务逻辑
        ├── auth_service.py        # 认证服务
        └── subscription_service.py # 订阅服务
```

---

## 🗄️ 数据库模型

### 核心数据表

**用户表 (users)**
- 用户名、密码哈希、角色（admin/engineer）
- 创建时间、最后活跃时间
- 项目关联关系

**项目表 (projects)**
- 项目基本信息：名称、描述、位置、类型、阶段
- 项目时间：开始日期、创建时间、更新时间
- 财务信息：合同金额、已结金额、发票金额
- 状态管理：合同状态、发票状态、结款状态
- 关联关系：创建者、附件、资金记录

**附件表 (attachments)**
- 文件名、保存路径、文件类型
- 上传时间、上传用户
- 项目关联

**资金记录表 (fund_records)**
- 金额、用途、备注
- 使用日期、创建时间
- 支出类型、项目关联

**能耗因子表 (energy_factors)**
- 能源名称、单位
- 当量系数、等价系数
- 分类、排序

**投资数据表 (investment_data)**
- 序号、项目名称
- 建筑费、安装费、设备费、其他费
- 单位、数量、指数
- 项目关联

---

## 🚀 快速开始

### 场景一：给客户公司部署 Web 系统

#### Windows 部署

1. **环境准备**
   ```bash
   # 安装 Python 3.8+
   # 下载地址：https://www.python.org/downloads/
   ```

2. **上传文件**
   ```bash
   # 将 客户系统/ 文件夹上传到目标服务器
   ```

3. **安装依赖**
   ```bash
   cd 客户系统
   pip install -r requirements.txt
   ```

4. **生成授权**
   ```bash
   # 在项目根目录执行
   python license_generator.py --auto-deploy 客户系统
   ```

5. **启动服务**
   ```bash
   cd 客户系统
   python app.py
   ```

6. **访问系统**
   ```
   http://localhost:5005
   默认账号：admin / admin123
   ```

#### Ubuntu 部署

1. **环境准备**
   ```bash
   sudo apt update
   sudo apt install python3 python3-pip python3-venv
   ```

2. **创建虚拟环境**
   ```bash
   cd 客户系统
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

4. **生成授权**
   ```bash
   python license_generator.py --auto-deploy 客户系统
   ```

5. **启动服务**
   ```bash
   python app.py
   # 或使用 gunicorn
   gunicorn -w 4 -b 0.0.0.0:5005 app:app
   ```

### 场景二：部署订阅管理后台

1. **上传文件**
   ```bash
   # 将 订阅管理系统/ 上传到云服务器
   ```

2. **安装依赖**
   ```bash
   cd 订阅管理系统
   pip install -r requirements.txt
   ```

3. **启动服务**
   ```bash
   python server.py
   ```

4. **访问管理后台**
   ```
   http://your-server-ip:5001
   ```

### 场景三：桌面端工具部署

1. **安装依赖**
   ```bash
   cd 客户系统/desktop
   pip install -r requirements.txt
   ```

2. **配置订阅服务器**
   ```json
   {
     "subscription_server": "http://your-server-ip:5001"
   }
   ```

3. **启动应用**
   ```bash
   python calculator_tool.py
   ```

4. **用户注册登录**
   - 注册账号
   - 选择订阅方案
   - 开始使用

---

## 🔑 授权机制

### Web 系统授权

- **授权模式**：买断制
- **绑定方式**：设备指纹（MAC地址 + 硬盘序列号）
- **有效期**：永久有效
- **生成命令**：`python license_generator.py --auto-deploy 客户系统`

### 桌面端工具授权

- **授权模式**：订阅制
- **验证方式**：通过订阅管理后台验证
- **设备限制**：每账号最多2台设备同时在线
- **订阅周期**：按月/按年订阅

---

## 💡 核心功能

### 项目管理

- **项目全生命周期管理**：立项、执行、监控、结项
- **多维度筛选**：按关键词、日期、状态、金额筛选
- **财务跟踪**：合同金额、已结金额、未结金额
- **状态管理**：合同状态、发票状态、结款状态
- **附件管理**：上传、下载、查看项目相关文件
- **数据导出**：支持 Excel 格式导出

### 经营管理

- **总收入构成**：已收账款、应收账款统计
- **收支分析**：收入、支出、利润分析
- **趋势图表**：近6个月经营状况可视化
- **点击导航**：点击图表跳转到对应项目列表
- **数据统计**：自动计算各项财务指标

### 投资估算

- **多项目类型**：建筑工程、安装工程、设备采购
- **费用分类**：建筑费、安装费、设备费、其他费
- **指数调整**：支持价格指数调整
- **费率计算**：管理费、设计费、监理费等
- **数据导入导出**：Excel 格式支持

### 能耗计算

- **多能源类型**：电力、天然气、热力、煤炭等
- **双系数计算**：当量系数、等价系数
- **标准对比**：与行业标准对比分析
- **负荷计算**：电力负荷计算
- **报告生成**：自动生成能耗报告

### 财务分析

- **投资回报分析**：NPV、IRR、投资回收期
- **偿债能力**：偿债备付率、覆盖率
- **现金流预测**：收入、支出预测
- **敏感性分析**：多方案对比
- **融资方案**：债券融资、股权融资

---

## 🔐 默认账号

### Web 系统

- **管理员账号**
  - 用户名：`admin`
  - 密码：`admin123`
  - 角色：管理员
  - 权限：完整系统管理权限

- **工程师账号**
  - 需要管理员手动创建
  - 角色：工程师
  - 权限：项目管理、数据录入

### 订阅管理系统

- **管理员账号**
  - 需要首次运行时创建
  - 角色：超级管理员
  - 权限：用户管理、订阅管理

---

## ⚙️ 配置说明

### Web 系统配置

```python
# 客户系统/web/config.py
class Config:
    BASEDIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{os.path.join(BASEDIR, "instance", "system.db")}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', os.path.abspath(os.path.join(BASEDIR, '上传的文件')))
    SECRET_KEY = '123456'
    STANDARD_FILES_FOLDER = os.path.join(UPLOAD_FOLDER, 'standard_files')
    VERSION = 'V5.0.1'
```

### 环境变量

- `UPLOAD_FOLDER`：文件上传目录（可选）
- `SECRET_KEY`：Flask 密钥（建议修改）

### 桌面端配置

```json
// 客户系统/desktop/config.json
{
  "subscription_server": "http://your-server-ip:5001"
}
```

---

## 📊 数据统计逻辑

### 收入构成

- **已收账款** = 已结款 + 部分结清
- **应收账款** = 未结款 + 未结算

### 结款状态

- `已结款`：完全结清
- `已结清`：完全结清
- `部分结清`：部分结清
- `未结款`：未结款
- `未结`：未结款
- `未结算`：未结算

### 金额单位

- **显示单位**：万元
- **存储单位**：元
- **转换比例**：1万元 = 10000元

---

## 🎯 使用指南

### 项目管理流程

1. **创建项目**
   - 填写项目基本信息
   - 设置合同金额、开始日期
   - 分配项目负责人

2. **项目管理**
   - 更新项目进度
   - 上传项目附件
   - 记录资金收支

3. **财务跟踪**
   - 更新发票状态
   - 记录结款金额
   - 查看财务报表

4. **项目结项**
   - 确认项目完成
   - 生成项目报告
   - 归档项目资料

### 经营管理流程

1. **数据录入**
   - 录入项目收入
   - 录入运营支出
   - 更新结款状态

2. **数据分析**
   - 查看总收入构成
   - 分析收支趋势
   - 评估经营状况

3. **决策支持**
   - 点击图表查看详情
   - 导出数据报表
   - 制定经营策略

---

## 🛠️ 常见问题

### 1. 登录失败

**问题**：点击登录按钮显示 "Not Found"

**解决**：
- 检查登录表单 action 是否为 `/auth/login`
- 检查用户名字段是否为 `username`

### 2. 数据库连接错误

**问题**：显示 "unable to open database file"

**解决**：
- 确保 `instance` 目录存在
- 检查数据库文件权限

### 3. 文件上传失败

**问题**：无法上传文件

**解决**：
- 检查上传目录权限
- 确认文件大小限制
- 检查磁盘空间

### 4. 授权验证失败

**问题**：启动时显示授权无效

**解决**：
- 重新生成授权文件
- 检查设备指纹是否匹配
- 确认授权文件路径正确

### 5. 统计数据不准确

**问题**：图表数据与实际不符

**解决**：
- 检查金额单位转换
- 确认结款状态设置
- 验证数据录入完整性

---

## 📞 技术支持

### 部署支持

- Windows 部署：参考 [Windows部署.md](./Windows部署.md)
- Ubuntu 部署：参考 [ubantu部署.md](./ubantu部署.md)

### 问题反馈

如遇到技术问题，请提供以下信息：
- 系统版本：V5.0.1
- 操作系统：Windows / Ubuntu
- 错误信息：完整错误日志
- 复现步骤：详细操作步骤

---

## 📝 更新日志

### V5.0.1 (当前版本)

**新增功能**
- 支付状态分组功能（已收/应收）
- 经营管理页面图表点击导航
- 项目管理页面多维度筛选
- 近6个月经营状况图表优化

**功能优化**
- 总收入构成逻辑更新
- 数据统计准确性提升
- 用户界面体验优化
- 系统名称统一为"项目管理系统"

**问题修复**
- 修复登录页面路由错误
- 修复数据库连接问题
- 修复JSON序列化错误
- 修复API端点404错误
- 修复图表数据显示问题

**系统改进**
- 移除默认工程师账号
- 优化授权验证机制
- 提升系统安全性
- 优化文件上传功能

---

## 📄 许可证

本项目采用商业授权模式，具体授权条款请参考授权协议。

---

## 🎉 快速部署命令

```bash
# 一键部署 Web 系统（Windows）
cd 客户系统
pip install -r requirements.txt
python license_generator.py --auto-deploy 客户系统
python app.py

# 一键部署 Web 系统（Ubuntu）
cd 客户系统
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python license_generator.py --auto-deploy 客户系统
python app.py

# 一键部署订阅管理系统
cd 订阅管理系统
pip install -r requirements.txt
python server.py

# 一键部署桌面端工具
cd 客户系统/desktop
pip install -r requirements.txt
python calculator_tool.py
```

---

**系统版本**：V5.0.1  
**最后更新**：2026-05-21  
**技术支持**：项目管理系统开发团队