from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app, send_file
from flask_login import login_required, current_user
from web.models import Project, EnergyFactor, InvestmentData
from web.extensions import db
import json
import os
import io
import datetime
import openpyxl

estimation_bp = Blueprint('estimation', __name__)


def get_project_folder(project):
    return os.path.join(current_app.config['UPLOAD_FOLDER'], f"{project.id}-{project.name}")


def _check_visitor_access(project):
    if current_user.role == 'visitor':
        if not project.visitors.filter_by(id=current_user.id).first():
            flash('您没有权限访问该项目')
            return redirect(url_for('projects.index'))
    return None


def _ensure_project_folder(project):
    folder = get_project_folder(project)
    os.makedirs(folder, exist_ok=True)
    return folder


def _read_json(folder, filename):
    filepath = os.path.join(folder, filename)
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def _write_json(folder, filename, data):
    filepath = os.path.join(folder, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ============================================================
# 投资估算
# ============================================================

@estimation_bp.route('/project/<int:project_id>/investment')
@login_required
def investment_estimate(project_id):
    project = Project.query.get_or_404(project_id)
    check_result = _check_visitor_access(project)
    if check_result:
        return check_result
    return render_template('investment_estimate.html', project=project, role=current_user.role)


@estimation_bp.route('/api/project/<int:project_id>/investment/save', methods=['POST'])
@login_required
def investment_save(project_id):
    project = Project.query.get_or_404(project_id)
    check_result = _check_visitor_access(project)
    if check_result:
        return jsonify({'success': False, 'message': '无权限'})

    data = request.json.get('data', [])

    folder = _ensure_project_folder(project)
    _write_json(folder, 'investment_data.json', data)

    try:
        InvestmentData.query.filter_by(project_id=project_id).delete()

        for item in data:
            inv = InvestmentData(
                project_id=project_id,
                serial_number=item.get('serial_number', ''),
                item_name=item.get('item_name', ''),
                building_cost=item.get('building_cost', 0),
                installation_cost=item.get('installation_cost', 0),
                equipment_cost=item.get('equipment_cost', 0),
                other_cost=item.get('other_cost', 0),
                unit=item.get('unit', ''),
                quantity=item.get('quantity', 0),
                index=item.get('index', 0),
                use_index=item.get('use_index', False),
                billing_basis=item.get('billing_basis', ''),
                calc_rate=item.get('calc_rate', 0),
                discount_rate=item.get('discount_rate', 100),
                build_category=item.get('build_category', ''),
                address_category=item.get('address_category', ''),
                is_reserve_rate=item.get('is_reserve_rate', False),
                reserve_rate=item.get('reserve_rate')
            )
            db.session.add(inv)

        db.session.commit()
        return jsonify({'success': True, 'message': '保存成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})


@estimation_bp.route('/api/project/<int:project_id>/investment/load')
@login_required
def investment_load(project_id):
    project = Project.query.get_or_404(project_id)
    check_result = _check_visitor_access(project)
    if check_result:
        return jsonify({'success': False, 'message': '无权限'})

    folder = get_project_folder(project)
    json_data = _read_json(folder, 'investment_data.json')

    if json_data is not None:
        return jsonify({'success': True, 'data': json_data})

    items = InvestmentData.query.filter_by(project_id=project_id).order_by(InvestmentData.serial_number).all()

    data = []
    for item in items:
        data.append({
            'serial_number': item.serial_number,
            'item_name': item.item_name,
            'building_cost': item.building_cost,
            'installation_cost': item.installation_cost,
            'equipment_cost': item.equipment_cost,
            'other_cost': item.other_cost,
            'unit': item.unit,
            'quantity': item.quantity,
            'index': item.index,
            'use_index': item.use_index,
            'billing_basis': item.billing_basis,
            'calc_rate': item.calc_rate,
            'discount_rate': item.discount_rate,
            'build_category': item.build_category,
            'address_category': item.address_category,
            'is_reserve_rate': item.is_reserve_rate,
            'reserve_rate': item.reserve_rate
        })

    return jsonify({'success': True, 'data': data})


@estimation_bp.route('/api/project/<int:project_id>/investment/export')
@login_required
def investment_export(project_id):
    project = Project.query.get_or_404(project_id)
    check_result = _check_visitor_access(project)
    if check_result:
        return jsonify({'success': False, 'message': '无权限'})

    folder = get_project_folder(project)
    json_data = _read_json(folder, 'investment_data.json')

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = '投资估算'

    headers = ['序号', '项目名称', '建筑工程费', '安装工程费', '设备购置费', '其他费用', '合计', '单位', '数量', '指标']
    ws.append(headers)

    rows = []
    if json_data is not None:
        for item in json_data:
            total = (item.get('building_cost', 0) or 0) + (item.get('installation_cost', 0) or 0) + \
                    (item.get('equipment_cost', 0) or 0) + (item.get('other_cost', 0) or 0)
            rows.append([
                item.get('serial_number', ''),
                item.get('item_name', ''),
                item.get('building_cost', 0) or 0,
                item.get('installation_cost', 0) or 0,
                item.get('equipment_cost', 0) or 0,
                item.get('other_cost', 0) or 0,
                total,
                item.get('unit', ''),
                item.get('quantity', 0) or 0,
                item.get('index', 0) or 0
            ])
    else:
        items = InvestmentData.query.filter_by(project_id=project_id).order_by(InvestmentData.serial_number).all()
        for item in items:
            total = (item.building_cost or 0) + (item.installation_cost or 0) + \
                    (item.equipment_cost or 0) + (item.other_cost or 0)
            rows.append([
                item.serial_number,
                item.item_name,
                item.building_cost or 0,
                item.installation_cost or 0,
                item.equipment_cost or 0,
                item.other_cost or 0,
                total,
                item.unit or '',
                item.quantity or 0,
                item.index or 0
            ])

    for row in rows:
        ws.append(row)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    filename = f"投资估算_{project.name}_{datetime.datetime.now().strftime('%Y%m%d')}.xlsx"
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                     as_attachment=True, download_name=filename)


# ============================================================
# 能耗估算
# ============================================================

@estimation_bp.route('/project/<int:project_id>/energy')
@login_required
def energy_estimate(project_id):
    project = Project.query.get_or_404(project_id)
    check_result = _check_visitor_access(project)
    if check_result:
        return check_result
    return render_template('energy_estimate.html', project=project, role=current_user.role)


@estimation_bp.route('/api/energy/factors')
@login_required
def energy_factors():
    factors = EnergyFactor.query.filter_by(is_active=True).order_by(EnergyFactor.sort_order, EnergyFactor.id).all()
    data = []
    for f in factors:
        data.append({
            'id': f.id,
            'name': f.name,
            'unit': f.unit,
            'equivalent_coef': f.equivalent_coef,
            'equivalent_note': f.equivalent_note,
            'equivalent_coef_val': f.equivalent_coef_val,
            'equivalent_val_note': f.equivalent_val_note,
            'category': f.category
        })
    return jsonify({'success': True, 'factors': data})


@estimation_bp.route('/api/project/<int:project_id>/energy/params', methods=['GET', 'POST'])
@login_required
def energy_params(project_id):
    project = Project.query.get_or_404(project_id)
    check_result = _check_visitor_access(project)
    if check_result:
        if request.method == 'POST':
            return jsonify({'success': False, 'message': '无权限'})
        return jsonify({'success': False, 'message': '无权限'})

    folder = _ensure_project_folder(project)

    if request.method == 'GET':
        data = _read_json(folder, 'energy_params.json')
        return jsonify({'success': True, 'data': data if data is not None else {}})

    if request.method == 'POST':
        data = request.json
        _write_json(folder, 'energy_params.json', data)
        return jsonify({'success': True, 'message': '保存成功'})


@estimation_bp.route('/api/project/<int:project_id>/energy/items', methods=['GET', 'POST'])
@login_required
def energy_items(project_id):
    project = Project.query.get_or_404(project_id)
    check_result = _check_visitor_access(project)
    if check_result:
        if request.method == 'POST':
            return jsonify({'success': False, 'message': '无权限'})
        return jsonify({'success': False, 'message': '无权限'})

    folder = _ensure_project_folder(project)

    if request.method == 'GET':
        data = _read_json(folder, 'energy_items.json')
        return jsonify({'success': True, 'data': data if data is not None else []})

    if request.method == 'POST':
        data = request.json
        _write_json(folder, 'energy_items.json', data)
        return jsonify({'success': True, 'message': '保存成功'})


@estimation_bp.route('/api/project/<int:project_id>/energy/electricity', methods=['GET', 'POST'])
@login_required
def energy_electricity(project_id):
    project = Project.query.get_or_404(project_id)
    check_result = _check_visitor_access(project)
    if check_result:
        if request.method == 'POST':
            return jsonify({'success': False, 'message': '无权限'})
        return jsonify({'success': False, 'message': '无权限'})

    folder = _ensure_project_folder(project)

    if request.method == 'GET':
        data = _read_json(folder, 'energy_electricity.json')
        return jsonify({'success': True, 'data': data if data is not None else {}})

    if request.method == 'POST':
        data = request.json
        _write_json(folder, 'energy_electricity.json', data)
        return jsonify({'success': True, 'message': '保存成功'})


@estimation_bp.route('/api/project/<int:project_id>/energy/export')
@login_required
def energy_export(project_id):
    project = Project.query.get_or_404(project_id)
    check_result = _check_visitor_access(project)
    if check_result:
        return jsonify({'success': False, 'message': '无权限'})

    folder = get_project_folder(project)
    items = _read_json(folder, 'energy_items.json') or []
    params = _read_json(folder, 'energy_params.json') or {}
    electricity = _read_json(folder, 'energy_electricity.json') or {}

    wb = openpyxl.Workbook()

    ws_items = wb.active
    ws_items.title = '能耗项目'

    headers_items = ['序号', '能耗项目', '折算标准煤系数(当量)', '折算标准煤系数(等价值)',
                     '年用量', '年当量标准煤(tce)', '年等价值标准煤(tce)']
    ws_items.append(headers_items)

    factors = {f.name: f for f in EnergyFactor.query.filter_by(is_active=True).all()}
    for idx, item in enumerate(items, 1):
        name = item.get('name', '')
        annual_qty = item.get('annual_qty', 0) or 0
        factor = factors.get(name)
        eq_coef = item.get('equivalent_coef') or (factor.equivalent_coef if factor else 0)
        ev_coef = item.get('equivalent_coef_val') or (factor.equivalent_coef_val if factor else 0)
        eq_tce = annual_qty * eq_coef
        ev_tce = annual_qty * ev_coef
        ws_items.append([idx, name, eq_coef, ev_coef, annual_qty, round(eq_tce, 4), round(ev_tce, 4)])

    ws_params = wb.create_sheet('能耗参数')
    if isinstance(params, dict):
        for key, value in params.items():
            ws_params.append([key, value])

    ws_electricity = wb.create_sheet('电力计算')
    if isinstance(electricity, dict):
        for key, value in electricity.items():
            ws_electricity.append([key, value])

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    filename = f"能耗估算_{project.name}_{datetime.datetime.now().strftime('%Y%m%d')}.xlsx"
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                     as_attachment=True, download_name=filename)


# ============================================================
# 财务分析
# ============================================================

@estimation_bp.route('/project/<int:project_id>/finance')
@login_required
def finance_select(project_id):
    project = Project.query.get_or_404(project_id)
    check_result = _check_visitor_access(project)
    if check_result:
        return check_result
    return render_template('finance_select.html', project=project, role=current_user.role)


@estimation_bp.route('/project/<int:project_id>/finance/bond')
@login_required
def finance_bond(project_id):
    project = Project.query.get_or_404(project_id)
    check_result = _check_visitor_access(project)
    if check_result:
        return check_result
    return render_template('finance_bond.html', project=project, role=current_user.role)


@estimation_bp.route('/project/<int:project_id>/finance/normal')
@login_required
def finance_normal(project_id):
    project = Project.query.get_or_404(project_id)
    check_result = _check_visitor_access(project)
    if check_result:
        return check_result
    return render_template('finance_normal.html', project=project, role=current_user.role)


@estimation_bp.route('/api/project/<int:project_id>/finance/save', methods=['POST'])
@login_required
def finance_save(project_id):
    project = Project.query.get_or_404(project_id)
    check_result = _check_visitor_access(project)
    if check_result:
        return jsonify({'success': False, 'message': '无权限'})

    data = request.json or {}
    mode = data.get('mode', 'normal')
    payload = data.get('data', {})

    folder = _ensure_project_folder(project)

    if mode == 'bond':
        _write_json(folder, 'finance_bond.json', payload)
    else:
        _write_json(folder, 'finance_normal.json', payload)

    return jsonify({'success': True, 'message': '保存成功'})


@estimation_bp.route('/api/project/<int:project_id>/finance/load')
@login_required
def finance_load(project_id):
    project = Project.query.get_or_404(project_id)
    check_result = _check_visitor_access(project)
    if check_result:
        return jsonify({'success': False, 'message': '无权限'})

    mode = request.args.get('mode', 'normal')
    folder = get_project_folder(project)

    if mode == 'bond':
        data = _read_json(folder, 'finance_bond.json')
    else:
        data = _read_json(folder, 'finance_normal.json')

    return jsonify({'success': True, 'data': data if data is not None else {}})


@estimation_bp.route('/api/project/<int:project_id>/finance/meta')
@login_required
def finance_meta(project_id):
    project = Project.query.get_or_404(project_id)
    check_result = _check_visitor_access(project)
    if check_result:
        return jsonify({'success': False, 'message': '无权限'})

    folder = get_project_folder(project)
    data = _read_json(folder, 'finance_meta.json')
    return jsonify({'success': True, 'data': data if data is not None else {}})


@estimation_bp.route('/api/project/<int:project_id>/finance/export')
@login_required
def finance_export(project_id):
    project = Project.query.get_or_404(project_id)
    check_result = _check_visitor_access(project)
    if check_result:
        return jsonify({'success': False, 'message': '无权限'})

    mode = request.args.get('mode', 'normal')
    folder = get_project_folder(project)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = '财务分析'

    if mode == 'bond':
        data = _read_json(folder, 'finance_bond.json') or {}
    else:
        data = _read_json(folder, 'finance_normal.json') or {}

    if isinstance(data, dict):
        row_idx = 1
        for section_name, section_data in data.items():
            ws.cell(row=row_idx, column=1, value=section_name)
            ws.cell(row=row_idx, column=1).font = openpyxl.styles.Font(bold=True)
            row_idx += 1
            if isinstance(section_data, list):
                for item in section_data:
                    if isinstance(item, dict):
                        col_idx = 1
                        for key, value in item.items():
                            ws.cell(row=row_idx, column=col_idx, value=value)
                            col_idx += 1
                        row_idx += 1
            elif isinstance(section_data, dict):
                for key, value in section_data.items():
                    ws.cell(row=row_idx, column=1, value=key)
                    ws.cell(row=row_idx, column=2, value=value)
                    row_idx += 1
            row_idx += 1
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                col_idx = 1
                for key, value in item.items():
                    ws.cell(row=row_idx, column=col_idx, value=key)
                    ws.cell(row=row_idx, column=col_idx + 1, value=value)
                    col_idx += 2
            row_idx += 1

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    filename = f"财务分析_{project.name}_{datetime.datetime.now().strftime('%Y%m%d')}.xlsx"
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                     as_attachment=True, download_name=filename)


@estimation_bp.route('/api/project/<int:project_id>/finance/export-all', methods=['POST'])
@login_required
def finance_export_all(project_id):
    project = Project.query.get_or_404(project_id)
    check_result = _check_visitor_access(project)
    if check_result:
        return jsonify({'success': False, 'message': '无权限'})

    folder = get_project_folder(project)
    normal_data = _read_json(folder, 'finance_normal.json') or {}
    bond_data = _read_json(folder, 'finance_bond.json') or {}

    wb = openpyxl.Workbook()

    def _write_sheet(ws, data, name):
        ws.title = name
        if isinstance(data, dict):
            row_idx = 1
            for section_name, section_data in data.items():
                ws.cell(row=row_idx, column=1, value=section_name)
                ws.cell(row=row_idx, column=1).font = openpyxl.styles.Font(bold=True)
                row_idx += 1
                if isinstance(section_data, list):
                    for item in section_data:
                        if isinstance(item, dict):
                            col_idx = 1
                            for key, value in item.items():
                                ws.cell(row=row_idx, column=col_idx, value=value)
                                col_idx += 1
                            row_idx += 1
                elif isinstance(section_data, dict):
                    for key, value in section_data.items():
                        ws.cell(row=row_idx, column=1, value=key)
                        ws.cell(row=row_idx, column=2, value=value)
                        row_idx += 1
                row_idx += 1
        elif isinstance(data, list):
            row_idx = 1
            for item in data:
                if isinstance(item, dict):
                    col_idx = 1
                    for key, value in item.items():
                        ws.cell(row=row_idx, column=col_idx, value=key)
                        ws.cell(row=row_idx, column=col_idx + 1, value=value)
                        col_idx += 2
                    row_idx += 1

    ws_normal = wb.active
    _write_sheet(ws_normal, normal_data, '一般财务分析')

    ws_bond = wb.create_sheet()
    _write_sheet(ws_bond, bond_data, '专项债财务分析')

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    filename = f"财务分析汇总_{project.name}_{datetime.datetime.now().strftime('%Y%m%d')}.xlsx"
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                     as_attachment=True, download_name=filename)
