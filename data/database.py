import sqlalchemy as sa
import sqlalchemy.orm as orm
from sqlalchemy.orm import Session
import sqlalchemy.ext.declarative as dec

Base = dec.declarative_base()
__factory = None


def global_init(db_password):
    global __factory
    if __factory:
        return

    conn_str = f'postgresql://postgres:{db_password}@localhost/PyTry'
    print(f"Подключение к базе данных по адресу {conn_str}")
    engine = sa.create_engine(conn_str, echo=False)
    __factory = orm.sessionmaker(bind=engine)
    from . import __all_models
    Base.metadata.create_all(engine)


def create_session() -> Session:
    global __factory
    return __factory()
