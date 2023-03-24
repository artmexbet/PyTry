import time
import uuid
from subprocess import Popen, PIPE, TimeoutExpired, run
from threading import Thread
from sqlalchemy.orm import Session
import os

from data.__all_models import Solve


class TaskChecker:
    def __init__(self,
                 code: str,
                 timeout: int,
                 cmd: str,
                 tests: dict,
                 options: str,
                 solve_uuid: uuid.UUID = ""):
        """
        :param code: код
        :param timeout: время на выполнение
        :param cmd: путь до компилятора
        :param tests: {"tests": [{"input": ..., "output": ...}, ...]}
        :param options: опции скрипта запуска
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
        self.time_interval = None
        self.options = options

    def __call__(self, session: Session, *args, **kwargs):
        solve = session.get(Solve, self.id)

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
        is_ok = True

        for i, test in enumerate(self.tests, 1):
            test_start_time = time.time()

            out = open(path_to_out, "w")
            err = open(path_to_err, "w")

            is_timeout_expired = False
            # Открытие потока выполнения программы
            with Popen(
                    f'{self.path} {self.options} "{self.path_to_file}"',
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
                self.time_interval = round(
                    (time.time() - test_start_time) * 100
                )
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
                is_ok = False
                break

            if error:
                self.verdict = TaskChecker.format_errors(error)
                self.verdict = self.verdict.replace(str(self.id), "solution")
                is_ok = False
                break

            if output.strip() != test["output"]:
                self.verdict = f"""Error:
                In test {i}.
                {TaskChecker.get_different_string(
                    test['output'], output.strip()
                )}"""
                is_ok = False
                break
        if is_ok:
            self.verdict = "OK"
        solve.verdict = self.verdict
        solve.time = self.time_interval
        session.commit()
        os.remove(self.path_to_file)
        return self.verdict

    @staticmethod
    def get_different_string(expectation: str, output: str) -> str:
        splited_exp = expectation.split("\n")
        splited_out = output.split("\n")

        if len(splited_exp) != len(splited_out):
            return f"Expected {len(splited_exp)}," \
                   f" got {len(splited_out)} instead."

        for i, e in enumerate(splited_exp):
            if e != splited_out[i]:
                return f"Expected {e} in line {i}," \
                       f" got {splited_out[i]} instead."
        return "Output doesn't match with example"

    @staticmethod
    def format_errors(error_text: str) -> str:
        return error_text.replace(os.getcwd(), "*")

    def run(self, session: Session) -> Thread:
        thread = Thread(target=self, args=(session,), name=str(self.id))
        thread.start()
        return thread
