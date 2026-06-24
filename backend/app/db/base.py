from sqlalchemy import BigInteger, Integer
from sqlalchemy.orm import DeclarativeBase


BIGINT_ID = BigInteger().with_variant(Integer, "sqlite")


class Base(DeclarativeBase):
    pass
