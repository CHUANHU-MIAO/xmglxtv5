from datetime import datetime
from collections import defaultdict
from sqlalchemy import extract, func, or_, and_
from web.extensions import db
from web.models import User, Project


_project_stats_cache = {'data': None, 'ts': 0}
CACHE_TTL = 60


def _now_ts():
    return datetime.now().timestamp()


def invalidate_project_stats_cache():
    _project_stats_cache['data'] = None
    _project_stats_cache['ts'] = 0


def get_index_statistics(months=12):
    now_ts = _now_ts()
    cached = _project_stats_cache['data']
    if cached and (now_ts - _project_stats_cache['ts']) < CACHE_TTL:
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

    rows = db.session.query(
        extract('year', Project.start_date).label('y'),
        extract('month', Project.start_date).label('m'),
        func.count('*').label('cnt')
    ).filter(
        Project.start_date >= earliest_date,
        Project.is_valid == 1
    ).group_by('y', 'm').all()

    month_count_map = {(int(r.y), int(r.m)): r.cnt for r in rows}

    month_labels = []
    month_data = []
    for i in range(months):
        month_offset = (months - 1) - i
        target_year = current_year
        target_month = current_month - month_offset
        while target_month <= 0:
            target_year -= 1
            target_month += 12
        while target_month > 12:
            target_year += 1
            target_month -= 12

        month_labels.append(f"{target_year}-{target_month:02d}")
        month_data.append(month_count_map.get((target_year, target_month), 0))

    area_expr = func.coalesce(Project.location, '未知')
    area_rows = db.session.query(
        area_expr.label('loc'),
        func.count('*').label('cnt')
    ).filter(Project.is_valid == 1).group_by(area_expr).all()
    area_dict = {r.loc: r.cnt for r in area_rows}

    eng_expr = func.coalesce(User.username, '未知')
    eng_rows = db.session.query(
        eng_expr.label('eng_name'),
        func.count('*').label('cnt')
    ).select_from(Project).outerjoin(
        User, Project.user_id == User.id
    ).filter(Project.is_valid == 1).group_by(eng_expr).all()
    eng_dict = {r.eng_name: r.cnt for r in eng_rows}

    year_total = Project.query.filter(Project.is_valid == 1).count()

    result = {
        'month_labels': month_labels,
        'month_data': month_data,
        'area_dict': area_dict,
        'eng_dict': eng_dict,
        'year_total': year_total,
    }

    _project_stats_cache['data'] = result
    _project_stats_cache['ts'] = now_ts

    return result


def search_projects(keyword, page=1, per_page=20):
    query = Project.query.join(User, Project.user_id == User.id)
    if keyword:
        from sqlalchemy import or_
        query = query.filter(
            or_(
                Project.name.like(f'%{keyword}%'),
                Project.owner.like(f'%{keyword}%'),
                Project.location.like(f'%{keyword}%'),
                Project.owner_name.like(f'%{keyword}%'),
                Project.service_content.like(f'%{keyword}%'),
                Project.remark.like(f'%{keyword}%'),
                User.username.like(f'%{keyword}%')
            )
        )
    return query.order_by(Project.create_time.desc()).paginate(page=page, per_page=per_page, error_out=False)


def find_duplicate_groups(user_id):
    """检测项目中的重复项。

    规则：项目名称相同 且 服务内容相同 → 视为重复项目。
    user_id 为 None 时检测所有用户（管理员视角）。
    返回：每个重复组的列表，每组包含多个 Project 对象。
    """
    query = Project.query.filter_by(is_valid=1)
    if user_id is not None:
        query = query.filter_by(user_id=user_id)
    projects = query.all()

    groups = defaultdict(list)
    for p in projects:
        key = (p.name.strip() if p.name else '', (p.service_content or '').strip())
        groups[key].append(p)

    # 只保留数量 > 1 的组，按组内最早创建时间排序
    duplicates = {k: v for k, v in groups.items() if len(v) > 1}
    sorted_duplicates = dict(
        sorted(duplicates.items(),
               key=lambda item: min(p.create_time or datetime.min for p in item[1]))
    )
    return sorted_duplicates
