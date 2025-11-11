"""v0.16.0 Polar integration

Revision ID: a1b2c3d4e5f6
Revises: 3c4d5e6f7a8b
Create Date: 2025-02-05 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "3c4d5e6f7a8b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "polar_accounts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            comment="User ID linked to this Polar account",
        ),
        sa.Column(
            "client_id",
            sa.String(length=512),
            nullable=True,
            comment="Polar client ID encrypted with Fernet",
        ),
        sa.Column(
            "client_secret",
            sa.String(length=512),
            nullable=True,
            comment="Polar client secret encrypted with Fernet",
        ),
        sa.Column(
            "state",
            sa.String(length=128),
            nullable=True,
            comment="Temporary OAuth state to prevent CSRF",
        ),
        sa.Column(
            "access_token",
            sa.String(length=512),
            nullable=True,
            comment="Polar access token encrypted with Fernet",
        ),
        sa.Column("token_type", sa.String(length=50), nullable=True),
        sa.Column("token_scope", sa.String(length=128), nullable=True),
        sa.Column("token_issued_at", sa.DateTime(), nullable=True),
        sa.Column("token_expires_at", sa.DateTime(), nullable=True),
        sa.Column(
            "x_user_id",
            sa.BigInteger(),
            nullable=True,
            comment="Polar ecosystem user id",
        ),
        sa.Column(
            "member_id",
            sa.String(length=128),
            nullable=True,
            comment="Partner defined member identifier",
        ),
        sa.Column(
            "polar_user_id",
            sa.BigInteger(),
            nullable=True,
            comment="Polar assigned user identifier",
        ),
        sa.Column("registration_date", sa.DateTime(), nullable=True),
        sa.Column("last_notification_at", sa.DateTime(), nullable=True),
        sa.Column(
            "is_linked",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
            comment="Indicates if the Polar account is currently linked",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
        sa.UniqueConstraint("user_id", name="uq_polar_accounts_user_id"),
    )
    op.create_index(
        "ix_polar_accounts_polar_user_id",
        "polar_accounts",
        ["polar_user_id"],
        unique=False,
    )
    op.add_column(
        "activities",
        sa.Column(
            "polar_exercise_id",
            sa.String(length=64),
            nullable=True,
            comment="Polar exercise hashed ID",
        ),
    )
    op.create_index(
        "uq_activities_polar_exercise_id",
        "activities",
        ["polar_exercise_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_activities_polar_exercise_id", table_name="activities")
    op.drop_column("activities", "polar_exercise_id")

    op.drop_index("ix_polar_accounts_polar_user_id", table_name="polar_accounts")
    op.drop_table("polar_accounts")
