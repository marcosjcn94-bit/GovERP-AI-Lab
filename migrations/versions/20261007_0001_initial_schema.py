from alembic import op

from gov_erp.models import Base

revision = "20261007_0001"
down_revision = None
branch_labels = None
depends_on = None

# Only tables owned by this revision; later revisions create their own tables.
INITIAL_TABLE_NAMES = (
    "municipalities",
    "demo_users",
    "municipal_access",
    "demo_sessions",
    "financial_transactions",
    "tenant_documents",
    "audit_findings",
    "assistant_runs",
)


def initial_tables():
    return [Base.metadata.tables[name] for name in INITIAL_TABLE_NAMES]


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    Base.metadata.create_all(bind=op.get_bind(), tables=initial_tables(), checkfirst=True)


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind(), tables=initial_tables(), checkfirst=True)
