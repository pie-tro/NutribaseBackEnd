from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "b6cd15532175"
down_revision = "86a82e821d14"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        "historico_consultas", "detalhes",
        existing_type=sa.JSON(), type_=postgresql.JSONB(),
        postgresql_using="detalhes::jsonb", existing_nullable=False,
    )


def downgrade():
    op.alter_column(
        "historico_consultas", "detalhes",
        existing_type=postgresql.JSONB(), type_=sa.JSON(),
        postgresql_using="detalhes::json", existing_nullable=False,
    )