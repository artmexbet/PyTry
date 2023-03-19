from sqlalchemy import Column, orm, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, TEXT, DATE, JSON
from .database import Base
import uuid


class Language(Base):
    __tablename__ = "languages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(TEXT, nullable=False)
    path = Column(TEXT, nullable=False)

    courses = orm.relationship("Course", back_populates="language")


class Course(Base):
    __tablename__ = "courses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(TEXT, nullable=False)
    description = Column(TEXT, nullable=False)
    pic = Column(TEXT)  # Путь до картинки
    language_id = Column(UUID(as_uuid=True), ForeignKey("languages.id"))

    language = orm.relationship("Language")
    lessons = orm.relationship("Lesson", back_populates="course")
    users = orm.relationship("User", secondary="users_to_courses",
                             backref="users")


class Lesson(Base):
    __tablename__ = "lessons"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.id"))
    name = Column(TEXT)
    description = Column(TEXT)

    course = orm.relationship("Course")
    links = orm.relationship("Link", back_populates="lesson")
    tasks = orm.relationship("Task", back_populates="lesson")


class Link(Base):
    __tablename__ = "useful_links"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lesson_id = Column(UUID(as_uuid=True), ForeignKey("lessons.id"))
    link = Column(TEXT)

    lesson = orm.relationship("Lesson")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lesson_id = Column(UUID(as_uuid=True), ForeignKey("lessons.id"))
    name = Column(TEXT)
    task_condition = Column(TEXT)
    tests = Column(JSON)

    lesson = orm.relationship("Lesson")
    solves = orm.relationship("Solve", back_populates="task")


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(TEXT, nullable=False)
    login = Column(TEXT, nullable=False)
    email = Column(TEXT, nullable=False)
    password = Column(TEXT, nullable=False)

    courses = orm.relationship("Course", secondary="users_to_courses",
                               backref="courses")
    solves = orm.relationship("Solve", back_populates="user")


class Attendance(Base):
    __tablename__ = "users_to_courses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.id"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    date = Column(DATE)


class Solve(Base):
    __tablename__ = "solves"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    verdict = Column(TEXT)
    code = Column(TEXT)

    task = orm.relationship("Task")
    user = orm.relationship("User")
