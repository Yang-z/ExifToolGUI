import json
import os
import exiftool

from PyQt6.QtWidgets import *
from PyQt6.QtCore import Qt


class ExifToolGUIMainWindow(QMainWindow):
    def __init__(self, parent=None):
        super(ExifToolGUIMainWindow, self).__init__(parent)
        
        # self._loading = True

        self.settings:dict={}
        self.dirs:list=[]
        self.tags_for_group_view:list=[]
        self.tags_for_single_view:dict={}
        self.exiftool_params:list=[]

        self.files:list=[]


        self.tab_menu:QTabWidget
        self.table_group:QTableWidget
        self.tab_single:QTabWidget

        self.init_settings()

        self.init_ui()


    def init_settings(self):
        with open('exiftoolgui_settings.json') as f:
            self.settings = json.load(f)
        
        self.dirs = self.settings['dirs']
        self.tags_for_group_view = self.settings['tags_for_group_view']
        self.tags_for_single_view = self.settings['tags_for_single_view']
        self.exiftool_params = self.settings['exiftool_params']

        for dir in self.dirs:
            f_o_d_s = os.listdir(dir)
            for f_o_d in f_o_d_s:
                p = os.path.join(dir,f_o_d)
                if os.path.isfile(p):
                    self.files.append(p)


    def init_ui(self):
        widget_main = QWidget()
        layout_main = QHBoxLayout()
        splitter_main = QSplitter(Qt.Orientation.Vertical)
        splitter_meta_view = QSplitter(Qt.Orientation.Horizontal)

        self.init_tab_menu()

        self.init_table_group()
        # self.table_group.setFrameShape(QFrame.StyledPanel)

        self.init_tab_single()

        splitter_meta_view.addWidget(self.table_group) # left
        splitter_meta_view.addWidget(self.tab_single) # right
        splitter_meta_view.setStretchFactor(0,10)
        splitter_meta_view.setStretchFactor(1,5)

        splitter_main.addWidget(self.menu) # up
        splitter_main.addWidget(splitter_meta_view) # mid

        layout_main.addWidget(splitter_main)
        widget_main.setLayout(layout_main)
        self.setCentralWidget(widget_main)

        self.setGeometry(0, 0, 1280, 800)
        self.setWindowTitle("MateFixer")
        
    def init_tab_menu(self):
        self.menu = QTabWidget()
        self.menu.setFixedHeight(120)
        
        tag_file = QWidget()

        layout_file = QGridLayout()
        layout_file.setAlignment(Qt.AlignmentFlag.AlignLeft)

        list_dirs = QListWidget()
        list_dirs.setMaximumWidth(600)
        c = 0
        for item in self.dirs:
            list_dirs.addItem(item)
            c = c + 1
        
        layout_file.addWidget(list_dirs)
        tag_file.setLayout(layout_file)
        self.menu.addTab(tag_file, "File")


        tag_options = QWidget()
        self.menu.addTab(tag_options, "Options")
        

        return

    def init_table_group(self):
        self.table_group = QTableWidget()
        self.table_group.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_group.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        self.table_group.setColumnCount(1+len(self.tags_for_group_view))
        self.table_group.setHorizontalHeaderLabels(["SourceFile"] + self.tags_for_group_view)

        self.get_tags_group()

    def init_tab_single(self):
        self.tab_single = QTabWidget()
        table_all = self.init_table_single("All")
        self.tab_single.addTab(table_all, "All")

        for cat in self.tags_for_single_view:
            table = self.init_table_single(cat)
            self.tab_single.addTab(table, cat)

        self.tab_single.currentChanged.connect(self.on_cur_change_tab_single)

        return

    def init_table_single(self, cat:str):
        table = QTableWidget()
        table.setAccessibleName(cat)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(["Tag Name", "Value"])

        return table


    def on_cur_item_change_table_group(self, current: QTableWidgetItem, previous: QTableWidgetItem):
        # print(current == self.table_group.currentItem()) # True
        # print(current.tableWidget() == self.table_group) # True

        if(previous is not None and current.row() == previous.row()):
            return
        self.get_tags_single()

    def on_cur_change_tab_single(self, index: int):
        if(self.table_group.currentItem() is None):
            return
        self.get_tags_single()


    def get_tags_group(self):
        self.table_group.clearContents()

        self.table_group.setRowCount(len(self.files))
        
        with exiftool.ExifToolHelper() as et:
            metadata = et.get_tags(self.files, self.tags_for_group_view, self.exiftool_params)
        for r in range(len(metadata)):
            self.table_group.setItem(r,0, QTableWidgetItem(metadata[r]['SourceFile']))
            for c in range(len(self.tags_for_group_view)):
                self.table_group.setItem(r,c+1, QTableWidgetItem(metadata[r].get(self.tags_for_group_view[c], '')))

        # self.table_group.itemSelectionChanged.connect(self.on_cur_item_change_group) # 点击空白也触发，但不改变currentItem()
        # self.table_group.itemClicked.connect(self.on_cur_item_change_group)
        # self.table_group.currentCellChanged.connect(self.on_cur_item_change_group)
        self.table_group.currentItemChanged.connect(self.on_cur_item_change_table_group)


    def get_tags_single(self):
        dir = self.table_group.item(self.table_group.currentItem().row(),0).text()
        table: QTableWidget = (self.tab_single.currentWidget(), None)[False]
        table.clearContents()
        cat = table.accessibleName()

        print (f'get_tags_single: [{cat}] - "{dir}"')

        try: 
            while True:
                table.itemChanged.disconnect(self.set_tag_single)
        except Exception as e: 
            # print(e)
            pass

        with exiftool.ExifToolHelper() as et:
            if cat == 'All':
                metadata = et.get_metadata(dir, self.exiftool_params)
            else:
                metadata = et.get_tags(dir, self.tags_for_single_view[cat], self.exiftool_params)
        
        if cat == 'All':
            table.setRowCount(len(metadata[0]))
            r = 0
            for k in metadata[0]:
                value = metadata[0][k]
                table.setItem(r,0, QTableWidgetItem(k))
                table.setItem(r,1, QTableWidgetItem(str(value)))
                r = r + 1
        else:
            table.setRowCount(1+len(self.tags_for_single_view[cat]))
            table.setItem(0, 0, QTableWidgetItem('SourceFile'))
            table.setItem(0, 1, QTableWidgetItem(metadata[0]['SourceFile']))

            r = 1
            for item in self.tags_for_single_view[cat]:
                table.setItem(r, 0, QTableWidgetItem(item))
                value = metadata[0].get(item, '')
                table.setItem(r, 1, QTableWidgetItem(value))
                r = r + 1

        table.itemChanged.connect(self.set_tag_single)


    def set_tag_single(self, item: QTableWidgetItem):
        table = item.tableWidget()

        # if(not table.hasFocus()):
        #     print(f"{item.row()}, {item.column()} : lost focus!!!")
        #     return

        dir = table.item(0,1).text()
        tag = table.item(item.row(), 0).text()
        value = item.text()

        # print(f"set_tag_single: {item.row()}, {item.column()} : {item.text()}")
        print(f'set_tag_single: "{dir}" : {tag} : {value}')
        
        with exiftool.ExifToolHelper() as et:
            r = et.set_tags(dir, {tag: value}, self.exiftool_params)
            # print(r)


        # !!!!!!update table_group




if __name__ == '__main__':
    import sys

    app = QApplication(sys.argv)
    etg = ExifToolGUIMainWindow()
    etg.show()

    sys.exit(app.exec())

