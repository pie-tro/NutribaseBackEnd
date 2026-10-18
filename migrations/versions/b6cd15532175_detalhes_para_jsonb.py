from sqlalchemy.dialects import postgresql

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