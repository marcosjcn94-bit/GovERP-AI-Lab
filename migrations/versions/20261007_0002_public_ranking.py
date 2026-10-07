import sqlalchemy as sa
from alembic import op

revision = "20261007_0002"
down_revision = "20261007_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "public_ranking_snapshots",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("edition_year", sa.Integer(), nullable=False),
        sa.Column("ibge_code", sa.String(length=7), nullable=False),
        sa.Column("municipality_name", sa.String(length=120), nullable=False),
        sa.Column("uf", sa.String(length=2), nullable=False),
        sa.Column("population", sa.Integer(), nullable=False),
        sa.Column("overall_score", sa.Numeric(10, 6), nullable=False),
        sa.Column("overall_rank", sa.Integer(), nullable=False),
        sa.Column("rank_change", sa.Integer()),
        sa.Column("pillar_scores", sa.JSON(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("source_sha256", sa.String(length=64), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("edition_year", "ibge_code", name="uq_clp_edition_municipality"),
    )
    op.create_index(
        "ix_clp_ranking_ibge_edition",
        "public_ranking_snapshots",
        ["ibge_code", "edition_year"],
    )


def downgrade() -> None:
    op.drop_index("ix_clp_ranking_ibge_edition", table_name="public_ranking_snapshots")
    op.drop_table("public_ranking_snapshots")
