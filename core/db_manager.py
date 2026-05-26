"""
Per-tenant database engine manager.

Dev:  one SQLite file per tenant  (database/tenant_<slug>.db)
Prod: PostgreSQL URL stored in Tenant.db_url

The existing Flask-SQLAlchemy `db` object continues to serve the
master database (tenants, settings, superadmin).  When a tenant
has its own db_url, use get_engine()/get_session() for isolated queries.
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker


class DBManager:
    _engines: dict = {}
    _sessions: dict = {}

    @classmethod
    def get_engine(cls, tenant):
        tid = tenant.id
        if tid not in cls._engines:
            url = cls._resolve_url(tenant)
            cls._engines[tid] = create_engine(url, pool_pre_ping=True)
        return cls._engines[tid]

    @classmethod
    def get_session(cls, tenant):
        tid = tenant.id
        if tid not in cls._sessions:
            engine = cls.get_engine(tenant)
            factory = sessionmaker(bind=engine)
            cls._sessions[tid] = scoped_session(factory)
        return cls._sessions[tid]

    @classmethod
    def bootstrap_tenant_db(cls, tenant, metadata):
        """Create all tables in the tenant's own database."""
        engine = cls.get_engine(tenant)
        metadata.create_all(engine)

    @classmethod
    def invalidate(cls, tenant_id: int):
        """Call after changing a tenant's db_url."""
        cls._engines.pop(tenant_id, None)
        sess = cls._sessions.pop(tenant_id, None)
        if sess:
            sess.remove()

    @classmethod
    def _resolve_url(cls, tenant) -> str:
        if tenant.db_url:
            return tenant.db_url
        base = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 'database'
        )
        os.makedirs(base, exist_ok=True)
        return f"sqlite:///{base}/tenant_{tenant.slug}.db"
