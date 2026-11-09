"""aceite da politica de privacidade (LGPD)

Revision ID: d8e51f3b7a41
Revises: c7d41a9e5b20
"""
from alembic import op
import sqlalchemy as sa

revision = "d8e51f3b7a41"
down_revision = "c7d41a9e5b20"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("usuarios", sa.Column("aceitou_politica_em", sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column("usuarios", "aceitou_politica_em")
