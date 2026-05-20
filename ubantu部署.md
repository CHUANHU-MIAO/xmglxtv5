# Ubuntu 部署项目管理系统 —— 完整命令清单

> 适用环境：Ubuntu 20.04/22.04/24.04 LTS（系统安装在 SSD，上传文件存放至机械硬盘）  
> 默认用户名：`xazx`，请替换为你的实际用户名

---

## 一、系统基础环境

```bash
sudo apt update && sudo apt upgrade -y
```
更新系统并升级所有软件包。

```bash
sudo apt install -y python3-pip python3-venv git nginx sqlite3 curl openssh-server
```
一次性安装所有依赖：

- `python3-pip`：Python 包管理
- `python3-venv`：Python 虚拟环境
- `git`：代码克隆与版本管理
- `nginx`：高性能 Web 服务器
- `sqlite3`：数据库工具
- `curl`：网络请求工具（用于安装 Tailscale）
- `openssh-server`：SSH 远程连接服务

---

## 二、挂载机械硬盘（存放上传文件）

```bash
lsblk
```
查看硬盘和分区，确认机械硬盘设备名（通常是 `sdb`）。

```bash
sudo mkdir -p /data/上传的文件
sudo mount /dev/sdb /data/上传的文件
sudo chown -R xazx:xazx /data/上传的文件
```
创建挂载点，挂载硬盘，并赋予用户写入权限。

```bash
echo '/dev/sdb /data/上传的文件 ext4 defaults 0 0' | sudo tee -a /etc/fstab
```
写入开机自动挂载配置。

---

## 三、上传项目文件到服务器

在你的 Mac/Windows 上打开终端，进入项目根目录：

```bash
cd /Users/hebeixinao/Desktop/项目管理系统-暂存
scp -r ./客户系统 xazx@192.168.1.100:/opt/
scp -r ./订阅管理系统 xazx@192.168.1.100:/opt/
scp ./license_generator.py xazx@192.168.1.100:/opt/
scp ./private_key.pem xazx@192.168.1.100:/opt/
```
> 把 `192.168.1.100` 替换为你 Ubuntu 服务器的实际 IP（`ip addr` 查看）

> 💡 也可以用 WinSCP、FileZilla 等工具拖拽到 `/opt/` 目录。

SSH 登录到服务器：
```bash
ssh xazx@192.168.1.100
```

---

## 四、部署客户系统

### 4.1 修复配置路径

```bash
cd /opt/客户系统
sed -i "s|^UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER',.*|UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', os.path.abspath(os.path.join(BASEDIR, '上传的文件')))|" web/config.py
```

### 4.2 创建虚拟环境并安装依赖

```bash
cd /opt/客户系统
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn
deactivate
```

### 4.3 创建上传目录

```bash
mkdir -p /opt/客户系统/uploads/标准文件
sudo chown -R xazx:xazx /opt/客户系统/uploads
```

---

## 五、客户系统 License 授权部署

### 5.1 一键授权（核心步骤）

```bash
cd /opt
python3 license_generator.py --auto-deploy /opt/客户系统
```

执行过程：
1. 自动读取 Ubuntu 设备指纹（MAC + 磁盘序列号 + CPU序列号）
2. 显示设备信息
3. 提示输入授权到期日期（回车默认一年）
4. 用私钥签名，自动生成 `license.key` 写入项目目录

### 5.2 验证 License

```bash
cd /opt/客户系统
source venv/bin/activate
python3 -c "from license_manager import verify_license; valid, msg = verify_license(); print(msg)"
deactivate
```

预期输出：`授权永久有效（买断制）`

### 5.3 安全清理（授权完成后务必执行）

```bash
sudo rm -f /opt/license_generator.py /opt/private_key.pem
```

执行后确认文件已删除：
```bash
ls /opt/license_generator.py /opt/private_key.pem 2>&1
# 应输出：No such file or directory
```

---

## 六、配置 Nginx 反向代理（客户系统）

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
    }
}
EOF
```
创建 Nginx 配置文件，并允许最大 100MB 上传。

```bash
sudo ln -s /etc/nginx/sites-available/项目管理系统 /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
```
启用站点并重载 Nginx。

---

## 七、配置 Gunicorn 系统服务（客户系统）

```bash
sudo tee /etc/systemd/system/项目管理系统.service > /dev/null <<EOF
[Unit]
Description=项目管理系统 Flask App
After=network.target

[Service]
User=xazx
Group=xazx
WorkingDirectory=/opt/客户系统
Environment="PATH=/opt/客户系统/venv/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
Environment="UPLOAD_FOLDER=/data/上传的文件"
ExecStartPre=/opt/客户系统/venv/bin/python -c "from license_manager import check_license_or_exit; check_license_or_exit()"
ExecStart=/opt/客户系统/venv/bin/gunicorn --workers=3 --bind=127.0.0.1:8000 app:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
```
服务文件包含：
- 使用 `xazx` 用户运行
- 注入 `UPLOAD_FOLDER` 环境变量指向机械硬盘
- `ExecStartPre` 在启动前验证 License，无效则拒绝启动

```bash
sudo systemctl daemon-reload
sudo systemctl start 项目管理系统
sudo systemctl enable 项目管理系统
sudo systemctl status 项目管理系统
```
启动服务并设置为开机自启，最后检查状态应显示 `active (running)`。

---

## 八、上传路径终极修复（软链接）

> 若上传时出现 `Permission denied`，执行下面一条命令即可永久解决：

```bash
sudo rm -rf /opt/客户系统/上传的文件 && sudo ln -s /data/上传的文件 /opt/客户系统/上传的文件 && sudo chown -h xazx:xazx /opt/客户系统/上传的文件 && sudo systemctl restart 项目管理系统
```

---

## 九、部署订阅管理后台

### 9.1 安装依赖

```bash
cd /opt/订阅管理系统
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
deactivate
```

### 9.2 创建数据库目录

```bash
mkdir -p /opt/订阅管理系统/database
sudo chown -R xazx:xazx /opt/订阅管理系统/database
```

### 9.3 配置 Gunicorn 服务

```bash
sudo tee /etc/systemd/system/订阅管理后台.service > /dev/null <<EOF
[Unit]
Description=订阅管理后台 Flask App
After=network.target

[Service]
User=xazx
Group=xazx
WorkingDirectory=/opt/订阅管理系统
Environment="PATH=/opt/订阅管理系统/venv/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
ExecStart=/opt/订阅管理系统/venv/bin/gunicorn --workers=2 --bind=127.0.0.1:5001 server:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
```

### 9.4 启动服务

```bash
sudo systemctl daemon-reload
sudo systemctl start 订阅管理后台
sudo systemctl enable 订阅管理后台
sudo systemctl status 订阅管理后台
```

### 9.5 配置 Nginx 反向代理（订阅后台）

```bash
sudo tee /etc/nginx/sites-available/订阅管理后台 > /dev/null <<'EOF'
server {
    listen 81;
    server_name localhost;
    client_max_body_size 50M;

    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
EOF
```

```bash
sudo ln -s /etc/nginx/sites-available/订阅管理后台 /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

---

## 十、订阅管理后台使用说明

### 10.1 管理账号

默认管理员账号：
- 用户名：`admin`
- 密码：`admin123`
> 首次登录后请修改密码！

### 10.2 API 使用示例

查看用户列表：
```bash
curl -X GET "http://127.0.0.1:5001/admin/api/users"
```

创建用户：
```bash
curl -X POST "http://127.0.0.1:5001/admin/api/users" \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"password123","email":"test@example.com"}'
```

设置用户订阅：
```bash
curl -X POST "http://127.0.0.1:5001/admin/api/users/1/subscription" \
  -H "Content-Type: application/json" \
  -d '{"level":"pro","expire_date":"2027-05-21"}'
```

订阅等级说明：
- `standard`：标准版，最多10个项目
- `pro`：专业版，最多50个项目，Excel导出带公式
- `max`：无限版，无限项目

查看设备列表：
```bash
curl -X GET "http://127.0.0.1:5001/admin/api/devices"
```

---

## 十一、防火墙配置

```bash
sudo ufw allow 80/tcp
sudo ufw allow 81/tcp
sudo ufw allow 22/tcp
sudo ufw enable
```

---

## 十二、Tailscale 内网穿透（外网访问）

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```
浏览器登录授权后，查看虚拟地址：
```bash
tailscale ip -4
```

> 📝 访问系统：
> - 客户系统：`http://Tailscale虚拟IP`
> - 订阅管理后台：`http://Tailscale虚拟IP:81`

---

## 十三、日常维护

### 13.1 客户系统

**查看服务状态：**
```bash
sudo systemctl status 项目管理系统
```

**查看日志：**
```bash
sudo journalctl -u 项目管理系统 --no-pager -n 50
```

**重启服务：**
```bash
sudo systemctl restart 项目管理系统
```

**备份数据库：**
```bash
cp /opt/客户系统/instance/system.db /opt/backup/customer-$(date +%Y%m%d).db
```

### 13.2 订阅管理后台

**查看服务状态：**
```bash
sudo systemctl status 订阅管理后台
```

**查看日志：**
```bash
sudo journalctl -u 订阅管理后台 --no-pager -n 50
```

**重启服务：**
```bash
sudo systemctl restart 订阅管理后台
```

**备份数据库：**
```bash
cp /opt/订阅管理系统/database/subscription.db /opt/backup/subscription-$(date +%Y%m%d).db
```

---

## 十四、常见故障快速修复

| 现象 | 解决命令 |
|------|----------|
| 客户系统服务无法启动 | `sudo journalctl -u 项目管理系统 --no-pager -n 20` 查看具体原因 |
| 授权验证失败 | 检查 `license.key` 是否存在：`ls /opt/客户系统/license.key`，重新生成并部署 |
| 413 Request Entity Too Large | 检查 Nginx 配置中的 `client_max_body_size` |
| 502 Bad Gateway | `sudo systemctl restart 项目管理系统` |
| 网络不通 / SSH 拒绝连接 | 检查防火墙 `sudo ufw status`，确保 `22/tcp` 和 `80/tcp` 为 `ALLOW` |
| Tailscale 无法连接 | 改用传统 SSH：`ssh xazx@局域网IP` |

---

## 十五、项目目录结构

```
/opt/
├── 客户系统/
│   ├── app.py
│   ├── license_manager.py
│   ├── license.key
│   ├── requirements.txt
│   ├── venv/
│   ├── core/
│   ├── web/
│   ├── desktop/
│   ├── instance/
│   └── uploads/ -> /data/上传的文件
├── 订阅管理系统/
│   ├── server.py
│   ├── config.py
│   ├── models.py
│   ├── requirements.txt
│   ├── venv/
│   ├── routes/
│   ├── services/
│   └── database/
└── backup/
```

---

> 📅 最后更新：2026-05-21
