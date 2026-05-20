# 河北鑫奥项目管理系统 - 部署总览

本系统包含三个组件，可根据需要选择部署：

---

## 组件概览

| 组件 | 部署位置 | 端口 | 说明 |
|------|----------|------|------|
| Web系统 | 客户公司本地（Windows/Ubuntu） | 5005 | 完整的项目管理系统，买断制 |
| 桌面端工具 | 个人电脑（Windows/Ubuntu桌面） | - | 轻量级测算工具，需订阅账号 |
| 订阅管理后台 | 你的云服务器（Ubuntu） | 5001 | 用户认证、订阅管理、设备绑定 |

---

## 快速选择

### 场景一：给客户公司部署 Web 系统

- [Windows 部署指南](./Windows部署.md) — 客户 Windows 服务器
- [Ubuntu 部署指南](./ubantu部署.md) — 客户 Linux 服务器

**流程**：
1. 在客户服务器上安装 Python
2. 上传 `客户系统/` 文件夹
3. 安装依赖 `pip install -r requirements.txt`
4. 运行 `license_generator.py --auto-deploy 客户系统` 生成授权
5. 启动 Web 服务 `python app.py`

### 场景二：部署你的订阅管理后台（在自己服务器上）

参考 [Ubuntu 部署指南](./ubantu部署.md) 的第七章。

**流程**：
1. 上传 `订阅管理系统/` 到你的云服务器
2. 安装依赖
3. 启动服务（端口5001）

### 场景三：桌面端工具（给订阅用户）

参考对应部署指南的"桌面端工具"章节。

**流程**：
1. 在用户电脑上安装 Python + PyQt5
2. 配置订阅服务器地址（`desktop/config.json`）
3. 启动 `calculator_tool.py`
4. 用户注册账号 → 登录 → 选择订阅方案

---

## 一键授权命令

```bash
# 在项目根目录执行，自动读取硬件指纹并生成 license.key
python license_generator.py --auto-deploy 客户系统
```

---

## 授权机制

| 项目 | 说明 |
|------|------|
| Web系统 | 买断制，设备指纹绑定，永久有效 |
| 桌面端工具 | 订阅制，通过订阅管理后台验证 |
| 设备限制 | 每账号最多2台设备同时在线 |

---

## 文件结构

```
项目管理系统-暂存/
├── license_generator.py          授权生成工具（你的管理工具）
├── private_key.pem               RSA私钥（请勿外泄）
├── public_key.pem                 RSA公钥
├── Windows部署.md                  Windows部署指南
├── Windows部署.txt                 Windows部署指南（纯文本版）
├── ubantu部署.md                   Ubuntu部署指南
├── ubantu部署.txt                  Ubuntu部署指南（纯文本版）
├── README_DEPLOY.md               本文件（部署总览）
├── README_DEPLOY.txt              本文件（纯文本版）
├── 客户系统/                       客户公司部署的Web系统
│   ├── app.py                     启动入口（端口5005）
│   ├── license_manager.py         授权验证
│   ├── requirements.txt           依赖
│   ├── core/                      核心计算（投资/能耗/财务）
│   ├── web/                       Web应用
│   └── desktop/                   桌面端工具
└── 订阅管理系统/                    你的订阅管理后台
    ├── server.py                  启动入口（端口5001）
    ├── config.py                  配置
    ├── models.py                  数据模型
    ├── routes/                    API路由
    └── services/                  业务逻辑
```
