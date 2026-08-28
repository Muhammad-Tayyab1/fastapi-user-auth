"""create users and otps"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("users", sa.Column("id", sa.Uuid(), primary_key=True),
                    sa.Column("email", sa.String(320), nullable=False), sa.Column("hashed_password", sa.String(), nullable=False),
                    sa.Column("full_name", sa.String(200)), sa.Column("role", sa.String(20), nullable=False),
                    sa.Column("is_verified", sa.Boolean(), nullable=False), sa.Column("is_active", sa.Boolean(), nullable=False),
                    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_table("otps", sa.Column("id", sa.Uuid(), primary_key=True),
                    sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
                    sa.Column("code", sa.String(6), nullable=False), sa.Column("purpose", sa.String(30), nullable=False),
                    sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False), sa.Column("is_used", sa.Boolean(), nullable=False),
                    sa.Column("attempts", sa.Integer(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_otps_user_id", "otps", ["user_id"])
    op.create_index("ix_otps_purpose", "otps", ["purpose"])


def downgrade() -> None:
    op.drop_table("otps")
    op.drop_table("users")

