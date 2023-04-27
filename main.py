from flask import Flask, request, Response, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager, get_jwt
from flask_jwt_extended import (create_access_token, create_refresh_token,
                                jwt_required, get_jwt_identity,
                                get_current_user)
from task_checking import TaskChecker
from data.__all_models import *
from time import sleep
from uuid import UUID

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
    # sess = create_session()
    user = sess.get(User, payload_data["sub"])
    return user


def check_task_request(course_id, lesson_id, task_id, user):
    sess = create_session()

    # user = get_current_user()
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
        return {
            "status":
                f"You have to send {', '.join(['login', 'password', 'name', 'email'])}"
        }, 400

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
        return {
            "status": "You have to send 'password' and 'email' or 'login'"
        }, 400

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
    user = get_current_user()
    temp = check_task_request(course_id, lesson_id, task_id, user)
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
    user = get_current_user()
    task = check_task_request(course_id, lesson_id, task_id, user)

    if isinstance(task, tuple):
        return task

    json = request.json

    if "code" not in json:
        return {"status": "You have to send 'code'"}, 400

    solve = Solve(task.id, user.id, json["code"])
    sess.add(solve)
    sess.commit()

    language = task.lesson.course.language

    checker = TaskChecker(json["code"], task.time_limit,
                          language.path,
                          task.tests, language.options, solve.id)
    thread = checker.run(sess)

    while thread.is_alive():
        sleep(0.5)

    return jsonify({"verdict": checker.verdict,
                    "time": checker.time_interval})


@app.route("/users/<user_id>/password", methods=["UPDATE"])
@jwt_required()
def update_password(user_id):
    sess = create_session()
    user = get_current_user()
    user_ = sess.get(User, user_id)

    if not user_:
        return {"status": "Not found"}, 404

    json = request.json

    if "new_password" not in json:
        return {"status": "You have to send 'new_password'"}, 400

    if user.is_admin and user != user_:
        user_.generate_hash_password(json["new_password"])
        sess.commit()
        return {"status": "OK"}

    if user == user_:
        if "old_password" not in json:
            return {"status": "You have to send 'old_password'"}

        if not user.check_password(json["old_password"]):
            return {"status": "Old passwords doesn't match"}, 406

        user.generate_hash_password(json["new_password"])
        sess.commit()
        return {"status": "success"}
    return {"status": "Forbidden"}, 403


@app.route("/courses/<course_id>", methods=["DELETE"])
@jwt_required()
def delete_course(course_id):
    user = get_current_user()

    if not user.is_admin:
        return {"status": "Forbidden"}, 403

    sess = create_session()
    course = sess.get(Course, course_id)

    if not course:
        return {"status": "Not found"}, 404

    sess.delete(course)
    sess.commit()
    return {"status": "success"}


@app.route("/courses/<course_id>/<lesson_id>", methods=["DELETE"])
@jwt_required()
def delete_lesson(course_id, lesson_id):
    user = get_current_user()

    if not user.is_admin:
        return {"status": "Forbidden"}, 403

    sess = create_session()
    course = sess.get(Course, course_id)

    if not course:
        return {"status": "Not found"}, 404

    lesson = sess.get(Lesson, lesson_id)

    if not lesson:
        return {"status": "Not found"}, 404

    if lesson not in course.lessons:
        return {"status": "Lesson is not bounded to this course"}, 400

    sess.delete(lesson)
    sess.commit()
    return {"status": "success"}


@app.route("/courses/<course_id>/<lesson_id>/<task_id>", methods=["DELETE"])
@jwt_required()
def delete_task(course_id, lesson_id, task_id):
    user = get_current_user()

    if not user.is_admin:
        return {"status": "Forbidden"}, 403

    sess = create_session()
    course = sess.get(Course, course_id)

    if not course:
        return {"status": "Not found"}, 404

    lesson = sess.get(Lesson, lesson_id)

    if not lesson:
        return {"status": "Not found"}, 404

    if lesson not in course.lessons:
        return {"status": "Lesson is not bounded to this course"}, 400

    task = sess.get(Task, task_id)

    if not task:
        return {"status": "Not found"}, 404

    if task not in lesson.tasks:
        return {"status": "Task is not bounded to this lesson"}, 400

    sess.delete(task)
    sess.commit()
    return {"status": "success"}


@app.route("/courses/<course_id>/<lesson_id>/<link_id>",
           methods=["DELETE"])
@jwt_required()
def delete_link(course_id, lesson_id, link_id):
    user = get_current_user()

    if not user.is_admin:
        return {"status": "Forbidden"}, 403

    sess = create_session()
    course = sess.get(Course, course_id)

    if not course:
        return {"status": "Not found"}, 404

    lesson = sess.get(Lesson, lesson_id)

    if not lesson:
        return {"status": "Not found"}, 404

    if lesson not in course.lessons:
        return {"status": "Lesson is not bounded to this course"}, 400

    link = sess.get(Link, link_id)

    if not link:
        return {"status": "Not found"}, 404

    if link not in lesson.links:
        return {"status": "Link is not bounded to this lesson"}, 400

    sess.delete(link)
    sess.commit()
    return {"status": "success"}


@app.route("/users/<user_id>", methods=["DELETE"])
@jwt_required()
def delete_user(user_id):
    user = get_current_user()

    sess = create_session()
    user_ = sess.get(User, user_id)

    if not user.is_admin:
        return {"status": "Forbidden"}, 403

    if not user_:
        return {"status": "Not found"}, 404

    sess.delete(user_)
    sess.commit()
    return {"status": "success"}


@app.route("/languages/<language_id>", methods=["DELETE"])
@jwt_required()
def delete_languages(language_id):
    user = get_current_user()

    if not user.is_admin:
        return {"status": "Forbidden"}, 403

    sess = create_session()

    language = sess.get(Language, language_id)

    if not language:
        return {"status": "Not found"}, 404

    sess.delete(language)
    sess.commit()
    return {"status": "success"}


@app.route("/refresh")
@jwt_required(refresh=True)
def refresh():
    current_user = get_jwt_identity()
    access_token = create_access_token(identity=current_user)
    return {'jwt_access': access_token}


@app.route("/add/language", methods=["POST"])
@jwt_required()
def add_language():
    user = get_current_user()

    if not user.is_admin:
        return {"status": "Forbidden"}, 403

    form = request.form

    if any([i not in form for i in ["name", "path", "options"]]):
        return {"status": "Not all arguments"}, 400

    name = form["name"]
    path = form["path"]
    options = form["options"]

    sess = create_session()
    language = Language(name, path, options)
    sess.add(language)
    sess.commit()
    return {"status": "success", "language": language.to_json()}


@app.route("/add/courses", methods=["POST"])
@jwt_required()
def add_course():
    user = get_current_user()

    if not user.is_admin:
        return {"status": "Forbidden"}, 403

    form = request.form

    if any([i not in form for i in ["name", "description", "pic", "language_id", "is_public"]]):
        return {"status": "Not all arguments"}, 400

    name = form["name"]
    description = form["description"]
    pic = form["pic"]
    language_id = form["language_id"]
    is_public = bool(form["is_public"])

    sess = create_session()

    language = sess.get(Language, language_id)
    if not language:
        return {"status": "Language not found"}, 404

    course = Course(name, description, pic, UUID(language_id), is_public)

    sess.add(course)
    sess.commit()

    return {"status": "success", "course": course.to_json()}


@app.route("/add/lesson", methods=["POST"])
@jwt_required()
def add_lesson():
    user = get_current_user()

    if not user.is_admin:
        return {"status": "Forbidden"}, 403

    form = request.form

    if any([i not in form for i in ["name", "description", "course_id"]]):
        return {"status": "Not all arguments"}, 400

    name = form["name"]
    description = form["description"]
    course_id = form["course_id"]

    sess = create_session()

    course = sess.get(Course, course_id)
    if not course:
        return {"status": "Course not found"}, 404

    lesson = Lesson(name, description, UUID(course_id))

    sess.add(lesson)
    sess.commit()

    return {"status": "success", "lesson": lesson.to_json()}


if __name__ == "__main__":
    global_init(db_password, db_username, db_address, db_name)
    sess = create_session()
    app.run(threaded=True, debug=True, host="0.0.0.0", port=5000)
