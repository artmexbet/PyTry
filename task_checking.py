import uuid
from subprocess import Popen, PIPE, TimeoutExpired
from threading import Thread
from sqlalchemy.orm import Session
import os


class TaskChecker:
    def __init__(self,
                 code: str,
                 timeout: int,
                 cmd: str,
                 tests: dict,
                 solve_uuid: uuid.UUID = ""):
        """
        :param code: код
        :param timeout: время на выполнение
        :param cmd: путь до компилятора
        :param tests: {"tests": [{"input": ..., "output": ...}, ...]}
        :param solve_uuid: ID решения для создания потока
        """
        test_path = os.path.join(os.getcwd(), "tests")
        if not os.path.exists(test_path):
            os.mkdir(test_path)

        self.path_to_file = os.path.join(os.getcwd(),
                                         "tests",
                                         f"{solve_uuid}.py")
        with open(self.path_to_file, "w") as f:
            f.write(code)

        # self.filename = code
        self.timeout = timeout
        self.path = cmd
        self.tests = tests["tests"]
        self.id = solve_uuid
        self.verdict = "Check"

    def __call__(self, session: Session, *args, **kwargs):

        # Открытие файлов для сохранения ошибок и вывода
        path_to_out = os.path.join(
            os.getcwd(),
            "tests",
            f"{str(self.id)}_out"
        )

        path_to_err = os.path.join(
            os.getcwd(),
            "tests",
            f"{str(self.id)}_err"
        )

        # Проверка тестов

        for i, test in enumerate(self.tests, 1):

            out = open(path_to_out, "w")
            err = open(path_to_err, "w")

            is_timeout_expired = False
            # Открытие потока выполнения программы
            with Popen(
                    f'{self.path} "{self.path_to_file}"',
                    stdin=PIPE,
                    stdout=out,
                    stderr=err,
                    encoding="utf8",
                    text=True
            ) as process:
                try:
                    stdout, stderr = process.communicate(test["input"],
                                                         self.timeout)
                except TimeoutExpired as te:
                    is_timeout_expired = True

            out.close()
            err.close()

            with open(path_to_err) as err:
                error = err.read()

            with open(path_to_out) as out:
                output = out.read()

            os.remove(path_to_out)
            os.remove(path_to_err)

            if is_timeout_expired:
                self.verdict = f"Time limit exceeded on test {i}"
                os.remove(self.path_to_file)
                return self.verdict

            if error:
                self.verdict = error
                os.remove(self.path_to_file)
                return error

            if output.strip() != test["output"]:
                self.verdict = f"error\nIn test {i}.\n"
                os.remove(self.path_to_file)
                return "error"
        self.verdict = "OK"
        os.remove(self.path_to_file)
        return "OK"

    def run(self, session: Session) -> Thread:
        thread = Thread(target=self, args=(session,), name=str(self.id))
        thread.start()
        return thread
