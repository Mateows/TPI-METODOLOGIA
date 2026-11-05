"""boxes

Revision ID: 0004_boxes
Revises: 0003_patient_management
Create Date: 2026-11-04 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0004_boxes'
down_revision: Union[str, None] = '0003_patient_management'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('boxes',
    sa.Column('clinic_id', sa.Uuid(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint("status IN ('active', 'maintenance')", name=op.f('ck_boxes_status')),
    sa.ForeignKeyConstraint(['clinic_id'], ['clinics.id'], name=op.f('fk_boxes_clinic_id_clinics'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_boxes'))
    )
    op.create_index(op.f('ix_boxes_clinic_id'), 'boxes', ['clinic_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_boxes_clinic_id'), table_name='boxes')
    op.drop_table('boxes')
