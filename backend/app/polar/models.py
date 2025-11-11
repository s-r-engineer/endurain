from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship

from core.database import Base


class PolarAccount(Base):
    __tablename__ = "polar_accounts"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_polar_accounts_user_id"),
    )

    id = Column(Integer, primary_key=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="User ID linked to this Polar account",
    )
    client_id = Column(
        String(length=512),
        nullable=True,
        comment="Polar client ID encrypted with Fernet",
    )
    client_secret = Column(
        String(length=512),
        nullable=True,
        comment="Polar client secret encrypted with Fernet",
    )
    state = Column(
        String(length=128),
        nullable=True,
        comment="Temporary OAuth state to prevent CSRF",
    )
    access_token = Column(
        String(length=512),
        nullable=True,
        comment="Polar access token encrypted with Fernet",
    )
    token_type = Column(String(length=50), nullable=True)
    token_scope = Column(String(length=128), nullable=True)
    token_issued_at = Column(DateTime, nullable=True)
    token_expires_at = Column(DateTime, nullable=True)
    x_user_id = Column(BigInteger, nullable=True, comment="Polar ecosystem user id")
    member_id = Column(
        String(length=128),
        nullable=True,
        comment="Partner defined member identifier",
    )
    polar_user_id = Column(
        BigInteger,
        nullable=True,
        index=True,
        comment="Polar assigned user identifier",
    )
    registration_date = Column(DateTime, nullable=True)
    last_notification_at = Column(DateTime, nullable=True)
    is_linked = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Indicates if the Polar account is currently linked",
    )
    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now(),
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        server_default=func.now(),
    )

    user = relationship("User", back_populates="polar_account")

