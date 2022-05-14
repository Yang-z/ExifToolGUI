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
        # self.table_for_group.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table_for_group.horizontalHeader().setSectionsMovable(True)
        # self.table_for_group.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table_for_group.verticalHeader().setSectionsMovable(True)

        self.tree_for_single_all.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.tree_for_single_custom.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)

    def reload_list_for_dirs(self):
        self.list_dirs.clear()
        self.list_dirs.addItems(self.settings.dirs)
        self.data.reload()
        self.reload_table_for_group()

    def reload_table_for_group(self):
        self.table_for_group.blockSignals(True)
        self.table_for_group.clear()

        tags = ['SourceFile'] + self.settings.tags_for_group
        tag_count = len(tags)
        self.table_for_group.setColumnCount(tag_count)
        self.table_for_group.setHorizontalHeaderLabels(tags)

        file_count = len(self.data.cache)
        self.table_for_group.setRowCount(file_count)

        for row in range(0, file_count):
            metadata = self.data.cache[row]
            for column in range(0, tag_count):
                tag = tags[column]
                value = ExifToolGUIData.Get(metadata, tag, '')
                item = QTableWidgetItem(str(value))

                if(tag == 'SourceFile'):
                    item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)

                    b: bytes = ExifToolGUIData.Get_Thumbnail(metadata)
                    if(b != None):
                        pic = QPixmap()
                        pic.loadFromData(b)
                        item.setData(Qt.DecorationRole, pic)

                        # label = QLabel()
                        # label.setPixmap(pic)
                        # self.table_for_group.setCellWidget(count_row,count_column,label)

                self.table_for_group.setItem(row, column, item)

        self.table_for_group.resizeColumnsToContents()
        self.table_for_group.resizeRowsToContents()
        if(self.table_for_group.columnWidth(0) > 300):
            self.table_for_group.setColumnWidth(0, 300)

        self.table_for_group.blockSignals(False)

    def reload_current_tree_for_single(self):
        cur = self.tab_for_single.currentWidget().objectName()
        if(cur == 'tab_for_single_all'):
            self.reload_tree_for_single_all()
        elif(cur == 'tab_for_single_custom'):
            self.reload_tree_for_single_custom()

    def reload_tree_for_single_all(self):
        tree = self.tree_for_single_all
        file_index: int = self.table_for_group.currentRow()
        metadata: dict[str, ] = self.data.cache[file_index]
        self.reload_tree_for_single(tree, metadata)
        self.edit_tree_for_single(tree, strict=True)

    def reload_tree_for_single_custom(self):
        tree = self.tree_for_single_custom
        file_index: int = self.table_for_group.currentRow()
        metadata = self.data.cache[file_index]
        metadata_temp: dict[str, ] = {
            'SourceFile': metadata['SourceFile']
        }
        for tag in self.settings.tags_for_single_custom:
            value = ExifToolGUIData.Get(metadata, tag, '')
            metadata_temp[tag] = value
        self.reload_tree_for_single(tree, metadata_temp)
        self.edit_tree_for_single(tree)

    def reload_tree_for_single(self, tree: QTreeWidget, metadata: dict[str, ]):
        tree.blockSignals(True)
        tree.clear()

        root: dict = {
            'item': None,
            'childen': {}
        }
        for tag in metadata:
            tag_list: list = tag.split(':')

            # apply max group level
            if(len(tag_list) - 2 > self.settings.max_group_level):
                tag_name = tag_list.pop()
                tag_list = tag_list[0:self.settings.max_group_level+1]
                tag_list.append(tag_name)

            # siplify groups
            if(self.settings.simplify_group_level):
                # combine same group names nearby
                for i in range(0, len(tag_list)-1):
                    if(tag_list[i] == ''):
                        continue
                    for j in range(i+1, len(tag_list)-1):
                        if(tag_list[j] == tag_list[i]):
                            tag_list[j] = ''
                        else:
                            break
                # delete empty tag groups
                while(True):
                    if('' not in tag_list):
                        break
                    tag_list.remove('')

            # form tree view
            parent: dict = root
            for i in range(0, len(tag_list)):
                tag_sub = tag_list[i]
                child = parent['childen'].get(tag_sub, None)
                if(child == None or i == len(tag_list)-1):
                    item_child = QTreeWidgetItem()
                    item_child.setText(0, tag_sub)
                    item_parent: QTreeWidgetItem = parent['item']
                    if(item_parent == None):
                        tree.addTopLevelItem(item_child)
                    else:
                        item_parent.addChild(item_child)

                    if (i != len(tag_list)-1):
                        child = {
                            'item': item_child,
                            'childen': {}
                        }
                        parent['childen'][tag_sub] = child
                    else:
                        value = metadata[tag]
                        # check the type of value
                        type_v = type(value)
                        if(type_v != str):
                            value = str(value)
                            if(type_v != int and type_v != float and type_v != bool):  # and type_v != list
                                print(f"{tag}:{type_v}")
                        item_child.setText(1, value)
                        item_child.setText(2, tag)  # save full tag
                        # item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsEditable)
                        # tree.openPersistentEditor(item, 1)
                parent = child

        tree.expandAll()
        tree.resizeColumnToContents(0)
        if(tree.columnWidth(0) > 200):
            tree.setColumnWidth(0, 200)

        tree.blockSignals(False)

    '''################################################################
    Editting and results
    ################################################################'''

    def get_cloumn__table_for_group(self, tag: str) -> int:
        table = self.table_for_group
        for c in range(0, table.columnCount()):
            if(ExifToolGUIData.Is_Tag_Equal(tag, table.horizontalHeaderItem(c).text())):
                return c
        return None

    def edit_table_for_group(self):
        self.table_for_group.blockSignals(True)
        for file_index in range(0, len(self.data.cache_edited)):

            # update source_file
            column_sf = self.get_cloumn__table_for_group('SourceFile')
            item_sf = self.table_for_group.item(file_index, column_sf)
            sf_old: str = item_sf.text()
            sf: str = self.data.cache[file_index]['SourceFile']
            if(sf_old != sf):
                item_sf.setText(sf)
                item_sf.setForeground(Qt.darkGreen)

            # update tags modified
            metadata_modified = self.data.cache_edited[file_index]
            for tag in metadata_modified:
                column = self.get_cloumn__table_for_group(tag)
                if(column == None):
                    continue
                item = self.table_for_group.item(file_index, column)

                # modified
                value_modified = metadata_modified[tag]
                item.setText(value_modified)
                item.setBackground(QBrush(Qt.yellow))  # or QColor(r, g, b)
                # font = item.font()
                # font.setBold(True)
                # item.setFont(font)

                # check if failded
                value_saved = ExifToolGUIData.Get(self.data.cache[file_index], tag, '')
                if(value_modified == str(value_saved)):
                    item.setBackground(QBrush(Qt.green))
                else:
                    value_failed = ExifToolGUIData.Get(self.data.cache_failed[file_index], tag, None)
                    if(value_modified == value_failed):
                        item.setBackground(QBrush(Qt.red))
                        item.setText(str(value_saved))

        self.table_for_group.blockSignals(False)

    @staticmethod
    def get_item__tree_for_single(tree: QTreeWidget, tag: str) -> QTreeWidgetItem:
        it = QTreeWidgetItemIterator(tree)
        while(it.value()):
            item = it.value()
            if(item.childCount() == 0):
                tag_found: str = item.text(2)
                if(ExifToolGUIData.Is_Tag_Equal(tag_found, tag)):
                    return it.value()
            it += 1
        return None

    @staticmethod
    def get_items__tree_for_single(tree: QTreeWidget, tag: str) -> list[QTreeWidgetItem]:
        it = QTreeWidgetItemIterator(tree)
        items: list[QTreeWidgetItem] = []
        while(it.value()):
            item = it.value()
            if(item.childCount() == 0):
                tag_found: str = item.text(2)
                if(ExifToolGUIData.Is_Tag_Equal(tag_found, tag)):
                    items.append(it.value())
            it += 1
        return items

    def edit_current_tree_for_single(self):
        cur = self.tab_for_single.currentWidget().objectName()
        if(cur == 'tab_for_single_all'):
            self.edit_tree_for_single(self.tree_for_single_all, strict=True)
        elif(cur == 'tab_for_single_custom'):
            self.edit_tree_for_single(self.tree_for_single_custom)

    def edit_tree_for_single(self, tree: QTreeWidget, strict: bool = False):
        tree.blockSignals(True)
        file_index: int = self.table_for_group.currentRow()
        metadata_modified = self.data.cache_edited[file_index]

        # update source_file
        item_sf = self.get_item__tree_for_single(tree, 'SourceFile')
        sf: str = self.data.cache[file_index]['SourceFile']
        sf_old = item_sf.text(1)
        if(sf_old != sf):
            item_sf.setText(1, sf)
            item_sf.setForeground(1, Qt.darkGreen)

        for tag in metadata_modified:
            items = self.get_items__tree_for_single(tree, tag)

            for item in items:
                # modified
                value_modified: str = metadata_modified[tag]
                item.setText(1, value_modified)
                item.setBackground(1, QBrush(Qt.yellow))
                # if(value_modified == ''):
                #     item.setBackground(0, QBrush(Qt.yellow))

                # check if failed
                value_saved = ExifToolGUIData.Get(self.data.cache[file_index], item.text(2), '', strict)
                if(value_modified == str(value_saved)):
                    item.setBackground(1, QBrush(Qt.green))
                else:
                    value_failed = ExifToolGUIData.Get(self.data.cache_failed[file_index], tag, None)
                    if(value_modified == value_failed):
                        item.setBackground(1, QBrush(Qt.red))
                        item.setText(1, str(value_saved))

        tree.blockSignals(False)

    '''################################################################
    Event Handlers
    ################################################################'''

    def add_event_handlers(self):
        # Signals
        self.button_add_dir.clicked.connect(self.on_clicked__button_add_dir)
        self.button_remove_dir.clicked.connect(self.on_clicked__button_remove_dir)
        self.button_save.clicked.connect(self.on_clicked__button_save)

        # self.table_group.itemSelectionChanged.connect() # 点击空白也触发，但不改变currentItem()
        self.table_for_group.currentItemChanged.connect(self.on_current_item_changed__table_for_group)
        self.table_for_group.itemChanged.connect(self.on_item_changed__table_for_group)

        self.tab_for_single.currentChanged.connect(self.on_current_changed__tab_for_single)

        self.tree_for_single_all.itemDoubleClicked.connect(self.on_item_double_clicked__tree_for_single)
        self.tree_for_single_all.currentItemChanged.connect(self.on_current_item_changed__tree_for_single)
        self.tree_for_single_all.itemChanged.connect(self.on_item_changed__tree_for_single)

        self.tree_for_single_custom.itemDoubleClicked.connect(self.on_item_double_clicked__tree_for_single)
        self.tree_for_single_custom.currentItemChanged.connect(self.on_current_item_changed__tree_for_single)
        self.tree_for_single_custom.itemChanged.connect(self.on_item_changed__tree_for_single)

    def on_clicked__button_save(self, checked=False):
        self.data.save()
        self.edit_table_for_group()
        self.edit_current_tree_for_single()

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
        file_index = item.row()
        tag = item.tableWidget().horizontalHeaderItem(item.column()).text()
        value = item.text()

        self.data.edit(file_index, tag, value, save=self.settings.auto_save)
        self.edit_table_for_group()
        self.edit_current_tree_for_single()

    def on_current_changed__tab_for_single(self, index):
        if(self.table_for_group.currentItem() == None):
            return
        self.reload_current_tree_for_single()

    def on_item_double_clicked__tree_for_single(self, item: QTreeWidgetItem, clumn: int):
        if(clumn == 1 and item.childCount() == 0 and not item.text(1).startswith('(Binary data')):
            item.treeWidget().openPersistentEditor(item, 1)

    def on_current_item_changed__tree_for_single(self, current: QTreeWidgetItem, previous: QTreeWidgetItem):
        if(previous and previous.childCount() == 0):
            previous.treeWidget().closePersistentEditor(previous, 1)

    def on_item_changed__tree_for_single(self, item: QTreeWidgetItem, column: int):
        item.treeWidget().closePersistentEditor(item, 1)
        if(column != 1):
            return
        file_index: int = self.table_for_group.currentRow()
        value = item.text(1)

        tag: str = item.text(2)  # full tag

        self.data.edit(file_index, tag, value, save=self.settings.auto_save)
        self.edit_table_for_group()
        # self.edit_tree_for_single(item.treeWidget())
        self.edit_current_tree_for_single()


if __name__ == '__main__':
    gui = ExifToolGUI()
