import sys
from datetime import datetime, timezone

import os

# from PySide6 import QtCore
from PySide6.QtCore import *  # QFile, QUrl
from PySide6.QtUiTools import *  # QUiLoader
from PySide6.QtWidgets import *  # QApplication
from PySide6.QtGui import *  # QImage, QPixmap
# from PySide6.QtMultimedia import QMediaPlayer
# from PySide6.QtMultimediaWidgets import QVideoWidget

# from qt_material import apply_stylesheet

from exiftoolgui_settings import ExifToolGUISettings
from exiftoolgui_data import ExifToolGUIData
from exiftool_options import ExifToolOptions


class ExifToolGUI(QObject):

    dataLocker: QMutex = QMutex()

    metadataLoaded = Signal(int)
    previewLoaded = Signal(QTableWidgetItem, QPixmap)

    def __init__(self) -> None:
        super().__init__()

        self.app: QApplication = QApplication(sys.argv)
        # apply_stylesheet(self.app, theme='dark_teal.xml')

        self.settings: ExifToolGUISettings = ExifToolGUISettings.Instance
        self.data: ExifToolGUIData = ExifToolGUIData.Instance
        self.exiftool_option_defs = ExifToolOptions.Instance

        self.main_window: QMainWindow = self.load_main_window()

        # # After any value in a table is modified, the ref would dead
        # # "RuntimeError: Internal C++ object (PySide6.QtWidgets.QTableWidget) already deleted."
        # self.table_for_group:QTableWidget = self.main_window.findChild(QTableWidget, 'table_for_group')
        # ...
        # # use @property to get dynamically

        self.adjust_main_window()

        self.load_tabs_for_single()
        self.load_comboBox_functions()
        self.init_exiftool_options()

        self.add_event_handlers()

        self.main_window.show()

        self.reload_list_for_dirs()  # reload_table_for_group()

        sys.exit(self.app.exec())

    '''################################################################
    Propertises
    ################################################################'''

    @property
    def table_for_group(self) -> QTableWidget:
        return self.main_window.findChild(QTableWidget, 'table_for_group')

    @property
    def tab_for_single(self) -> QTabWidget:
        return self.main_window.findChild(QTabWidget, 'tab_for_single')

    @property
    def list_dirs(self) -> QListWidget:
        return self.main_window.findChild(QListWidget, 'list_dirs')

    @property
    def button_add_dir(self) -> QPushButton:
        return self.main_window.findChild(QPushButton, 'button_add_dir')

    @property
    def button_remove_dir(self) -> QPushButton:
        return self.main_window.findChild(QPushButton, 'button_remove_dir')

    @property
    def button_save(self) -> QPushButton:
        return self.main_window.findChild(QPushButton, 'button_save')

    @property
    def button_reset(self) -> QPushButton:
        return self.main_window.findChild(QPushButton, 'button_reset')

    @property
    def button_refresh(self) -> QPushButton:
        return self.main_window.findChild(QPushButton, 'button_refresh')

    @property
    def button_rebuild(self) -> QPushButton:
        return self.main_window.findChild(QPushButton, 'button_rebuild')

    @property
    def comboBox_functions(self) -> QComboBox:
        return self.main_window.findChild(QComboBox, 'comboBox_functions')

    @property
    def groupBox_parameters(self) -> QGroupBox:
        return self.main_window.findChild(QGroupBox, 'groupBox_parameters')

    @property
    def pushButton_functions_exec(self) -> QPushButton:
        return self.main_window.findChild(QPushButton, 'pushButton_functions_exec')

    # memu_exiftool

    @property
    def exiftool_options_display(self) -> QGridLayout:
        return self.main_window.findChild(QGridLayout, 'exiftool_options_display')

    @property
    def exiftool_options_editor(self) -> QGridLayout:
        return self.main_window.findChild(QGridLayout, 'exiftool_options_editor')

    @property
    def exiftool_options_editor_state(self) -> QCheckBox:
        return self.main_window.findChild(QCheckBox, 'exiftool_options_editor_state')

    @property
    def exiftool_options_editor_input(self) -> QComboBox:
        return self.main_window.findChild(QComboBox, 'exiftool_options_editor_input')

    @property
    def exiftool_options_editor_add(self) -> QPushButton:
        return self.main_window.findChild(QPushButton, 'exiftool_options_editor_add')

    @property
    def exiftool_options_editor_delete(self) -> QPushButton:
        return self.main_window.findChild(QPushButton, 'exiftool_options_editor_delete')

    @property
    def exiftool_options_editor_description(self) -> QTextBrowser:
        return self.main_window.findChild(QTextBrowser, 'exiftool_options_editor_description')

    def load_main_window(self) -> QMainWindow:
        ui_file = QFile(self.settings.assets_ui)
        loader = QUiLoader()
        main_window = loader.load(ui_file)
        ui_file.close()
        return main_window

    '''################################################################
    UI
    ################################################################'''

    @staticmethod
    def clear_layout(layout: QLayout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            sub_layout = item.layout()

            if widget:
                widget.setParent(None)
                widget.deleteLater()
            elif sub_layout:
                ExifToolGUI.clear_layout(sub_layout)
                sub_layout.setParent(None)
                sub_layout.deleteLater()

            # layout.removeItem(item)
            del item

    def adjust_main_window(self):
        # this should be done by designer, but...
        # ref: https://stackoverflow.com/questions/55539617/qt-designer-auto-fitting-the-tablewidget-directly-from-the-designer
        # self.table_for_group.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table_for_group.horizontalHeader().setSectionsMovable(True)
        # self.table_for_group.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        # self.table_for_group.verticalHeader().setSectionsMovable(True)
        self.table_for_group.verticalScrollBar().setSingleStep(10)
        self.table_for_group.horizontalScrollBar().setSingleStep(10)

    def reload_list_for_dirs(self):
        list_dirs: QListWidget = self.list_dirs
        list_dirs.clear()
        list_dirs.addItems(self.settings.dirs)
        with QMutexLocker(ExifToolGUI.dataLocker):
            self.data.reload()
            self.reload_table_for_group()
            self.edit_table_for_group()

    def reload_table_for_group(self):

        table: QTableWidget = self.table_for_group

        # ExifToolGUI.dataLocker.lock()
        table.blockSignals(True)
        table.clear()

        tags = self.settings.tags_for_group
        tags_count = len(tags)
        table.setColumnCount(tags_count)
        table.setHorizontalHeaderLabels(tags)

        file_count = len(self.data.cache)
        table.setRowCount(file_count)
        # table.setVerticalHeaderLabels([str(x) for x in range(0, file_count)])

        for file_index in range(0, file_count):

            if len(self.data.cache[file_index]) <= 1:
                GetDataTask(file_index, self)

            for column in range(0, tags_count):
                tag = tags[column]
                value = self.data.get(file_index, tag, default='')
                item = QTableWidgetItem(str(value))

                item.setData(Qt.UserRole, {"file_index": file_index, "tag": tag, "gui": self})  # mark

                if tag == 'SourceFile':
                    item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)

                    GetPreviewTask(item, value, self.settings.preview_size, self.settings.preview_precision)

                table.setItem(file_index, column, item)

        table.resizeColumnsToContents()
        table.resizeRowsToContents()
        if table.columnWidth(0) > 300:
            table.setColumnWidth(0, 300)

        table.blockSignals(False)
        # ExifToolGUI.dataLocker.unlock()

    def reflash_table_for_group(self, file_indexs: list[int] = None):
        table: QTableWidget = self.table_for_group

        table.blockSignals(True)

        for row in range(0, table.rowCount()):
            for column in range(0, table.columnCount()):
                item = table.item(row, column)
                user_data: dict[str,] = item.data(Qt.UserRole)
                file_index: int = user_data['file_index']

                # None means all
                if file_indexs != None and file_index not in file_indexs:
                    break

                tag: str = user_data['tag']
                value = self.data.get(file_index, tag, default='')
                item.setText(value)

        table.blockSignals(False)

    def sort_table_for_group(self, column):
        table = self.table_for_group

        table.blockSignals(True)

        order = table.horizontalHeader().sortIndicatorOrder()

        h_tag = table.horizontalHeaderItem(column).text()
        is_datetime = self.data.is_datetime(h_tag)

        current_item = table.currentItem()
        selected_items = table.selectedItems()

        rows = []
        for row in range(table.rowCount()):
            items = []
            for col in range(table.columnCount()):
                item = table.takeItem(row, col)
                items.append(item)
            rows.append(items)

        table.clearSelection()

        def sort_value(row: list[QTableWidgetItem]):
            value = row[column].text()
            assert (value != None)
            if is_datetime:
                file_index: int = row[column].data(Qt.UserRole)['file_index']
                tag: str = row[column].data(Qt.UserRole)['tag']
                dt, _ = self.data.get_datetime(file_index, tag, value, self.settings.default_timezone)
                return dt if dt else datetime.min.replace(tzinfo=timezone.utc)
            else:
                return value

        rows.sort(
            key=lambda row: sort_value(row),
            reverse=(order == Qt.DescendingOrder)
        )

        for row, items in enumerate(rows):
            for col, item in enumerate(items):
                table.setItem(row, col, item)

        table.setCurrentItem(current_item)
        table.clearSelection()
        for item in selected_items:
            item.setSelected(True)

        table.blockSignals(False)

    def load_tabs_for_single(self):
        tab_wedget: QTabWidget = self.tab_for_single

        tab_wedget.currentChanged.connect(self.on_current_changed__tab_for_single)  # EVENT

        for tab_type in self.settings.tags_for_single.keys():

            widget: QWidget = QWidget()
            tab_wedget.addTab(widget, tab_type)

            tree: QTreeWidget = QTreeWidget()
            tree.setColumnCount(2)
            tree.setHeaderLabels(["Tag", "Value"])

            tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # UI
            # tree.setStyleSheet("QTreeWidget::item { border-bottom: 1px solid gray; }")  # style

            tree.itemDoubleClicked.connect(self.on_item_double_clicked__tree_for_single)  # EVENT
            tree.currentItemChanged.connect(self.on_current_item_changed__tree_for_single)  # EVENT
            tree.itemChanged.connect(self.on_item_changed__tree_for_single)  # EVENT

            layout = QGridLayout()
            layout.setContentsMargins(1, 1, 1, 1)  # UI
            layout.addWidget(tree)
            widget.setLayout(layout)

    def reload_current_tree_for_single(self):
        tab_wedget = self.tab_for_single
        title = tab_wedget.tabText(tab_wedget.currentIndex())

        cur_tab = tab_wedget.currentWidget()
        tree = cur_tab.findChild(QTreeWidget)

        file_index: int = self.table_for_group.currentItem().data(Qt.UserRole)['file_index']
        strict = False

        if title == 'all':
            metadata_temp = self.data.cache[file_index]
            strict = True
        else:
            metadata_temp: dict[str,] = {}
            for tag in self.settings.tags_for_single[title]:
                value = self.data.get(file_index, tag, default='')
                metadata_temp[tag] = value

        self.reload_tree_for_single(tree, metadata_temp)
        self.edit_tree_for_single(tree, strict)

    def reload_tree_for_single(self, tree: QTreeWidget, metadata: dict[str, ]):
        tree.blockSignals(True)
        tree.clear()

        root: dict = {
            'item': None,
            'childen': {}
        }
        for tag in metadata:
            tag_list: list = tag.split(':')

            # apply max_group_level
            if len(tag_list) - 2 > self.settings.max_group_level:
                tag_name = tag_list.pop()
                tag_list = tag_list[0:self.settings.max_group_level+1]
                tag_list.append(tag_name)

            # simplify groups
            if self.settings.simplify_group_level:
                # combine same group names nearby
                for i in range(0, len(tag_list)-1):
                    if tag_list[i] == '':
                        continue
                    for j in range(i+1, len(tag_list)-1):
                        if tag_list[j] == tag_list[i]:
                            tag_list[j] = ''
                        else:
                            break
                # delete empty groups
                while True:
                    if '' not in tag_list:
                        break
                    tag_list.remove('')

            # form tree view
            parent: dict = root
            for i in range(0, len(tag_list)):
                tag_sub = tag_list[i]
                child = parent['childen'].get(tag_sub, None)
                if child == None or i == len(tag_list)-1:
                    item_child = QTreeWidgetItem()
                    item_child.setText(0, tag_sub)
                    # save full tag
                    item_child.setData(0, Qt.UserRole, tag)  # mark
                    item_parent: QTreeWidgetItem = parent['item']
                    if item_parent == None:
                        tree.addTopLevelItem(item_child)
                    else:
                        item_parent.addChild(item_child)

                    if i != len(tag_list)-1:
                        child = {
                            'item': item_child,
                            'childen': {}
                        }
                        parent['childen'][tag_sub] = child
                    else:
                        value = metadata[tag]
                        # check the type of value
                        type_v = type(value)
                        if type_v != str:
                            value = str(value)

                            # debug usage
                            if type_v != int and type_v != float and type_v != bool:  # and type_v != list
                                print(f"{tag}:{type_v}")

                        item_child.setText(1, value)

                        # item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsEditable)
                        # tree.openPersistentEditor(item, 1)
                parent = child

        tree.expandAll()
        tree.resizeColumnToContents(0)
        if tree.columnWidth(0) > 200:
            tree.setColumnWidth(0, 200)

        tree.blockSignals(False)

    def load_comboBox_functions(self):
        comboBox_functions: QComboBox = self.comboBox_functions
        for key, value in self.settings.functions.items():
            comboBox_functions.addItem(key, value)

        self.reload_groupBox_parameters()

    def reload_groupBox_parameters(self):
        comboBox_functions: QComboBox = self.comboBox_functions
        current_date: dict[str, dict[str,]] = comboBox_functions.currentData()

        groupBox_parameters: QGroupBox = self.groupBox_parameters
        layout: QGridLayout = groupBox_parameters.layout()
        ExifToolGUI.clear_layout(layout)

        r: int = 0
        c: int = 0
        for key, value in current_date.items():
            sub_layout: QHBoxLayout = QHBoxLayout()
            layout.addLayout(sub_layout, r, c)

            if value['type'] == 'bool':
                checkbox: QCheckBox = QCheckBox(key)
                checkbox.setChecked(value['default'])
                sub_layout.addWidget(checkbox)

            else:
                lable: QLabel = QLabel(key)
                sub_layout.addWidget(lable)
                lineEdit: QLineEdit = QLineEdit(str(value['default']))
                sub_layout.addWidget(lineEdit)

            r += 1
            if r == 3:
                r = 0
                c += 1

    # memu_exiftool

    def init_exiftool_options(self):
        self.init_exiftool_options_display()
        self.init_exiftool_options_editor()

    def init_exiftool_options_display(self):

        layout: QGridLayout = self.exiftool_options_display
        ExifToolGUI.clear_layout(layout)

        option_list: list[QToolButton] = []
        layout.setProperty('userdata', {0: option_list})  # userdata (shallow copy)

        options = self.settings.exiftool_options
        for option, state in options.items():
            butt = self.init_exiftool_option(option.split('\0')[0], state)
            option_list.append(butt)
            self.update_exiftool_option(butt)

        self.relocate_exiftool_options()

    def init_exiftool_options_editor(self):

        self.exiftool_options_editor.setProperty("userdata", {0: None})  # userdata

        input: QComboBox = self.exiftool_options_editor_input

        input.clear()
        option_defs = self.exiftool_option_defs.get_options_non_tag_name()
        for hint, description in option_defs.items():
            input.addItem(
                f"{hint}\n {description}\n________________",
                # f"<html><b>{hint}</b><br>{description}</html>",
                (hint, description)
            )

        self.clear_exiftool_options_editor()

        completer = QCompleter(input.model())
        input.setCompleter(completer)

        # input.activated.connect(self.on_activated_exiftool_options_editor_input)  # signal
        # input.lineEdit().returnPressed.connect(self.on_returnPressed_exiftool_options_editor_input) # signal

    def clear_exiftool_options_editor(self):
        self.exiftool_options_editor.property('userdata')[0] = None

        # state
        self.exiftool_options_editor_state.setEnabled(True)
        self.exiftool_options_editor_state.setCheckState(Qt.CheckState.Unchecked)

        # input
        self.exiftool_options_editor_input.setCurrentIndex(-1)
        # self.exiftool_options_editor_input.setCurrentText("")  # no need
        self.exiftool_options_editor_input.setEnabled(True)

        # description
        self.exiftool_options_editor_description.setText("")

        # button
        self.exiftool_options_editor_delete.setEnabled(False)

    def update_exiftool_options_editor(self, update_state: bool = True, update_input: bool = True, update_description: bool = True, update_button: bool = True):
        layout_editor = self.exiftool_options_editor
        button: QToolButton = layout_editor.property('userdata')[0]

        if button:
            option: str = button.text()
            state: str = button.property('userdata')[1]

        # state
        if button and update_state:
            self.exiftool_options_editor_state.setEnabled(False if state == 'auto' or state == 'forced' else True)

            checkState: Qt.CheckState = \
                Qt.CheckState.PartiallyChecked if state == 'auto' else \
                Qt.CheckState.Checked if state == 'forced' or state == 'on' else \
                Qt.CheckState.Unchecked
            self.exiftool_options_editor_state.setCheckState(checkState)

        # input
        if button and update_input:
            self.exiftool_options_editor_input.setCurrentText(option)
            self.exiftool_options_editor_input.setEnabled(False if state == 'auto' or state == 'forced' else True)

        # description
        if update_description:
            if not button:
                option = self.exiftool_options_editor_input.currentText()

            option_def = self.exiftool_option_defs.find_option(option)
            self.exiftool_options_editor_description.setText(
                f"{option_def[0]}\n {option_def[1]}" if option_def else "Unrecognized option."
            )

        # button_delete
        if button and update_button:
            self.exiftool_options_editor_delete.setEnabled(False if state == 'auto' or state == 'forced' or state == 'on' else True)

    def init_exiftool_option(self, option, state) -> QToolButton:
        button = QToolButton()
        button.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        button.setCheckable(True)

        button.setProperty("userdata", {0: option, 1: state})  # userdata (shallow copy)

        button.clicked.connect(self.on_clicked_exiftool_option)  # signal

        return button

    def update_exiftool_option(self, button: QToolButton, update_text: bool = True, update_state: bool = True):

        option: str = button.property('userdata')[0]
        state: str = button.property('userdata')[1]

        if update_text:
            button.setText(option)

        if update_state:
            colour: QColor = None

            if state == 'auto':
                colour = QColor(0, 191, 255, 255)
            elif state == 'forced':
                colour = QColor(255, 127, 0, 255)
            elif state == 'on':
                colour = QColor(255, 69, 0, 223)
            elif state == 'off':
                colour = QColor(154, 205, 50, 255)

            if colour:
                rgba = f"rgba({colour.red()}, {colour.green()}, {colour.blue()}, {colour.alphaF()})"
                rgba_h = f"rgba({colour.red()}, {colour.green()}, {colour.blue()}, {colour.alphaF()/2})"
                rgba_d = f"rgba({colour.red()/2}, {colour.green()/2}, {colour.blue()/2}, {colour.alphaF()})"
                button.setStyleSheet(f"""
                    QToolButton {{
                        background-color: {rgba};
                        border-radius: 10px;
                    }}

                    QToolButton:hover {{
                        background-color: {rgba_h};
                    }}

                    QToolButton:checked {{
                        background-color: {rgba};
                        border: 2px solid {rgba_d};
                    }}

                """)

    def relocate_exiftool_options(self):
        layout: QGridLayout = self.exiftool_options_display
        option_list: list[QToolButton] = layout.property('userdata')[0]

        # get total length
        count_letters = 0
        for button in option_list:
            _length = len(button.property('userdata')[0])
            _length = _length if _length > 0 else 1
            count_letters += _length

        # determin location
        r = 0
        c = 0
        for button in option_list:
            option: str = button.property('userdata')[0]
            _length = len(option)
            _length = _length if _length > 0 else 1
            layout.addWidget(button, r, c, 1, _length)  # auto clear?

            c += _length
            if c+1 > count_letters/3:
                r += 1
                c = 0

    def save_exiftool_options(self):
        option_list: list[QToolButton] = self.exiftool_options_display.property('userdata')[0]
        from collections import OrderedDict
        options: OrderedDict[str, str] = {}
        for butt in option_list:
            option = butt.property('userdata')[0]
            state = butt.property('userdata')[1]

            dup: int = 0
            option_base = option
            while option in options:
                dup += 1
                option = f"{option_base}\0{dup}"

            options[option] = state
        self.settings.exiftool_options = options

    '''################################################################
    Editting and Functions
    ################################################################'''

    def get_selected_file_indexes(self) -> list[int]:
        file_indexes: list[int] = []
        table: QTableWidget = self.table_for_group
        for item in table.selectedItems():
            file_index = item.data(Qt.UserRole)['file_index']
            if file_index not in file_indexes:
                file_indexes.append(file_index)
        return file_indexes

    def edit_tag(self, file_index: int, tag: str, value: str, strict: bool = False):
        value_saved, value_edited, status = self.data.get(file_index, tag, default="", strict=strict, editing=True)
        value_saved = str(value_saved)

        # value_saved = str(ExifToolGUIData.Get(self.data.cache[file_index], tag, "", strict))
        # value_edited = ExifToolGUIData.Get(self.data.cache_edited[file_index], tag, None)
        # value_failed = ExifToolGUIData.Get(self.data.cache_failed[file_index], tag, None)

        colour = None
        show_value = None

        if value_edited != None:
            # print(f"---\n{value_saved}\n{value_edited}\n{status}")
            if status == True:
                colour = Qt.green  # or QColor(r, g, b)
                show_value = value_saved
            elif status == False:
                colour = Qt.red
                show_value = value_saved
            else:
                colour = Qt.yellow
                show_value = value_edited
        else:
            if value != value_saved:
                colour = Qt.darkGreen
                show_value = value_saved
        return show_value, colour

    def edit_table_for_group(self, file_indexs: list[int] = None):
        table = self.table_for_group
        table.blockSignals(True)

        for row in range(0, table.rowCount()):
            for column in range(0, table.columnCount()):
                item = table.item(row, column)
                user_data: dict[str,] = item.data(Qt.UserRole)
                file_index: int = user_data['file_index']

                # None means all
                if file_indexs != None and file_index not in file_indexs:
                    break

                tag: str = user_data['tag']
                value = item.text()

                show_value, colour = self.edit_tag(file_index, tag, value)
                if show_value != None and show_value != value:
                    item.setText(show_value)
                if colour:
                    item.setBackground(QBrush(colour))
                else:
                    item.setBackground(QBrush())

        table.blockSignals(False)

    def edit_current_tree_for_single(self):
        tab_wedget = self.tab_for_single
        title = tab_wedget.tabText(tab_wedget.currentIndex())
        tree = tab_wedget.currentWidget().findChild(QTreeWidget)
        strict = (title == 'all')
        self.edit_tree_for_single(tree, strict)

    def edit_tree_for_single(self, tree: QTreeWidget, strict: bool = False):
        currentTableItem: QTableWidgetItem = self.table_for_group.currentItem()
        if not currentTableItem:
            return

        tree.blockSignals(True)
        file_index: int = currentTableItem.data(Qt.UserRole)['file_index']

        it = QTreeWidgetItemIterator(tree)
        while it.value():
            item = it.value()
            if item.childCount() == 0:
                tag: str = item.data(0, Qt.UserRole)
                value = item.text(1)

                show_value, colour = self.edit_tag(file_index, tag, value, strict)
                if show_value != None and show_value != value:
                    item.setText(1, show_value)
                if colour:
                    item.setBackground(1, QBrush(colour))
            it += 1

        tree.blockSignals(False)

    def get_results__functions_parameters(self) -> tuple[str, dict[str,]]:
        func: str = self.comboBox_functions.currentText()

        dict_args: dict[str,] = {}

        dict_args['file_indexes'] = self.get_selected_file_indexes()
        table: QTableWidget = self.table_for_group
        # for item in table.selectedItems():
        #     file_index = item.data(Qt.UserRole)['file_index']
        #     if file_index not in dict_args['file_indexes']:
        #         dict_args['file_indexes'].append(file_index)

        dict_args['ref'] = table.currentItem().data(Qt.UserRole)['file_index']

        layout: QGridLayout = self.groupBox_parameters.layout()
        for column in range(layout.columnCount()):
            for row in range(layout.rowCount()):
                item = layout.itemAtPosition(row, column)
                if item:
                    sub_layout: QHBoxLayout = item.layout()
                    if sub_layout:
                        widget = sub_layout.itemAt(0).widget()

                        if type(widget) == QCheckBox:
                            checkBox: QCheckBox = widget
                            dict_args[checkBox.text()] = checkBox.isChecked()

                        elif type(widget) == QLabel:
                            lable: QLabel = widget
                            lineEdit: QLineEdit = sub_layout.itemAt(1).widget()
                            dict_args[lable.text()] = lineEdit.text()

        return func, dict_args

    '''################################################################
    Event Handlers
    ################################################################'''

    def add_event_handlers(self):
        # Signals
        self.button_add_dir.clicked.connect(self.on_clicked__button_add_dir)
        self.button_remove_dir.clicked.connect(self.on_clicked__button_remove_dir)

        self.button_save.clicked.connect(self.on_clicked__button_save)
        self.button_reset.clicked.connect(self.on_clicked__button_reset)
        self.button_refresh.clicked.connect(self.on_clicked__button_refresh)
        self.button_rebuild.clicked.connect(self.on_clicked__button_rebuild)

        # 点击空白也触发，但不改变currentItem()
        # self.table_for_group.itemSelectionChanged.connect()
        # 点击任意按钮，再切换tab便触发？
        self.table_for_group.currentItemChanged.connect(self.on_current_item_changed__table_for_group)
        self.table_for_group.itemChanged.connect(self.on_item_changed__table_for_group)
        self.table_for_group.horizontalHeader().sectionClicked.connect(self.sort_table_for_group)

        self.comboBox_functions.currentIndexChanged.connect(self.on_currentIndexChanged__comboBox_functions)
        self.pushButton_functions_exec.clicked.connect(self.on_clicked__pushButton_functions_exec)

        self.exiftool_options_editor_state.clicked.connect(self.on_clicked_exiftool_options_editor_state)
        self.exiftool_options_editor_input.currentTextChanged.connect(self.on_currentTextChanged_exiftool_options_editor_input)
        self.exiftool_options_editor_add.clicked.connect(self.on_clicked_exiftool_options_editor_add)
        self.exiftool_options_editor_delete.clicked.connect(self.on_clicked_exiftool_options_editor_delete)

        self.metadataLoaded.connect(self.on_metadataLoaded)
        self.previewLoaded.connect(self.on_previewLoaded)

        self.app.aboutToQuit.connect(self.on_aboutToQuit)

    def on_clicked__button_add_dir(self, checked=False):
        dir = QFileDialog().getExistingDirectory(self.main_window)
        if not dir or dir in self.settings.dirs:
            return
        self.settings.add_dir(dir)
        self.reload_list_for_dirs()
        # print(dir)

    def on_clicked__button_remove_dir(self, checked=False):
        list_dirs_curr = self.list_dirs.currentItem()
        if list_dirs_curr is None:
            return
        dir = list_dirs_curr.text()
        self.settings.remove_dir(dir)
        self.reload_list_for_dirs()

    def on_clicked__button_save(self, checked=False):
        with QMutexLocker(ExifToolGUI.dataLocker):
            self.data.save()
        self.edit_table_for_group()
        self.edit_current_tree_for_single()

    def on_clicked__button_reset(self):
        file_indexes: list[int] = self.get_selected_file_indexes()
        for file_index in file_indexes:
            with QMutexLocker(ExifToolGUI.dataLocker):
                self.data.reset(file_index)
        self.reflash_table_for_group(file_indexes)
        self.edit_table_for_group(file_indexes)
        self.reload_current_tree_for_single()

    def on_clicked__button_refresh(self):
        file_indexes: list[int] = self.get_selected_file_indexes()
        for file_index in file_indexes:
            with QMutexLocker(ExifToolGUI.dataLocker):
                self.data.refresh(file_index)
        self.reflash_table_for_group(file_indexes)
        self.edit_table_for_group(file_indexes)
        self.reload_current_tree_for_single()

    def on_clicked__button_rebuild(self):
        file_indexes: list[int] = self.get_selected_file_indexes()
        for file_index in file_indexes:
            self.data.rebuild(file_index)
        self.reflash_table_for_group(file_indexes)
        self.edit_table_for_group(file_indexes)
        self.edit_current_tree_for_single()

    def on_current_item_changed__table_for_group(self, current: QTableWidgetItem, previous: QTableWidgetItem):
        # print(f"{current.row()}, {current.column()}")
        # print(f"{current.data(Qt.UserRole)}")
        if (
            current == None or
            (previous != None and previous.row() == current.row())
        ):
            return
        self.reload_current_tree_for_single()

    def on_item_changed__table_for_group(self, item: QTableWidgetItem):
        print(f"on_item_changed: {item.row(), item.column()}")

        if item.column() == 0:
            return

        file_index = item.data(Qt.UserRole)['file_index']
        tag = item.tableWidget().horizontalHeaderItem(item.column()).text()
        value = item.text()

        self.data.edit(file_index, tag, value, save=self.settings.auto_save, normalise=True)
        self.edit_table_for_group([file_index])
        self.edit_current_tree_for_single()

    def on_current_changed__tab_for_single(self, index):
        if self.table_for_group.currentItem() == None:
            return
        self.reload_current_tree_for_single()

    def on_item_double_clicked__tree_for_single(self, item: QTreeWidgetItem, clumn: int):
        if clumn == 1 and item.childCount() == 0 and not item.text(1).startswith('(Binary data'):
            item.treeWidget().openPersistentEditor(item, 1)

    def on_current_item_changed__tree_for_single(self, current: QTreeWidgetItem, previous: QTreeWidgetItem):
        if previous and previous.childCount() == 0:
            previous.treeWidget().closePersistentEditor(previous, 1)

    def on_item_changed__tree_for_single(self, item: QTreeWidgetItem, column: int):
        item.treeWidget().closePersistentEditor(item, 1)
        if column != 1:
            return
        file_index: int = self.table_for_group.currentItem().data(Qt.UserRole)['file_index']
        value = item.text(1)

        # tag: str = item.text(2)  # full tag
        tag = item.data(0, Qt.UserRole)

        self.data.edit(file_index, tag, value, save=self.settings.auto_save, normalise=True)
        self.edit_table_for_group([file_index])
        # self.edit_tree_for_single(item.treeWidget())
        self.edit_current_tree_for_single()

    def on_currentIndexChanged__comboBox_functions(self, index):
        self.reload_groupBox_parameters()

    def on_clicked__pushButton_functions_exec(self):
        func, args = self.get_results__functions_parameters()
        # print(func)
        # print(args)
        from exiftoolgui_functions import ExifToolGUIFuncs

        ExifToolGUIFuncs.Exec(func, args)
        self.edit_table_for_group(args['file_indexes'])
        self.edit_current_tree_for_single()

    # memu_exiftool

    def on_clicked_exiftool_option(self):
        button: QPushButton = self.sender()

        if button.isChecked():

            layout_editor = self.exiftool_options_editor

            last: QToolButton = layout_editor.property('userdata')[0]
            if last and last is not button:
                last.setChecked(False)

            layout_editor.property('userdata')[0] = button

            self.update_exiftool_options_editor()

        else:
            self.clear_exiftool_options_editor()

    def on_clicked_exiftool_options_editor_state(self):
        button: QToolButton = self.exiftool_options_editor.property('userdata')[0]
        if button:
            state: str = 'on' if self.exiftool_options_editor_state.isChecked() else 'off'
            button.property('userdata')[1] = state

            self.update_exiftool_option(button, False, True)
            self.update_exiftool_options_editor(False, False, False, True)

            self.save_exiftool_options()

    def on_currentTextChanged_exiftool_options_editor_input(self):
        # get rid of description
        input: QComboBox = self.exiftool_options_editor_input
        text = input.currentText()
        text_l = text.split('\n')
        input.setCurrentText(text_l[0])

        button: QToolButton = self.exiftool_options_editor.property('userdata')[0]
        if button:
            option = self.exiftool_options_editor_input.currentText()
            button.property('userdata')[0] = option

            self.update_exiftool_option(button, True, False)

            self.relocate_exiftool_options()

        self.update_exiftool_options_editor(False, False, True, False)
        self.save_exiftool_options()

    def on_clicked_exiftool_options_editor_add(self):
        layout_display: QGridLayout = self.exiftool_options_display
        layout_editor: QGridLayout = self.exiftool_options_editor

        option_list: list[QToolButton] = layout_display.property('userdata')[0]
        option_last: QToolButton = layout_editor.property('userdata')[0]

        index = len(option_list)
        if option_last:  # and option_last in option_list:
            index = option_list.index(option_last)

        button = self.init_exiftool_option(
            self.exiftool_options_editor_input.currentText(),
            'off'
        )

        option_list.insert(index, button)

        self.update_exiftool_option(button)
        self.relocate_exiftool_options()

        if option_last:
            option_last.setChecked(False)

        button.setChecked(True)

        layout_editor.property('userdata')[0] = button
        self.update_exiftool_options_editor(False, False, False, True)

        self.save_exiftool_options()

    def on_clicked_exiftool_options_editor_delete(self):
        layout_display: QGridLayout = self.exiftool_options_display
        layout_editor: QGridLayout = self.exiftool_options_editor

        option_list: list[QToolButton] = layout_display.property('userdata')[0]
        option_current: QToolButton = layout_editor.property('userdata')[0]

        if option_current:
            self.clear_exiftool_options_editor()

            option_list.remove(option_current)

            layout_display.removeWidget(option_current)
            option_current.deleteLater()

            self.relocate_exiftool_options()

        self.save_exiftool_options()

    #

    def on_metadataLoaded(self, file_index: int):
        self.reflash_table_for_group([file_index])
        self.edit_table_for_group([file_index])
        # self.gui.reload_current_tree_for_single()

    def on_previewLoaded(self, item: QTableWidgetItem, pixmap: QPixmap):

        item.tableWidget().blockSignals(True)

        item.setData(Qt.DecorationRole, pixmap)
        item.tableWidget().resizeRowToContents(item.row())
        # item.tableWidget().resizeColumnToContents(item.column())

        item.tableWidget().blockSignals(False)

    def on_aboutToQuit(self):
        GetDataTask.threadPool.clear()
        GetPreviewTask.threadPool.clear()

        GetDataTask.threadPool.waitForDone()
        GetPreviewTask.threadPool.waitForDone()

        GetDataTask.threadPool.deleteLater()
        GetPreviewTask.threadPool.deleteLater()


'''################################################################
Additional
################################################################'''


class GetDataTask(QRunnable):

    threadPool = QThreadPool()

    def __init__(self, file_index: int, gui: ExifToolGUI) -> None:
        super().__init__()
        self.file_index: int = file_index
        self.gui: ExifToolGUI = gui

        GetDataTask.threadPool.start(self)

    def run(self):

        with QMutexLocker(ExifToolGUI.dataLocker):
            self.gui.data.refresh(self.file_index)

        self.gui.metadataLoaded.emit(self.file_index)


class GetPreviewTask(QRunnable):

    cache_preview: dict[str, QPixmap] = {}

    cache_preview_locker: QMutex = QMutex()
    signal_locker: QMutex = QMutex()

    threadPool = QThreadPool()
    # threadPool.setMaxThreadCount(5)

    def __init__(self, item: QTableWidgetItem, file_path: str, size: int, precision: float = 1.0, load_embedded: bool = False) -> None:
        super().__init__()
        self.item: QTableWidgetItem = item
        self.file_path: str = file_path
        self.size: int = size
        self.precision: float = precision
        self.load_embedded: bool = load_embedded

        self.gui: ExifToolGUI = self.item.data(Qt.UserRole)["gui"]
        self.pixel_ratio = self.gui.app.primaryScreen().physicalDotsPerInch()/96.0

        GetPreviewTask.threadPool.start(self)

    def run(self):

        pixmap = self.get_preview(cache=True)
        self.set_preview(pixmap)
        if pixmap:
            return

        pixmap = self.get_preview(cache=False, fast=True)
        self.set_preview(pixmap)

        pixmap = self.get_preview(cache=False, fast=False)
        self.set_preview(pixmap)

    def set_preview(self, pixmap: QPixmap):
        if pixmap:
            # delay to avoid freezing UI
            with QMutexLocker(GetPreviewTask.signal_locker):
                QThread.msleep(50)

            self.gui.previewLoaded.emit(self.item, pixmap)

    def get_preview(self, cache: bool = True, fast: bool = False) -> QPixmap:

        pixmap: QPixmap = None

        if cache:
            with QMutexLocker(GetPreviewTask.cache_preview_locker):
                for file in GetPreviewTask.cache_preview.keys():
                    if os.path.samefile(file, self.file_path):
                        pixmap = GetPreviewTask.cache_preview.get(file, None)
                        break
            return pixmap

        # embedded
        if pixmap == None and fast == False:
            if self.load_embedded:
                b: bytes = self.data.load_thumbnail(self.file_path)
                if b:
                    pixmap = QPixmap()
                    pixmap.loadFromData(b)

        # image
        if pixmap == None and fast == False:
            QImageReader.setAllocationLimit(0)
            image_reader = QImageReader(self.file_path)
            image_reader.setAutoTransform(True)
            if image_reader.canRead():
                image: QImage = image_reader.read()
                pixmap = QPixmap.fromImage(image)

        # video
        if pixmap == None and fast == False:
            import cv2
            cap = cv2.VideoCapture(self.file_path)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret:
                    height, width, channels = frame.shape
                    image = QImage(frame.data, width, height, channels * width, QImage.Format_BGR888)
                    pixmap = QPixmap.fromImage(image)
            cap.release()

        # other
        if pixmap == None:
            icon: QIcon = QFileIconProvider().icon(QFileInfo(self.file_path))
            pixmap = icon.pixmap(icon.availableSizes()[0])

        if pixmap:
            precision = self.precision if self.precision >= 1.0 else 1.0
            pixmap.setDevicePixelRatio(self.pixel_ratio * precision)
            pixmap = pixmap.scaledToHeight(self.size * precision)

            with QMutexLocker(GetPreviewTask.cache_preview_locker):
                GetPreviewTask.cache_preview[self.file_path] = pixmap

            return pixmap


if __name__ == '__main__':
    gui = ExifToolGUI()
