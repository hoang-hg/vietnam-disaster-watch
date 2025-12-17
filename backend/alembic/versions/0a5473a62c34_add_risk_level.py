"""add_risk_level

Revision ID: 0a5473a62c34
Revises: b5660dfff4b9
Create Date: 2025-12-16 23:00:38.273870

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0a5473a62c34'
down_revision: Union[str, Sequence[str], None] = '685e3d7f7cc3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('articles', sa.Column('risk_level', sa.Integer(), nullable=True))
    op.add_column('events', sa.Column('risk_level', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_articles_risk_level'), 'articles', ['risk_level'], unique=False)
    op.create_index(op.f('ix_events_risk_level'), 'events', ['risk_level'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_events_risk_level'), table_name='events')
    op.drop_index(op.f('ix_articles_risk_level'), table_name='articles')
    op.drop_column('events', 'risk_level')
    op.drop_column('articles', 'risk_level')
