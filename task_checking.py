from subprocess import run
from threading import Thread
from sqlalchemy.orm import Session


class TaskChecker:
    def __init__(self,
                 filename: str,
                 timeout: int,
                 path: str,
                 tests: dict):
        """
        :param filename: имя исполняемого файла
        :param timeout: время на выполнение
        :param path: путь до компилятора
        """
        self.filename = filename
        self.timeout = timeout
        self.path = path
        self.tests = []

    def __call__(self, *args, **kwargs):
        proc = run(f"{self.path} {self.filename}", stdin=)
        # TODO: Дописать работу с stdin и stdout

    def run(self, session: Session):
        thread = Thread(target=self)
