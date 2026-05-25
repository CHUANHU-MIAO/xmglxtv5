# 项目管理系统 V5.0.1 — Code Wiki

## 目录

1. [项目概述](#1-项目概述)
2. [系统架构](#2-系统架构)
3. [项目目录结构](#3-项目目录结构)
4. [技术栈](#4-技术栈)
5. [Web 系统模块详解](#5-web-系统模块详解)
   - [5.1 应用入口与配置](#51-应用入口与配置)
   - [5.2 数据库模型](#52-数据库模型)
   - [5.3 蓝图（路由/控制器）](#53-蓝图路由控制器)
   - [5.4 服务层](#54-服务层)
   - [5.5 前端模板](#55-前端模板)
   - [5.6 核心计算模块](#56-核心计算模块)
6. [桌面端模块详解](#6-桌面端模块详解)
7. [订阅管理系统模块详解](#7-订阅管理系统模块详解)
8. [授权与License机制](#8-授权与license机制)
9. [依赖关系](#9-依赖关系)
10. [项目运行方式](#10-项目运行方式)
11. [常见问题](#11-常见问题)

---

## 1. 项目概述

**项目管理系统 V5.0.1** 是一个综合性的工程项目管理平台，提供完整的项目全生命周期管理功能。系统面向工程咨询公司，覆盖项目管理、投资估算、能耗计算、财务分析等核心业务场景。

系统采用 **Flask + SQLite + PySide6** 技术栈，同时支持 **Web 端** 和 **桌面端** 两种使用模式，并附带独立的 **订阅管理后台**。

### 主要能力

- **项目管理**：项目创建、编辑、删除、搜索、批量导入、Excel 导出
- **投资估算**：建筑工程费、安装工程费、设备购置费等分类估算
- **能耗计算**：多能源类型（电力、天然气、热力等）的折标煤计算
- **财务分析**：NPV/IRR 计算、还本付息测算、收入成本预测
- **经营管理**：收支统计、月度利润趋势、应收账款管理
- **文件管理**：项目附件上传下载、标准规范文件库
- **用户管理**：管理员/工程师/访客三种角色，支持权限控制

---

## 2. 系统架构

系统采用 **微内核 + 分层架构**，整体分为三大子系统：

```
┌──────────────────────────────────────────────────────────┐
│                    桌面端 (PySide6)                        │
│  ┌──────────────┐  ┌──────────────────────────────┐      │
│  │ Subscription  │  │  QWebEngineView 内嵌 Web UI  │      │
│  │   Client      │  │  项目树/列表 + 浏览操作       │      │
│  └──────┬───────┘  └──────────────┬───────────────┘      │
└─────────┼─────────────────────────┼──────────────────────┘
          │ HTTP API                │ iframe / HTTP
          ▼                         ▼
┌──────────────────────────────────────────────────────────┐
│                  Flask Web 系统 (端口 5005)                │
│  ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌─────────────┐  │
│  │ 蓝图层   │ │ 服务层    │ │ 模型层   │ │  核心计算层   │  │
│  │(路由/    │ │(业务逻辑) │ │(ORM)    │ │(energy/     │  │
│  │控制器)   │ │          │ │         │ │ finance/    │  │
│  │         │ │          │ │         │ │ investment) │  │
│  └─────────┘ └──────────┘ └──────────┘ └─────────────┘  │
└────────────────────┬─────────────────────────────────────┘
                     │ HTTP API
                     ▼
┌──────────────────────────────────────────────────────────┐
│              订阅管理系统 (端口 5001)                       │
│  ┌──────────┐ ┌──────────────┐ ┌────────────────────┐    │
│  │ 认证路由  │ │ 订阅服务      │ │ 用户/设备/订阅模型  │    │
│  └──────────┘ └──────────────┘ └────────────────────┘    │
└──────────────────────────────────────────────────────────┘
```

- **Web系统** — 核心业务系统，Flask 应用，提供完整的管理和测算功能
- **桌面端工具** — PySide6 桌面应用，内嵌 WebView，带订阅验证功能
- **订阅管理系统** — 独立部署的认证与订阅管理服务

---

## 3. 项目目录结构

```
项目根目录/
├── 一键迁移数据.py              # 数据迁移脚本
├── .gitignore
├── README_DEPLOY.md             # 部署总览文档
├── Windows部署.md               # Windows 部署详细指南
├── ubantu部署.md                # Ubuntu 部署详细指南
│
├── 客户系统/                     # ★ 核心系统
│   ├── core/                    # 核心计算模块
│   │   ├── __init__.py
│   │   ├── energy/
│   │   │   ├── __init__.py
│   │   │   ├── factors.py       # 能耗因子常量定义（22种能源）
│   │   │   └── calculator.py    # 能耗计算引擎
│   │   ├── finance/
│   │   │   ├── __init__.py
│   │   │   └── calculator.py    # 财务分析引擎（NPV/IRR/偿债等）
│   │   └── investment/
│   │       ├── __init__.py
│   │       └── calculator.py    # 投资估算引擎（各项费用计算）
│   │   └── tests/               # 单元测试
│   │       ├── test_energy.py
│   │       ├── test_finance.py
│   │       └── test_investment.py
│   │
│   ├── web/                     # Flask Web 应用
│   │   ├── app.py               # 应用工厂（create_app）
│   │   ├── config.py            # 配置类（版本 V5.0.1）
│   │   ├── extensions.py        # Flask 扩展（db, login_manager）
│   │   ├── models.py            # 6个 ORM 模型
│   │   ├── utils.py             # 工具函数（数字格式化）
│   │   ├── blueprints/          # 路由控制器（5个蓝图）
│   │   │   ├── auth.py          # 认证蓝图
│   │   │   ├── projects.py      # 项目管理蓝图
│   │   │   ├── admin.py         # 管理员蓝图
│   │   │   ├── files.py         # 文件管理蓝图
│   │   │   └── estimation.py    # 估算功能蓝图
│   │   ├── services/            # 业务逻辑层
│   │   │   ├── project_service.py  # 项目统计服务
│   │   │   └── finance_service.py  # 财务统计服务
│   │   ├── templates/           # Jinja2 模板（~20个）
│   │   └── static/              # 静态资源（style.css, app.js）
│   │
│   └── desktop/                 # PySide6 桌面应用
│       ├── __init__.py
│       ├── desktop_app.py       # 桌面应用入口
│       ├── main_window.py       # 主窗口 + WebView + UI
│       ├── first_run_config.py  # 首次运行配置向导
│       ├── subscription.py      # 订阅客户端（设备指纹+API）
│       └── requirements.txt     # 桌面端依赖（含PySide6）
│
└── 订阅管理系统/                  # 独立认证订阅服务
    ├── server.py                # 服务入口（端口 5001）
    ├── config.py                # 配置（JWT密钥等）
    ├── models.py                # 4个 ORM 模型
    ├── routes/                  # API 路由
    │   ├── auth.py              # 认证 API（注册/登录/验证）
    │   ├── subscription.py      # 订阅 API
    │   ├── device.py            # 设备管理 API
    │   └── admin.py             # 管理后台 API
    └── services/                # 业务逻辑
        ├── auth_service.py      # 认证服务（bcrypt+JWT）
        └── subscription_service.py  # 订阅服务
```

---

## 4. 技术栈

### Web 系统

| 技术 | 用途 | 版本 |
|------|------|------|
| Python | 编程语言 | 3.11+ |
| Flask | Web 框架 | 3.0.0 |
| Flask-SQLAlchemy | ORM | 3.1.1 |
| Flask-Login | 用户会话管理 | 0.6.3 |
| Flask-WTF | 表单保护 | 1.2.1 |
| SQLite | 数据库 | — |
| openpyxl | Excel 读写 | 3.1.2 |
| cryptography | 加密（License 验证） | 41.0.7 |
| Jinja2 | 模板引擎 | — |
| HTML/CSS/JS | 前端 | — |

### 桌面端

| 技术 | 用途 | 版本 |
|------|------|------|
| PySide6 | Qt GUI 框架 | 6.6+ |
| QWebEngineView | 内嵌 Web 浏览器 | — |
| requests | HTTP 客户端 | 2.31+ |

### 订阅管理系统

| 技术 | 用途 | 版本 |
|------|------|------|
| Flask | Web 框架 | 3.0.0 |
| PyJWT | JWT 令牌 | 2.8.0 |
| bcrypt | 密码哈希 | 4.1.2 |
| SQLite | 数据库 | — |

---

## 5. Web 系统模块详解

### 5.1 应用入口与配置

#### [app.py](file:///c:/Users/Administrator/Desktop/xmglxtv5/客户系统/web/app.py)

应用工厂模式创建 Flask 实例，核心流程：

1. **加载配置** — 从 `Config` 类读取数据库路径、上传目录、密钥等
2. **初始化扩展** — `db.init_app(app)` + `login_manager.init_app(app)`
3. **注册蓝图** — 注册 5 个蓝图（auth, projects, admin, files, estimation）
4. **用户加载器** — `@login_manager.user_loader` 根据 user_id 查询 User
5. **模板注入** — `@app.context_processor` 注入 `system_version` 到所有模板
6. **初始化数据** — 自动建表、创建默认 admin 用户、初始化 22 种能耗因子
7. **桌面模式** — 若 `DESKTOP_MODE=true`，自动创建"桌面测算项目"

**关键函数：**

| 函数 | 功能 |
|------|------|
| `create_app()` | 应用工厂，返回 Flask 实例 |
| `_ensure_desktop_default_project()` | 桌面模式自动创建默认测算项目 |
| `inject_version()` | 上下文处理器，注入版本号 |
| `load_user(user_id)` | Flask-Login 用户加载回调 |

#### [config.py](file:///c:/Users/Administrator/Desktop/xmglxtv5/客户系统/web/config.py)

```python
class Config:
    BASEDIR                        # 项目根目录
    DESKTOP_MODE                   # 桌面模式标志（环境变量）
    UPLOAD_FOLDER                  # 上传文件存储路径
    STANDARD_FILES_FOLDER          # 标准规范文件目录
    DESKTOP_DATA_DIR               # 桌面模式数据库目录
    SQLALCHEMY_DATABASE_URI        # SQLite 数据库 URI
    SECRET_KEY = '123456'          # Flask 密钥
    VERSION = 'V5.0.1'             # 系统版本
```

#### [extensions.py](file:///c:/Users/Administrator/Desktop/xmglxtv5/客户系统/web/extensions.py)

- `db = SQLAlchemy()` — 数据库 ORM 实例
- `login_manager = LoginManager()` — 登录管理器

#### [utils.py](file:///c:/Users/Administrator/Desktop/xmglxtv5/客户系统/web/utils.py)

| 函数 | 功能 |
|------|------|
| `format_number(value)` | 格式化数字为保留两位小数字符串 |
| `format_wan(value)` | 将数值除以 10000 并保留两位小数（元→万元） |

---

### 5.2 数据库模型

#### [models.py](file:///c:/Users/Administrator/Desktop/xmglxtv5/客户系统/web/models.py)

**6 个 ORM 模型 + 1 张关联表：**

##### User（用户表 — `users`）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | 主键 |
| username | String(80) UNIQUE | 用户名 |
| password_hash | String(256) | 密码哈希 |
| role | String(20) | 角色: admin/engineer/visitor |
| created_at | DateTime | 注册时间 |
| last_active_time | DateTime | 最后活跃时间 |

**关联：** `projects` — 拥有的项目；`visitor_projects_rel` — 可查看的项目（多对多）

**方法：**

| 方法 | 功能 |
|------|------|
| `set_password(password)` | 使用 werkzeug 安全哈希密码 |
| `check_password(password)` | 校验密码 |

##### Project（项目表 — `projects`）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | 主键 |
| name | String(200) | 项目名称 |
| description | Text | 描述 |
| location | String(200) | 所在地 |
| project_type | String(100) | 项目类型 |
| phase | String(100) | 项目阶段 |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |
| user_id | FK→users.id | 创建者 |
| author | String(80) | 编制人 |
| progress | String(50) | 进度 |
| is_valid | Integer | 是否有效(1/0)，软删除 |
| start_date | Date | 开始日期 |
| owner | String(200) | 业主单位 |
| total_investment | Float | 总投资(万元) |
| contract_amount | Float | 合同金额(万元) |
| contract_status | String(50) | 合同情况 |
| invoice_status | String(50) | 开票情况 |
| invoiced_amount | Float | 已开票金额 |
| payment_status | String(50) | 结款情况 |
| settled_amount | Float | 已结清金额 |
| payment_settlement_status | String(50) | 结算提成 |
| source | String(100) | 来源 |
| owner_name | String(100) | 业主姓名 |
| owner_phone | String(20) | 业主电话 |
| service_content | Text | 服务内容 |
| remark | Text | 备注 |
| create_time | DateTime | 创建时间 |

**关联：** `creator` → User；`attachments` → Attachment；`fund_records` → FundRecord；`investment_data` → InvestmentData；`visitors` → User（多对多）

##### Attachment（附件表 — `attachments`）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | 主键 |
| project_id | FK→projects.id | 关联项目 |
| filename | String(200) | 原始文件名 |
| save_name | String(200) | 存储文件名 |
| file_type | String(50) | 文件类型（扩展名） |
| upload_time | DateTime | 上传时间 |
| upload_user | String(50) | 上传用户 |

##### Log（日志表 — `logs`）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | 主键 |
| project_id | Integer | 关联项目 |
| user | String(50) | 操作用户 |
| content | Text | 操作内容 |
| time | DateTime | 操作时间 |

##### StandardFile（标准文件表 — `standard_files`）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | 主键 |
| filename | String(200) | 原始文件名 |
| standard_name | String(200) | 标准名称 |
| version | String(50) | 版本号 |
| file_type | String(50) | 文件类型（如"建设标准"） |
| file_path | String(500) | 存储路径 |
| upload_time | DateTime | 上传时间 |
| upload_user | String(50) | 上传用户 |
| download_count | Integer | 下载次数 |

##### FundRecord（资金记录表 — `fund_records`）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | 主键 |
| amount | Float | 金额(元) |
| purpose | String(100) | 用途 |
| remark | Text | 备注 |
| use_date | Date | 使用日期 |
| create_time | DateTime | 创建时间 |
| create_user | String(50) | 创建用户 |
| expense_type | String(20) | 支出类型(运营支出/项目支出) |
| project_id | FK→projects.id | 关联项目 |

##### EnergyFactor（能耗因子表 — `energy_factors`）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | 主键 |
| name | String(100) UNIQUE | 能源名称 |
| unit | String(50) | 计量单位 |
| equivalent_coef | Float | 折标煤系数(当量值) |
| equivalent_note | String(200) | 当量值说明 |
| equivalent_coef_val | Float | 折标煤系数(等价值) |
| equivalent_val_note | String(200) | 等价值说明 |
| category | String(50) | 分类(能源/耗能工质) |
| is_active | Boolean | 是否激活 |
| sort_order | Integer | 排序号 |

**预置数据（22条）：** 电力、天然气、热力、原煤、洗精煤、焦炭、汽油、柴油、燃料油、液化石油气、炼厂干气、煤焦油、粗苯、甲醇、乙醇、氢气、生物质颗粒、除盐水、压缩空气、氧气、氮气、水

##### InvestmentData（投资数据表 — `investment_data`）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | 主键 |
| project_id | FK→projects.id | 关联项目 |
| serial_number | String(20) | 序号（如 1.1, 1.2） |
| item_name | String(200) | 工程/费用名称 |
| building_cost | Float | 建筑工程费 |
| installation_cost | Float | 安装工程费 |
| equipment_cost | Float | 设备购置费 |
| other_cost | Float | 其他费用 |
| unit | String(20) | 单位 |
| quantity | Float | 数量 |
| index | Float | 单价/指数 |
| use_index | Boolean | 是否使用指数法 |
| billing_basis | String(200) | 取费依据 |
| calc_rate | Float | 费率(%) |
| discount_rate | Float | 折扣率(%) |
| build_category | String(50) | 建筑类别 |
| address_category | String(50) | 地区类别 |
| is_reserve_rate | Boolean | 是否预留费率 |
| reserve_rate | Float | 预留费率(%) |

##### visitor_projects（关联表）

多对多关联 `User` 与 `Project`，用于访客权限控制。

---

### 5.3 蓝图（路由/控制器）

#### 5.3.1 认证蓝图 — [auth.py](file:///c:/Users/Administrator/Desktop/xmglxtv5/客户系统/web/blueprints/auth.py)

`url_prefix: /auth`

| 路由 | 方法 | 功能 | 权限 |
|------|------|------|------|
| `/auth/login` | GET/POST | 用户登录；GET 时清理一年未活跃的访客 | 公开 |
| `/auth/register` | GET/POST | 用户注册 | 公开 |
| `/auth/logout` | GET | 用户登出 | 已登录 |
| `/auth/change_password` | GET/POST | 修改当前用户密码 | 已登录 |

#### 5.3.2 项目管理蓝图 — [projects.py](file:///c:/Users/Administrator/Desktop/xmglxtv5/客户系统/web/blueprints/projects.py)

`url_prefix: 无（根路由）`

| 路由 | 方法 | 功能 | 权限 |
|------|------|------|------|
| `/` | GET | 首页，显示项目列表、月度统计、地区/工程师分布 | 已登录 |
| `/export_projects` | GET | 导出所有项目为 Excel | 已登录 |
| `/api/projects/search` | GET | 高级搜索（关键词/日期/状态等多维度筛选），返回 JSON | 已登录 |
| `/project/detail/<id>` | GET | 项目详情页 | 已登录+权限 |
| `/project/add` | GET/POST | 创建新项目 | 已登录(访客除外) |
| `/my_projects` | GET | 我的项目列表 | 已登录 |
| `/export_my_projects` | GET | 导出我的项目为 Excel | 已登录 |
| `/project/batch_upload` | POST | 批量导入 Excel 项目 | 已登录(访客除外) |
| `/project/edit/<id>` | GET/POST | 编辑项目 | 已登录(本人或admin) |
| `/project/update_settlement` | POST | 更新结算提成状态 | 已登录(本人或admin) |
| `/project/delete` | POST | 软删除项目（表单提交） | 已登录(本人或admin) |
| `/project/delete/<id>` | GET | 软删除项目（链接跳转） | 已登录(本人或admin) |

**核心常量：** `PROVINCES` — 34 个中国省级行政区列表

**关键函数详情：**

- `index()` — 首页分页列表，调用 `get_index_statistics()` 获取月度趋势、地区分布、工程师分布数据
- `api_projects_search()` — 支持 10+ 维度过滤（keyword/year/month/start_date/end_date/contract_status/payment_status/payment_group/invoice_status/settlement），返回分页 JSON
- `batch_upload()` — 解析 Excel 文件，通过 `COLUMN_MAP`（18 个中文字段→模型字段映射）导入项目
- `export_projects()` / `export_my_projects()` — 使用 openpyxl 生成带样式的 Excel 报表

#### 5.3.3 管理蓝图 — [admin.py](file:///c:/Users/Administrator/Desktop/xmglxtv5/客户系统/web/blueprints/admin.py)

`url_prefix: /admin`

**装饰器：** `admin_required` — 自定义装饰器，校验当前用户角色为 admin

| 路由 | 方法 | 功能 |
|------|------|------|
| `/admin/users` | GET/POST | 用户列表+创建用户（支持访客分配可查看项目） |
| `/admin/user/delete/<id>` | GET/POST | 删除用户（有保护逻辑） |
| `/admin/projects` | GET | 管理员视角项目列表（多维度筛选） |
| `/admin/projects/export` | GET | 管理员导出项目 Excel |
| `/admin/project/delete/<id>` | GET/POST | 彻底删除项目（物理删除+级联删除日志/资金记录） |
| `/admin/operations` | GET/POST | 经营管理：收支记录录入、查看、统计图表 |
| `/admin/operations/delete/<id>` | POST | 删除支出记录 |
| `/admin/operations/export` | GET | 导出支出记录 Excel |
| `/admin/database` | GET | 标准规范文件库列表 |
| `/admin/database/upload` | POST | 上传标准规范文件 |
| `/admin/database/download/<id>` | GET | 下载文件（下载计数+1） |
| `/admin/database/update/<id>` | POST | 更新文件版本 |
| `/admin/database/view/<id>` | GET | 在线预览文件 |
| `/admin/database/raw/<id>` | GET | 获取文件原始内容 |

**关键逻辑：**

- `users()` — 创建用户时可以设置角色和分配访客可见项目
- `user_delete()` — 有保护逻辑：不能删除自己、不能删除 admin 账号、有项目时拒绝删除
- `operations()` — 支出记录管理和完整的经营统计：
  - 计算总收入（已收+应收）
  - 按项目支出/运营支出分类汇总
  - 近 6 个月月度收入/支出/利润趋势

#### 5.3.4 文件管理蓝图 — [files.py](file:///c:/Users/Administrator/Desktop/xmglxtv5/客户系统/web/blueprints/files.py)

`url_prefix: /files`

| 路由 | 方法 | 功能 |
|------|------|------|
| `/files/<project_id>` | GET | 项目文件查看器 |
| `/files/upload/<project_id>` | POST | 上传文件到项目（写入日志） |
| `/files/download/<project_id>/<filename>` | GET | 下载项目文件 |
| `/files/delete/<project_id>/<filename>` | POST/GET | 删除项目文件（写入日志） |

#### 5.3.5 估算蓝图 — [estimation.py](file:///c:/Users/Administrator/Desktop/xmglxtv5/客户系统/web/blueprints/estimation.py)

`url_prefix: 无`

**辅助函数：**

| 函数 | 功能 |
|------|------|
| `get_project_folder(project)` | 返回项目专属数据目录 `{UPLOAD_FOLDER}/{project.id}-{project.name}` |
| `_check_visitor_access(project)` | 访客权限校验 |
| `_ensure_project_folder(project)` | 确保项目数据目录存在 |
| `_read_json(folder, filename)` | 读取 JSON 文件 |
| `_write_json(folder, filename, data)` | 写入 JSON 文件 |

**投资估算（Investment Estimation）：**

| 路由 | 方法 | 功能 |
|------|------|------|
| `/project/<id>/investment` | GET | 投资估算页面 |
| `/api/project/<id>/investment/save` | POST | 保存投资估算数据（写入 DB + JSON） |
| `/api/project/<id>/investment/load` | GET | 加载投资估算数据（优先 JSON，回退 DB） |
| `/api/project/<id>/investment/export` | GET | 导出投资估算 Excel |

**能耗估算（Energy Estimation）：**

| 路由 | 方法 | 功能 |
|------|------|------|
| `/project/<id>/energy` | GET | 能耗估算页面 |
| `/api/energy/factors` | GET | 获取所有能耗因子列表 |
| `/api/project/<id>/energy/params` | GET/POST | 读取/保存能耗参数 |
| `/api/project/<id>/energy/items` | GET/POST | 读取/保存能耗项目明细 |
| `/api/project/<id>/energy/electricity` | GET/POST | 读取/保存电力负荷数据 |
| `/api/project/<id>/energy/export` | GET | 导出完整能耗估算 Excel（含用电负荷表和能源消耗表） |

**财务分析（Finance Analysis）：**

| 路由 | 方法 | 功能 |
|------|------|------|
| `/project/<id>/finance` | GET | 财务测算方式选择页 |
| `/project/<id>/finance/bond` | GET | 专项债财务测算页面 |
| `/project/<id>/finance/normal` | GET | 一般项目财务测算页面 |
| `/api/project/<id>/finance/save` | POST | 保存财务数据（支持多模式共存） |
| `/api/project/<id>/finance/load` | GET | 加载财务数据 |
| `/api/project/<id>/finance/meta` | GET | 加载财务元数据（当前模式） |
| `/api/project/<id>/finance/export` | GET | 导出财务测算 Excel（资金计划/还本付息/收入成本/税费） |
| `/api/project/<id>/finance/export-all` | POST | 导出完整财务测算 Excel（客户端生成的所有表格） |

**能耗导出（`energy_export`）详解：**
- 生成包含"用电负荷计算表"和"项目能源消耗估算表"两个部分的多工作表 Excel
- 自动计算同时系数（Kp/Ksq）、无功补偿、有功/无功/视在功率
- 自动计算各项能源的当量值/等价值标准煤和年费用

**财务导出（`finance_export`）详解：**
- 支持专项债(bond)和一般项目(normal)两种模式
- 生成资金使用计划表、还本付息表、收入成本表、税费参数表
- normal 模式额外包含折旧摊销参数表和项目基本信息表

---

### 5.4 服务层

#### [project_service.py](file:///c:/Users/Administrator/Desktop/xmglxtv5/客户系统/web/services/project_service.py)

**核心函数：**

| 函数 | 功能 |
|------|------|
| `get_index_statistics(months=12)` | 获取首页统计数据：每月项目数、地区分布、工程师分布、年度总数 |
| `search_projects(keyword, page, per_page)` | 多字段模糊搜索项目 |
| `invalidate_project_stats_cache()` | 使项目统计缓存失效 |

**缓存机制：** 使用内存字典 `_project_stats_cache` 缓存统计结果，TTL 为 60 秒

#### [finance_service.py](file:///c:/Users/Administrator/Desktop/xmglxtv5/客户系统/web/services/finance_service.py)

**核心函数：**

| 函数 | 功能 |
|------|------|
| `calculate_revenue(start_date, end_date)` | 计算总收入、已收、应收 |
| `calculate_expenses(start_date, end_date)` | 计算总支出（按项目/运营分类） |
| `get_monthly_profit(months=6)` | 近 N 个月月度利润趋势 |
| `invalidate_finance_stats_cache()` | 使财务统计缓存失效 |

**收入计算逻辑：**
- 已结款/已结清状态 → `settled_amount` 为 0 时取 `contract_amount`
- 部分结清 → `settled_amount`
- 其他 → `settled_amount`
- 应收账款 = `contract_amount - settled_amount`

---

### 5.5 前端模板

约 **20 个 Jinja2 模板**，全部继承基础模板 `base.html`。

**模板层级：**

```
base.html (布局、导航、页脚)
├── login.html               # 登录页
├── register.html            # 注册页(如需)
├── index.html               # 首页（项目列表+统计图表）
├── my_projects.html         # 我的项目列表
├── project_add.html         # 新增项目表单
├── project_edit.html        # 编辑项目表单
├── project_detail.html      # 项目详情
├── change_password.html     # 修改密码
├── admin_users.html         # 用户管理
├── admin_projects.html      # 管理员项目管理
├── admin_operations.html    # 经营管理
├── database.html            # 标准规范文件库
├── file_viewer.html         # 项目文件查看器
├── energy_estimate.html     # 能耗估算
├── investment_estimate.html # 投资估算
├── finance_select.html      # 财务测算选择
├── finance_bond.html        # 专项债财务测算
├── finance_normal.html      # 一般项目财务测算
└── includes/                # 共享模板片段
    ├── _finance_shared_js.html
    ├── _finance_shared_modals.html
    └── _finance_shared_tabs.html
```

**静态资源：**
- `static/style.css` — 全局样式
- `static/app.js` — 前端交互 JavaScript

---

### 5.6 核心计算模块

#### 5.6.1 能耗计算 — [core/energy/](file:///c:/Users/Administrator/Desktop/xmglxtv5/客户系统/core/energy/)

**factors.py** — 能耗因子常量字典

定义了 15 种能源和耗能工质的折标煤系数（当量值 + 等价值）：
- 能源类：电力、原煤、洗精煤、焦炭、天然气、液化天然气、汽油、煤油、柴油、燃料油、液化石油气、热力
- 耗能工质类：水、压缩空气、二氧化碳

| 函数 | 功能 |
|------|------|
| `get_factor(name)` | 根据名称获取能耗因子 |
| `list_factors()` | 返回所有能耗因子名称列表 |

**calculator.py** — 能耗计算引擎

| 函数 | 功能 |
|------|------|
| `calculate_equivalent_tce(qty, coef)` | 计算当量值标准煤 |
| `calculate_equivalent_val_tce(qty, coef)` | 计算等价值标准煤 |
| `calculate_annual_cost(qty, price)` | 计算年费用（万元） |
| `calculate_energy_item_tce(name, qty, eq_coef, ev_coef)` | 单项能源的当量/等价标准煤 |
| `calculate_total_energy(items)` | 汇总多项能源的总标准煤和总费用 |
| `calculate_energy_benchmarks(total_eq, total_ev, area, output, product_qty)` | 计算能耗指标（单位面积能耗、单位产出能耗等） |
| `calculate_electricity_load(density, qty, kc, cos_phi, hours)` | 计算电力负荷（有功/无功/视在功率/年耗电量） |

#### 5.6.2 财务计算 — [core/finance/calculator.py](file:///c:/Users/Administrator/Desktop/xmglxtv5/客户系统/core/finance/calculator.py)

| 函数 | 功能 |
|------|------|
| `calculate_yearly_debt_service_equal_principal()` | 等额本金还本付息计算 |
| `calculate_yearly_debt_service_equal_installment()` | 等额本息还本付息计算 |
| `calculate_yearly_debt_service_lump_sum()` | 到期一次性还本计算 |
| `calculate_debt_service_schedule(principal, rate, years, start_year, method)` | 统一调度入口 |
| `calculate_npv(cash_flows, discount_rate)` | 净现值计算 |
| `calculate_irr(cash_flows, guess, max_iter, tolerance)` | 内部收益率计算（牛顿迭代法） |
| `calculate_payback_period(cash_flows)` | 投资回收期计算 |
| `calculate_coverage_ratio(net_income, debt_service)` | 偿债覆盖率计算 |
| `calculate_total_debt_service(schedule)` | 汇总还本付息总额 |
| `calculate_revenue_projection(revenue, growth_rate, years)` | 收入预测 |
| `calculate_profit(revenues, costs, taxes, depreciation, amortization)` | 利润计算 |
| `calculate_sensitivity(base_npv, base_irr, revenue_change, cost_change)` | 敏感性分析 |

#### 5.6.3 投资估算 — [core/investment/calculator.py](file:///c:/Users/Administrator/Desktop/xmglxtv5/客户系统/core/investment/calculator.py)

| 函数 | 功能 |
|------|------|
| `linear_interpolate(table, x)` | 线性插值工具函数 |
| `calculate_project_management_fee(total)` | 项目管理费（费率阶梯） |
| `calculate_design_fee(total)` | 设计费（费率阶梯） |
| `calculate_survey_fee(area, base_rate)` | 勘察费 |
| `calculate_construction_prep_fee(total, rate)` | 建设准备费 |
| `calculate_consultation_fee(total)` | 咨询费（费率阶梯） |
| `calculate_drawing_review_fee(survey_fee, design_fee, rate)` | 施工图审查费 |
| `calculate_cost_consulting_fee(total, rate)` | 造价咨询费 |
| `calculate_bidding_agent_fee(total)` | 招标代理费（费率阶梯） |
| `calculate_supervision_fee(total)` | 监理费（费率阶梯） |
| `calculate_insurance_fee(total, rate)` | 保险费 |
| `calculate_final_settlement_fee(total, rate)` | 竣工结算审核费 |
| `calculate_infrastructure_fee(area_or_cost, rate)` | 基础设施配套费 |
| `calculate_air_defense_fee(area, rate)` | 人防易地建设费 |
| `calculate_all(engineering_total, building_area)` | 汇总计算所有费用 |

#### 5.6.4 单元测试 — [core/tests/](file:///c:/Users/Administrator/Desktop/xmglxtv5/客户系统/core/tests/)

| 文件 | 测试内容 |
|------|---------|
| `test_energy.py` | 能耗计算测试 |
| `test_finance.py` | 财务计算测试 |
| `test_investment.py` | 投资估算测试 |

---

## 6. 桌面端模块详解

技术选型：**PySide6 (Qt for Python)** + **QWebEngineView** 内嵌 Web 系统

### 文件结构

| 文件 | 功能 |
|------|------|
| [desktop_app.py](file:///c:/Users/Administrator/Desktop/xmglxtv5/客户系统/desktop/desktop_app.py) | 桌面应用启动入口 |
| [main_window.py](file:///c:/Users/Administrator/Desktop/xmglxtv5/客户系统/desktop/main_window.py) | 主窗口 UI + WebView + 项目导航 |
| [first_run_config.py](file:///c:/Users/Administrator/Desktop/xmglxtv5/客户系统/desktop/first_run_config.py) | 首次运行配置向导对话框 |
| [subscription.py](file:///c:/Users/Administrator/Desktop/xmglxtv5/客户系统/desktop/subscription.py) | 订阅客户端（设备指纹+API通信） |

### 启动流程（desktop_app.py）

1. 设置 `DESKTOP_MODE=true` 环境变量
2. 检查首次运行 → 弹出文件存储路径配置向导
3. 启动 Flask 后台线程（端口 5005，不自动重载）
4. 轮询等待 Flask 启动就绪
5. 创建 `EstimateStudioWindow` 主窗口
6. 显示 Qt 应用

### 主窗口（main_window.py）

**核心类说明：**

| 类 | 功能 |
|------|------|
| `EstimateStudioWindow(QMainWindow)` | 主窗口：左侧边栏导航 + 右侧 WebView 内容区 |
| `SubscriptionDialog(QDialog)` | 订阅登录对话框（用户名/密码/记住凭据） |
| `NavButton(QPushButton)` | 侧边栏导航按钮（可选中状态） |
| `ProjectNavButton(QPushButton)` | 项目列表按钮 |
| `YearGroupWidget(QWidget)` | 年份分组折叠组件 |
| `MonthGroupWidget(QWidget)` | 月份分组折叠组件 |

**订阅等级：**

| 等级 | 标签 | 项目上限 |
|------|------|---------|
| standard | 标准版 | 5 |
| pro | 专业版 | 50 |
| max | 旗舰版 | 999999 |

**关键功能：**

- `_setup_ui()` — 构建左侧导航栏（添加/搜索/常用文件按钮 + 项目树/列表）
- `_check_subscription()` — 启动时验证订阅，未登录弹出登录对话框
- `_navigate_to(target)` — 导航栏切换页面，控制项目上限
- `_on_page_loaded(ok)` — 页面加载完成后自动注入登录凭据
- `_delayed_extract_projects()` — 从 Web 页面提取项目列表
- `_update_project_list()` — 更新侧边栏项目树（支持时间序列树状视图和列表视图两种模式）
- `_toggle_view_mode()` — 切换项目展示模式（树状/列表）
- `_toggle_sort_mode()` — 切换项目排序方式（时间/名称）
- `INJECT_DETAIL_BUTTONS_JS` — 在项目详情页注入"投资估算/能耗估算/财务测算"快捷按钮

### 订阅客户端（subscription.py）

| 函数/方法 | 功能 |
|-----------|------|
| `get_mac_address()` | 获取本机 MAC 地址 |
| `get_disk_serial()` | 获取硬盘序列号（Windows/Linux） |
| `get_cpu_id()` | 获取 CPU ID（Windows/Linux） |
| `get_machine_fingerprint()` | 生成设备指纹（MAC+磁盘+CPU 的 SHA256 摘要） |
| `SubscriptionClient.login()` | 向订阅服务器发起登录请求 |
| `SubscriptionClient.verify()` | 验证当前 token 是否有效 |
| `SubscriptionClient.save_credentials()` | 保存登录凭据到 config.json |
| `SubscriptionClient.get_saved_credentials()` | 读取已保存的凭据 |

---

## 7. 订阅管理系统模块详解

独立 Flask 服务（端口 5001），提供 RESTful API 认证和订阅管理。

### 入口 — [server.py](file:///c:/Users/Administrator/Desktop/xmglxtv5/订阅管理系统/server.py)

- 加载 Config 配置
- 注册 4 个蓝图（auth/subscription/device/admin）
- 全局错误处理（404/500）

### 配置 — [config.py](file:///c:/Users/Administrator/Desktop/xmglxtv5/订阅管理系统/config.py)

| 配置项 | 说明 |
|--------|------|
| `SECRET_KEY` | Flask 密钥 |
| `SQLALCHEMY_DATABASE_URI` | SQLite 数据库路径 |
| `JWT_SECRET_KEY` | JWT 签名密钥 |
| `JWT_ACCESS_TOKEN_EXPIRES` | Token 有效期（7 天） |
| `ADMIN_USERNAME/PASSWORD` | 管理员默认凭据 |

### 数据模型 — [models.py](file:///c:/Users/Administrator/Desktop/xmglxtv5/订阅管理系统/models.py)

**4 个 ORM 模型：**

| 模型 | 表名 | 关键字段 |
|------|------|---------|
| `User` | users | id, username, password_hash, email, status |
| `Subscription` | subscriptions | user_id, level, max_projects, start_date, expire_date, status |
| `Device` | devices | user_id, device_id, device_name, is_active |
| `PaymentRecord` | payment_records | user_id, amount, payment_method, transaction_id |

### API 路由

**认证路由 — `/api/auth/`**

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/auth/register` | POST | 用户注册 |
| `/api/auth/login` | POST | 登录（含设备绑定） |
| `/api/auth/verify` | POST | Token 验证 |
| `/api/auth/logout` | POST | 登出 |

**订阅路由 — `/api/subscription/`**

| 端点 | 方法 | 功能 | 认证 |
|------|------|------|------|
| `/api/subscription/info` | GET | 获取当前订阅信息 | Bearer Token |

**设备路由 — `/api/device/`**

| 端点 | 方法 | 功能 |
|------|------|------|

**管理员路由 — `/admin/api/`**

| 端点 | 方法 | 功能 |
|------|------|------|

### 服务层

**auth_service.py：**

| 函数 | 功能 |
|------|------|
| `hash_password(password)` | bcrypt 密码哈希 |
| `verify_password(password, hash)` | 密码验证 |
| `create_user(username, password, email)` | 创建用户 |
| `login_user(username, password)` | 用户登录 |
| `create_token(user_id)` | 生成 JWT（7天有效） |
| `verify_token(token)` | 验证 JWT |
| `bind_device(user, device_id, name)` | 绑定设备（上限 2 台） |
| `unbind_device(user, device_id)` | 解绑设备 |
| `get_user_devices(user)` | 获取用户所有活跃设备 |

**subscription_service.py：**

| 函数 | 功能 |
|------|------|
| `get_user_subscription(user)` | 获取用户当前订阅（无则创建默认 standard） |
| `check_subscription_valid(sub)` | 检查订阅是否有效（状态+有效期） |
| `upgrade_subscription(user, level, months)` | 升级订阅等级 |
| `create_subscription_for_admin(user_id, level, expire_date)` | 管理员为用户创建订阅 |

**订阅等级配置：**

| 等级 | 最大项目数 | 自定义公式 |
|------|-----------|-----------|
| standard | 10 | ❌ |
| pro | 50 | ✅ |
| max | 999999 | ✅ |

---

## 8. 授权与License机制

### Web 系统授权（买断制）

- **授权模式**：永久买断
- **绑定方式**：设备指纹（MAC 地址 + 硬盘序列号 + CPU ID）
- **验证文件**：`license.key` 放置在项目根目录
- **加密方式**：RSA 非对称加密签名（私钥在管理 U 盘，公钥在代码中）

**工作流程：**
1. 部署时使用 U 盘工具 `license_generator.py` 读取客户设备指纹
2. 使用 RSA 私钥签名生成 `license.key`
3. 系统启动时 `license_manager.py` 验证签名和设备指纹
4. 验证通过则系统正常运行，否则拒绝启动

### 桌面端授权（订阅制）

- **授权模式**：按时间订阅
- **验证方式**：通过订阅管理系统 API 验证
- **设备限制**：每账号最多 2 台设备同时在线
- **通信协议**：HTTP RESTful API
- **凭据存储**：`config.json` 保存 token

---

## 9. 依赖关系

### Web + 桌面端依赖（客户系统/desktop/requirements.txt）

```
Flask==3.0.0               # Web 框架
Flask-SQLAlchemy==3.1.1    # ORM
Flask-Login==0.6.3         # 用户会话
Flask-WTF==1.2.1           # CSRF 保护
cryptography==41.0.7       # License 加密
openpyxl==3.1.2            # Excel 读写
xlrd==2.0.1                # 旧版 Excel 支持
python-dateutil==2.8.2     # 日期处理
lxml==6.1.1                # XML 解析
PySide6>=6.6.0             # Qt GUI 框架（桌面端）
requests>=2.31.0           # HTTP 请求（桌面端）
```

### 订阅管理系统依赖（订阅管理系统/requirements.txt）

```
Flask==3.0.0               # Web 框架
Flask-SQLAlchemy==3.1.1    # ORM
PyJWT==2.8.0               # JWT 令牌
bcrypt==4.1.2              # 密码哈希
python-dateutil==2.8.2     # 日期处理
```

### 模块间依赖关系

```
客户系统/desktop/
    ├── PySide6 (GUI)
    ├── requests (HTTP → 订阅管理系统:5001)
    └── Flask/Web (内嵌 QWebEngineView)
        ├── core/ (纯 Python 计算逻辑，无外部依赖)
        ├── openpyxl (Excel 导出)
        ├── Flask-Login (用户会话)
        └── SQLite (数据持久化)

订阅管理系统/
    ├── bcrypt (密码)
    ├── PyJWT (令牌)
    ├── Flask-SQLAlchemy (ORM)
    └── SQLite (数据持久化)
```

---

## 10. 项目运行方式

### 场景一：部署 Web 系统（给客户公司）

#### Windows 部署

```bash
# 1. 安装 Python 3.11+
# 2. 安装依赖
cd 客户系统\desktop
pip install -r requirements.txt

# 3. 生成 License（管理 U 盘操作）
python license_generator.py --auto-deploy 客户系统

# 4. 启动 Web 服务（端口 5005）
cd 客户系统
python web\app.py     # 或直接运行 app.py
```

> 更详细的 Windows 部署步骤参考 [Windows部署.md](file:///c:/Users/Administrator/Desktop/xmglxtv5/Windows部署.md)

#### Ubuntu 部署

```bash
# 1. 安装 Python
sudo apt install python3 python3-pip python3-venv

# 2. 创建虚拟环境
cd 客户系统
python3 -m venv venv
source venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 生成 License
python license_generator.py --auto-deploy 客户系统

# 5. 启动
python app.py
# 或 gunicorn -w 4 -b 0.0.0.0:5005 app:app
```

**访问地址：** `http://localhost:5005`
**默认账号：** admin / admin123

### 场景二：部署订阅管理后台

```bash
cd 订阅管理系统
pip install -r requirements.txt
python server.py    # 端口 5001
```

### 场景三：运行桌面端工具

```bash
cd 客户系统\desktop
pip install -r requirements.txt
python desktop_app.py
```

桌面端会自动：
1. 在后台启动 Flask Web 服务（端口 5005）
2. 弹出 PySide6 主窗口
3. 验证订阅（需要连接订阅管理后台 5001）
4. 内嵌 WebView 展示 Web 界面

### 数据迁移

```bash
python 一键迁移数据.py    # 从旧版本迁移数据到 V5.0.1
```

---

## 11. 常见问题

### 数据库相关

| 问题 | 解决 |
|------|------|
| "unable to open database file" | 确保 `instance/` 目录存在且有写权限 |
| 数据库损坏 | 删除 `instance/system.db` 后重新启动系统自动初始化 |
| 数据丢失 | 恢复备份文件 `instance/system.db` |

### 启动相关

| 问题 | 解决 |
|------|------|
| License 验证失败 | 检查 `license.key` 是否存在于项目根目录 |
| 端口被占用 | 修改 `config.py` 中的端口或关闭占用进程 |
| 模块导入错误 | 确认已激活虚拟环境 |
| Flask 服务启动失败 | 检查 Python 版本和依赖包版本 |

### 权限相关

| 问题 | 解决 |
|------|------|
| 登录显示 "Not Found" | 检查登录表单的 action 是否为 `/auth/login` |
| 访客看不到项目 | 管理员在用户管理中为访客分配可查看项目 |
| 无法删除用户 | 用户拥有有效项目时需要先转移或删除项目 |

---

> **文档版本**：V5.0.1
> **生成日期**：2026-05-25
> **项目路径**：`c:\Users\Administrator\Desktop\xmglxtv5`