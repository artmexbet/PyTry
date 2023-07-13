import json

from flask import Flask, request, Response, jsonify, session
from flask_cors import CORS
from flask_jwt_extended import JWTManager, get_jwt
from flask_jwt_extended import (create_access_token, create_refresh_token,
                                jwt_required, get_jwt_identity,
                                get_current_user, decode_token)
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
app.config["CORS_SUPPORTS_CREDENTIALS"] = True
CORS(app, supports_credentials=True)
app.config["JWT_SECRET_KEY"] = "SECRET_KEY"
app.config["SECRET_KEY"] = "LONG_LONG_KEY"
jwt_manager = JWTManager(app)


@jwt_manager.user_lookup_loader
def take_user(header_data, payload_data) -> User:
    # print(header_data, payload_data)
    # sess = create_session()
    user = g_sess.get(User, payload_data["sub"])
    return user


def check_task_request(course_id, lesson_id, task_id, user):
    sess = create_session()

    # user = get_current_user()
    course = sess.get(Course, course_id)
    lesson = sess.get(Lesson, lesson_id)
    task = sess.get(Task, task_id)

    if course not in user.courses and not user.check_perm("/c"):
        return {"status": "User not at course"}, 403

    if lesson not in course.lessons:
        return {"status": "Not found"}, 404

    if task not in lesson.tasks:
        return {"status": "Not found"}, 404

    return task


def prepare_starting():
    sess = create_session()

    user_role = sess.query(Role).filter(Role.title == "user").first()
    if not user_role:
        sess.add(Role("user", "/Ca /Ua"))
        sess.commit()


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
                email=json["email"],
                role_id=sess.query(Role).filter(Role.title == "user").first().id)
    user.generate_hash_password(json["password"])

    sess.add(user)
    sess.commit()

    refresh_token = create_refresh_token(identity=user.id, additional_claims={"login": user.login})

    return {
        "status": "success",
        "jwt_access": create_access_token(identity=user.id,
                                          additional_claims={
                                              "login": user.login
                                          }),
        "jwt_refresh": refresh_token,
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

    refresh_token = create_refresh_token(identity=user.id, additional_claims={"login": user.login})

    return {
        "status": "success",
        "jwt_access": create_access_token(
            identity=user.id,
            additional_claims={
                "login": user.login
            }
        ),
        "jwt_refresh": refresh_token,
        "user": user.to_json()
    }, 200


@app.route("/courses")
@jwt_required(optional=True)
def get_courses():
    sess = create_session()
    courses = sess.query(Course).all()
    if get_jwt():
        user = get_current_user()
        if user.check_perm("/c"):
            return {"courses": [course.to_json() for course in courses]}
    return {"courses": [course.to_json()
                        for course in courses if course.is_public]}


@app.route("/courses/attend/<course_id>")
@jwt_required()
def attend(course_id):
    sess = create_session()
    sess.expire_on_commit = False

    user = get_current_user()
    course = sess.get(Course, course_id)

    if not course:
        return {"status": "Not found"}, 404

    if not course.is_public and not user.check_perm("/c"):
        return {"status": "Forbidden"}, 403

    if user.check_course(course) or course.check_user(user):
        return {"status": "Already on course"}

    sess.add(Attendance(course.id, user.id))
    sess.commit()
    return {"status": "success"}


@app.route("/courses/<course_id>")
@jwt_required()
def get_course(course_id):
    sess = create_session()
    sess.expire_on_commit = False

    user = get_current_user()
    course = sess.get(Course, course_id)

    if not course:
        return {"status": "Course not found"}, 404

    resp = course.to_json()
    resp["at_course"] = True

    attendance = sess.query(Attendance).filter(Attendance.user_id == user.id, Attendance.course_id == course.id).first()
    if not attendance and user.check_perm("/c"):
        resp["at_course"] = False
    elif not attendance:
        resp["at_course"] = False
        resp.pop("lessons")

    return resp


@app.route("/lessons/<lesson_id>")
@jwt_required()
def get_lesson(lesson_id):
    sess = create_session()
    user = get_current_user()
    lesson = sess.get(Lesson, lesson_id)

    if not lesson:
        return {"status": "Not found"}, 404

    if lesson.course not in user.courses and not user.check_perm("/c"):
        return {"status": "User not at course"}, 403

    return lesson.to_json()


@app.route("/tasks/<task_id>")
@jwt_required()
def get_task(task_id):
    user = get_current_user()

    sess = create_session()
    task = sess.get(Task, task_id)

    if not task:
        return {"status": "Task not found"}, 404

    if task.lesson.course not in user.courses and not user.check_perm("/c"):
        return {"status": "Forbidden"}, 403

    return task.to_json()


@app.route("/user/courses/<user_id>")
@jwt_required()
def get_courses_of_user(user_id):
    sess = create_session()
    user = get_current_user()
    requested_user = sess.get(User, user_id)

    if not requested_user:
        return {"status": "Not found"}, 404

    if user.id == requested_user.id:
        return {"courses": [course.to_json() for course in user.courses]}

    if user.check_perm("/u"):
        return {
            "courses": [course.to_json() for course in requested_user.courses]
        }

    return {"status": "Forbidden"}, 403


@app.route("/tasks/<task_id>", methods=["POST"])
@jwt_required()
def post_task(task_id):
    sess = create_session()
    sess.expire_on_commit = False
    user = get_current_user()

    task = sess.get(Task, task_id)

    if not task:
        return {"status": "Task is not found"}, 404

    if task.lesson.course not in user.courses and not user.check_perm("/c"):
        return {"status": "Forbidden"}, 403

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

    # while thread.is_alive():
    #     sleep(0.5)

    return {"status": "checking", "solve_id": solve.id}


@app.route("/solves/<solve_id>")
@jwt_required()
def check_solve_status(solve_id):
    user = get_current_user()

    sess = create_session()

    solve = sess.get(Solve, solve_id)

    if not solve:
        return {"status": "Solve not found"}, 404

    if solve.user.id != user.id and not user.check_perm("/C"):
        return {"status": "Forbidden"}, 403

    if solve.verdict == "Check":
        return {"status": "Checking", "is_checked": False}

    info = solve.to_json()
    info["is_checked"] = True

    return info


@app.route("/tasks/<task_id>/solves")
@jwt_required()
def get_task_solves(task_id):
    user = get_current_user()

    sess = create_session()
    task = sess.get(Task, task_id)

    if not task:
        return {"status": "Not found"}, 404

    return {"solves": [solve.to_json() for solve in task.solves if solve.user_id == user.id]}


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

    if user.check_perm("/U") and user != user_:
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

    sess = create_session()
    course = sess.get(Course, course_id)

    if not course:
        return {"status": "Not found"}, 404

    if user != course.author or not user.check_perm("/Ca"):
        return {"status": "Forbidden"}, 403

    sess.delete(course)
    sess.commit()
    return {"status": "success"}


@app.route("/lessons/<lesson_id>", methods=["DELETE"])
@jwt_required()
def delete_lesson(lesson_id):
    user = get_current_user()

    sess = create_session()
    lesson = sess.get(Lesson, lesson_id)

    if not lesson:
        return {"status": "Not found"}, 404

    if user != lesson.course.author or not user.check_perm("/Ca"):
        return {"status": "Forbidden"}, 403

    sess.delete(lesson)
    sess.commit()
    return {"status": "success"}


@app.route("/tasks/<task_id>", methods=["DELETE"])
@jwt_required()
def delete_task(task_id):
    user = get_current_user()

    sess = create_session()
    task = sess.get(Task, task_id)

    if not task:
        return {"status": "Not found"}, 404

    if user != task.lesson.course.author or not user.check_perm("/Ca"):
        return {"status": "Forbidden"}, 403

    sess.delete(task)
    sess.commit()
    return {"status": "success"}


@app.route("/links/<link_id>",
           methods=["DELETE"])
@jwt_required()
def delete_link(link_id):
    user = get_current_user()

    sess = create_session()
    link = sess.get(Link, link_id)

    if not link:
        return {"status": "Not found"}, 404

    if user != link.lesson.course.author or not user.check_perm("/Ca"):
        return {"status": "Forbidden"}, 403

    sess.delete(link)
    sess.commit()
    return {"status": "success"}


@app.route("/users/<user_id>", methods=["DELETE"])
@jwt_required()
def delete_user(user_id):
    user = get_current_user()

    sess = create_session()
    user_ = sess.get(User, user_id)

    if not user.check_perm("/Ua"):
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

    if not user.check_perm("/Ca"):
        return {"status": "Forbidden"}, 403

    sess = create_session()

    language = sess.get(Language, language_id)

    if not language:
        return {"status": "Not found"}, 404

    sess.delete(language)
    sess.commit()
    return {"status": "success"}


@app.route("/languages")
@jwt_required()
def get_languages():
    user = get_current_user()

    if not user.check_perm("/C"):
        return {"status": "Forbidden"}, 403

    sess = create_session()

    return {"languages": [language.to_json() for language in sess.query(Language).all()]}


@app.route("/refresh")
@jwt_required(refresh=True)
def refresh():
    # refresh_jwt = session.get("jwt_refresh", None)

    # if refresh_jwt is None:
    #     return {"status": "Not authorized"}, 401

    # info = decode_token(refresh_jwt)

    current_user = get_jwt_identity()
    access_token = create_access_token(identity=current_user)
    return {'jwt_access': access_token}


@app.route("/languages", methods=["POST"])
@jwt_required()
def add_language():
    user = get_current_user()

    if not user.check_perm("/Ca"):
        return {"status": "Forbidden"}, 403

    form = request.json

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


@app.route("/courses", methods=["POST"])
@jwt_required()
def add_course():
    user = get_current_user()

    if not user.check_perm("/C"):
        return {"status": "Forbidden"}, 403

    form = request.form

    if any([i not in form for i in ["name", "description", "language_id", "is_public"]]):
        return {"status": "Not all arguments"}, 400

    files = request.files

    if "pic" not in files:
        return {"status": "Error! You have to sent pic"}, 400

    name = form["name"]
    description = form["description"]
    language_id = form["language_id"]
    is_public = bool(form["is_public"])

    sess = create_session()

    language = sess.get(Language, language_id)
    if not language:
        return {"status": "Language not found"}, 404

    course = Course(name, description, UUID(language_id), is_public)
    course.author_id = user.id

    sess.add(course)
    sess.commit()

    pic = f"static/{course.id}.{files['pic'].filename.split('.')[-1]}"
    files["pic"].save(pic)
    course.pic = pic
    sess.commit()

    return {"status": "success", "course": course.to_json()}


@app.route("/lessons", methods=["POST"])
@jwt_required()
def add_lesson():
    user = get_current_user()

    if not user.check_perm("/C"):
        return {"status": "Forbidden"}, 403

    form = request.json

    if any([i not in form for i in ["name", "description", "course_id"]]):
        return {"status": "Not all arguments"}, 400

    name = form["name"]
    description = form["description"]
    course_id = form["course_id"]
    links = form.get("links", [])

    sess = create_session()

    course = sess.get(Course, course_id)
    if not course:
        return {"status": "Course not found"}, 404

    if course.author.id != user.id:
        return {"status": "Forbidden"}, 403

    lessons = sess.query(Lesson).filter(Lesson.course_id == course.id).order_by(Lesson.order).all()

    if not lessons:
        lesson = Lesson(name, description, UUID(course_id), 0)
    else:
        lesson = Lesson(name, description, UUID(course_id), lessons[-1].order + 1)

    sess.add(lesson)
    sess.commit()

    for link in links:
        obj = Link(link["title"], link["link"], lesson.id)
        lesson.links.append(obj)

    sess.commit()

    return {"status": "success", "lesson": lesson.to_json()}


@app.route("/tasks", methods=["POST"])
@jwt_required()
def add_task():
    sess = create_session()
    sess.expire_on_commit = False
    user = get_current_user()

    form = request.form

    lesson_id = form.get("lesson_id", "")
    lesson = sess.get(Lesson, lesson_id)

    if not lesson:
        return {"status": "Lesson not found"}, 404

    course = sess.get(Course, lesson.course_id)

    if not user.check_perm("/Ca") and course.author_id != user.id:
        return {"status": "Forbidden: haven't permissions"}, 403

    required_params = ["name", "task_condition", "tests", "time_limit"]

    if any([i not in form for i in required_params]):
        return {"status": "Not all arguments"}, 400

    tasks = sess.query(Task).filter(Task.lesson_id == lesson_id).order_by(Task.order).all()

    if not tasks:
        task = Task(form["name"], form["task_condition"],
                    json.loads(form["tests"]), UUID(form["lesson_id"]), 0)
    else:
        task = Task(form["name"], form["task_condition"],
                    json.loads(form["tests"]), UUID(form["lesson_id"]), tasks[-1].order + 1)

    sess.add(task)
    sess.commit()

    return {"status": "success", "task": task.to_json()}


@app.route("/auth")
@jwt_required()
def get_user_info():
    user = get_current_user()

    user_info = user.to_json()
    user_info.pop("courses")

    return {"info": user_info}


@app.route("/courses", methods=["UPDATE"])
@jwt_required()
def update_courses():
    """
    Нужно, чтобы пришёл хотя бы один изменённый параметр
    """
    allowed_parameters = ["name", "description", "pic", "language_id"]

    user = get_current_user()

    if not user.check_perm("/C"):
        return {"status": "Forbidden"}, 403

    form = request.json

    if "id" not in form:
        return {"status": "Error: you should send id of course that you want to edit"}, 400

    sess = create_session()

    course = sess.get(Course, form.pop("id"))

    if not course:
        return {"status": "Course not found"}, 404

    if not any([i in form for i in allowed_parameters]):
        return {"status": f"Canceled: You should send some parameter from {allowed_parameters}"}, 400

    attributes = dir(course)
    for key in form:
        if key not in attributes:
            return {"status": "Canceled: You sent parameter which is not contains in Course class"}, 400

    for key, value in form.items():
        course.__setattr__(key, value)

    return {"status": "ok"}


if __name__ == "__main__":
    global_init(db_password, db_username, db_address, db_name)
    prepare_starting()
    g_sess = create_session()
    g_sess.expire_on_commit = False
    app.run(threaded=True, debug=True, host="0.0.0.0", port=5000)
