import os
from importlib import resources
from pandas import DataFrame

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QMessageBox
from PyQt5.QtWidgets import QPushButton, QSplitter, QTabWidget, QShortcut
from PyQt5.QtWidgets import QListWidget, QListWidgetItem, QLabel, QFileDialog
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QKeySequence, QIcon, QFont
from ..components.search_bar import search_bar
from ..components.data_table import data_table, update_table, reset_table, add_row
from ..components.routine_item import BadgerRoutineItem
from ..components.history_navigator import HistoryNavigator
from ..components.run_monitor import BadgerOptMonitor
from ..components.routine_editor import BadgerRoutineEditor
from ..components.status_bar import BadgerStatusBar
from ..components.filter_cbox import BadgerFilterBox
from ..utils import create_button
from ....db import list_routine, load_routine, remove_routine, get_runs_by_routine, get_runs
from ....db import import_routines, export_routines
from ....archive import load_run, delete_run
from ....utils import get_header, strtobool
from ....settings import read_value


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
    sig_routine_activated = pyqtSignal(bool)

    def __init__(self):
        super().__init__()

        self.mode = 'regular'  # home page mode
        self.splitter_state = None  # store the run splitter state
        self.tab_state = None  # store the tabs state before creating new routine

        self.init_ui()
        self.config_logic()

        self.load_all_runs()

    def init_ui(self):
        icon_ref = resources.files(__package__) / '../images/add.png'
        with resources.as_file(icon_ref) as icon_path:
            self.icon_add = QIcon(str(icon_path))
        icon_ref = resources.files(__package__) / '../images/import.png'
        with resources.as_file(icon_ref) as icon_path:
            self.icon_import = QIcon(str(icon_path))
        icon_ref = resources.files(__package__) / '../images/export.png'
        with resources.as_file(icon_ref) as icon_path:
            self.icon_export = QIcon(str(icon_path))

        # cool_font = QFont()
        # cool_font.setWeight(QFont.DemiBold)
        # cool_font.setPixelSize(13)

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
        panel_routine.setMinimumWidth(360)
        vbox_routine = QVBoxLayout(panel_routine)

        # Search bar
        panel_search = QWidget()
        hbox_search = QHBoxLayout(panel_search)
        hbox_search.setContentsMargins(0, 0, 0, 0)
        # hbox_search.setSpacing(8)

        self.sbar = sbar = search_bar()
        sbar.setFixedHeight(36)
        f = sbar.font()
        f.setPixelSize(16)
        sbar.setFont(f)
        self.btn_new = btn_new = QPushButton()
        btn_new.setFixedSize(36, 36)
        btn_new.setIcon(self.icon_add)
        btn_new.setToolTip('Create new routine')
        hbox_search.addWidget(sbar)
        # hbox_search.addSpacing(4)
        hbox_search.addWidget(btn_new)
        vbox_routine.addWidget(panel_search)

        # Filters
        self.filter_box = filter_box = BadgerFilterBox(self, title=' Filters')
        if not strtobool(read_value('BADGER_ENABLE_ADVANCED')):
            filter_box.hide()
        vbox_routine.addWidget(filter_box)

        # Routine list
        self.routine_list = routine_list = QListWidget()
        routine_list.setAlternatingRowColors(True)
        routine_list.setSpacing(1)
        routine_list.setViewportMargins(0, 0, 17, 0)  # leave space for scrollbar
        self.refresh_routine_list()
        self.prev_routine_item = None  # last selected routine
        vbox_routine.addWidget(routine_list)

        # Action bar
        action_bar = QWidget()
        hbox_action = QHBoxLayout(action_bar)
        hbox_action.setContentsMargins(0, 0, 0, 0)
        self.btn_export = btn_export = QPushButton()
        btn_export.setFixedSize(28, 28)
        btn_export.setIcon(self.icon_export)
        btn_export.setToolTip('Export filtered routines')
        self.btn_import = btn_import = QPushButton()
        btn_import.setFixedSize(28, 28)
        btn_import.setIcon(self.icon_import)
        btn_import.setToolTip('Import routines')
        hbox_action.addStretch(1)
        hbox_action.addWidget(btn_import)
        hbox_action.addWidget(btn_export)
        vbox_routine.addWidget(action_bar)

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
        self.btn_prev = btn_prev = create_button(
            "next.png", "Go to the next run", size=(24, 24))
        self.btn_next = btn_next = create_button(
            "previous.png", "Go to the previous run", size=(24, 24))
        btn_prev.setDisabled(True)
        btn_next.setDisabled(True)
        hbox_nav.addWidget(label_nav)
        hbox_nav.addWidget(cb_history, 1)
        hbox_nav.addWidget(btn_next)
        hbox_nav.addWidget(btn_prev)

        self.tabs = tabs = QTabWidget()
        vbox_view.addWidget(tabs)

        # Run monitor + data table
        self.splitter_run = splitter_run = QSplitter(Qt.Vertical)
        splitter_run.setStretchFactor(0, 1)
        splitter_run.setStretchFactor(1, 0)
        tabs.addTab(splitter_run, 'Run Monitor')

        # Run monitor
        self.run_view = run_view = QWidget()  # for consistent bg
        vbox_run_view = QVBoxLayout(run_view)
        vbox_run_view.setContentsMargins(0, 10, 0, 10)
        self.run_monitor = run_monitor = BadgerOptMonitor()
        vbox_run_view.addWidget(run_monitor)

        # Data table
        self.run_table = run_table = data_table()

        splitter_run.addWidget(run_view)
        splitter_run.addWidget(run_table)
        splitter_run.setSizes([1, 0])  # collapse table by default

        splitter_run.setStretchFactor(0, 1)
        splitter_run.setStretchFactor(1, 0)

        # Add panels to splitter
        splitter.addWidget(panel_routine)
        splitter.addWidget(panel_info)

        # Routine view
        self.routine_view = routine_view = QWidget()  # for consistent bg
        vbox_routine_view = QVBoxLayout(routine_view)
        vbox_routine_view.setContentsMargins(0, 0, 0, 10)
        self.routine_editor = routine_editor = BadgerRoutineEditor()
        vbox_routine_view.addWidget(routine_editor)
        tabs.addTab(routine_view, 'Routine Editor')

        self.status_bar = status_bar = BadgerStatusBar()
        status_bar.set_summary('Badger is ready!')
        vbox_view.addWidget(status_bar)

    def config_logic(self):
        self.colors = ['c', 'g', 'm', 'y', 'b', 'r', 'w']
        self.symbols = ['o', 't', 't1', 's', 'p', 'h', 'd']

        self.sbar.textChanged.connect(self.refresh_routine_list)
        self.btn_new.clicked.connect(self.create_new_routine)
        self.routine_list.itemClicked.connect(self.select_routine)
        self.run_table.cellClicked.connect(self.solution_selected)
        self.run_table.itemSelectionChanged.connect(self.table_selection_changed)

        self.filter_box.cb_obj.currentIndexChanged.connect(self.refresh_routine_list)
        self.filter_box.cb_reg.currentIndexChanged.connect(self.refresh_routine_list)
        self.filter_box.cb_gain.currentIndexChanged.connect(self.refresh_routine_list)

        self.cb_history.currentIndexChanged.connect(self.go_run)
        self.btn_prev.clicked.connect(self.go_prev_run)
        self.btn_next.clicked.connect(self.go_next_run)

        self.run_monitor.sig_inspect.connect(self.inspect_solution)
        self.run_monitor.sig_lock.connect(self.toggle_lock)
        self.run_monitor.sig_new_run.connect(self.new_run)
        self.run_monitor.sig_run_name.connect(self.run_name)
        self.run_monitor.sig_progress.connect(self.progress)
        self.run_monitor.sig_del.connect(self.delete_run)

        self.routine_editor.sig_saved.connect(self.routine_saved)
        self.routine_editor.sig_canceled.connect(self.done_create_routine)
        self.routine_editor.sig_deleted.connect(self.routine_deleted)
        self.routine_editor.routine_page.sig_updated.connect(self.routine_description_updated)

        # Assign shortcuts
        self.shortcut_go_search = QShortcut(QKeySequence('Ctrl+L'), self)
        self.shortcut_go_search.activated.connect(self.go_search)

        # Export/import routines
        self.btn_export.clicked.connect(self.export_routines)
        self.btn_import.clicked.connect(self.import_routines)

    def go_search(self):
        self.sbar.setFocus()

    def load_all_runs(self):
        runs = get_runs()
        self.cb_history.updateItems(runs)

    def create_new_routine(self):
        self.splitter_state = self.splitter_run.saveState()
        self.routine_editor.set_routine(None)
        self.tab_state = self.tabs.currentIndex()
        self.tabs.setCurrentIndex(1)
        self.mode = 'new routine'
        self.routine_editor.switch_mode(self.mode)
        self.toggle_lock(True, 0)

    def select_routine(self, routine_item: QListWidgetItem):
        if self.prev_routine_item:
            try:
                self.routine_list.itemWidget(self.prev_routine_item).deactivate()
            except ValueError:
                pass

            if self.prev_routine_item.routine_name == routine_item.routine_name:  #
                # click a routine again to deselect
                self.prev_routine_item = None
                self.current_routine = None
                self.load_all_runs()
                if not self.cb_history.count():
                    self.go_run(-1)  # sometimes we need to trigger this manually
                self.sig_routine_activated.emit(False)
                return

        self.prev_routine_item = routine_item  # note that prev_routine is an item!
        self.sig_routine_activated.emit(True)

        routine, timestamp = load_routine(routine_item.routine_name)
        self.current_routine = routine
        self.routine_editor.set_routine(routine)
        runs = get_runs_by_routine(routine.name)
        self.cb_history.updateItems(runs)
        if not self.cb_history.count():
            self.go_run(-1)  # sometimes we need to trigger this manually

        if not runs:  # auto plot will not be triggered
            self.run_monitor.init_plots(routine)

        self.routine_list.itemWidget(routine_item).activate()

    def build_routine_list(self,
                           routines: list[str],
                           timestamps: list[str],
                           descriptions: list[str]):
        try:
            selected_routine = self.prev_routine_item.routine_name
        except Exception:
            selected_routine = None
        self.routine_list.clear()
        for i, routine in enumerate(routines):
            _item = BadgerRoutineItem(routine, timestamps[i],
                                      descriptions[i], self)
            _item.sig_del.connect(self.delete_routine)
            item = QListWidgetItem(self.routine_list)
            item.routine_name = routine  # dirty trick
            item.setSizeHint(_item.sizeHint())
            self.routine_list.addItem(item)
            self.routine_list.setItemWidget(item, _item)
            if routine == selected_routine:
                _item.activate()
                self.prev_routine_item = item

    def get_current_routines(self):
        keyword = self.sbar.text()
        tag_obj = self.filter_box.cb_obj.currentText()
        tag_reg = self.filter_box.cb_reg.currentText()
        tag_gain = self.filter_box.cb_gain.currentText()
        tags = {}
        if tag_obj:
            tags['objective'] = tag_obj
        if tag_reg:
            tags['region'] = tag_reg
        if tag_gain:
            tags['gain'] = tag_gain
        routines, timestamps, descriptions = list_routine(keyword, tags)

        return routines, timestamps, descriptions

    def refresh_routine_list(self):
        routines, timestamps, descriptions = self.get_current_routines()

        self.build_routine_list(routines, timestamps, descriptions)

    def go_run(self, i: int):
        if self.cb_history.itemText(0) == 'Optimization in progress...':
            return
        # if self.cb_history.currentText() == 'Optimization in progress...':
        #     return

        self.btn_prev.setDisabled(self.cb_history.currentIsFirst())
        self.btn_next.setDisabled(self.cb_history.currentIsLast())

        if i == -1:
            update_table(self.run_table)
            self.run_monitor.init_plots(self.current_routine)
            if not self.current_routine:
                self.routine_editor.clear()
                self.status_bar.set_summary('no active routine')
            else:
                self.status_bar.set_summary(f'current routine: {self.current_routine.name}')
            return

        run_filename = self.cb_history.currentText()
        try:
            _routine = load_run(run_filename)
            routine, _ = load_routine(_routine.name)  # get the initial routine
            routine.data = _routine.data
        except (IndexError, AttributeError):
            return
        self.current_routine = routine  # update the current routine
        update_table(self.run_table, routine.sorted_data)
        self.run_monitor.init_plots(routine, run_filename)
        self.routine_editor.set_routine(routine)
        self.status_bar.set_summary(f'current routine: {self.current_routine.name}')

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

    def toggle_lock(self, lock, lock_tab=1):
        if lock:
            self.panel_routine.setDisabled(True)
            self.history_nav_bar.setDisabled(True)
            self.tabs.setTabEnabled(lock_tab, False)
        else:
            self.panel_routine.setDisabled(False)
            self.history_nav_bar.setDisabled(False)
            self.tabs.setTabEnabled(0, True)
            self.tabs.setTabEnabled(1, True)

    def new_run(self):
        self.cb_history.insertItem(0, 'Optimization in progress...')
        self.cb_history.setCurrentIndex(0)

        header = get_header(self.current_routine)
        reset_table(self.run_table, header)

    def run_name(self, name):
        if self.prev_routine_item:
            runs = get_runs_by_routine(self.current_routine.name)
        else:
            runs = get_runs()
        self.cb_history.updateItems(runs)

    def progress(self, solution: DataFrame):
        vocs = self.current_routine.vocs
        vars = list(solution[vocs.variable_names].to_numpy()[0])
        objs = list(solution[vocs.objective_names].to_numpy()[0])
        cons = list(solution[vocs.constraint_names].to_numpy()[0])
        stas = list(solution[vocs.observable_names].to_numpy()[0])
        add_row(self.run_table, objs + cons + vars + stas)

    def delete_run(self):
        run_name = self.cb_history.currentText()

        reply = QMessageBox.question(
            self, 'Delete run',
            f'Are you sure you want to delete run {run_name}?',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes:
            return

        delete_run(run_name)
        # Reset current routine if no routine is selected
        if not self.prev_routine_item:
            self.current_routine = None
            runs = get_runs()
        else:
            runs = get_runs_by_routine(self.current_routine.name)
        self.cb_history.updateItems(runs)
        if not self.cb_history.count():
            self.go_run(-1)  # sometimes we need to trigger this manually

    def routine_saved(self):
        self.refresh_routine_list()
        self.select_routine(self.routine_list.item(0))
        self.tab_state = 0  # force jump to run monitor
        self.done_create_routine()

    def done_create_routine(self):
        if self.mode == 'new routine':
            self.mode = 'regular'
            self.routine_editor.switch_mode(self.mode)
            self.routine_editor.set_routine(self.current_routine)
            self.splitter_run.restoreState(self.splitter_state)
            self.splitter_state = None
            self.tabs.setCurrentIndex(self.tab_state)
            self.tab_state = None
            self.toggle_lock(False)
        else:
            self.tabs.setCurrentIndex(self.tab_state)
            self.tab_state = None

    def delete_routine(self, name):
        remove_routine(name)
        self.routine_deleted(name)

    def routine_deleted(self, name=None):
        if self.prev_routine_item:
            if self.prev_routine_item.routine_name == name:
                self.prev_routine_item = None
                self.current_routine = None
                self.load_all_runs()
                if not self.cb_history.count():
                    self.go_run(-1)  # sometimes we need to trigger this manually
                self.sig_routine_activated.emit(False)

        self.refresh_routine_list()

    def routine_description_updated(self, name, descr):
        for i in range(self.routine_list.count()):
            item = self.routine_list.item(i)
            if item is not None:
                routine_item = self.routine_list.itemWidget(item)
                if routine_item.name == name:
                    routine_item.update_description(descr)
                    break

    def export_routines(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        filename, _ = QFileDialog.getSaveFileName(self, 'Export Badger routines', '', 'Database Files (*.db)', options=options)

        if not filename:
            return

        _, ext = os.path.splitext(filename)
        if not ext:
            filename = filename + '.db'

        try:
            routines, _, _ = self.get_current_routines()
            export_routines(filename, routines)

            QMessageBox.information(
                self, 'Success!', f'Export succeeded: filtered routines exported to {filename}')
        except Exception as e:
            QMessageBox.critical(self, 'Export failed!', f'Export failed: {str(e)}')

    def import_routines(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        filename, _ = QFileDialog.getOpenFileName(self, 'Import Badger routines',
                                                  '', 'Database Files (*.db)',
                                                  options=options)

        if not filename:
            return

        _, ext = os.path.splitext(filename)
        if not ext:
            filename = filename + '.db'

        try:
            import_routines(filename)

            QMessageBox.information(
                self, 'Success!', f'Import succeeded: imported all routines from {filename}')
        except Exception as e:
            QMessageBox.warning(self, 'Heads-up!', f'Failed to import the following routines since they already existed: \n{str(e)}')
