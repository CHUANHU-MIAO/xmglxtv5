# 订阅管理系统 - 用户注册/找回密码/订阅定价 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为订阅管理系统添加用户注册、唯一性校验、找回密码、订阅定价展示功能

**Architecture:** 在现有 Flask 订阅管理系统中新增公共页面（注册页、找回密码页）和 API 端点，修改 User 模型增加 phone/old_password_hash 字段，后端做真实数据库校验

**Tech Stack:** Flask + SQLite + Jinja2 + JWT

---

## 文件结构

| 文件 | 操作 | 职责 |
|------|------|------|
| `订阅管理系统/models.py` | 修改 | User 模型增加 phone, old_password_hash 字段 |
| `订阅管理系统/services/auth_service.py` | 修改 | 增加 check_unique, verify_forgot, reset_password 等函数 |
| `订阅管理系统/routes/auth.py` | 修改 | 更新 register 端点，增加 check_unique, forgot-password, reset-password 端点 |
| `订阅管理系统/server.py` | 修改 | 增加公共页面路由（/register, /forgot-password, /pricing） |
| `订阅管理系统/templates/register.html` | 新建 | 用户注册页面 |
| `订阅管理系统/templates/forgot_password.html` | 新建 | 找回密码页面 |
| `订阅管理系统/templates/pricing.html` | 新建 | 订阅定价页面 |
| `订阅管理系统/config.py` | 修改 | 增加联系微信配置项 |

---

### Task 1: 修改 User 模型增加 phone 和 old_password_hash 字段

**Files:**
- Modify: `订阅管理系统/models.py:1-66`

- [ ] **Step 1: 修改 models.py，为 User 增加 phone 和 old_password_hash 字段**

修改 `User` 类，增加 phone 和 old_password_hash 字段；修改 `Subscription` 增加 max_projects 默认值对应标准版：

```python
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    old_password_hash = db.Column(db.String(255))  # 上一个密码哈希，用于找回密码验证
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='active')
```

`email` 和 `phone` 也要加唯一索引，修改为：

```python
    email = db.Column(db.String(100), unique=True)
    phone = db.Column(db.String(20), unique=True)
```

- [ ] **Step 2: 确认修改后的 models.py 完整性**

确保所有 import 和后续的 PairSession、PhoneSession 等类不受影响。

---

### Task 2: 扩展 auth_service.py，增加校验和找回密码功能

**Files:**
- Modify: `订阅管理系统/services/auth_service.py:1-71`

- [ ] **Step 1: 添加 check_unique 函数**

在 `auth_service.py` 中添加：

```python
def check_unique(username=None, email=None, phone=None):
    """检查用户名/邮箱/手机号是否已被注册，返回第一个重复的字段名"""
    if username and User.query.filter_by(username=username).first():
        return 'username'
    if email and User.query.filter_by(email=email).first():
        return 'email'
    if phone and User.query.filter_by(phone=phone).first():
        return 'phone'
    return None
```

- [ ] **Step 2: 更新 create_user 函数**

修改 `create_user` 函数，增加 phone 参数和唯一性校验：

```python
def create_user(username, password, email=None, phone=None):
    dup = check_unique(username=username, email=email, phone=phone)
    if dup == 'username':
        return None, '用户名已存在'
    if dup == 'email':
        return None, '该邮箱已被注册'
    if dup == 'phone':
        return None, '该手机号已被注册'
    hashed = hash_password(password)
    user = User(username=username, password_hash=hashed, email=email, phone=phone)
    db.session.add(user)
    db.session.commit()
    # 为新用户创建标准版订阅
    from services.subscription_service import SUBSCRIPTION_LEVELS
    sub = Subscription(
        user_id=user.id,
        level='standard',
        max_projects=SUBSCRIPTION_LEVELS['standard']['max_projects'],
        status='active'
    )
    db.session.add(sub)
    db.session.commit()
    return user, '注册成功'
```

注意需要在 models.py 中 import Subscription，或者在函数内部 import 避免循环依赖。

- [ ] **Step 3: 添加 forgot_password_verify 函数**

```python
def forgot_password_verify(username):
    """根据用户名查找用户，返回脱敏后的邮箱和手机号"""
    user = User.query.filter_by(username=username).first()
    if not user:
        return None, '用户不存在'
    # 脱敏处理
    masked_email = None
    if user.email and '@' in user.email:
        name, domain = user.email.split('@')
        masked_email = name[0] + '****' + name[-1] + '@' + domain if len(name) > 2 else name[0] + '****@' + domain
    masked_phone = None
    if user.phone and len(user.phone) >= 7:
        masked_phone = user.phone[:3] + '****' + user.phone[-4:]
    has_old_pwd = bool(user.old_password_hash)
    return {
        'user_id': user.id,
        'username': user.username,
        'masked_email': masked_email,
        'masked_phone': masked_phone,
        'has_old_password': has_old_pwd,
    }, None
```

- [ ] **Step 4: 添加 verify_and_reset_password 函数**

```python
def verify_and_reset_password(username, verify_methods, new_password):
    """验证身份并重置密码
    verify_methods: [{'method': 'email', 'value': '验证码'}, {'method': 'phone', 'value': '验证码'}, {'method': 'old_password', 'value': '曾用密码'}]
    至少需提供两项
    """
    user = User.query.filter_by(username=username).first()
    if not user:
        return False, '用户不存在'

    if len(verify_methods) < 2:
        return False, '请至少选择两种验证方式'

    passed = 0
    for vm in verify_methods:
        method = vm.get('method')
        value = vm.get('value', '')
        if method == 'email':
            # 当前模拟：只要邮箱匹配且验证码不为空就算通过
            # 后续可对接真实邮件服务
            if user.email and value == 'verified':
                passed += 1
        elif method == 'phone':
            # 当前模拟：只要手机号匹配且验证码不为空就算通过
            # 后续可对接真实短信服务
            if user.phone and value == 'verified':
                passed += 1
        elif method == 'old_password':
            if user.old_password_hash and verify_password(value, user.old_password_hash):
                passed += 1

    if passed < 2:
        return False, '身份验证未通过，请确认信息是否正确'

    # 重置密码：将当前密码哈希移到 old_password_hash，设置新密码
    user.old_password_hash = user.password_hash
    user.password_hash = hash_password(new_password)
    db.session.commit()
    return True, '密码重置成功'
```

- [ ] **Step 5: 添加 update_password 函数（用于已登录用户修改密码）**

```python
def update_password(user_id, old_password, new_password):
    """修改密码时，将旧密码哈希保存到 old_password_hash"""
    user = User.query.get(user_id)
    if not user:
        return False, '用户不存在'
    if not verify_password(old_password, user.password_hash):
        return False, '原密码错误'
    user.old_password_hash = user.password_hash
    user.password_hash = hash_password(new_password)
    db.session.commit()
    return True, '密码修改成功'
```

---

### Task 3: 更新 routes/auth.py，增加新 API 端点

**Files:**
- Modify: `订阅管理系统/routes/auth.py:1-76`

- [ ] **Step 1: 更新 import，引入新函数**

```python
from flask import Blueprint, request, jsonify, session
from models import db
from services.auth_service import (
    create_user, login_user, create_token, verify_token,
    bind_device, unbind_device, get_user_devices,
    check_unique, forgot_password_verify, verify_and_reset_password
)
from services.subscription_service import get_user_subscription, check_subscription_valid
from datetime import datetime
```

- [ ] **Step 2: 更新 register 端点**

```python
@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    email = data.get('email', '').strip() or None
    phone = data.get('phone', '').strip() or None
    if not username or not password:
        return jsonify({'success': False, 'message': '用户名和密码必填'}), 400
    if len(password) < 6:
        return jsonify({'success': False, 'message': '密码长度不能少于6位'}), 400
    if email and not check_email(email):
        return jsonify({'success': False, 'message': '邮箱格式不正确'}), 400
    if phone and not check_phone(phone):
        return jsonify({'success': False, 'message': '手机号格式不正确'}), 400
    user, msg = create_user(username, password, email, phone)
    if user:
        return jsonify({'success': True, 'message': msg, 'user': {'id': user.id, 'username': user.username}})
    else:
        return jsonify({'success': False, 'message': msg}), 400

def check_email(email):
    import re
    return re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email) is not None

def check_phone(phone):
    import re
    return re.match(r'^1\d{10}$', phone) is not None
```

- [ ] **Step 3: 新增 check_unique 端点**

```python
@auth_bp.route('/check-unique', methods=['POST'])
def check_unique_api():
    data = request.get_json()
    username = data.get('username', '').strip() or None
    email = data.get('email', '').strip() or None
    phone = data.get('phone', '').strip() or None
    dup = check_unique(username=username, email=email, phone=phone)
    if dup:
        field_map = {'username': '用户名', 'email': '邮箱', 'phone': '手机号'}
        return jsonify({'success': False, 'field': dup, 'message': f'{field_map.get(dup, dup)}已被注册'})
    return jsonify({'success': True, 'message': '均可使用'})
```

- [ ] **Step 4: 新增 forgot-password 端点（第一步：验证用户名，返回脱敏信息）**

```python
@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    data = request.get_json()
    username = data.get('username', '').strip()
    if not username:
        return jsonify({'success': False, 'message': '请输入用户名'}), 400
    result, err = forgot_password_verify(username)
    if err:
        return jsonify({'success': False, 'message': err}), 404
    return jsonify({'success': True, 'data': result})
```

- [ ] **Step 5: 新增 reset-password 端点（第二步：验证并重置密码）**

```python
@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    data = request.get_json()
    username = data.get('username', '').strip()
    verify_methods = data.get('verify_methods', [])
    new_password = data.get('new_password', '')
    if not username or not new_password:
        return jsonify({'success': False, 'message': '参数不完整'}), 400
    if len(new_password) < 6:
        return jsonify({'success': False, 'message': '密码长度不能少于6位'}), 400
    ok, msg = verify_and_reset_password(username, verify_methods, new_password)
    if ok:
        return jsonify({'success': True, 'message': msg})
    else:
        return jsonify({'success': False, 'message': msg}), 400
```

---

### Task 4: 更新 server.py，增加公共页面路由

**Files:**
- Modify: `订阅管理系统/server.py:1-79`

- [ ] **Step 1: 新增 register、forgot_password、pricing 路由**

在 `server.py` 中，`index()` 函数后面添加：

```python
@app.route('/register')
def register_page():
    return render_template('register.html')

@app.route('/forgot-password')
def forgot_password_page():
    return render_template('forgot_password.html')

@app.route('/pricing')
def pricing_page():
    return render_template('pricing.html')
```

---

### Task 5: 创建注册页面 register.html

**Files:**
- Create: `订阅管理系统/templates/register.html`

- [ ] **Step 1: 创建注册页面模板**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>注册 - 订阅管理系统</title>
    <link href="https://cdn.bootcdn.net/ajax/libs/twitter-bootstrap/5.3.3/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.bootcdn.net/ajax/libs/bootstrap-icons/1.11.3/font/bootstrap-icons.min.css" rel="stylesheet">
    <style>
        :root {
            --primary: #0f3460;
            --accent: #10b981;
            --danger: #ef4444;
            --text-dark: #1e293b;
            --text-muted: #64748b;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .reg-wrapper {
            display: flex;
            max-width: 860px;
            width: 100%;
            background: #fff;
            border-radius: 16px;
            box-shadow: 0 4px 24px rgba(0,0,0,0.06);
            overflow: hidden;
            animation: fadeIn 0.4s ease-out;
        }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: translateY(0); } }
        .reg-left {
            flex: 1;
            background: linear-gradient(135deg, #1a1a2e 0%, #0f3460 50%, #16213e 100%);
            padding: 48px 36px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            color: #fff;
            position: relative;
            overflow: hidden;
        }
        .reg-left::before {
            content: '';
            position: absolute; inset: 0;
            background: radial-gradient(ellipse at 20% 50%, rgba(16,185,129,0.12) 0%, transparent 50%),
                        radial-gradient(ellipse at 80% 50%, rgba(99,102,241,0.08) 0%, transparent 50%);
        }
        .reg-left > * { position: relative; z-index: 1; }
        .reg-left .big-icon { font-size: 44px; margin-bottom: 16px; }
        .reg-left h2 { font-size: 24px; font-weight: 700; margin-bottom: 6px; }
        .reg-left p { color: rgba(255,255,255,0.6); font-size: 14px; line-height: 1.6; margin-bottom: 24px; }
        .reg-left ul { list-style: none; padding: 0; }
        .reg-left ul li { padding: 7px 0; color: rgba(255,255,255,0.8); font-size: 13px; display: flex; align-items: center; gap: 10px; }
        .reg-left ul li i { color: var(--accent); }
        .reg-right { width: 420px; padding: 36px 32px; display: flex; flex-direction: column; justify-content: center; }
        .reg-right h3 { font-size: 20px; font-weight: 700; color: var(--text-dark); margin-bottom: 2px; }
        .reg-right .reg-sub { color: var(--text-muted); font-size: 13px; margin-bottom: 20px; }
        .form-group { margin-bottom: 14px; }
        .form-group label { display: block; font-size: 13px; font-weight: 600; color: var(--text-dark); margin-bottom: 4px; }
        .form-group .input-wrap { position: relative; }
        .form-group .input-wrap i { position: absolute; left: 12px; top: 50%; transform: translateY(-50%); color: #94a3b8; }
        .form-group input {
            width: 100%; height: 42px; border: 2px solid #e9ecef; border-radius: 10px;
            padding: 0 12px 0 38px; font-size: 14px; transition: border-color 0.2s; outline: none;
        }
        .form-group input:focus { border-color: var(--accent); box-shadow: 0 0 0 3px rgba(16,185,129,0.1); }
        .form-group input.error { border-color: var(--danger); }
        .form-group .validation-msg { font-size: 12px; margin-top: 3px; display: flex; align-items: center; gap: 4px; }
        .form-group .validation-msg.error { color: var(--danger); }
        .form-group .validation-msg.success { color: var(--accent); }
        .btn-reg {
            background: linear-gradient(135deg, var(--accent), #059669); color: #fff; border: none;
            padding: 12px; border-radius: 10px; font-size: 15px; font-weight: 700; width: 100%;
            cursor: pointer; transition: all 0.2s; margin-top: 4px;
        }
        .btn-reg:hover { transform: translateY(-1px); box-shadow: 0 4px 16px rgba(16,185,129,0.3); }
        .btn-reg:disabled { opacity: 0.6; cursor: not-allowed; transform: none; box-shadow: none; }
        .login-link { text-align: center; margin-top: 14px; font-size: 13px; color: var(--text-muted); }
        .login-link a { color: var(--accent); text-decoration: none; font-weight: 600; }
        .login-link a:hover { text-decoration: underline; }
        .msg-box { padding: 10px 14px; border-radius: 8px; margin-bottom: 14px; font-size: 13px; display: none; }
        .msg-box.error { display: block; background: #fef2f2; color: var(--danger); border: 1px solid #fecaca; }
        .msg-box.success { display: block; background: #f0fdf4; color: #059669; border: 1px solid #bbf7d0; }
        @media (max-width: 700px) { .reg-left { display: none; } .reg-right { width: 100%; padding: 28px 24px; } }
    </style>
</head>
<body>
<div class="reg-wrapper">
    <div class="reg-left">
        <div class="big-icon">📋</div>
        <h2>订阅管理系统</h2>
        <p>注册账号，管理您的桌面端订阅授权</p>
        <ul>
            <li><i class="bi bi-check-circle-fill"></i> 注册即享标准版（免费永久）</li>
            <li><i class="bi bi-check-circle-fill"></i> 用户名/邮箱/手机号唯一校验</li>
            <li><i class="bi bi-check-circle-fill"></i> 支持找回密码</li>
            <li><i class="bi bi-check-circle-fill"></i> 随时升级 Pro / Max</li>
        </ul>
    </div>
    <div class="reg-right">
        <h3>创建账号</h3>
        <p class="reg-sub">注册后自动开通标准版订阅</p>
        <div id="message" class="msg-box"></div>
        <form id="registerForm" onsubmit="return handleRegister(event)">
            <div class="form-group">
                <label>用户名 <span style="color:var(--danger)">*</span></label>
                <div class="input-wrap">
                    <i class="bi bi-person"></i>
                    <input type="text" id="username" placeholder="设置登录用户名" required autofocus onblur="checkField('username')">
                </div>
                <div class="validation-msg" id="v-username"></div>
            </div>
            <div class="form-group">
                <label>邮箱</label>
                <div class="input-wrap">
                    <i class="bi bi-envelope"></i>
                    <input type="email" id="email" placeholder="输入邮箱地址（用于找回密码）" onblur="checkField('email')">
                </div>
                <div class="validation-msg" id="v-email"></div>
            </div>
            <div class="form-group">
                <label>手机号</label>
                <div class="input-wrap">
                    <i class="bi bi-phone"></i>
                    <input type="tel" id="phone" placeholder="输入手机号（用于找回密码）" onblur="checkField('phone')">
                </div>
                <div class="validation-msg" id="v-phone"></div>
            </div>
            <div class="form-group">
                <label>密码 <span style="color:var(--danger)">*</span></label>
                <div class="input-wrap">
                    <i class="bi bi-lock"></i>
                    <input type="password" id="password" placeholder="密码不少于6位" required minlength="6">
                </div>
            </div>
            <div class="form-group">
                <label>确认密码 <span style="color:var(--danger)">*</span></label>
                <div class="input-wrap">
                    <i class="bi bi-lock-fill"></i>
                    <input type="password" id="password2" placeholder="再次输入密码" required>
                </div>
            </div>
            <button type="submit" class="btn-reg" id="regBtn"><i class="bi bi-person-plus"></i> 注册并开通标准版</button>
        </form>
        <div class="login-link">
            已有账号？<a href="/admin/login">去登录</a>
            &middot; <a href="/forgot-password">忘记密码？</a>
            &middot; <a href="/pricing">订阅方案</a>
        </div>
    </div>
</div>
<script>
let checkedFields = {};

async function checkField(field) {
    const el = document.getElementById(field);
    const val = el.value.trim();
    const msgEl = document.getElementById('v-' + field);
    if (!val) { msgEl.className = 'validation-msg'; msgEl.textContent = ''; return; }
    const body = {};
    body[field] = val;
    try {
        const res = await fetch('/api/auth/check-unique', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(body)
        });
        const data = await res.json();
        if (data.success) {
            msgEl.className = 'validation-msg success';
            msgEl.innerHTML = '<i class="bi bi-check-circle-fill"></i> 可用';
            checkedFields[field] = true;
        } else {
            msgEl.className = 'validation-msg error';
            msgEl.innerHTML = '<i class="bi bi-exclamation-circle-fill"></i> ' + data.message;
            checkedFields[field] = false;
        }
    } catch(e) {
        msgEl.className = 'validation-msg error';
        msgEl.innerHTML = '<i class="bi bi-exclamation-circle-fill"></i> 验证失败';
    }
}

document.getElementById('username').addEventListener('blur', function() { checkField('username'); });
document.getElementById('email').addEventListener('blur', function() { checkField('email'); });
document.getElementById('phone').addEventListener('blur', function() { checkField('phone'); });

async function handleRegister(e) {
    e.preventDefault();
    const username = document.getElementById('username').value.trim();
    const email = document.getElementById('email').value.trim();
    const phone = document.getElementById('phone').value.trim();
    const password = document.getElementById('password').value;
    const password2 = document.getElementById('password2').value;
    const msgEl = document.getElementById('message');

    if (!username || !password) { msgEl.className = 'msg-box error'; msgEl.textContent = '用户名和密码为必填项'; return; }
    if (password.length < 6) { msgEl.className = 'msg-box error'; msgEl.textContent = '密码不能少于6位'; return; }
    if (password !== password2) { msgEl.className = 'msg-box error'; msgEl.textContent = '两次密码输入不一致'; return; }

    // 如果邮箱或手机号已填写但未校验，先校验
    if (email && checkedFields['email'] === undefined) { await checkField('email'); }
    if (phone && checkedFields['phone'] === undefined) { await checkField('phone'); }
    if ((email && checkedFields['email'] === false) || (phone && checkedFields['phone'] === false)) {
        msgEl.className = 'msg-box error';
        msgEl.textContent = '请修改已被占用的邮箱或手机号';
        return;
    }

    const btn = document.getElementById('regBtn');
    btn.disabled = true; btn.textContent = '注册中...';
    msgEl.className = 'msg-box';

    try {
        const res = await fetch('/api/auth/register', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({username, password, email, phone})
        });
        const data = await res.json();
        if (data.success) {
            msgEl.className = 'msg-box success';
            msgEl.innerHTML = '<i class="bi bi-check-circle-fill"></i> 注册成功！正在跳转登录页...';
            setTimeout(() => { window.location.href = '/admin/login'; }, 1500);
        } else {
            msgEl.className = 'msg-box error';
            msgEl.textContent = data.message;
            btn.disabled = false; btn.innerHTML = '<i class="bi bi-person-plus"></i> 注册并开通标准版';
        }
    } catch(e) {
        msgEl.className = 'msg-box error';
        msgEl.textContent = '网络错误，请重试';
        btn.disabled = false; btn.innerHTML = '<i class="bi bi-person-plus"></i> 注册并开通标准版';
    }
    return false;
}
</script>
</body>
</html>
```

- [ ] **Step 2: 创建找回密码页面 forgot_password.html**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>找回密码 - 订阅管理系统</title>
    <link href="https://cdn.bootcdn.net/ajax/libs/twitter-bootstrap/5.3.3/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.bootcdn.net/ajax/libs/bootstrap-icons/1.11.3/font/bootstrap-icons.min.css" rel="stylesheet">
    <style>
        :root {
            --primary: #0f3460; --accent: #10b981; --danger: #ef4444;
            --text-dark: #1e293b; --text-muted: #64748b;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
            min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 20px;
        }
        .forgot-card {
            background: #fff; border-radius: 16px; padding: 36px 32px;
            box-shadow: 0 4px 24px rgba(0,0,0,0.06); max-width: 460px; width: 100%;
            animation: fadeIn 0.4s ease-out;
        }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: translateY(0); } }
        .forgot-card h3 { font-size: 20px; font-weight: 700; color: var(--text-dark); margin-bottom: 4px; }
        .forgot-card .forgot-sub { color: var(--text-muted); font-size: 13px; margin-bottom: 20px; }
        .form-group { margin-bottom: 14px; }
        .form-group label { display: block; font-size: 13px; font-weight: 600; color: var(--text-dark); margin-bottom: 4px; }
        .form-group input { width: 100%; height: 42px; border: 2px solid #e9ecef; border-radius: 10px; padding: 0 14px; font-size: 14px; outline: none; transition: border-color 0.2s; }
        .form-group input:focus { border-color: var(--accent); box-shadow: 0 0 0 3px rgba(16,185,129,0.1); }
        .verify-section { background: #f8fafc; border-radius: 12px; padding: 18px; margin-bottom: 14px; display: none; }
        .verify-section .verify-title { font-size: 14px; font-weight: 600; color: var(--text-dark); margin-bottom: 10px; }
        .verify-section .verify-title small { font-weight: 400; color: var(--text-muted); font-size: 12px; }
        .verify-option { display: flex; align-items: center; gap: 12px; padding: 10px 12px; background: #fff; border: 2px solid #e9ecef; border-radius: 8px; margin-bottom: 6px; cursor: pointer; transition: all 0.2s; }
        .verify-option:hover { border-color: var(--accent); }
        .verify-option.selected { border-color: var(--accent); background: #d1fae5; }
        .verify-option input[type="checkbox"] { width: 18px; height: 18px; accent-color: var(--accent); cursor: pointer; }
        .verify-option .option-label { font-size: 14px; color: var(--text-dark); font-weight: 500; }
        .verify-option .option-desc { font-size: 12px; color: var(--text-muted); }
        .verify-option .send-code-btn {
            margin-left: auto; padding: 4px 12px; border: 1px solid var(--accent); border-radius: 6px;
            background: #fff; color: var(--accent); font-size: 12px; cursor: pointer; flex-shrink: 0;
        }
        .verify-option .send-code-btn:hover { background: var(--accent); color: #fff; }
        .verify-option .send-code-btn:disabled { opacity: 0.5; cursor: not-allowed; }
        .verify-code-input { display: none; margin-top: 8px; padding-left: 42px; }
        .verify-code-input input { width: 140px; height: 36px; border: 2px solid #e9ecef; border-radius: 8px; padding: 0 10px; font-size: 13px; outline: none; }
        .btn-reset { background: linear-gradient(135deg, var(--accent), #059669); color: #fff; border: none; padding: 12px; border-radius: 10px; font-size: 15px; font-weight: 700; width: 100%; cursor: pointer; transition: all 0.2s; }
        .btn-reset:hover { box-shadow: 0 4px 16px rgba(16,185,129,0.3); }
        .btn-reset:disabled { opacity: 0.5; cursor: not-allowed; }
        .msg-box { padding: 10px 14px; border-radius: 8px; margin-bottom: 14px; font-size: 13px; display: none; }
        .msg-box.error { display: block; background: #fef2f2; color: var(--danger); border: 1px solid #fecaca; }
        .msg-box.success { display: block; background: #f0fdf4; color: #059669; border: 1px solid #bbf7d0; }
        .msg-box.info { display: block; background: #eff6ff; color: #2563eb; border: 1px solid #bfdbfe; }
        .back-link { text-align: center; margin-top: 14px; font-size: 13px; color: var(--text-muted); }
        .back-link a { color: var(--accent); text-decoration: none; font-weight: 600; }
        .step { display: none; }
        .step.active { display: block; }
    </style>
</head>
<body>
<div class="forgot-card">
    <div style="text-align:center;margin-bottom:16px">
        <div style="font-size:40px;margin-bottom:8px">🔑</div>
        <h3>找回密码</h3>
        <p class="forgot-sub">验证身份后即可重置密码</p>
    </div>

    <div id="message" class="msg-box"></div>

    <!-- Step 1: Input username -->
    <div class="step active" id="step1">
        <div class="form-group">
            <label>用户名</label>
            <input type="text" id="fp-username" placeholder="输入您的用户名">
        </div>
        <button class="btn-reset" onclick="step1Verify()">下一步</button>
    </div>

    <!-- Step 2: Verify identity -->
    <div class="step" id="step2">
        <div class="verify-section" id="verifySection" style="display:block">
            <div class="verify-title">身份验证 <small>请至少选择两项</small></div>
            <div id="verifyOptions"></div>
        </div>
        <div class="form-group">
            <label>新密码</label>
            <input type="password" id="new-password" placeholder="密码不少于6位">
        </div>
        <div class="form-group">
            <label>确认新密码</label>
            <input type="password" id="new-password2" placeholder="再次输入新密码">
        </div>
        <button class="btn-reset" onclick="step2Reset()">验证并重置密码</button>
    </div>

    <!-- Step 3: Success -->
    <div class="step" id="step3">
        <div style="text-align:center;padding:20px 0">
            <div style="font-size:48px;margin-bottom:12px">✅</div>
            <h3 style="margin-bottom:8px">密码重置成功！</h3>
            <p style="color:var(--text-muted);font-size:14px">请使用新密码登录</p>
        </div>
        <button class="btn-reset" onclick="window.location.href='/admin/login'">去登录</button>
    </div>

    <div class="back-link"><a href="/register">没有账号？去注册</a></div>
</div>

<script>
let fpData = null;
let verifiedMethods = {};

function showMsg(msg, type) {
    const el = document.getElementById('message');
    el.className = 'msg-box ' + (type || 'info');
    el.textContent = msg;
}

function showStep(n) {
    document.querySelectorAll('.step').forEach(el => el.classList.remove('active'));
    document.getElementById('step' + n).classList.add('active');
    document.getElementById('message').className = 'msg-box';
}

async function step1Verify() {
    const username = document.getElementById('fp-username').value.trim();
    if (!username) { showMsg('请输入用户名', 'error'); return; }
    showMsg('查询中...', 'info');
    try {
        const res = await fetch('/api/auth/forgot-password', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({username})
        });
        const data = await res.json();
        if (!data.success) { showMsg(data.message, 'error'); return; }
        fpData = data.data;
        buildVerifyOptions(fpData);
        showStep(2);
    } catch(e) { showMsg('网络错误', 'error'); }
}

function buildVerifyOptions(data) {
    const container = document.getElementById('verifyOptions');
    container.innerHTML = '';
    verifiedMethods = {};
    if (data.masked_email) {
        container.innerHTML += `
            <label class="verify-option">
                <input type="checkbox" value="email" onchange="toggleMethod('email', this.checked)">
                <div>
                    <div class="option-label">📧 邮箱验证</div>
                    <div class="option-desc">验证注册邮箱 ${data.masked_email}</div>
                </div>
            </label>`;
    }
    if (data.masked_phone) {
        container.innerHTML += `
            <label class="verify-option">
                <input type="checkbox" value="phone" onchange="toggleMethod('phone', this.checked)">
                <div>
                    <div class="option-label">📱 手机号验证</div>
                    <div class="option-desc">验证注册手机号 ${data.masked_phone}</div>
                </div>
            </label>`;
    }
    if (data.has_old_password) {
        container.innerHTML += `
            <label class="verify-option">
                <input type="checkbox" value="old_password" onchange="toggleMethod('old_password', this.checked)">
                <div>
                    <div class="option-label">🔐 曾用密码验证</div>
                    <div class="option-desc">输入上一次使用的密码</div>
                </div>
            </label>`;
    }
}

function toggleMethod(method, checked) {
    if (checked) verifiedMethods[method] = '';
    else delete verifiedMethods[method];
}

async function step2Reset() {
    const newPwd = document.getElementById('new-password').value;
    const newPwd2 = document.getElementById('new-password2').value;
    if (!newPwd || newPwd.length < 6) { showMsg('密码不能少于6位', 'error'); return; }
    if (newPwd !== newPwd2) { showMsg('两次密码输入不一致', 'error'); return; }

    const selected = Object.keys(verifiedMethods);
    if (selected.length < 2) { showMsg('请至少选择两种验证方式', 'error'); return; }

    const verifyMethods = [];
    for (const m of selected) {
        if (m === 'old_password') {
            const val = prompt('请输入曾用密码：');
            if (!val) { showMsg('请输入曾用密码', 'error'); return; }
            verifyMethods.push({method: m, value: val});
        } else {
            // 模拟验证码：直接标记为已验证
            verifyMethods.push({method: m, value: 'verified'});
        }
    }

    showMsg('验证中...', 'info');
    try {
        const res = await fetch('/api/auth/reset-password', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                username: fpData.username,
                verify_methods: verifyMethods,
                new_password: newPwd
            })
        });
        const data = await res.json();
        if (data.success) { showStep(3); }
        else { showMsg(data.message, 'error'); }
    } catch(e) { showMsg('网络错误', 'error'); }
}
</script>
</body>
</html>
```

- [ ] **Step 3: 创建订阅定价页面 pricing.html**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>订阅方案 - 订阅管理系统</title>
    <link href="https://cdn.bootcdn.net/ajax/libs/twitter-bootstrap/5.3.3/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.bootcdn.net/ajax/libs/bootstrap-icons/1.11.3/font/bootstrap-icons.min.css" rel="stylesheet">
    <style>
        :root { --accent: #10b981; --text-dark: #1e293b; --text-muted: #64748b; }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
            min-height: 100vh; padding: 40px 20px;
        }
        .header { text-align: center; margin-bottom: 36px; }
        .header h1 { font-size: 28px; font-weight: 700; color: var(--text-dark); margin-bottom: 6px; }
        .header p { color: var(--text-muted); font-size: 14px; }
        .pricing-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; max-width: 960px; margin: 0 auto; }
        .pricing-card {
            background: #fff; border-radius: 16px; padding: 32px 28px; box-shadow: 0 4px 24px rgba(0,0,0,0.06);
            border: 2px solid transparent; transition: transform 0.2s, box-shadow 0.2s; position: relative;
        }
        .pricing-card:hover { transform: translateY(-4px); box-shadow: 0 12px 40px rgba(0,0,0,0.1); }
        .pricing-card.featured { border-color: var(--accent); transform: scale(1.03); }
        .pricing-card.featured:hover { transform: scale(1.03) translateY(-4px); }
        .popular-badge {
            position: absolute; top: -12px; left: 50%; transform: translateX(-50%);
            background: linear-gradient(135deg, var(--accent), #059669); color: #fff;
            font-size: 12px; font-weight: 600; padding: 4px 16px; border-radius: 20px;
        }
        .plan-icon {
            width: 48px; height: 48px; border-radius: 12px; display: flex;
            align-items: center; justify-content: center; font-size: 24px; margin-bottom: 14px;
        }
        .plan-icon.standard { background: #e3f2fd; color: #1565c0; }
        .plan-icon.pro { background: #d1fae5; color: #059669; }
        .plan-icon.max { background: #f3e8ff; color: #7c3aed; }
        .plan-name { font-size: 18px; font-weight: 700; color: var(--text-dark); margin-bottom: 4px; }
        .plan-desc { font-size: 13px; color: var(--text-muted); margin-bottom: 18px; }
        .price-block { margin-bottom: 18px; padding-bottom: 18px; border-bottom: 1px solid #f0f2f5; }
        .price { font-size: 34px; font-weight: 800; color: var(--text-dark); }
        .price .currency { font-size: 16px; font-weight: 600; vertical-align: super; }
        .price .period { font-size: 14px; font-weight: 400; color: var(--text-muted); }
        .price-note { font-size: 13px; color: var(--text-muted); margin-top: 4px; }
        .annual-price { font-size: 14px; color: var(--accent); font-weight: 600; }
        .plan-features { list-style: none; padding: 0; margin: 0 0 20px 0; }
        .plan-features li { padding: 5px 0; font-size: 14px; color: var(--text-dark); display: flex; align-items: center; gap: 8px; }
        .plan-features li i { color: var(--accent); }
        .plan-features li .na { color: #cbd5e1; }
        .btn-upgrade { width: 100%; padding: 12px; border-radius: 10px; font-size: 15px; font-weight: 600; border: none; cursor: pointer; transition: all 0.2s; }
        .btn-upgrade.btn-outline { background: transparent; border: 2px solid #e9ecef; color: var(--text-dark); cursor: default; }
        .btn-upgrade.btn-solid { background: linear-gradient(135deg, var(--accent), #059669); color: #fff; }
        .btn-upgrade.btn-solid:hover { box-shadow: 0 4px 16px rgba(16,185,129,0.3); }
        .btn-upgrade.btn-purple { background: linear-gradient(135deg, #7c3aed, #6d28d9); color: #fff; }
        .btn-upgrade.btn-purple:hover { box-shadow: 0 4px 16px rgba(124,58,237,0.3); }
        .contact-hint { text-align: center; font-size: 12px; color: var(--text-muted); margin-top: 8px; }
        .footer-links { text-align: center; margin-top: 24px; font-size: 13px; }
        .footer-links a { color: var(--accent); text-decoration: none; font-weight: 600; }
        .footer-links a:hover { text-decoration: underline; }
        @media (max-width: 650px) { .pricing-grid { grid-template-columns: 1fr; } .pricing-card.featured { transform: none; } }
    </style>
</head>
<body>
<div class="header">
    <h1>选择适合您的订阅方案</h1>
    <p>注册即享标准版，按需升级更高级别</p>
</div>

<div class="pricing-grid">
    <div class="pricing-card">
        <div class="plan-icon standard"><i class="bi bi-rocket-takeoff"></i></div>
        <div class="plan-name">标准版</div>
        <div class="plan-desc">个人用户入门首选</div>
        <div class="price-block">
            <div class="price"><span class="currency">¥</span>0 <span class="period">/ 永久</span></div>
            <div class="price-note">注册即享，无需付费</div>
        </div>
        <ul class="plan-features">
            <li><i class="bi bi-check-circle-fill"></i> 最多 10 个项目</li>
            <li><i class="bi bi-check-circle-fill"></i> 基础能耗计算</li>
            <li><i class="bi bi-check-circle-fill"></i> 2 台设备绑定</li>
            <li><i class="bi bi-x-circle-fill" style="color:#cbd5e1"></i> <span class="na">高级投资估算</span></li>
            <li><i class="bi bi-x-circle-fill" style="color:#cbd5e1"></i> <span class="na">财务分析</span></li>
        </ul>
        <button class="btn-upgrade btn-outline" disabled>当前方案</button>
    </div>

    <div class="pricing-card featured">
        <div class="popular-badge">🔥 热门推荐</div>
        <div class="plan-icon pro"><i class="bi bi-stars"></i></div>
        <div class="plan-name">专业版 Pro</div>
        <div class="plan-desc">工程师团队必备</div>
        <div class="price-block">
            <div class="price"><span class="currency">¥</span>9.9 <span class="period">/ 月</span></div>
            <div style="margin-top:4px"><span class="annual-price">¥99 / 年</span> <span style="font-size:12px;color:var(--text-muted)">(省¥19.8)</span></div>
            <div class="price-note" style="margin-top:4px">或 <strong>¥199</strong> 终身有效</div>
        </div>
        <ul class="plan-features">
            <li><i class="bi bi-check-circle-fill"></i> 最多 50 个项目</li>
            <li><i class="bi bi-check-circle-fill"></i> 完整能耗计算</li>
            <li><i class="bi bi-check-circle-fill"></i> 高级投资估算</li>
            <li><i class="bi bi-check-circle-fill"></i> 财务分析（NPV/IRR）</li>
            <li><i class="bi bi-check-circle-fill"></i> 2 台设备绑定</li>
        </ul>
        <button class="btn-upgrade btn-solid" onclick="showContact()">升级到 Pro</button>
        <div class="contact-hint">联系微信：17631020218</div>
    </div>

    <div class="pricing-card">
        <div class="plan-icon max"><i class="bi bi-gem"></i></div>
        <div class="plan-name">旗舰版 Max</div>
        <div class="plan-desc">企业级全功能</div>
        <div class="price-block">
            <div class="price"><span class="currency">¥</span>29.9 <span class="period">/ 月</span></div>
            <div style="margin-top:4px"><span class="annual-price">¥299 / 年</span> <span style="font-size:12px;color:var(--text-muted)">(省¥59.8)</span></div>
            <div class="price-note" style="margin-top:4px">或 <strong>¥599</strong> 终身有效</div>
        </div>
        <ul class="plan-features">
            <li><i class="bi bi-check-circle-fill"></i> 项目数量 <strong>无限制</strong></li>
            <li><i class="bi bi-check-circle-fill"></i> 完整能耗计算</li>
            <li><i class="bi bi-check-circle-fill"></i> 高级投资估算</li>
            <li><i class="bi bi-check-circle-fill"></i> 财务分析（NPV/IRR）</li>
            <li><i class="bi bi-check-circle-fill"></i> 2 台设备绑定</li>
        </ul>
        <button class="btn-upgrade btn-purple" onclick="showContact()">升级到 Max</button>
        <div class="contact-hint">联系微信：17631020218</div>
    </div>
</div>

<div class="footer-links">
    <a href="/register">注册账号</a> &middot; <a href="/admin/login">登录</a>
</div>

<script>
function showContact() {
    alert('📞 订阅升级请联系\n\n微信/电话同号：17631020218\n\n目前支付功能正在开发中，请联系客服为您开通。');
}
</script>
</body>
</html>
```

---

### Task 6: 更新 config.py，添加联系人配置

**Files:**
- Modify: `订阅管理系统/config.py:1-14`

- [ ] **Step 1: 添加联系方式和订阅定价配置**

```python
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{DATABASE_PATH}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'jwt-secret-key-change-in-production'
    JWT_ACCESS_TOKEN_EXPIRES = 86400 * 7  # 7天
    ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME') or 'admin'
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD') or 'admin123'
    SERVER_PUBLIC_URL = os.environ.get('SERVER_PUBLIC_URL') or ''
    CONTACT_WECHAT = os.environ.get('CONTACT_WECHAT') or '17631020218'  # 联系微信
```

---

### Task 7: 更新 admin_dashboard.html 中的用户管理，支持显示手机号

**Files:**
- Modify: `订阅管理系统/templates/admin_dashboard.html`

- [ ] **Step 1: 更新 users API 返回 phone 字段**

修改 `订阅管理系统/routes/admin.py` 中 users 端点的返回，增加 phone 字段：

```python
@admin_bp.route('/users', methods=['GET'])
def users():
    users = User.query.all()
    return jsonify({'success': True, 'users': [{
        'id': u.id, 'username': u.username, 'email': u.email, 'phone': u.phone,
        'status': u.status, 'created_at': u.created_at.isoformat()
    } for u in users]})
```

- [ ] **Step 2: 更新 admin_dashboard.html 用户列表列，增加手机号列**

在 admin_dashboard.html 的表格 thead 和 tbody 中，在"邮箱"列后增加"手机号"列。

---

### Task 8: 启动并测试

- [ ] **Step 1: 删除旧的数据库文件，重启服务**

```bash
# 停止当前 Flask 服务
# 删除旧的数据库（模型变了需要重建）
del 订阅管理系统\database\subscription.db
# 重新启动
cd 订阅管理系统
python server.py
```

- [ ] **Step 2: 测试注册流程**

```bash
# 测试唯一性校验
curl -X POST http://127.0.0.1:5001/api/auth/check-unique -H "Content-Type: application/json" -d "{\"username\":\"test\"}"

# 测试注册
curl -X POST http://127.0.0.1:5001/api/auth/register -H "Content-Type: application/json" -d "{\"username\":\"test\",\"password\":\"123456\",\"email\":\"test@test.com\",\"phone\":\"13800138000\"}"

# 测试重复注册
curl -X POST http://127.0.0.1:5001/api/auth/register -H "Content-Type: application/json" -d "{\"username\":\"test\",\"password\":\"123456\"}"
```

- [ ] **Step 3: 浏览器验证**

打开 `http://127.0.0.1:5001/register` 验证注册页面
打开 `http://127.0.0.1:5001/forgot-password` 验证找回密码页面
打开 `http://127.0.0.1:5001/pricing` 验证定价页面
打开 `http://127.0.0.1:5001/admin/dashboard` 验证管理后台
