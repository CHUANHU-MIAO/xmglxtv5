# 项目管理系统 V5.0.1 —— Ubuntu 部署指南

> 适用环境：Ubuntu 20.04 / 22.04 / 24.04 LTS
> 默认部署用户：`xazx`（请替换为实际用户名）
> Web 端口：`5005`（开发） / `80`（Nginx 生产）

---

## 一、系统基础环境

```bash
sudo apt update && sudo apt upgrade -y
```

```bash
sudo apt install -y python3 python3-pip python3-venv git nginx sqlite3 curl openssh-server
```

| 组件 | 用途 |
|------|------|
| `python3` `python3-pip` `python3-venv` | Python 运行环境 |
| `git` | 版本管理 |
| `nginx` | Web 反向代理 |
| `sqlite3` | 数据库工具 |
| `curl` | 网络请求 |
| `openssh-server` | 远程连接 |

---

## 二、（可选）挂载机械硬盘存放上传文件

```bash
lsblk
```
确认机械硬盘设备名（通常 `sdb` 或 `sda`）。

```bash
sudo mkdir -p /data/上传的文件
sudo mount /dev/sdb /data/上传的文件
sudo chown -R xazx:xazx /data/上传的文件
```

```bash
echo '/dev/sdb /data/上传的文件 ext4 defaults 0 0' | sudo tee -a /etc/fstab
```

---

## 三、上传项目文件

在你本地电脑上：

```bash
scp -r ./客户系统 xazx@192.168.1.100:/opt/
```

> 把 `192.168.1.100` 换成服务器实际 IP。也可用 WinSCP / FileZilla。

SSH 登录：

```bash
ssh xazx@192.168.1.100
```

---

## 四、部署客户系统（核心）

### 4.1 创建虚拟环境

```bash
cd /opt/客户系统
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn
deactivate
```

### 4.2 创建必要目录

```bash
mkdir -p /opt/客户系统/instance
mkdir -p /opt/客户系统/上传的文件/standard_files
sudo chown -R xazx:xazx /opt/客户系统/instance /opt/客户系统/上传的文件
```

### 4.3 首次运行（初始化数据库）

```bash
cd /opt/客户系统
source venv/bin/activate
python app.py
```

看到 `Running on http://127.0.0.1:5005` 后按 `Ctrl+C` 停止。此时数据库 `system.db` 已生成。

### 4.4 确认默认账号

默认已创建管理员：
- 用户名：`admin`
- 密码：`admin123`

---

## 五、一键数据迁移（从第三版系统）

```bash
# 将旧系统 database 复制过来（如果 kyglxtv3 和 xmglxtv5 在同一父目录）
cp /path/to/kyglxtv3/instance/system.db /tmp/old_system.db

# 运行迁移脚本
cd /opt/客户系统/..
python3 一键迁移数据.py --old-db /tmp/old_system.db --old-upload /path/to/旧上传的文件 -y
```

> 不迁移可跳过本章，全新部署无需执行。

---

## 六、授权部署

```bash
cd /opt
python3 license_generator.py --auto-deploy /opt/客户系统
```

按提示输入到期日期（回车默认一年），自动生成 `license.key`。

验证：

```bash
cd /opt/客户系统
source venv/bin/activate
python3 -c "from license_manager import verify_license; v,m=verify_license(); print(m)"
deactivate
```

预期：`授权永久有效（买断制）`

**安全清理**（完成后务必执行）：

```bash
sudo rm -f /opt/license_generator.py /opt/private_key.pem
```

---

## 七、Nginx 反向代理

```bash
sudo tee /etc/nginx/sites-available/项目管理系统 > /dev/null <<'EOF'
server {
    listen 80;
    server_name localhost;
    client_max_body_size 100M;

    location /static/ {
        alias /opt/客户系统/web/static/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
EOF
```

```bash
sudo ln -sf /etc/nginx/sites-available/项目管理系统 /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
```

---

## 八、Gunicorn 系统服务

```bash
sudo tee /etc/systemd/system/项目管理系统.service > /dev/null <<EOF
[Unit]
Description=项目管理系统 V5.0.1
After=network.target

[Service]
User=xazx
Group=xazx
WorkingDirectory=/opt/客户系统
Environment="PATH=/opt/客户系统/venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="UPLOAD_FOLDER=/data/上传的文件"
ExecStartPre=/opt/客户系统/venv/bin/python -c "from license_manager import check_license_or_exit; check_license_or_exit()"
ExecStart=/opt/客户系统/venv/bin/gunicorn --workers=3 --bind=127.0.0.1:8000 app:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
```

```bash
sudo systemctl daemon-reload
sudo systemctl start 项目管理系统
sudo systemctl enable 项目管理系统
sudo systemctl status 项目管理系统
```

状态应为 `active (running)`。

---

## 九、上传路径软链接

```bash
sudo rm -rf /opt/客户系统/上传的文件
sudo ln -s /data/上传的文件 /opt/客户系统/上传的文件
sudo chown -h xazx:xazx /opt/客户系统/上传的文件
sudo systemctl restart 项目管理系统
```

---

## 十、防火墙

```bash
sudo ufw allow 80/tcp
sudo ufw allow 22/tcp
sudo ufw enable
```

---

## 十一、Tailscale 内网穿透

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
tailscale ip -4
```

访问：`http://Tailscale虚拟IP`

---

## 十二、订阅管理后台（可选）

```bash
cd /opt/订阅管理系统
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
deactivate
```

```bash
sudo tee /etc/systemd/system/订阅管理后台.service > /dev/null <<EOF
[Unit]
Description=订阅管理后台
After=network.target

[Service]
User=xazx
Group=xazx
WorkingDirectory=/opt/订阅管理系统
Environment="PATH=/opt/订阅管理系统/venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/opt/订阅管理系统/venv/bin/gunicorn --workers=2 --bind=127.0.0.1:5001 server:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
```

```bash
sudo systemctl daemon-reload
sudo systemctl start 订阅管理后台
sudo systemctl enable 订阅管理后台
```

---

## 十三、日常维护

### 客户系统

```bash
# 状态
sudo systemctl status 项目管理系统

# 重启
sudo systemctl restart 项目管理系统

# 日志
sudo journalctl -u 项目管理系统 --no-pager -n 50

# 备份数据库
cp /opt/客户系统/instance/system.db /opt/backup/system-$(date +%Y%m%d).db

# 备份上传文件
rsync -av /data/上传的文件/ /opt/backup/上传的文件/
```

### 订阅后台

```bash
sudo systemctl status 订阅管理后台
sudo systemctl restart 订阅管理后台
sudo journalctl -u 订阅管理后台 --no-pager -n 50
```

---

## 十四、快速部署（一行命令）

```bash
# 首次部署
cd /opt/客户系统 && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt gunicorn && deactivate && mkdir -p instance 上传的文件/standard_files

# 启动开发服务器（调试用）
cd /opt/客户系统 && source venv/bin/activate && python app.py

# 启动生产服务
sudo systemctl start 项目管理系统
```

---

## 十五、故障排查

| 现象 | 解决 |
|------|------|
| 服务无法启动 | `sudo journalctl -u 项目管理系统 -n 30` |
| `ImportError: No module named 'web'` | 确认 `WorkingDirectory=/opt/客户系统`，gunicorn 在该目录执行 |
| `unable to open database file` | `mkdir -p /opt/客户系统/instance && chown xazx:xazx /opt/客户系统/instance` |
| 413 上传过大 | Nginx `client_max_body_size` 调大 |
| 502 Bad Gateway | `sudo systemctl restart 项目管理系统` |
| 授权失败 | 重新运行 `license_generator.py --auto-deploy` |
| 静态文件 404 | 确认 Nginx `alias` 指向 `/opt/客户系统/web/static/` |

---

## 十六、目录结构

```
/opt/
├── 客户系统/
│   ├── app.py                 # 启动入口 from web.app import create_app
│   ├── requirements.txt
│   ├── license.key
│   ├── venv/
│   ├── core/                  # 计算引擎
│   ├── web/
│   │   ├── app.py             # Flask create_app()
│   │   ├── config.py          # V5.0.1 配置
│   │   ├── models.py
│   │   ├── blueprints/
│   │   ├── services/
│   │   ├── static/
│   │   └── templates/
│   ├── desktop/
│   ├── instance/
│   │   └── system.db          # SQLite 数据库
│   └── 上传的文件 -> /data/上传的文件
└── 订阅管理系统/
    ├── server.py
    ├── config.py
    ├── models.py
    ├── venv/
    ├── routes/
    └── services/
```

---

> 版本：V5.0.1 | 更新：2026-05-21
