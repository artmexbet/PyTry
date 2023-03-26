from sqlalchemy import Column, orm, ForeignKey
from sqlalchemy.dialects.postgresql import (UUID, TEXT, DATE,
                                            JSON, BOOLEAN, BIGINT)
from werkzeug.security import generate_password_hash, check_password_hash
from .database import Base
import datetime
import uuid


class Language(Base):
    __tablename__ = "languages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(TEXT, nullable=False)
    path = Column(TEXT, nullable=False)
    options = Column(TEXT)

    courses = orm.relationship("Course",
                               back_populates="language",
                               cascade="all, delete")

    def __init__(self,
                 name: str,
                 path: str,
                 options: str = ""):
        """
        :param name: Название языка программирования
        :param path: путь до сервера, на котором выполняется тестирование
        :param options: опции скрипта запуска
        """
        self.name = name
        self.path = path
        self.options = options

    def to_json(self) -> dict:
        return {
            "id": self.id,
            "name": self.name
        }


class Course(Base):
    __tablename__ = "courses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(TEXT, nullable=False)
    description = Column(TEXT, nullable=False)
    pic = Column(TEXT)  # Путь до картинки
    language_id = Column(UUID(as_uuid=True), ForeignKey("languages.id"))
    is_public = Column(BOOLEAN, default=True, nullable=False)

    language = orm.relationship("Language")
    lessons = orm.relationship("Lesson",
                               back_populates="course",
                               cascade="all, delete")
    users = orm.relationship("User", secondary="users_to_courses",
                             backref="users")

    def __init__(self, name: str,
                 description: str,
                 pic: str,
                 language_id: uuid.UUID,
                 is_public=True):
        """
        :param name: Название курса
        :param description: Описание курса
        :param pic: Путь до картинки в папке static
        :param language_id: UUID языка программирования,
         на котором решается курс
        :param is_public: True если курс публичный
        """
        self.name = name
        self.description = description
        self.pic = pic
        self.language_id = language_id
        self.is_public = is_public

    def __repr__(self):
        return f"<Course '{self.name}'>"

    def to_json(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "pic": self.pic,
            "id": self.id,
            "language": self.language.to_json(),
            "is_public": self.is_public,
            "lessons": [lesson.to_json() for lesson in self.lessons]
        }


class Lesson(Base):
    __tablename__ = "lessons"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.id"))
    name = Column(TEXT)
    description = Column(TEXT)

    course = orm.relationship("Course")
    links = orm.relationship("Link",
                             back_populates="lesson",
                             cascade="all, delete")
    tasks = orm.relationship("Task",
                             back_populates="lesson",
                             cascade="all, delete")

    def __init__(self, name: str, description: str, course_id: uuid.UUID):
        """
        :param name: Название урока
        :param description: Описание урока
        :param course_id: UUID курса, к которому привязан урок
        """
        self.name = name
        self.description = description
        self.course_id = course_id

    def to_json(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "tasks": [task.to_json() for task in self.tasks],
            "links": [link.to_json() for link in self.links]
        }


class Link(Base):
    __tablename__ = "useful_links"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lesson_id = Column(UUID(as_uuid=True), ForeignKey("lessons.id"))
    title = Column(TEXT)
    link = Column(TEXT)

    lesson = orm.relationship("Lesson")

    def __init__(self, title: str, link: str, lesson_id: uuid.UUID):
        """
        :param title: название ссылки
        :param link: ссылка на ресурс
        :param lesson_id: UUID урока, к которому привязана ссылка
        """
        self.link = link
        self.lesson_id = lesson_id
        self.title = title

    def to_json(self) -> dict:
        return {
            "link": self.link,
            "title": self.title,
        }


class Task(Base):
    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lesson_id = Column(UUID(as_uuid=True), ForeignKey("lessons.id"))
    name = Column(TEXT)
    task_condition = Column(TEXT)
    tests = Column(JSON)
    time_limit = Column(BIGINT)

    lesson = orm.relationship("Lesson")
    solves = orm.relationship("Solve",
                              back_populates="task",
                              cascade="all, delete")

    def __init__(self, name: str,
                 task_condition: str,
                 tests: dict,
                 lesson_id: uuid.UUID,
                 time_limit: int = 1):
        """
        :param name: Название задания
        :param task_condition: Условие задания
        :param tests: JSON с тестами
        :param lesson_id: UUID урока, к которому привязано задание
        """
        self.name = name
        self.task_condition = task_condition
        self.tests = tests
        self.lesson_id = lesson_id
        self.time_limit = time_limit

    def to_json(self) -> dict:
        return {
            "name": self.name,
            "task_condition": self.task_condition,
            "time_limit": self.time_limit,
            "tests": self.tests["tests"][:2]
        }


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(TEXT, nullable=False)
    login = Column(TEXT, nullable=False, unique=True)
    email = Column(TEXT, nullable=False)
    password = Column(TEXT, nullable=False)
    is_admin = Column(BOOLEAN, default=False)

    courses = orm.relationship("Course", secondary="users_to_courses",
                               backref="courses")
    solves = orm.relationship("Solve",
                              back_populates="user",
                              cascade="all, delete")

    def __init__(self, name: str, login: str, email: str, is_admin: bool=False):
        """
        :param name: Имя пользователя
        :param login: Логин пользователя
        :param email: Почта пользователя
        :param is_admin: True если пользователь - админ
        """
        self.name = name
        self.login = login
        self.email = email
        self.is_admin = is_admin

    def generate_hash_password(self, password: str):
        self.password = generate_password_hash(password)

    def check_password(self, password: str):
        return check_password_hash(self.password, password)

    def to_json(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "login": self.login,
            "email": self.email,
            "is_admin": self.is_admin,
            "courses": [course.to_json() for course in self.courses]
        }

    def get_solves(self) -> dict:
        return {"solves": [solve.to_json() for solve in self.solves]}


class Attendance(Base):
    __tablename__ = "users_to_courses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.id"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    date = Column(DATE, default=datetime.datetime.now)

    def __init__(self, course_id: uuid.UUID, user_id: uuid.UUID):
        """
        :param course_id: UUID курса, к которому прикрепляется пользователь
        :param user_id: UUID пользователя
        """
        self.course_id = course_id
        self.user_id = user_id


class Solve(Base):
    __tablename__ = "solves"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    verdict = Column(TEXT)
    code = Column(TEXT)
    time = Column(BIGINT)
    date = Column(DATE, default=datetime.datetime.now)

    task = orm.relationship("Task")
    user = orm.relationship("User")

    def __init__(self, task_id: uuid.UUID,
                 user_id: uuid.UUID,
                 code: str,
                 time: int = 0,
                 verdict: str = "Check"):
        """
        :param task_id: UUID задания
        :param user_id: UUID пользователя
        :param code: код, отправленный на проверку
        :param time: время выполнения кода
        :param verdict: результат выполнения кода
        """
        self.task_id = task_id
        self.user_id = user_id
        self.code = code
        self.verdict = verdict
        self.time = time

    def to_json(self) -> dict:
        return {
            "id": self.id,
            "task": self.task.to_json(),
            "user": self.user.to_json(),
            "time": self.time,
            "date": self.date
        }
