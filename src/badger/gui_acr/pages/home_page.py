import numpy as np
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from PyQt5.QtWidgets import QPushButton, QSplitter, QTextEdit, QShortcut
from PyQt5.QtWidgets import QListWidget, QListWidgetItem, QLabel
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QKeySequence
from ..components.search_bar import search_bar
from ..components.data_table import data_table, update_table, reset_table, add_row
from ..components.routine_item import routine_item, stylesheet_normal, stylesheet_selected
from ..components.history_navigator import HistoryNavigator
from ..components.run_monitor import BadgerOptMonitor
from ..components.routine_editor import BadgerRoutineEditor
from ..components.status_bar import BadgerStatusBar
from ...db import list_routine, load_routine, get_runs_by_routine, get_runs
from ...archive import load_run, delete_run
from ...utils import ystring, get_header


stylesheet = '''
QPushButton:hover:pressed
{
    background-color: #C7737B;
}
QPushButton:hover
{
    background-color: #BF616A;
}
QPushButton
{
    background-color: #A9444E;
}
'''

class BadgerHomePage(QWidget):
    def __init__(self):
        super().__init__()

        self.init_ui()
        self.config_logic()

        self.load_all_runs()

    def init_ui(self):
        # Set up the layout
        vbox = QVBoxLayout(self)
        vbox.setContentsMargins(0, 0, 0, 0)
        splitter = QSplitter(Qt.Horizontal)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        # splitter.setSizes([100, 200])
        vbox.addWidget(splitter, 1)

        # Routine panel
        self.panel_routine = panel_routine = QWidget()
        vbox_routine = QVBoxLayout(panel_routine)

        # Search bar
        panel_search = QWidget()
        hbox_search = QHBoxLayout(panel_search)
        hbox_search.setContentsMargins(0, 0, 0, 0)

        self.sbar = sbar = search_bar()
        sbar.setFixedHeight(36)
        f = sbar.font()
        f.setPixelSize(16)
        sbar.setFont(f)
        self.btn_new = btn_new = QPushButton('+')
        btn_new.setFixedSize(36, 36)
        btn_new.setFont(f)
        hbox_search.addWidget(sbar)
        hbox_search.addWidget(btn_new)
        vbox_routine.addWidget(panel_search)

        # Routine list
        self.routine_list = routine_list = QListWidget()
        routine_list.setAlternatingRowColors(True)
        routine_list.setSpacing(1)
        self.build_routine_list()
        self.prev_routine = None  # last selected routine
        vbox_routine.addWidget(routine_list)

        # Info panel
        panel_info = QWidget()
        vbox_info = QVBoxLayout(panel_info)

        panel_view = QWidget()
        vbox_view = QVBoxLayout(panel_view)
        vbox_view.setContentsMargins(0, 0, 0, 0)
        vbox_info.addWidget(panel_view)

        # History run nav
        self.history_nav_bar = history_nav_bar = QWidget()
        hbox_nav = QHBoxLayout(history_nav_bar)
        hbox_nav.setContentsMargins(0, 0, 0, 0)
        vbox_view.addWidget(history_nav_bar)

        label_nav = QLabel('History Run')
        self.cb_history = cb_history = HistoryNavigator()
        self.btn_prev = btn_prev = QPushButton('<')
        self.btn_next = btn_next = QPushButton('>')
        btn_prev.setFixedWidth(32)
        btn_next.setFixedWidth(32)
        btn_prev.setDisabled(True)
        btn_next.setDisabled(True)
        hbox_nav.addWidget(label_nav)
        hbox_nav.addWidget(cb_history, 1)
        hbox_nav.addWidget(btn_prev)
        hbox_nav.addWidget(btn_next)

        # Routine edit + run monitor + data table
        self.splitter_run = splitter_run = QSplitter(Qt.Vertical)
        splitter_run.setStretchFactor(0, 0)
        splitter_run.setStretchFactor(1, 1)
        splitter_run.setStretchFactor(2, 0)
        vbox_view.addWidget(splitter_run)

        # Run monitor
        self.run_view = run_view = QWidget()  # for consistent bg
        vbox_run_view = QVBoxLayout(run_view)
        vbox_run_view.setContentsMargins(0, 10, 0, 10)
        self.run_monitor = run_monitor = BadgerOptMonitor()
        vbox_run_view.addWidget(run_monitor)

        # Data table
        self.run_table = run_table = data_table()

        # Routine view
        self.routine_view = routine_view = QWidget()  # for consistent bg
        vbox_routine_view = QVBoxLayout(routine_view)
        vbox_routine_view.setContentsMargins(0, 0, 0, 10)
        self.routine_editor = routine_editor = BadgerRoutineEditor()
        vbox_routine_view.addWidget(routine_editor)

        splitter_run.addWidget(routine_view)
        splitter_run.addWidget(run_view)
        splitter_run.addWidget(run_table)
        splitter_run.setSizes([0, 1, 0])  # collapse routine/table by default

        # Action bar
        # action_bar = QWidget()
        # hbox_action = QHBoxLayout(action_bar)
        # hbox_action.setContentsMargins(0, 0, 0, 0)

        # cool_font = QFont()
        # cool_font.setWeight(QFont.DemiBold)
        # # cool_font.setPixelSize(16)

        # self.btn_del = btn_del = QPushButton('Delete')
        # btn_del.setFixedSize(64, 64)
        # btn_del.setFont(cool_font)
        # btn_del.setStyleSheet(stylesheet)
        # self.btn_edit = btn_edit = QPushButton('Edit')
        # btn_edit.setFixedSize(64, 64)
        # btn_edit.setFont(cool_font)
        # self.btn_run = btn_run = QPushButton('Run')
        # btn_run.setFixedSize(128, 64)
        # btn_run.setFont(cool_font)
        # hbox_action.addWidget(btn_del)
        # hbox_action.addStretch(1)
        # hbox_action.addWidget(btn_edit)
        # hbox_action.addWidget(btn_run)
        # vbox_info.addWidget(action_bar)

        # Add panels to splitter
        splitter.addWidget(panel_routine)
        splitter.addWidget(panel_info)

        self.status_bar = status_bar = BadgerStatusBar()
        status_bar.set_summary('Badger is ready!')
        vbox_view.addWidget(status_bar)

    def config_logic(self):
        self.colors = ['c', 'g', 'm', 'y', 'b', 'r', 'w']
        self.symbols = ['o', 't', 't1', 's', 'p', 'h', 'd']

        self.sbar.textChanged.connect(self.build_routine_list)
        self.routine_list.itemClicked.connect(self.select_routine)
        self.run_table.cellClicked.connect(self.solution_selected)
        self.run_table.itemSelectionChanged.connect(self.table_selection_changed)

        self.cb_history.currentIndexChanged.connect(self.go_run)
        self.btn_prev.clicked.connect(self.go_prev_run)
        self.btn_next.clicked.connect(self.go_next_run)

        self.run_monitor.sig_inspect.connect(self.inspect_solution)
        self.run_monitor.sig_lock.connect(self.toggle_lock)
        self.run_monitor.sig_new_run.connect(self.new_run)
        self.run_monitor.sig_run_name.connect(self.run_name)
        self.run_monitor.sig_progress.connect(self.progress)
        self.run_monitor.sig_del.connect(self.delete_run)

        # Assign shortcuts
        self.shortcut_go_search = QShortcut(QKeySequence('Ctrl+L'), self)
        self.shortcut_go_search.activated.connect(self.go_search)

    def go_search(self):
        self.sbar.setFocus()

    def load_all_runs(self):
        runs = get_runs()
        self.cb_history.updateItems(runs)

    def select_routine(self, item):
        if self.prev_routine:
            try:
                self.routine_list.itemWidget(self.prev_routine).setStyleSheet(stylesheet_normal)
            except:
                pass

            if self.prev_routine.routine == item.routine:  # click a routine again to deselect
                self.prev_routine = None
                self.current_routine = None
                self.load_all_runs()
                if not self.cb_history.count():
                    self.go_run(-1)  # sometimes we need to trigger this manually
                return

        self.prev_routine = item  # note that prev_routine is an item!

        routine, timestamp = load_routine(item.routine)
        self.current_routine = routine
        self.routine_editor.set_routine(routine)
        runs = get_runs_by_routine(routine['name'])
        self.cb_history.updateItems(runs)
        if not self.cb_history.count():
            self.go_run(-1)  # sometimes we need to trigger this manually

        if not runs:  # auto plot will not be triggered
            self.run_monitor.init_plots(routine)

        self.routine_list.itemWidget(item).setStyleSheet(stylesheet_selected)

    def build_routine_list(self, keyword=''):
        routines, timestamps = list_routine(keyword)

        try:
            selected_routine = self.prev_routine.routine
        except:
            selected_routine = None
        self.routine_list.clear()
        for i, routine in enumerate(routines):
            _item = routine_item(routine, timestamps[i])
            item = QListWidgetItem(self.routine_list)
            item.routine = routine  # dirty trick
            item.setSizeHint(_item.sizeHint())
            self.routine_list.addItem(item)
            self.routine_list.setItemWidget(item, _item)
            if routine == selected_routine:
                _item.setStyleSheet(stylesheet_selected)
                self.prev_routine = item

    def go_run(self, i):
        if self.cb_history.currentText() == 'Optimization in progress...':
            return

        self.btn_prev.setDisabled(self.cb_history.currentIsFirst())
        self.btn_next.setDisabled(self.cb_history.currentIsLast())

        if i == -1:
            update_table(self.run_table)
            self.run_monitor.init_plots(self.current_routine)
            if not self.current_routine:
                self.routine_editor.clear()
                self.status_bar.set_summary('no active routine')
            else:
                self.status_bar.set_summary(f'current routine: {self.current_routine["name"]}')
            return

        run_filename = self.cb_history.currentText()
        try:
            run = load_run(run_filename)
        except:
            return
        self.current_routine = run['routine']  # update the current routine
        update_table(self.run_table, run['data'])
        self.run_monitor.init_plots(run['routine'], run['data'], run_filename)
        self.routine_editor.set_routine(run['routine'])
        self.status_bar.set_summary(f'current routine: {self.current_routine["name"]}')

    def go_prev_run(self):
        self.cb_history.selectPreviousItem()

    def go_next_run(self):
        self.cb_history.selectNextItem()

    def inspect_solution(self, idx):
        self.run_table.selectRow(idx)

    def solution_selected(self, r, c):
        self.run_monitor.jump_to_solution(r)

    def table_selection_changed(self):
        indices = self.run_table.selectedIndexes()
        if len(indices) == 1:  # let other method handles it
            return

        row = -1
        for index in indices:
            _row = index.row()
            if _row == row:
                continue

            if row == -1:
                row = _row
                continue

            return

        self.run_monitor.jump_to_solution(row)

    def toggle_lock(self, lock):
        if lock:
            self.panel_routine.setDisabled(True)
            self.history_nav_bar.setDisabled(True)
        else:
            self.panel_routine.setDisabled(False)
            self.history_nav_bar.setDisabled(False)

    def new_run(self):
        self.cb_history.insertItem(0, 'Optimization in progress...')
        self.cb_history.setCurrentIndex(0)

        header = get_header(self.current_routine)
        reset_table(self.run_table, header)

    def run_name(self, name):
        if self.prev_routine:
            runs = get_runs_by_routine(self.current_routine['name'])
        else:
            runs = get_runs()
        self.cb_history.updateItems(runs)

    def progress(self, vars, objs, cons):
        add_row(self.run_table, objs + cons + vars)

    def delete_run(self):
        run_name = self.cb_history.currentText()
        delete_run(run_name)
        # Reset current routine if no routine is selected
        if not self.prev_routine:
            self.current_routine = None
            runs = get_runs()
        else:
            runs = get_runs_by_routine(self.current_routine['name'])
        self.cb_history.updateItems(runs)
