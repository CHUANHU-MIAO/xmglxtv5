from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from web.models import Project
from web.extensions import db

estimation_bp = Blueprint('estimation', __name__)


@estimation_bp.route('/project/<int:project_id>/investment')
@login_required
def investment_estimate(project_id):
    project = Project.query.get_or_404(project_id)
    return render_template('investment_estimate.html', project=project)


@estimation_bp.route('/project/<int:project_id>/energy')
@login_required
def energy_estimate(project_id):
    project = Project.query.get_or_404(project_id)
    return render_template('energy_estimate.html', project=project)


@estimation_bp.route('/project/<int:project_id>/finance')
@login_required
def finance_select(project_id):
    project = Project.query.get_or_404(project_id)
    return render_template('finance_select.html', project=project)


@estimation_bp.route('/project/<int:project_id>/finance/normal')
@login_required
def finance_normal(project_id):
    project = Project.query.get_or_404(project_id)
    return render_template('finance_normal.html', project=project)


@estimation_bp.route('/project/<int:project_id>/finance/bond')
@login_required
def finance_bond(project_id):
    project = Project.query.get_or_404(project_id)
    return render_template('finance_bond.html', project=project)
