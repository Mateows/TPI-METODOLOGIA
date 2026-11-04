"""patient management

Revision ID: 0003_patient_management
Revises: 0002_core_models_tenants
Create Date: 2026-11-04 18:54:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0003_patient_management'
down_revision: Union[str, None] = '0002_core_models_tenants'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'patients',
        sa.Column('clinic_id', sa.Uuid(), nullable=False),
        sa.Column('first_name', sa.String(length=120), nullable=False),
        sa.Column('last_name', sa.String(length=120), nullable=False),
        sa.Column('dni', sa.String(length=32), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('birth_date', sa.Date(), nullable=True),
        sa.Column('medical_history_summary', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ['clinic_id'],
            ['clinics.id'],
            name=op.f('fk_patients_clinic_id_clinics'),
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_patients')),
        sa.UniqueConstraint('clinic_id', 'dni', name=op.f('uq_patients_clinic_id')),
    )
    op.create_index(
        op.f('ix_patients_clinic_id'),
        'patients',
        ['clinic_id'],
        unique=False,
    )
    op.create_index(
        'ix_patients_clinic_id_last_name_first_name',
        'patients',
        ['clinic_id', 'last_name', 'first_name'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        'ix_patients_clinic_id_last_name_first_name',
        table_name='patients',
    )
    op.drop_index(
        op.f('ix_patients_clinic_id'),
        table_name='patients',
    )
    op.drop_table('patients')
