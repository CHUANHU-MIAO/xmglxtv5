from datetime import datetime
from sqlalchemy import extract, func, case
from web.extensions import db
from web.models import Project, FundRecord


_finance_stats_cache = {'data': None, 'ts': 0}
CACHE_TTL = 60


def _now_ts():
    return datetime.now().timestamp()


def invalidate_finance_stats_cache():
    _finance_stats_cache['data'] = None
    _finance_stats_cache['ts'] = 0


def calculate_revenue(start_date=None, end_date=None):
    query = Project.query
    if start_date:
        query = query.filter(Project.start_date >= start_date)
    if end_date:
        query = query.filter(Project.start_date <= end_date)

    projects = query.all()

    received = 0.0
    receivable = 0.0

    for p in projects:
        contract_amount = float(p.contract_amount) if p.contract_amount else 0.0
        settled_amount = float(p.settled_amount) if p.settled_amount else 0.0

        if p.payment_status in ('已结款', '已结清'):
            actual_settled = settled_amount if settled_amount > 0 else contract_amount
            received += actual_settled
            receivable += max(0.0, contract_amount - actual_settled)
        elif p.payment_status == '部分结清':
            received += settled_amount
            receivable += max(0.0, contract_amount - settled_amount)
        else:
            received += settled_amount
            receivable += max(0.0, contract_amount - settled_amount)

    total_revenue = received + receivable
    return total_revenue, received, receivable


def calculate_expenses(start_date=None, end_date=None):
    base = db.session.query(FundRecord)
    if start_date:
        base = base.filter(FundRecord.use_date >= start_date)
    if end_date:
        base = base.filter(FundRecord.use_date <= end_date)

    project_expenses = base.with_entities(
        func.coalesce(func.sum(FundRecord.amount), 0.0)
    ).filter(FundRecord.expense_type == '项目支出').scalar()

    operating_expenses = base.with_entities(
        func.coalesce(func.sum(FundRecord.amount), 0.0)
    ).filter(
        (FundRecord.expense_type == '运营支出') |
        (FundRecord.expense_type == None) |
        (FundRecord.expense_type == '')
    ).scalar()

    total_expenses = (project_expenses + operating_expenses) / 10000.0
    project_expenses = project_expenses / 10000.0
    operating_expenses = operating_expenses / 10000.0
    return total_expenses, project_expenses, operating_expenses


def get_monthly_profit(months=6):
    now_ts = _now_ts()
    cached = _finance_stats_cache['data']
    if cached and (now_ts - _finance_stats_cache['ts']) < CACHE_TTL:
        return cached

    today = datetime.now()
    current_year = today.year
    current_month = today.month

    earliest_year = current_year
    earliest_month = current_month - (months - 1)
    while earliest_month <= 0:
        earliest_year -= 1
        earliest_month += 12
    earliest_date = datetime(earliest_year, earliest_month, 1)

    projects = Project.query.filter(Project.start_date >= earliest_date).all()

    revenue_map = {}
    for p in projects:
        if not p.start_date:
            continue
        key = (p.start_date.year, p.start_date.month)
        contract_amount = float(p.contract_amount) if p.contract_amount else 0.0
        settled_amount = float(p.settled_amount) if p.settled_amount else 0.0

        if p.payment_status in ('已结款', '已结清'):
            actual_received = settled_amount if settled_amount > 0 else contract_amount
        elif p.payment_status == '部分结清':
            actual_received = settled_amount
        else:
            actual_received = settled_amount

        revenue_map[key] = revenue_map.get(key, 0.0) + actual_received

    expense_rows = db.session.query(
        extract('year', FundRecord.use_date).label('y'),
        extract('month', FundRecord.use_date).label('m'),
        func.sum(FundRecord.amount).label('exp')
    ).filter(
        FundRecord.use_date >= earliest_date
    ).group_by('y', 'm').all()
    expense_map = {(int(r.y), int(r.m)): float(r.exp or 0) / 10000.0 for r in expense_rows}

    month_labels = []
    month_revenues = []
    month_expenses_list = []
    month_profits = []

    for i in range(months):
        offset = (months - 1) - i
        target_year = current_year
        target_month = current_month - offset
        while target_month <= 0:
            target_year -= 1
            target_month += 12
        while target_month > 12:
            target_year += 1
            target_month -= 12

        label = f"{target_year}年{target_month:02d}月"
        month_labels.append(label)

        rev = revenue_map.get((target_year, target_month), 0.0)
        exp = expense_map.get((target_year, target_month), 0.0)
        month_revenues.append(rev)
        month_expenses_list.append(exp)
        month_profits.append(rev - exp)

    result = (month_labels, month_revenues, month_expenses_list, month_profits)

    _finance_stats_cache['data'] = result
    _finance_stats_cache['ts'] = now_ts

    return result
