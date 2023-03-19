from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager

import logging

from data.database import *
from config import *

logging.basicConfig(filename="runtime.log",
                    format='%(asctime)s %(levelname)s %(name)s %(message)s',
                    level=logging.DEBUG)

app = Flask(__name__)
CORS(app)
app.config["JWT_SECRET_KEY"] = "SECRET_KEY"
jwt_manager = JWTManager(app)


if __name__ == "__main__":
    global_init(db_password)
    app.run(debug=True)

