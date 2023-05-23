import sqlalchemy as sa
import sqlalchemy.orm as orm
from sqlalchemy.orm import Session
import sqlalchemy.ext.declarative as dec

Base = dec.declarative_base()
__factory = None


def global_init(db_password, db_username, db_address, db_name):
    global __factory
    if __factory:
        return

    conn_str = f'postgresql://{db_username}:{db_password}@' \
               f'{db_address}/{db_name}'
    print(f"Подключение к базе данных по адресу {conn_str}")
    engine = sa.create_engine(conn_str, echo=False, pool_size=0, max_overflow=25)
    __factory = orm.sessionmaker(bind=engine)
    from . import __all_models
    Base.metadata.create_all(engine)


def create_session() -> Session:
    global __factory
    return __factory()
