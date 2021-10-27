import time
import pandas as pd
from PyQt5.QtCore import pyqtSignal, QObject, QRunnable
from ...utils import run_routine, curr_ts_to_str


class BadgerRoutineSignals(QObject):
    finished = pyqtSignal()
    progress = pyqtSignal(list, list)
    error = pyqtSignal(Exception)


class BadgerRoutineRunner(QRunnable):

    def __init__(self, routine, save, verbose=2, use_full_ts=False):
        super().__init__()

        # Signals should belong to instance rather than class
        # Since there could be multiple runners runing in parallel
        self.signals = BadgerRoutineSignals()

        self.routine = routine
        var_names = [next(iter(d)) for d in routine['config']['variables']]
        obj_names = [next(iter(d)) for d in routine['config']['objectives']]
        self.data = pd.DataFrame(None, columns=['timestamp'] + obj_names + var_names)
        self.save = save
        self.verbose = verbose
        self.use_full_ts = use_full_ts

        self.is_paused = False
        self.is_killed = False

    def run(self):
        error = None
        try:
            run_routine(self.routine, True, self.save, self.verbose,
                        self.before_evaluate, self.after_evaluate)
        except Exception as e:
            error = e

        self.signals.finished.emit()
        if error:
            self.signals.error.emit(error)

    def before_evaluate(self, vars):
        # vars: ndarray
        while self.is_paused:
            time.sleep(0)
            if self.is_killed:
                raise Exception('Optimization run has been terminated!')

        if self.is_killed:
            raise Exception('Optimization run has been terminated!')

    def after_evaluate(self, vars, obses):
        # vars: ndarray
        # obses: ndarray
        self.signals.progress.emit(list(vars), list(obses))

        # Append solution to data
        fmt = 'lcls-log-full' if self.use_full_ts else 'lcls-log'
        solution = [curr_ts_to_str(fmt)] + list(obses) + list(vars)
        self.data = self.data.append(pd.Series(solution, index=self.data.columns), ignore_index=True)

        # take a break to let the outside signal to change the status
        time.sleep(0.1)

    def ctrl_routine(self, pause):
        self.is_paused = pause

    def stop_routine(self):
        self.is_killed = True
