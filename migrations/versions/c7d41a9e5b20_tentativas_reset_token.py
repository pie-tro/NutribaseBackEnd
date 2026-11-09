"""tentativas no código de recuperação de senha

Revision ID: c7d41a9e5b20
Revises: b6cd15532175
"""
from alembic import op
import sqlalchemy as sa

revision = "c7d41a9e5b20"
down_revision = "b6cd15532175"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "password_reset_tokens",
        sa.Column("tentativas", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade():
    op.drop_column("password_reset_tokens", "tentativas")
