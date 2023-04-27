from data.database import *
from data.__all_models import User
from config import *

if __name__ == "__main__":
    global_init(db_password, db_username, db_address, db_name)
    sess = create_session()

    name = input("Введите имя: ")
    login = input("Введите логин: ")
    email = input("Введите почту: ")
    password = input("Введите пароль: ")
    admin = bool(input("Админ (по умочанию: нет): "))

    user = User(name, login, email, admin)
    user.generate_hash_password(password)

    sess.add(user)
    sess.commit()
