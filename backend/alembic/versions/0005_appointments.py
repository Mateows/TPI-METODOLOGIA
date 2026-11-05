"""appointments

Revision ID: 0005_appointments
Revises: 0004_boxes
Create Date: 2026-11-05 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0005_appointments'
down_revision: Union[str, None] = '0004_boxes'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'appointments',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('clinic_id', sa.Uuid(), nullable=False),
        sa.Column('patient_id', sa.Uuid(), nullable=False),
        sa.Column('dentist_id', sa.Uuid(), nullable=False),
        sa.Column('box_id', sa.Uuid(), nullable=False),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('scheduled', 'confirmed', 'attended', 'cancelled', 'no_show')",
            name=op.f('ck_appointments_status'),
        ),
        sa.ForeignKeyConstraint(
            ['clinic_id'],
            ['clinics.id'],
            name=op.f('fk_appointments_clinic_id_clinics'),
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['patient_id'],
            ['patients.id'],
            name=op.f('fk_appointments_patient_id_patients'),
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['dentist_id'],
            ['users.id'],
            name=op.f('fk_appointments_dentist_id_users'),
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['box_id'],
            ['boxes.id'],
            name=op.f('fk_appointments_box_id_boxes'),
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_appointments')),
    )
    op.create_index(
        op.f('ix_appointments_clinic_id'),
        'appointments',
        ['clinic_id'],
        unique=False,
    )
    op.create_index(
        'ix_appointments_clinic_dentist_start',
        'appointments',
        ['clinic_id', 'dentist_id', 'start_time'],
        unique=False,
    )
    op.create_index(
        'ix_appointments_clinic_box_start',
        'appointments',
        ['clinic_id', 'box_id', 'start_time'],
        unique=False,
    )

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist;")
        op.execute("""
            ALTER TABLE appointments
            ADD CONSTRAINT ex_appointments_dentist_no_overlap
            EXCLUDE USING gist (
                clinic_id WITH =,
                dentist_id WITH =,
                tstzrange(start_time, end_time) WITH &&
            ) WHERE (status != 'cancelled');
        """)
        op.execute("""
            ALTER TABLE appointments
            ADD CONSTRAINT ex_appointments_box_no_overlap
            EXCLUDE USING gist (
                clinic_id WITH =,
                box_id WITH =,
                tstzrange(start_time, end_time) WITH &&
            ) WHERE (status != 'cancelled');
        """)


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TABLE appointments DROP CONSTRAINT IF EXISTS ex_appointments_box_no_overlap;")
        op.execute("ALTER TABLE appointments DROP CONSTRAINT IF EXISTS ex_appointments_dentist_no_overlap;")

    op.drop_index('ix_appointments_clinic_box_start', table_name='appointments')
    op.drop_index('ix_appointments_clinic_dentist_start', table_name='appointments')
    op.drop_index(op.f('ix_appointments_clinic_id'), table_name='appointments')
    op.drop_table('appointments')
