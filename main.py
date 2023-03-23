from flask import Flask, request, Response
from flask_cors import CORS
from flask_jwt_extended import JWTManager, get_jwt
from flask_jwt_extended import (create_access_token, create_refresh_token,
                                jwt_required, get_jwt_identity,
                                get_current_user)
from task_checking import TaskChecker
from data.__all_models import *

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


@jwt_manager.user_lookup_loader
def take_user(header_data, payload_data) -> User:
    # print(header_data, payload_data)
    sess = create_session()
    user = sess.get(User, payload_data["sub"])
    return user


def check_task_request(course_id, lesson_id, task_id):
    sess = create_session()

    user = get_current_user()
    course = sess.get(Course, course_id)
    lesson = sess.get(Lesson, lesson_id)
    task = sess.get(Task, task_id)

    if course not in user.courses and not user.is_admin:
        return {"status": "User not at course"}, 403

    if lesson not in course.lessons:
        return {"status": "Not found"}, 404

    if task not in lesson.tasks:
        return {"status": "Not found"}, 404

    return task


@app.route("/reg", methods=["POST"])
def reg():
    json = request.json
    if any([i not in json for i in ["login", "password", "name", "email"]]):
        return {"status": "Not all arguments"}, 500

    sess = create_session()

    if sess.query(User).filter_by(login=json["login"]).first() or \
            sess.query(User).filter_by(email=json["email"]).first():
        return {"status": "already"}

    user = User(name=json["name"],
                login=json["login"],
                email=json["email"])
    user.generate_hash_password(json["password"])

    sess.add(user)
    sess.commit()
    return {
        "status": "success",
        "jwt_access": create_access_token(identity=user.id,
                                          additional_claims={
                                              "login": user.login
                                          }),
        "jwt_refresh": create_refresh_token(identity=user.id,
                                            additional_claims={
                                                "login": user.login
                                            }),
        "user": user.to_json()
    }, 200


@app.route("/login", methods=["POST"])
def login():
    json = request.json

    if not ("password" in json and ("email" in json or "login" in json)):
        return {"status": "Not all arguments"}, 500

    sess = create_session()

    user = sess.query(User).filter(
        (
                User.login == json.get("login", "")
        ) | (
                User.email == json.get("email", "")
        )
    ).first()
    if not user or not user.check_password(json["password"]):
        return {"status": "incorrect"}, 404

    return {
        "status": "success",
        "jwt_access": create_access_token(
            identity=user.id,
            additional_claims={
                "login": user.login
            }
        ),
        "jwt_refresh": create_refresh_token(
            identity=user.id,
            additional_claims={
                "login": user.login
            }
        ),
        "user": user.to_json()
    }, 200


@app.route("/courses")
@jwt_required(optional=True)
def get_courses():
    sess = create_session()
    courses = sess.query(Course).all()
    if get_jwt() and get_current_user().is_admin:
        return {"courses": [course.to_json() for course in courses]}
    else:
        return {"courses": [course.to_json()
                            for course in courses if course.is_public]}


@app.route("/courses/attend/<course_id>")
@jwt_required()
def attend(course_id):
    sess = create_session()

    user = get_current_user()
    course = sess.get(Course, course_id)

    if not course:
        return {"status": "Not found"}, 404

    if not course.is_public and not user.is_admin:
        return {"status": "Forbidden"}, 403

    if course in user.courses:
        return {"status": "Already on course"}

    sess.add(Attendance(course.id, user.id))
    sess.commit()
    return {"status": "success"}


@app.route("/courses/<course_id>")
@jwt_required()
def get_course(course_id):
    sess = create_session()

    user = get_current_user()
    course = sess.get(Course, course_id)

    if not course:
        return {"status": "Course not found"}, 404

    if course not in user.courses and not user.is_admin:
        return {"status": "User not at course"}, 403

    return course.to_json()


@app.route("/courses/<course_id>/<lesson_id>")
@jwt_required()
def get_lesson(course_id, lesson_id):
    sess = create_session()
    user = get_current_user()
    course = sess.get(Course, course_id)
    lesson = sess.get(Lesson, lesson_id)

    if course not in user.courses and not user.is_admin:
        return {"status": "User not at course"}, 403

    if lesson not in course.lessons:
        return {"status": "Not found"}, 404

    return lesson.to_json()


@app.route("/courses/<course_id>/<lesson_id>/<task_id>")
@jwt_required()
def get_task(course_id, lesson_id, task_id):
    temp = check_task_request(course_id, lesson_id, task_id)
    if isinstance(temp, tuple):
        return temp
    return temp.to_json()


@app.route("/user/courses/<user_id>")
@jwt_required()
def get_courses_of_user(user_id):
    sess = create_session()
    user = get_current_user()
    requested_user = sess.get(User, user_id)

    if not requested_user:
        return {"status": "Not found"}, 404

    if user == requested_user:
        return {"courses": [course.to_json() for course in user.courses]}

    if user.is_admin:
        return {
            "courses": [course.to_json() for course in requested_user.courses]
        }

    return {"status": "Forbidden"}, 403


@app.route("/courses/<course_id>/<lesson_id>/<task_id>", methods=["POST"])
@jwt_required()
def post_task(course_id, lesson_id, task_id):
    sess = create_session()
    sess.expire_on_commit = False
    task = check_task_request(course_id, lesson_id, task_id)

    if isinstance(task, tuple):
        return task

    json = request.json

    if "code" not in json:
        return {"status": "Not all argument"}, 500

    user = get_current_user()
    solve = Solve(task.id, user.id, json["code"])
    sess.add(solve)
    sess.commit()

    def check_task():
        checker = TaskChecker(json["code"], task.time_limit,
                              task.lesson.course.language.path,
                              task.tests, solve.id)
        thread = checker.run(sess)
        yield '{"verdict": '
        while thread.is_alive():
            yield ""
        yield f'"{checker.verdict}", "time": {checker.time_interval}' + "}"

    return Response(check_task(), mimetype="text/json")


@app.route("/refresh")
@jwt_required(refresh=True)
def refresh():
    current_user = get_jwt_identity()
    access_token = create_access_token(identity=current_user)
    return {'jwt_access': access_token}


if __name__ == "__main__":
    global_init(db_password, db_username, db_address, db_name)
    app.run(threaded=True)
