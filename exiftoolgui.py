import sys
import os
from datetime import datetime, timezone, timedelta

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
# from exiftoolgui_aide import ExifToolGUIAide


class ExifToolGUI():
    def __init__(self) -> None:
        self.app: QApplication = QApplication(sys.argv)
        # apply_stylesheet(self.app, theme='dark_teal.xml')

        self.settings: ExifToolGUISettings = ExifToolGUISettings.Instance
        self.data: ExifToolGUIData = ExifToolGUIData.Instance

        self.main_window: QMainWindow = self.load_main_window()

        # # After nay value in a table is modified, the ref would dead
        # # "RuntimeError: Internal C++ object (PySide6.QtWidgets.QTableWidget) already deleted."
        # self.table_for_group:QTableWidget = self.main_window.findChild(QTableWidget, 'table_for_group')
        # ...
        # # use @property to get dynamically

        self.adjust_main_window()

        self.reload_list_for_dirs()  # reload_table_for_group()

        self.load_tabs_for_single()
        self.load_comboBox_functions()
        self.load_layout_exiftool_options()

        self.add_event_handlers()

        self.main_window.show()
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
    def layout_exiftool_options(self) -> QGridLayout:
        return self.main_window.findChild(QGridLayout, 'gridLayout_exiftoolOptions')

    @property
    def comboBox_functions(self) -> QComboBox:
        return self.main_window.findChild(QComboBox, 'comboBox_functions')

    @property
    def groupBox_parameters(self) -> QGroupBox:
        return self.main_window.findChild(QGroupBox, 'groupBox_parameters')

    @property
    def pushButton_functions_exec(self) -> QPushButton:
        return self.main_window.findChild(QPushButton, 'pushButton_functions_exec')

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
        self.data.reload()
        self.reload_table_for_group()

    def reload_table_for_group(self):
        table: QTableWidget = self.table_for_group

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
            for column in range(0, tags_count):
                tag = tags[column]
                value = self.data.get(file_index, tag, '')
                item = QTableWidgetItem(str(value))

                item.setData(Qt.UserRole, {"file_index": file_index, "tag": tag})  # mark

                if tag == 'SourceFile':
                    item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)

                    pic = self.get_preview(value, 128)

                    if pic:
                        item.setData(Qt.DecorationRole, pic)

                        # label = QLabel()
                        # label.setPixmap(pic)
                        # table.setCellWidget(count_row,count_column,label)

                table.setItem(file_index, column, item)

        table.resizeColumnsToContents()
        table.resizeRowsToContents()
        if table.columnWidth(0) > 300:
            table.setColumnWidth(0, 300)

        table.blockSignals(False)

    def sort_table_for_group(self, column):
        table = self.table_for_group
        order = table.horizontalHeader().sortIndicatorOrder()

        h_tag = table.horizontalHeaderItem(column).text()
        is_datetime = self.data.is_datetime(h_tag)

        current_item = table.currentItem()
        selected_items = table.selectedItems()

        table.blockSignals(True)

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
            if is_datetime:
                file_index: int = row[column].data(Qt.UserRole)['file_index']
                tag: str = row[column].data(Qt.UserRole)['tag']
                dt = self.data.get_datetime(file_index, tag, value, self.settings.default_timezone)
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
                value = self.data.get(file_index, tag, '')
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

    def load_layout_exiftool_options(self):
        options = self.settings.exiftool_options
        layout: QGridLayout = self.layout_exiftool_options
        count_letters = 0
        for k in options:
            count_letters += len(k)
        r = 0
        c = 0
        for k, v in options.items():
            butt = QToolButton()
            butt.setCheckable(True)
            butt.setText(k)
            butt.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
            layout.addWidget(butt, r, c, 1, len(k))  # auto clear?
            if v == 'auto':
                butt.setChecked(False)
                butt.setEnabled(False)
            elif v == 'forced':
                butt.setChecked(True)
                butt.setEnabled(False)
            elif v == 'on':
                butt.setChecked(True)
                butt.setEnabled(True)
            elif v == 'off':
                butt.setChecked(False)
                butt.setEnabled(True)

            c += len(k)
            if c+1 > count_letters/3:
                r += 1
                c = 0

    '''################################################################
    Editting and Functions
    ################################################################'''

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

    def edit_table_for_group(self):
        table = self.table_for_group
        table.blockSignals(True)

        for row in range(0, table.rowCount()):
            for column in range(0, table.columnCount()):

                item = table.item(row, column)
                user_data: dict[str,] = item.data(Qt.UserRole)
                file_index: int = user_data['file_index']
                tag: str = user_data['tag']
                value = item.text()

                show_value, colour = self.edit_tag(file_index, tag, value)
                if show_value != None and show_value != value:
                    item.setText(show_value)
                if colour:
                    item.setBackground(QBrush(colour))

        table.blockSignals(False)

    def edit_current_tree_for_single(self):
        tab_wedget = self.tab_for_single
        title = tab_wedget.tabText(tab_wedget.currentIndex())
        tree = tab_wedget.currentWidget().findChild(QTreeWidget)
        strict = (title == 'all')
        self.edit_tree_for_single(tree, strict)

    def edit_tree_for_single(self, tree: QTreeWidget, strict: bool = False):
        tree.blockSignals(True)
        file_index: int = self.table_for_group.currentItem().data(Qt.UserRole)['file_index']

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

        dict_args['file_indexes'] = []
        table: QTableWidget = self.table_for_group
        for item in table.selectedItems():
            file_index = item.data(Qt.UserRole)['file_index']
            if file_index not in dict_args['file_indexes']:
                dict_args['file_indexes'].append(file_index)

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

        # 点击空白也触发，但不改变currentItem()
        # self.table_for_group.itemSelectionChanged.connect()
        # 点击任意按钮，再切换tab便触发？
        self.table_for_group.currentItemChanged.connect(self.on_current_item_changed__table_for_group)
        self.table_for_group.itemChanged.connect(self.on_item_changed__table_for_group)
        self.table_for_group.horizontalHeader().sectionClicked.connect(self.sort_table_for_group)

        self.comboBox_functions.currentIndexChanged.connect(self.on_currentIndexChanged__comboBox_functions)
        self.pushButton_functions_exec.clicked.connect(self.on_clicked__pushButton_functions_exec)

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
        self.data.save()
        self.edit_table_for_group()
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
        file_index = item.data(Qt.UserRole)['file_index']
        tag = item.tableWidget().horizontalHeaderItem(item.column()).text()
        value = item.text()

        self.data.edit(file_index, tag, value, save=self.settings.auto_save)
        self.edit_table_for_group()
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

        self.data.edit(file_index, tag, value, save=self.settings.auto_save)
        self.edit_table_for_group()
        # self.edit_tree_for_single(item.treeWidget())
        self.edit_current_tree_for_single()

    def on_currentIndexChanged__comboBox_functions(self, index):
        self.reload_groupBox_parameters()

    def on_clicked__pushButton_functions_exec(self):
        func, args = self.get_results__functions_parameters()
        print(func)
        print(args)
        from exiftoolgui_functions import ExifToolGUIFuncs

        ExifToolGUIFuncs.Exec(func, args)
        self.edit_table_for_group()
        self.edit_current_tree_for_single()

    '''################################################################
    Additional
    ################################################################'''

    def get_preview(self, file_path: str, size: int, load_embedded: bool = False) -> QPixmap:
        if not hasattr(self, "pixel_ratio"):
            pixel_ratio = self.app.primaryScreen().physicalDotsPerInch()/96.0

        pixmap: QPixmap = None

        if load_embedded:
            b: bytes = self.data.load_thumbnail(file_path)
            if b:
                pixmap = QPixmap()
                pixmap.loadFromData(b)

        # image
        if pixmap == None:
            image_reader = QImageReader(file_path)
            if image_reader.canRead():
                image: QImage = image_reader.read()
                pixmap = QPixmap.fromImage(image)

        # video
        if pixmap == None:
            ''' failed: always return empty image
            # video_extensions = ['.mp4', '.avi', '.mov', '.mkv']
            # if os.path.splitext(file_path)[1].lower() in video_extensions:
            #     media_player = QMediaPlayer()
            #     media_player.setSource(QUrl.fromLocalFile(file_path))

            #     video_widget = QVideoWidget()
            #     media_player.setVideoOutput(video_widget)

            #     video_widget.show()
            #     media_player.play()
            #     media_player.pause()
            #     frame = video_widget.grab().toImage()
            #     media_player.stop()
            #     pixmap = QPixmap.fromImage(frame)
            '''

            import cv2
            cap = cv2.VideoCapture(file_path)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret:
                    height, width, channels = frame.shape
                    image = QImage(frame.data, width, height, channels * width, QImage.Format_BGR888)
                    pixmap = QPixmap.fromImage(image)
            cap.release()

        # other
        if pixmap == None:
            icon: QIcon = QFileIconProvider().icon(QFileInfo(file_path))
            pixmap = icon.pixmap(icon.availableSizes()[0])

        if pixmap:
            precision = 2.0
            pixmap.setDevicePixelRatio(pixel_ratio * precision)
            pixmap = pixmap.scaledToHeight(size * precision)
            return pixmap


if __name__ == '__main__':
    gui = ExifToolGUI()
