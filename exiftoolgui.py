import sys

from PySide6.QtCore import *  # QFile
from PySide6.QtUiTools import *  # QUiLoader
from PySide6.QtWidgets import *
from PySide6.QtGui import *

# from qt_material import apply_stylesheet

from exiftoolgui_settings import ExifToolGUISettings
from exiftoolgui_data import ExifToolGUIData


class ExifToolGUI():
    def __init__(self) -> None:
        self.app: QApplication = QApplication(sys.argv)
        # apply_stylesheet(self.app, theme='dark_teal.xml')

        self.settings: ExifToolGUISettings = ExifToolGUISettings()
        self.data: ExifToolGUIData = ExifToolGUIData(self.settings)

        self.main_window: QMainWindow = self.load_main_window()

        # # After nay value in a table is modified, the ref would dead
        # # "RuntimeError: Internal C++ object (PySide6.QtWidgets.QTableWidget) already deleted."
        # self.table_for_group:QTableWidget = self.main_window.findChild(QTableWidget, 'table_for_group')
        # ...
        # # use @property to get dynamically

        self.adjust_main_window()
        self.reload_list_for_dirs()
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
    def tree_for_single_all(self) -> QTreeWidget:
        return self.main_window.findChild(QTreeWidget, 'tree_for_single_all')

    @property
    def tree_for_single_custom(self) -> QTreeWidget:
        return self.main_window.findChild(QTreeWidget, 'tree_for_single_custom')

    # @property
    # def current_tree_for_single(self) -> QTreeView:
    #     if(self.tab_for_single.currentWidget().objectName() == 'tab_for_single_all'):
    #         return self.tree_for_single_all
    #     elif(self.tab_for_single.currentWidget().objectName() == 'tab_for_single_custom'):
    #         return self.tree_for_single_custom
    #     return None

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

    def load_main_window(self) -> QMainWindow:
        ui_file = QFile(self.settings.ui)
        loader = QUiLoader()
        main_window = loader.load(ui_file)
        ui_file.close()
        return main_window

    '''################################################################
    Reload UI
    ################################################################'''

    def adjust_main_window(self):
        # this should be done by designer, but...
        # ref: https://stackoverflow.com/questions/55539617/qt-designer-auto-fitting-the-tablewidget-directly-from-the-designer
        self.table_for_group.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch)
        self.table_for_group.horizontalHeader().setSectionsMovable(True)
        self.table_for_group.verticalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents)
        self.table_for_group.verticalHeader().setSectionsMovable(True)

    def reload_list_for_dirs(self):
        self.list_dirs.clear()
        self.list_dirs.addItems(self.settings.dirs)
        self.data.reload()
        self.reload_table_for_group()
        pass

    def reload_table_for_group(self):
        self.table_for_group.blockSignals(True)
        self.table_for_group.clear()

        self.table_for_group.setColumnCount(
            1+len(self.settings.tags_for_group))
        self.table_for_group.setHorizontalHeaderLabels(
            ['SourceFile'] + self.settings.tags_for_group)

        file_count = len(self.data.cache)
        self.table_for_group.setRowCount(file_count)

        count_row = 0
        for source_file in self.data.cache:
            count_column = 0
            item_sourcefile = QTableWidgetItem(source_file)
            item_sourcefile.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)

            b: bytes = self.data.get_thumbnail(source_file)
            if (b):
                pic = QPixmap()
                pic.loadFromData(b)
                item_sourcefile.setData(Qt.DecorationRole, pic)

                # label = QLabel()
                # label.setPixmap(pic)
                # self.table_for_group.setCellWidget(count_row,count_column,label)

            self.table_for_group.setItem(
                count_row,
                count_column,
                item_sourcefile
            )

            count_column = 1
            for tag in self.settings.tags_for_group:
                value = self.data.get(source_file, tag, '')
                self.table_for_group.setItem(
                    count_row,
                    count_column,
                    QTableWidgetItem(str(value))
                )
                count_column = count_column + 1
            count_row = count_row + 1

        self.table_for_group.blockSignals(False)

    def reload_current_tree_for_single(self):
        cur = self.tab_for_single.currentWidget().objectName()
        if(cur == 'tab_for_single_all'):
            self.reload_tree_for_single_all()
        elif(cur == 'tab_for_single_custom'):
            self.reload_tree_for_single_custom()

    def reload_tree_for_single_all(self):
        tree = self.tree_for_single_all
        source_file: str = self.table_for_group.item(
            self.table_for_group.currentItem().row(), 0
        ).text()
        metadata: dict[str, ] = self.data.cache[source_file]
        self.reload_tree_for_single(tree, metadata)
        self.edit_tree_for_single(tree)

    def reload_tree_for_single_custom(self):
        tree = self.tree_for_single_custom
        source_file: str = self.table_for_group.item(
            self.table_for_group.currentItem().row(), 0
        ).text()
        metadata: dict[str, ] = {
            'SourceFile': source_file
        }
        for tag in self.settings.tags_for_single_custom:
            metadata[tag] = self.data.get(source_file, tag, '')
        self.reload_tree_for_single(tree, metadata)
        self.edit_tree_for_single(tree)

    @staticmethod
    def reload_tree_for_single(tree: QTreeWidget, metadata: dict[str, ]):
        tree.blockSignals(True)
        tree.clear()

        # root = QTreeWidgetItem()
        # root.setText(0, "root")
        # tree.addTopLevelItem(root)
        structure: dict = {
            'item': None,
            'childen': {}
        }
        for tag in metadata:
            tag_s = tag.split(':')
            parent: dict = structure
            for tag_l in tag_s:
                child = parent['childen'].get(tag_l, None)
                if(child == None):
                    item_child = QTreeWidgetItem()
                    item_child.setText(0, tag_l)
                    item_parent: QTreeWidgetItem = parent['item']
                    if(item_parent == None):
                        tree.addTopLevelItem(item_child)
                    else:
                        item_parent.addChild(item_child)
                    child = {
                        'item': item_child,
                        'childen': {}
                    }
                    parent['childen'][tag_l] = child
                parent = child

            item: QTreeWidgetItem = child['item']
            item.setText(1, str(metadata[tag]))
            # item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsEditable)
            # tree.openPersistentEditor(item, 1)
        tree.expandAll()
        tree.blockSignals(False)

    '''################################################################
    Editting and results
    ################################################################'''

    def get_cloumn__table_for_group(self, tag: str) -> int:
        table = self.table_for_group
        for c in range(0, table.columnCount()):
            if (ExifToolGUIData.is_tag_equal(tag, table.horizontalHeaderItem(c).text())):
                return c
        return None

    def get_row__table_for_group(self, source_file: str) -> int:
        table = self.table_for_group
        for r in range(0, table.rowCount()):
            c = self.get_cloumn__table_for_group('SourceFile')
            if (c != None):
                item = table.item(r, c)
                if (item.text() == source_file):
                    return r
        return None

    # def get_item__table_for_group(self, source_file: str, tag: str):
    #     c = self.get_cloumn__table_for_group(tag)
    #     r = self.get_row__table_for_group(source_file)
    #     if (c != None and r != None):
    #         return self.table_for_group.item(r, c)
    #     return None

    def edit_table_for_group(self):
        self.table_for_group.blockSignals(True)
        for source_file in self.data.cache_modified:
            row = self.get_row__table_for_group(source_file)
            if(row == None):
                continue
            for tag in self.data.cache_modified[source_file]:
                column = self.get_cloumn__table_for_group(tag)
                if(column == None):
                    continue
                item = self.table_for_group.item(row, column)

                # modified
                value_modified = self.data.cache_modified[source_file][tag]
                item.setText(value_modified)
                item.setBackground(QBrush(Qt.yellow))  # or QColor(r, g, b)
                # font = item.font()
                # font.setBold(True)
                # item.setFont(font)

                # check if failded
                value_saved = self.data.get(source_file, tag, '')
                if(value_modified == str(value_saved)):
                    item.setBackground(QBrush(Qt.green))
                else:
                    value_failed = self.data.get_failed(source_file, tag, None)
                    if(value_modified == value_failed):
                        item.setBackground(QBrush(Qt.red))
                        item.setText(str(value_saved))

        self.table_for_group.blockSignals(False)

    @staticmethod
    def get_item__tree_for_single(tree: QTreeWidget, tag: str):
        it = QTreeWidgetItemIterator(tree)
        while(it.value()):
            item = it.value()
            if(item.childCount() == 0):
                tag_l: list = [item.text(0)]
                while(item.parent()):
                    tag_l.insert(0, item.parent().text(0))
                    item = item.parent()
                tag_found: str = ':'.join(tag_l)

                if(ExifToolGUIData.is_tag_equal(tag_found, tag)):
                    return it.value()
            it += 1
        return None

    def edit_current_tree_for_single(self):
        cur = self.tab_for_single.currentWidget().objectName()
        if(cur == 'tab_for_single_all'):
            self.edit_tree_for_single(self.tree_for_single_all)
        elif(cur == 'tab_for_single_custom'):
            self.edit_tree_for_single(self.tree_for_single_custom)

    def edit_tree_for_single(self, tree: QTreeWidget):
        tree.blockSignals(True)
        source_file: str = tree.findItems(
            'SourceFile', Qt.MatchExactly, 0
        )[0].text(1)

        metadata_modified = self.data.cache_modified.get(source_file, None)
        if(metadata_modified != None):
            for tag in metadata_modified:
                item = self.get_item__tree_for_single(tree, tag)
                if(item == None):
                    continue

                # modified
                value_modified: str = metadata_modified[tag]
                item.setText(1, value_modified)
                item.setBackground(1, QBrush(Qt.yellow))
                # if(value_modified == ''):
                #     item.setBackground(0, QBrush(Qt.yellow))

                # check if failed
                value_saved = self.data.get(source_file, tag, '')
                if(value_modified == str(value_saved)):
                    item.setBackground(1, QBrush(Qt.green))
                else:
                    value_failed = self.data.get_failed(source_file, tag, None)
                    if(value_modified == value_failed):
                        item.setBackground(1, QBrush(Qt.red))
                        item.setText(1, str(value_saved))

        tree.blockSignals(False)

    '''################################################################
    Event Handlers
    ################################################################'''

    def add_event_handlers(self):
        # Signals
        self.button_add_dir.clicked.connect(
            self.on_clicked__button_add_dir)
        self.button_remove_dir.clicked.connect(
            self.on_clicked__button_remove_dir)
        self.button_save.clicked.connect(
            self.on_clicked__button_save)

        # self.table_group.itemSelectionChanged.connect() # 点击空白也触发，但不改变currentItem()
        self.table_for_group.currentItemChanged.connect(
            self.on_current_item_changed__table_for_group)
        self.table_for_group.itemChanged.connect(
            self.on_item_changed__table_for_group)

        self.tab_for_single.currentChanged.connect(
            self.on_current_changed__tab_for_single)

        self.tree_for_single_all.itemDoubleClicked.connect(
            self.on_item_double_clicked__tree_for_single)
        self.tree_for_single_all.currentItemChanged.connect(
            self.on_current_item_changed__tree_for_single)
        self.tree_for_single_all.itemChanged.connect(
            self.on_item_changed__tree_for_single)

        self.tree_for_single_custom.itemDoubleClicked.connect(
            self.on_item_double_clicked__tree_for_single)
        self.tree_for_single_custom.currentItemChanged.connect(
            self.on_current_item_changed__tree_for_single)
        self.tree_for_single_custom.itemChanged.connect(
            self.on_item_changed__tree_for_single)

    def on_clicked__button_save(self, checked=False):
        self.data.save()
        self.reload_table_for_group()
        self.edit_table_for_group()
        # self.edit_current_tree_for_single()
        self.table_for_group.setCurrentCell(self.table_for_group.rowCount()-1,0)

    def on_clicked__button_add_dir(self, checked=False):
        dir = QFileDialog().getExistingDirectory(self.main_window)
        if dir in self.settings.dirs:
            return
        self.settings.add_dir(dir)
        self.reload_list_for_dirs()
        print(dir)

    def on_clicked__button_remove_dir(self, checked=False):
        list_dirs_curr = self.list_dirs.currentItem()
        if list_dirs_curr is None:
            return
        dir = list_dirs_curr.text()
        self.settings.remove_dir(dir)
        self.reload_list_for_dirs()

    def on_current_item_changed__table_for_group(self, current: QTableWidgetItem, previous: QTableWidgetItem):
        if(
            current == None or
            (previous != None and previous.row() == current.row())
        ):
            return
        self.reload_current_tree_for_single()

    def on_item_changed__table_for_group(self, item: QTableWidgetItem):
        # get source_file
        source_file = item.tableWidget().item(
            item.row(),
            self.get_cloumn__table_for_group('SourceFile')
        ).text()
        tag = item.tableWidget().horizontalHeaderItem(item.column()).text()
        value = item.text()

        self.data.set(source_file, tag, value, save=self.settings.auto_save)
        self.edit_table_for_group()
        self.edit_current_tree_for_single()

    def on_current_changed__tab_for_single(self, index):
        if(self.table_for_group.currentItem() == None):
            return
        self.reload_current_tree_for_single()

    def on_item_double_clicked__tree_for_single(self, item: QTreeWidgetItem, clumn: int):
        if(clumn == 1 and item.childCount() == 0):
            item.treeWidget().openPersistentEditor(item, 1)

    def on_current_item_changed__tree_for_single(self, current: QTreeWidgetItem, previous: QTreeWidgetItem):
        if(previous and previous.childCount() == 0):
            previous.treeWidget().closePersistentEditor(previous, 1)

    def on_item_changed__tree_for_single(self, item: QTreeWidgetItem, column: int):
        item.treeWidget().closePersistentEditor(item, 1)
        if(column != 1):
            return
        source_file: str = item.treeWidget().findItems(
            'SourceFile', Qt.MatchExactly, 0
        )[0].text(1)
        value = item.text(1)

        tag_l: list[str] = [item.text(0)]
        while(item.parent()):
            tag_l.insert(0, item.parent().text(0))
            item = item.parent()
        tag: str = ':'.join(tag_l)

        self.data.set(source_file, tag, value, save=self.settings.auto_save)
        self.edit_table_for_group()
        # self.edit_tree_for_single(item.treeWidget())
        self.edit_current_tree_for_single()


if __name__ == '__main__':
    gui = ExifToolGUI()
