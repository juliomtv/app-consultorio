"""Per-tenant SQLite engine + session management — one DB file per tenant."""
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

_engines: dict = {}


def _data_dir() -> str:
    from flask import current_app
    return current_app.config.get('DATA_DIR', os.path.join(
        os.path.dirname(__file__), '..', 'data'
    ))


def _db_path(slug: str) -> str:
    return os.path.join(_data_dir(), f'{slug}.db')


def db_exists(slug: str) -> bool:
    try:
        return os.path.exists(_db_path(slug))
    except Exception:
        return False


def get_engine(slug: str):
    if slug in _engines:
        return _engines[slug]

    data_dir = _data_dir()
    os.makedirs(data_dir, exist_ok=True)
    path = _db_path(slug)
    engine = create_engine(
        f'sqlite:///{path}',
        connect_args={'check_same_thread': False},
    )

    from database.models import db as flask_db
    flask_db.metadata.create_all(engine)
    _migrate_engine(engine)

    _engines[slug] = engine
    return engine


def open_session(slug: str):
    engine = get_engine(slug)
    Session = sessionmaker(bind=engine)
    return Session()


def _migrate_engine(engine):
    """Idempotently adds columns introduced after the initial schema."""
    new_cols = [
        ('appointments', 'payment_type',    "VARCHAR(20) DEFAULT 'particular'"),
        ('appointments', 'plan_id',         'INTEGER REFERENCES health_plans(id)'),
        ('users',        'is_demo',         'BOOLEAN NOT NULL DEFAULT 0'),
        ('tenants',      'demo_expires_at', 'DATETIME'),
    ]
    with engine.connect() as conn:
        for table, col, definition in new_cols:
            try:
                conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {col} {definition}'))
                conn.commit()
            except Exception:
                pass


class Pagination:
    """Minimal Flask-SQLAlchemy-compatible pagination object."""

    def __init__(self, items, page: int, per_page: int, total: int):
        self.items    = items
        self.page     = page
        self.per_page = per_page
        self.total    = total
        self.pages    = max(1, (total + per_page - 1) // per_page)
        self.has_prev = page > 1
        self.has_next = page < self.pages
        self.prev_num = page - 1 if self.has_prev else None
        self.next_num = page + 1 if self.has_next else None

    def iter_pages(self, left_edge=2, right_edge=2, left_current=2, right_current=5):
        last = 0
        for num in range(1, self.pages + 1):
            if (num <= left_edge
                    or (self.page - left_current - 1 < num < self.page + right_current)
                    or num > self.pages - right_edge):
                if last + 1 != num:
                    yield None
                yield num
                last = num


def remove_db(slug: str) -> bool:
    """Deletes the tenant DB file and clears the engine cache. Returns True if removed."""
    import os as _os
    _engines.pop(slug, None)
    path = _db_path(slug)
    if _os.path.exists(path):
        _os.remove(path)
        return True
    return False


def paginate(query, page: int, per_page: int) -> Pagination:
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    return Pagination(items, page, per_page, total)
