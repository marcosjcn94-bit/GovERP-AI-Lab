from alembic import command
from alembic.config import Config
from psycopg_pool import ConnectionPool
from sqlalchemy import text

from gov_erp.database import owner_engine
from gov_erp.settings import settings

TENANT_TABLES = ("financial_transactions", "tenant_documents", "audit_findings", "assistant_runs")


def migrate() -> None:
    with owner_engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    alembic = Config("alembic.ini")
    command.upgrade(alembic, "head")

    with owner_engine.begin() as connection:
        policies = {
            "municipalities": "true",
            "demo_users": "id = nullif(current_setting('app.user_id', true), '')",
            "municipal_access": (
                "municipality_id = nullif(current_setting('app.tenant_id', true), '') "
                "AND user_id = nullif(current_setting('app.user_id', true), '')"
            ),
            "demo_sessions": (
                "municipality_id = nullif(current_setting('app.tenant_id', true), '') "
                "AND user_id = nullif(current_setting('app.user_id', true), '')"
            ),
        }
        for table in (*policies, *TENANT_TABLES):
            connection.execute(text(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY'))
            connection.execute(text(f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY'))
            expression = policies.get(
                table,
                "municipality_id = nullif(current_setting('app.tenant_id', true), '')",
            )
            policy = f"tenant_context_{table}"
            connection.execute(text(f' DROP POLICY IF EXISTS "{policy}" ON "{table}"'))
            connection.execute(
                text(
                    f'CREATE POLICY "{policy}" ON "{table}" TO goverp_app '
                    f"USING ({expression}) WITH CHECK ({expression})"
                )
            )
        connection.execute(text("GRANT SELECT ON municipalities TO goverp_app"))
        connection.execute(text("GRANT SELECT ON public_ranking_snapshots TO goverp_app"))
        connection.execute(text("GRANT SELECT ON demo_users TO goverp_app"))
        connection.execute(text("GRANT SELECT ON municipal_access TO goverp_app"))
        connection.execute(
            text("GRANT SELECT, INSERT, UPDATE, DELETE ON demo_sessions TO goverp_app")
        )
        connection.execute(
            text("GRANT SELECT, INSERT, UPDATE, DELETE ON financial_transactions TO goverp_app")
        )
        connection.execute(
            text("GRANT SELECT, INSERT, UPDATE, DELETE ON tenant_documents TO goverp_app")
        )
        connection.execute(
            text("GRANT SELECT, INSERT, UPDATE, DELETE ON audit_findings TO goverp_app")
        )
        connection.execute(text("GRANT SELECT, INSERT ON assistant_runs TO goverp_app"))
        connection.execute(
            text("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO goverp_app")
        )

    owner_dsn = settings.owner_database_url.replace("postgresql+psycopg://", "postgresql://", 1)
    with ConnectionPool(
        owner_dsn,
        kwargs={"autocommit": True, "prepare_threshold": 0},
        min_size=1,
        max_size=2,
    ) as pool:
        from langgraph.checkpoint.postgres import PostgresSaver

        saver = PostgresSaver(pool)
        saver.setup()
        with owner_engine.begin() as connection:
            for table in ("checkpoints", "checkpoint_blobs", "checkpoint_writes"):
                connection.execute(
                    text(f'GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE "{table}" TO goverp_app')
                )

    print("Migracoes PostgreSQL e politicas de isolamento aplicadas.")


if __name__ == "__main__":
    migrate()
