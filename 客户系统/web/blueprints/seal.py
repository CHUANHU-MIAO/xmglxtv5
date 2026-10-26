import os
import time
import uuid
import shutil
import threading
import traceback
import subprocess

from flask import (Blueprint, render_template, request, jsonify,
                   send_from_directory, abort, current_app, flash,
                   redirect, url_for)
from flask_login import login_required, current_user

try:
    from web.services import seal_engine as se
except Exception:
    se = None

seal_bp = Blueprint('seal', __name__, url_prefix='/seal')

FALLBACK_REVIEWERS = ["马立亚", "杨亚杰", "吴梦莹", "张喆"]
MAX_UPLOAD = 200 * 1024 * 1024
ALLOWED_DOWNLOADS = {"盖章成稿.pdf", "三页.pdf"}
KEEP_ON_CLEANUP = ALLOWED_DOWNLOADS | {"原始文件名.txt"}

_seal_lock = threading.Lock()


def _is_visitor():
    return current_user.role == 'visitor'


def _tmp_root():
    root = os.path.join(current_app.instance_path, 'seal_tmp')
    os.makedirs(root, exist_ok=True)
    return root


def _purge_stale(root, max_age=7200):
    now = time.time()
    try:
        entries = os.listdir(root)
    except OSError:
        return
    for name in entries:
        path = os.path.join(root, name)
        try:
            if now - os.path.getmtime(path) > max_age:
                shutil.rmtree(path, ignore_errors=True)
        except OSError:
            continue


def _payload_error(message):
    return jsonify({"ok": False, "error": message})


def _safe_pdf_name(raw):
    """沿用上传文件名作为下载名，扩展名统一改为 .pdf。"""
    name = os.path.basename(str(raw or '').replace('\\', '/')).strip()
    name = ''.join(ch for ch in name if ch >= ' ' and ch not in '<>:"/\\|?*')
    stem = os.path.splitext(name)[0].strip().strip('.')
    if not stem:
        return '盖章成稿.pdf'
    return stem[:120] + '.pdf'


def _validate_upload():
    if request.content_length and request.content_length > MAX_UPLOAD:
        return None, _payload_error("文件超过 200MB，请压缩后重试")
    f = request.files.get('file')
    if not f or not f.filename:
        return None, _payload_error("请先选择报告文件（PDF 或 Word）")
    name = f.filename.lower()
    if not (name.endswith('.pdf') or name.endswith('.docx')):
        return None, _payload_error("仅支持 .pdf 或 .docx 格式")
    return f, None


@seal_bp.route('/')
@login_required
def index():
    if _is_visitor():
        flash('访客账号无签章权限')
        return redirect(url_for('projects.index'))
    reviewers = se.REVIEWER_OPTIONS if se else FALLBACK_REVIEWERS
    return render_template('seal.html', reviewer_options=reviewers, active_page='seal')


@seal_bp.route('/api/parse', methods=['POST'])
@login_required
def parse_cover():
    if _is_visitor():
        return _payload_error("访客账号无签章权限"), 403
    if se is None:
        return _payload_error("签章引擎未就绪，请联系管理员安装依赖")
    f, err = _validate_upload()
    if err:
        return err

    workdir = os.path.join(_tmp_root(), uuid.uuid4().hex[:12])
    os.makedirs(workdir, exist_ok=True)
    try:
        if f.filename.lower().endswith('.pdf'):
            src = os.path.join(workdir, '待识别.pdf')
            f.save(src)
            project_name, report_type, warns = se.parse_cover_from_pdf(src)
        else:
            src = os.path.join(workdir, '待识别.docx')
            f.save(src)
            project_name, report_type, warns = se.parse_cover_from_docx(src)
        return jsonify({"ok": True, "project_name": project_name,
                        "report_type": report_type, "warns": warns})
    except Exception as e:
        traceback.print_exc()
        return _payload_error(f"识别失败：{e}")
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


@seal_bp.route('/api/generate', methods=['POST'])
@login_required
def generate():
    if _is_visitor():
        return _payload_error("访客账号无签章权限"), 403
    if se is None:
        return _payload_error("签章引擎未就绪，请联系管理员安装依赖")
    f, err = _validate_upload()
    if err:
        return err

    root = _tmp_root()
    _purge_stale(root)
    token = uuid.uuid4().hex[:12]
    workdir = os.path.join(root, token)
    os.makedirs(workdir, exist_ok=True)
    is_pdf = f.filename.lower().endswith('.pdf')
    src = os.path.join(workdir, '原报告' + ('.pdf' if is_pdf else '.docx'))
    download_name = _safe_pdf_name(request.form.get('original_name', '') or f.filename)

    try:
        f.save(src)

        project_name = request.form.get('project_name', '').strip()
        report_type = request.form.get('report_type', '').strip()
        level = request.form.get('level', '乙级')
        seal_type = request.form.get('seal_type', '公章')
        reviewer = request.form.get('reviewer', '马立亚').strip()

        if level not in se.CERT_NO:
            level = '乙级'
        if seal_type not in se.SEAL_FILE:
            seal_type = '公章'
        if reviewer not in se.REVIEWER_OPTIONS:
            reviewer = '马立亚'

        if is_pdf:
            auto_name, auto_type, warns = se.parse_cover_from_pdf(src)
        else:
            auto_name, auto_type, warns = se.parse_cover_from_docx(src)
        project_name = project_name or auto_name
        report_type = report_type or auto_type

        if not project_name or not report_type:
            shutil.rmtree(workdir, ignore_errors=True)
            return jsonify({"ok": False, "warns": warns,
                            "error": "未能识别封面的项目名称/报告类型，请手动填写后再生成"})

        final_pdf = os.path.join(workdir, '盖章成稿.pdf')
        with _seal_lock:
            three_pdf = se.build_three_pages_pdf(
                project_name, report_type, level, seal_type, workdir, reviewer)
            if is_pdf:
                se.merge_report_pdf(src, three_pdf, final_pdf)
            else:
                body_docx = os.path.join(workdir, '正文去封面.docx')
                se.remove_cover(src, body_docx)
                body_pdf = se.docx_to_pdf(body_docx, workdir)
                se.merge_pdfs([three_pdf, body_pdf], final_pdf)

        with open(os.path.join(workdir, '原始文件名.txt'), 'w', encoding='utf-8') as fh:
            fh.write(download_name)

        return jsonify({
            "ok": True,
            "token": token,
            "download_name": download_name,
            "project_name": project_name,
            "report_type": report_type,
            "reviewer": reviewer,
            "cert_no": se.CERT_NO[level],
            "seal_type": seal_type,
            "pdf_url": url_for('seal.download', token=token, filename='盖章成稿.pdf'),
            "three_url": url_for('seal.download', token=token, filename='三页.pdf'),
            "warns": warns,
        })
    except FileNotFoundError:
        traceback.print_exc()
        shutil.rmtree(workdir, ignore_errors=True)
        return _payload_error("服务器未安装 LibreOffice，无法生成 PDF，请联系管理员安装后重试")
    except subprocess.CalledProcessError:
        traceback.print_exc()
        shutil.rmtree(workdir, ignore_errors=True)
        return _payload_error("文档转换 PDF 失败，请确认服务器 LibreOffice 运行正常，或改传 PDF 版本")
    except Exception as e:
        traceback.print_exc()
        shutil.rmtree(workdir, ignore_errors=True)
        return _payload_error(f"生成失败：{e}")


@seal_bp.route('/download/<token>/<filename>')
@login_required
def download(token, filename):
    if _is_visitor():
        abort(403)
    if len(token) != 12 or not token.isalnum():
        abort(400)
    if filename not in ALLOWED_DOWNLOADS:
        abort(400)

    workdir = os.path.join(_tmp_root(), token)
    file_path = os.path.join(workdir, filename)
    if not os.path.isfile(file_path):
        abort(404)

    download_name = filename
    if filename == '盖章成稿.pdf':
        try:
            with open(os.path.join(workdir, '原始文件名.txt'), encoding='utf-8') as fh:
                saved = fh.read().strip()
            if saved:
                download_name = saved
        except OSError:
            pass

    response = send_from_directory(workdir, filename, as_attachment=True,
                                   download_name=download_name)

    def _cleanup():
        for attempt in range(4):
            try:
                for name in os.listdir(workdir):
                    path = os.path.join(workdir, name)
                    if os.path.isdir(path):
                        shutil.rmtree(path, ignore_errors=True)
                    elif name not in KEEP_ON_CLEANUP or name == filename:
                        os.remove(path)
                if not os.listdir(workdir):
                    os.rmdir(workdir)
                return
            except FileNotFoundError:
                return
            except Exception:
                if attempt == 3:
                    return
                time.sleep(3)

    threading.Thread(target=_cleanup, daemon=True).start()
    return response
