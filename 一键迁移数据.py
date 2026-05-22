# -*- coding: utf-8 -*-
"""
项目管理系统 V5.0.1  一键数据迁移工具
将 kyglxtv3（第三代）的数据迁移到 xmglxtv5（第五代）

用法:
    python3 一键迁移数据.py                          # 自动检测路径
    python3 一键迁移数据.py --old-db path/to/old.db   # 指定旧数据库路径
    python3 一键迁移数据.py --help                    # 查看帮助
"""

import os
import sys
import shutil
import sqlite3
import re
import argparse
from datetime import datetime, timezone

NOW = datetime.now(timezone.utc).replace(microsecond=0, tzinfo=None).isoformat()


def find_old_db():
    """自动查找旧数据库，适配Linux服务器环境"""
    candidates = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'kyglxtv3', 'instance', 'system.db'),
        '/opt/kyglxtv3/instance/system.db',
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'kyglxtv3', 'instance', 'system.db'),
    ]
    for c in candidates:
        if os.path.exists(c):
            return os.path.abspath(c)
    return None


def find_old_upload():
    """自动查找旧上传目录"""
    candidates = [
        '/data/上传的文件',
        os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '上传的文件'),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), '上传的文件'),
    ]
    for c in candidates:
        if os.path.isdir(c):
            return os.path.abspath(c)
    return None


def get_new_db():
    """新系统数据库路径"""
    base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, '客户系统', 'instance', 'system.db')


def get_new_upload():
    """新系统上传目录路径（文件放data机械硬盘，opt只放系统代码）"""
    base = os.path.dirname(os.path.abspath(__file__))
    data_path = '/data/上传的文件'
    if os.path.isdir(data_path):
        return os.path.realpath(data_path)
    candidate = os.path.join(base, '客户系统', '上传的文件')
    if os.path.isdir(candidate):
        return os.path.realpath(candidate)
    return data_path


def to_float(v, default=0.0):
    if v is None:
        return default
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(str(v).replace(',', '').replace(' ', ''))
    except (ValueError, TypeError):
        return default


def backup(db_path):
    if not os.path.exists(db_path):
        return None
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    dst = db_path + '.migrate_backup.' + stamp
    shutil.copy2(db_path, dst)
    return dst


def migrate_users(old, new):
    print('\n' + '=' * 50)
    print('  1. 迁移用户')
    print('=' * 50)
    try:
        rows = old.execute("PRAGMA table_info('user')").fetchall()
        cols = [r[1] for r in rows]
    except sqlite3.OperationalError:
        print('  [跳过] 用户表不存在')
        return {}

    users = old.execute('SELECT * FROM "user"').fetchall()
    id_map = {}

    import hashlib as _hashlib

    def _make_pw_hash(password):
        salt = os.urandom(16)
        iterations = 260000
        dk = _hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, iterations)
        return f'pbkdf2:sha256:{iterations}${salt.hex()}${dk.hex()}'

    for u in users:
        d = dict(zip(cols, u))
        old_id = d['id']
        username = d['name']
        plain_pw = d.get('password') or '123456'
        role = d.get('role') or 'engineer'
        last_active = d.get('last_active_time')

        pw_hash = _make_pw_hash(plain_pw)

        try:
            new.execute(
                'INSERT INTO users (username, password_hash, role, last_active_time, created_at) '
                'VALUES (?, ?, ?, ?, ?)',
                (username, pw_hash, role, last_active, NOW)
            )
        except sqlite3.IntegrityError:
            existing = new.execute(
                'SELECT id FROM users WHERE username = ?', (username,)
            ).fetchone()
            if existing:
                new_id = existing[0]
                id_map[old_id] = new_id
                print(f'  [已存在] {username} ({role})  id {old_id} -> {new_id}')
                continue
            raise

        new_id = new.lastrowid
        id_map[old_id] = new_id
        print(f'  {username} ({role})  id {old_id} -> {new_id}')

    new.connection.commit()
    print(f'  共迁移 {len(id_map)} 个用户')
    return id_map


def migrate_projects(old, new, user_id_map):
    print('\n' + '=' * 50)
    print('  2. 迁移项目')
    print('=' * 50)
    try:
        rows = old.execute("PRAGMA table_info('project')").fetchall()
        cols = [r[1] for r in rows]
    except sqlite3.OperationalError:
        print('  [跳过] 项目表不存在')
        return {}

    projects = old.execute('SELECT * FROM "project"').fetchall()
    id_map = {}

    for p in projects:
        d = dict(zip(cols, p))
        old_id = d['id']
        old_engineer_id = d.get('engineer_id')
        new_user_id = user_id_map.get(old_engineer_id, 1) if old_engineer_id else 1

        old_user_name = None
        if old_engineer_id:
            old_user_row = old.execute(
                'SELECT name FROM "user" WHERE id = ?', (old_engineer_id,)
            ).fetchone()
            if old_user_row:
                old_user_name = old_user_row[0]

        try:
            new.execute(
                'INSERT INTO projects (name, description, location, project_type, phase, '
                'created_at, updated_at, user_id, author, progress, is_valid, '
                'start_date, owner, total_investment, contract_amount, contract_status, '
                'invoice_status, invoiced_amount, payment_status, settled_amount, '
                'payment_settlement_status, source, owner_name, owner_phone, '
                'service_content, remark, create_time) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (
                    d.get('name'),
                    None,
                    d.get('location'),
                    None,
                    None,
                    d.get('create_time') or NOW,
                    d.get('create_time') or NOW,
                    new_user_id,
                    old_user_name,
                    '进行中',
                    1,
                    d.get('start_date'),
                    d.get('owner'),
                    to_float(d.get('total_investment')),
                    to_float(d.get('contract_amount')),
                    d.get('contract_status'),
                    d.get('invoice_status'),
                    to_float(d.get('invoiced_amount')),
                    d.get('payment_status'),
                    to_float(d.get('settled_amount')),
                    d.get('payment_settlement_status'),
                    d.get('source'),
                    d.get('owner_name'),
                    d.get('owner_phone'),
                    d.get('service_content'),
                    d.get('remark'),
                    d.get('create_time') or NOW,
                )
            )
        except sqlite3.IntegrityError:
            print(f'  [跳过] 项目已存在: {d.get("name")}')
            continue

        new_id = new.lastrowid
        id_map[old_id] = new_id
        print(f'  [{old_id} -> {new_id}] {d.get("name")}')

    new.connection.commit()
    print(f'  共迁移 {len(id_map)} 个项目')
    return id_map


def migrate_attachments(old, new, project_id_map):
    print('\n' + '=' * 50)
    print('  3. 迁移附件')
    print('=' * 50)
    try:
        rows = old.execute("PRAGMA table_info('attachment')").fetchall()
        cols = [r[1] for r in rows]
    except sqlite3.OperationalError:
        print('  [跳过] 附件表不存在')
        return

    attachments = old.execute('SELECT * FROM attachment').fetchall()
    count = 0
    for a in attachments:
        d = dict(zip(cols, a))
        old_pid = d.get('project_id')
        new_pid = project_id_map.get(old_pid)
        if new_pid is None:
            continue
        try:
            new.execute(
                'INSERT INTO attachments (project_id, filename, save_name, '
                'file_type, upload_time, upload_user) VALUES (?, ?, ?, ?, ?, ?)',
                (new_pid, d.get('filename'), d.get('save_name'),
                 d.get('file_type'), d.get('upload_time'), d.get('upload_user'))
            )
            count += 1
        except sqlite3.IntegrityError:
            pass
    new.connection.commit()
    print(f'  共迁移 {count} 个附件')


def migrate_logs(old, new, project_id_map):
    print('\n' + '=' * 50)
    print('  4. 迁移操作日志')
    print('=' * 50)
    try:
        rows = old.execute("PRAGMA table_info('log')").fetchall()
        cols = [r[1] for r in rows]
    except sqlite3.OperationalError:
        print('  [跳过] 日志表不存在')
        return

    logs = old.execute('SELECT * FROM log').fetchall()
    count = 0
    for l in logs:
        d = dict(zip(cols, l))
        old_pid = d.get('project_id')
        new_pid = project_id_map.get(old_pid) if old_pid else None
        new.execute(
            'INSERT INTO logs (project_id, "user", content, "time") VALUES (?, ?, ?, ?)',
            (new_pid, d.get('user'), d.get('content'), d.get('time'))
        )
        count += 1
    new.connection.commit()
    print(f'  共迁移 {count} 条')


def migrate_standard_files(old, new, new_upload):
    print('\n' + '=' * 50)
    print('  5. 迁移标准文件')
    print('=' * 50)
    try:
        rows = old.execute("PRAGMA table_info('standard_file')").fetchall()
        cols = [r[1] for r in rows]
    except sqlite3.OperationalError:
        print('  [跳过] 标准文件表不存在')
        return

    files = old.execute('SELECT * FROM standard_file').fetchall()
    count = 0
    for f in files:
        d = dict(zip(cols, f))
        old_path = d.get('file_path', '')
        new_path = old_path
        if new_upload and old_path:
            fname = os.path.basename(old_path)
            new_path = os.path.join(new_upload, 'standard_files', fname)
        try:
            new.execute(
                'INSERT INTO standard_files (filename, standard_name, version, file_type, '
                'file_path, upload_time, upload_user, download_count) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                (d.get('filename'), d.get('standard_name'), d.get('version', '1.0'),
                 d.get('file_type', '建设标准'), new_path,
                 d.get('upload_time'), d.get('upload_user'), d.get('download_count', 0))
            )
            count += 1
        except sqlite3.IntegrityError:
            pass
    new.connection.commit()
    print(f'  共迁移 {count} 个')


def migrate_fund_records(old, new, project_id_map):
    print('\n' + '=' * 50)
    print('  6. 迁移资金记录')
    print('=' * 50)
    try:
        rows = old.execute("PRAGMA table_info('fund_record')").fetchall()
        cols = [r[1] for r in rows]
    except sqlite3.OperationalError:
        print('  [跳过] 资金记录表不存在')
        return

    records = old.execute('SELECT * FROM fund_record').fetchall()
    count = 0
    for r in records:
        d = dict(zip(cols, r))
        old_pid = d.get('project_id')
        new_pid = project_id_map.get(old_pid) if old_pid else None
        new.execute(
            'INSERT INTO fund_records (amount, purpose, remark, use_date, '
            'create_time, create_user, expense_type, project_id) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            (d.get('amount'), d.get('purpose'), d.get('remark'),
             d.get('use_date'), d.get('create_time'), d.get('create_user'),
             d.get('expense_type', '运营支出'), new_pid)
        )
        count += 1
    new.connection.commit()
    print(f'  共迁移 {count} 条')


def migrate_energy_factors(old, new):
    print('\n' + '=' * 50)
    print('  7. 迁移能耗因子（增量）')
    print('=' * 50)
    try:
        existing = {r[0] for r in new.execute('SELECT name FROM energy_factors')}
        rows = old.execute("PRAGMA table_info('energy_factor')").fetchall()
        cols = [r[1] for r in rows]
    except sqlite3.OperationalError:
        print('  [跳过] 能耗因子表不存在（新系统已预置）')
        return

    factors = old.execute('SELECT * FROM energy_factor').fetchall()
    added = 0
    for f in factors:
        d = dict(zip(cols, f))
        if d['name'] in existing:
            continue
        new.execute(
            'INSERT INTO energy_factors (name, unit, equivalent_coef, equivalent_note, '
            'equivalent_coef_val, equivalent_val_note, category, is_active, sort_order, created_at) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (d['name'], d['unit'], d['equivalent_coef'],
             d.get('equivalent_note'), d.get('equivalent_coef_val', 0),
             d.get('equivalent_val_note'), d.get('category', '能源'),
             d.get('is_active', 1), d.get('sort_order', 0), NOW)
        )
        added += 1
    new.connection.commit()
    print(f'  新增 {added} 条（新系统已内置标准系数）')


def migrate_visitor_relations(old, new, user_id_map, project_id_map):
    print('\n' + '=' * 50)
    print('  8. 迁移访客关系')
    print('=' * 50)
    try:
        relations = old.execute('SELECT * FROM visitor_projects').fetchall()
    except sqlite3.OperationalError:
        print('  [跳过] 访客关系表不存在')
        return

    count = 0
    for r in relations:
        old_uid, old_pid = r[0], r[1]
        new_uid = user_id_map.get(old_uid)
        new_pid = project_id_map.get(old_pid)
        if new_uid and new_pid:
            try:
                new.execute(
                    'INSERT INTO visitor_projects (user_id, project_id) VALUES (?, ?)',
                    (new_uid, new_pid)
                )
                count += 1
            except sqlite3.IntegrityError:
                pass
    new.connection.commit()
    print(f'  共迁移 {count} 条')


def migrate_project_files(old_upload, new_upload, project_id_map):
    print('\n' + '=' * 50)
    print('  9. 迁移项目文件（JSON + 附件）')
    print('=' * 50)

    if not old_upload or not os.path.isdir(old_upload):
        print(f'  [跳过] 源目录不存在: {old_upload}')
        return

    real_old = os.path.realpath(old_upload)
    real_new = os.path.realpath(new_upload)
    same_fs = (real_old == real_new)

    if same_fs:
        print(f'  [信息] 新旧系统共用同一文件目录: {real_old}')
        print(f'  [信息] 将在原地重命名项目文件夹')
    else:
        os.makedirs(new_upload, exist_ok=True)

    migrated_dirs = 0
    target_path = real_old if same_fs else new_upload

    for entry in os.listdir(old_upload):
        src_path = os.path.join(old_upload, entry)
        if not os.path.isdir(src_path):
            continue

        if entry == 'standard_files':
            dst_path = os.path.join(new_upload, entry)
            if not os.path.exists(dst_path):
                shutil.copytree(src_path, dst_path)
            else:
                for fname in os.listdir(src_path):
                    s, d = os.path.join(src_path, fname), os.path.join(dst_path, fname)
                    if not os.path.exists(d):
                        shutil.copy2(s, d)
            print(f'  标准文件目录已同步')
            continue

        match = re.match(r'^(\d+)-(.+)$', entry)
        if not match:
            continue

        old_pid = int(match.group(1))
        safe_name = match.group(2)
        new_pid = project_id_map.get(old_pid)
        if new_pid is None:
            continue
        if new_pid == old_pid:
            continue

        new_name = f'{new_pid}-{safe_name}'
        dst_path = os.path.join(target_path, new_name)
        if os.path.exists(dst_path):
            print(f'  [已存在] {new_name}')
            migrated_dirs += 1
            continue

        if same_fs:
            os.rename(src_path, dst_path)
        else:
            shutil.copytree(src_path, dst_path)
        migrated_dirs += 1
        print(f'  {entry}  ->  {new_name}')

    print(f'  共迁移 {migrated_dirs} 个项目目录')


def main():
    parser = argparse.ArgumentParser(description='项目管理系统 V5.0.1 一键数据迁移')
    parser.add_argument('--old-db', help='旧系统数据库路径 (kyglxtv3/instance/system.db)')
    parser.add_argument('--old-upload', help='旧系统上传目录')
    parser.add_argument('--new-db', help='新系统数据库路径')
    parser.add_argument('--new-upload', help='新系统上传目录')
    parser.add_argument('--yes', '-y', action='store_true', help='跳过确认')
    args = parser.parse_args()

    old_db = args.old_db or find_old_db()
    old_upload = args.old_upload or find_old_upload()
    new_db = args.new_db or get_new_db()
    new_upload = args.new_upload or get_new_upload()

    print('=' * 55)
    print('  项目管理系统 V5.0.1  一键数据迁移')
    print('=' * 55)
    print(f'  旧数据库: {old_db or "未找到"}')
    print(f'  旧文件库: {old_upload or "未找到"}')
    print(f'  新数据库: {new_db}')
    print(f'  新文件库: {new_upload}')
    print('=' * 55)

    if not old_db or not os.path.exists(old_db):
        print('\n[错误] 找不到旧系统数据库！')
        print('请确保 kyglxtv3 数据库文件存在于 /opt/kyglxtv3/instance/system.db')
        print('或使用 --old-db 指定路径。')
        sys.exit(1)

    if not os.path.exists(new_db):
        print('\n[错误] 找不到新系统数据库！')
        print('请先启动一次 xmglxtv5 系统以初始化数据库结构，然后重新运行本脚本。')
        sys.exit(1)

    if not os.path.exists(new_upload):
        os.makedirs(new_upload, exist_ok=True)

    if not args.yes:
        resp = input('\n确认开始迁移？(输入 yes 继续): ')
        if resp.strip().lower() != 'yes':
            print('已取消。')
            sys.exit(0)

    backup_path = backup(new_db)
    if backup_path:
        print(f'[备份] {backup_path}')

    old_conn = sqlite3.connect(old_db)
    old = old_conn.cursor()
    new_conn = sqlite3.connect(new_db)
    new = new_conn.cursor()

    try:
        user_id_map = migrate_users(old, new)
        project_id_map = migrate_projects(old, new, user_id_map)
        migrate_attachments(old, new, project_id_map)
        migrate_logs(old, new, project_id_map)
        migrate_standard_files(old, new, new_upload)
        migrate_fund_records(old, new, project_id_map)
        migrate_energy_factors(old, new)
        migrate_visitor_relations(old, new, user_id_map, project_id_map)
        migrate_project_files(old_upload, new_upload, project_id_map)
    finally:
        old_conn.close()
        new_conn.close()

    print('\n' + '=' * 55)
    print('  迁移完成！')
    print(f'  迁移用户: {len(user_id_map)} 个')
    print(f'  迁移项目: {len(project_id_map)} 个')
    if backup_path:
        print(f'  备份文件: {os.path.basename(backup_path)}')
    print('=' * 55)


if __name__ == '__main__':
    main()
