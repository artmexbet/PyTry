from dotenv import dotenv_values
from os import environ

config_ = {**dotenv_values(), **environ}

db_password = config_["DB_PASSWORD"]
db_username = config_["DB_USERNAME"]
db_address = config_["DB_ADDRESS"]  # путь до базы данных
db_name = config_["DB_NAME"]  # путь до базы данных
