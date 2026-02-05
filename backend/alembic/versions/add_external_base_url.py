"""add external_base_url to families

Revision ID: add_external_base_url
Revises: add_notification_columns
Create Date: 2026-02-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_external_base_url'
down_revision: Union[str, None] = 'add_notification_columns'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 添加外网地址配置字段
    op.add_column('families', sa.Column('external_base_url', sa.String(200), nullable=True))


def downgrade() -> None:
    op.drop_column('families', 'external_base_url')
