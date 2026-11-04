"""search

Revision ID: 13cb58eb2a0e
Revises: 26509779cf2a
Create Date: 2026-10-31 14:08:27.961859

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '13cb58eb2a0e'
down_revision: Union[str, Sequence[str], None] = '26509779cf2a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add searchable text to guides/specs, fill it for existing rows, and (on Postgres)
    add trigram indexes so 'contains these words' searches stay fast."""
    with op.batch_alter_table('entries', schema=None) as batch_op:
        batch_op.add_column(sa.Column('search_text', sa.Text(), nullable=False, server_default=''))

    import json

    from app.modules.community.service import search_text_for

    conn = op.get_bind()
    rows = conn.execute(sa.text(
        "SELECT e.id, r.title, r.data FROM entries e JOIN entry_revisions r ON r.id = e.current_revision_id"
    )).fetchall()
    for entry_id, title, data in rows:
        data = json.loads(data) if isinstance(data, str) else (data or {})
        conn.execute(sa.text("UPDATE entries SET search_text = :t WHERE id = :i"),
                     {"t": search_text_for(title, data), "i": entry_id})

    if conn.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
        op.execute("CREATE INDEX IF NOT EXISTS ix_entries_search_trgm ON entries USING gin (search_text gin_trgm_ops)")
        op.execute("CREATE INDEX IF NOT EXISTS ix_dtcs_title_trgm ON dtcs USING gin (lower(title) gin_trgm_ops)")
        op.execute("CREATE INDEX IF NOT EXISTS ix_tsbs_summary_trgm ON tsbs USING gin (lower(summary) gin_trgm_ops)")


def downgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        op.execute("DROP INDEX IF EXISTS ix_entries_search_trgm")
        op.execute("DROP INDEX IF EXISTS ix_dtcs_title_trgm")
        op.execute("DROP INDEX IF EXISTS ix_tsbs_summary_trgm")
    with op.batch_alter_table('entries', schema=None) as batch_op:
        batch_op.drop_column('search_text')
