from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from gov_erp.settings import settings

owner_engine = create_engine(settings.owner_database_url, pool_pre_ping=True)
app_engine = create_engine(settings.app_database_url, pool_pre_ping=True)
OwnerSession = sessionmaker(owner_engine, expire_on_commit=False)
AppSession = sessionmaker(app_engine, expire_on_commit=False)


@contextmanager
def tenant_session(municipality_id: str, user_id: str) -> Iterator[Session]:
    """Bind tenant and user context for this transaction before any tenant query."""
    with AppSession() as session, session.begin():
        session.execute(
            text("SELECT set_config('app.tenant_id', :value, true)"), {"value": municipality_id}
        )
        session.execute(text("SELECT set_config('app.user_id', :value, true)"), {"value": user_id})
        yield session
