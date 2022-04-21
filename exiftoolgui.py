import sys
import locale
import base64

from PySide6.QtCore import * # QFile
from PySide6.QtUiTools import * # QUiLoader
from PySide6.QtWidgets import *
from PySide6.QtGui import *

# from qt_material import apply_stylesheet

import exiftool


from exiftoolgui_settings import ExifToolGUISettings

class ExifToolGUI():
    def __init__(self) -> None:
        self.settings:ExifToolGUISettings = ExifToolGUISettings()

        self.app:QApplication = QApplication(sys.argv)
        # apply_stylesheet(self.app, theme='dark_teal.xml')
        
        self.main_window:QMainWindow = self.load_main_window()
        

        # # After nay value in a table is modified, the ref would dead
        # # RuntimeError: Internal C++ object (PySide6.QtWidgets.QTableWidget) already deleted.
        # self.table_for_group:QTableWidget = self.main_window.findChild(QTableWidget, 'table_for_group')
        # self.tab_for_single:QTabWidget = self.main_window.findChild(QTabWidget, 'tab_for_single')
        # self.table_for_single_all:QTableWidget = self.main_window.findChild(QTableWidget, 'table_for_single_all')
        # self.table_for_single_custom:QTableWidget = self.main_window.findChild(QTableWidget, 'table_for_single_custom')
        # # use @property to get dynamically

        self.adjust_main_window()

        self.update_list_for_dirs()
        
        self.main_window.show()

    




    @property
    def table_for_group(self) -> QTableWidget:
        return self.main_window.findChild(QTableWidget, 'table_for_group')
    @property
    def tab_for_single(self) -> QTabWidget:
        return self.main_window.findChild(QTabWidget, 'tab_for_single')
    @property
    def table_for_single_all(self) -> QTableWidget:
        return self.main_window.findChild(QTableWidget, 'table_for_single_all')
    @property
    def table_for_single_custom(self) -> QTableWidget:
        return self.main_window.findChild(QTableWidget, 'table_for_single_custom')

    @property
    def list_dirs(self) -> QListWidget:
        return self.main_window.findChild(QListWidget, 'list_dirs')

    @property
    def button_add_dir(self) -> QPushButton:
        return self.main_window.findChild(QPushButton, 'button_add_dir')

    @property
    def button_remove_dir(self) -> QPushButton:
        return self.main_window.findChild(QPushButton, 'button_remove_dir')


    def load_main_window(self) -> QMainWindow:
        ui_file = QFile(self.settings.ui)
        loader = QUiLoader()
        main_window = loader.load(ui_file)
        ui_file.close()
        return main_window

    def adjust_main_window(self):
        # this should be done by designer, but...
        # ref: https://stackoverflow.com/questions/55539617/qt-designer-auto-fitting-the-tablewidget-directly-from-the-designer
        self.table_for_group.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_for_group.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table_for_single_all.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_for_single_custom.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        # QHeaderView.[ResizeMode.]Stretch
        # QHeaderView.[ResizeMode.]ResizeToContents

        # Signals
        # self.table_group.itemSelectionChanged.connect(self.on_cur_item_change_group) # 点击空白也触发，但不改变currentItem()
        # self.table_group.currentCellChanged.connect(self.on_cur_item_change_group) # 内容变化
        self.table_for_group.currentItemChanged.connect(self.on_current_item_changed__table_for_group)
        self.tab_for_single.currentChanged.connect(self.on_current_changed__tab_for_single)
        self.table_for_single_all.itemChanged.connect(self.on_item_changed__table_single)
        self.table_for_single_custom.itemChanged.connect(self.on_item_changed__table_single)

        self.button_add_dir.clicked.connect(self.on_clicked__button_add_dir)
        self.button_remove_dir.clicked.connect(self.on_clicked__button_remove_dir)


    def update_list_for_dirs(self):
        self.list_dirs.clear()
        self.list_dirs.addItems(self.settings.dirs)
        self.update_table_for_group()
        pass

    def update_table_for_group(self):
        self.table_for_group.blockSignals(True)
        # self.table_for_group.clearContents()

        self.table_for_group.setColumnCount(1+len(self.settings.tags_for_group))
        self.table_for_group.setHorizontalHeaderLabels(["SourceFile"] + self.settings.tags_for_group)

        files = self.settings.files
        file_count = len(files)
        self.table_for_group.setRowCount(file_count)
        if (file_count == 0): return

        with exiftool.ExifToolHelper() as et:
            metadata:list[dict] = et.get_tags(
                files, 
                ['EXIF:ThumbnailImage']+self.settings.tags_for_group, 
                self.settings.exiftool_params
            )

        self._fix_unicode_file_name(metadata)

        for r in range(len(metadata)):

            s:str = metadata[r]['EXIF:ThumbnailImage']
            b:bytes = base64.b64decode(s[7:])
            pic = QPixmap()
            pic.loadFromData(b)

            # label = QLabel()
            # label.setPixmap(pic)
            # self.table_for_group.setCellWidget(r,0,label)

            item_sourcefile = QTableWidgetItem(metadata[r]['SourceFile'])
            item_sourcefile.setData(Qt.DecorationRole, pic)
            self.table_for_group.setItem(r,0, item_sourcefile)

            for c in range(len(self.settings.tags_for_group)):
                self.table_for_group.setItem(r, 1+c, QTableWidgetItem(metadata[r].get(self.settings.tags_for_group[c], '')))

        self.table_for_group.blockSignals(False)

    def update_table_for_single(self):
        cur = self.tab_for_single.currentWidget().objectName()
        if(cur == 'tab_for_single_all'):
            self.update_table_for_single_all()
        elif(cur == 'tab_for_single_custom'):
            self.update_table_for_single_custom()

    def update_table_for_single_all(self):
        self.table_for_single_all.blockSignals(True)
        # self.table_for_single_all.clearContents()

        dir = self.table_for_group.item(self.table_for_group.currentItem().row(),0).text()
        
        with exiftool.ExifToolHelper() as et:
            metadata:dict = et.get_metadata(dir, self.settings.exiftool_params)[0]
        
        self.table_for_single_all.setRowCount(len(metadata))
        r = 0
        for key in metadata:
            value = metadata[key]
            self.table_for_single_all.setItem(r,0, QTableWidgetItem(key))
            self.table_for_single_all.setItem(r,1, QTableWidgetItem(str(value)))
            r = r + 1

        self.table_for_single_all.blockSignals(False)

    def update_table_for_single_custom(self):
        self.table_for_single_custom.blockSignals(True)

        self.table_for_single_custom.clearContents()

        dir = self.table_for_group.item(self.table_for_group.currentItem().row(),0).text()
        with exiftool.ExifToolHelper() as et:
            metadata:dict = et.get_tags(dir, self.settings.tags_for_single_custom, self.settings.exiftool_params)[0]
        
        self.table_for_single_custom.setRowCount(1+len(self.settings.tags_for_single_custom))
        r = 0
        self.table_for_single_custom.setItem(r, 0, QTableWidgetItem('SourceFile'))
        self.table_for_single_custom.setItem(r, 1, QTableWidgetItem(metadata['SourceFile']))
        r = 1
        for tag in self.settings.tags_for_single_custom:
            self.table_for_single_custom.setItem(r, 0, QTableWidgetItem(tag))
            value = metadata.get(tag, '')
            self.table_for_single_custom.setItem(r, 1, QTableWidgetItem(value))
            r = r + 1

        self.table_for_single_custom.blockSignals(False)
        
    def set_tag_by_table_for_single(self, item:QTableWidgetItem):
        table = item.tableWidget()

        dir = table.item(0,1).text()
        tag = table.item(item.row(), 0).text()
        value = item.text()

        print(f'set_tag_by_single[{item.row()}, {item.column()}]: "{dir}" - {{{tag} : {value}}}')
        
        with exiftool.ExifToolHelper() as et:
            r = et.set_tags(dir, {tag: value}, self.settings.exiftool_params)
            # print(r)

        # !!!!!!update table_group
        return
    
    def on_clicked__button_add_dir(self, checked=False):
        dir = QFileDialog().getExistingDirectory(self.main_window)
        if dir in self.settings.dirs: return
        self.settings.add_dir(dir)
        self.update_list_for_dirs()
        print(dir)
    
    def on_clicked__button_remove_dir(self, checked=False):
        list_dirs_curr = self.list_dirs.currentItem()
        if list_dirs_curr is None: return
        dir = list_dirs_curr.text()
        self.settings.remove_dir(dir)
        self.update_list_for_dirs()

    
    def on_current_item_changed__table_for_group(self, current:QTableWidgetItem, previous:QTableWidgetItem):
        if (    current is None or 
                (previous is not None and previous.row() == current.row())
            ): return
        self.update_table_for_single()

    def on_current_changed__tab_for_single(self, index):
        if (self.table_for_group.currentItem() is None):
            return
        self.update_table_for_single()

    def on_item_changed__table_single(self, item:QTableWidgetItem):
        self.set_tag_by_table_for_single(item)


    def _fix_unicode_file_name(self, metadata:list[dict]) -> None:
        to_be_fixed_tags:list = ['SourceFile', 'File:FileName', 'File:Directory']
        for m in metadata:
            for tag in to_be_fixed_tags:
                value:str = m.get(tag, None)
                if value and value.startswith('base64:'):
                    b:bytes=base64.b64decode(value[7:])
                    # # s:str=lm_b.decode('gb2312')
                    s:str=b.decode(locale.getpreferredencoding(False)) #cp936
                    m[tag] = s



if __name__ == '__main__':


    gui = ExifToolGUI()
    sys.exit(gui.app.exec())

