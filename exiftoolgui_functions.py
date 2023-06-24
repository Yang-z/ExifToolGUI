import os
import re
from datetime import timedelta

from exiftoolgui_aide import ExifToolGUIAide
from exiftoolgui_settings import ExifToolGUISettings
from exiftoolgui_data import ExifToolGUIData


class ExifToolGUIFuncs:
    _instance: 'ExifToolGUIFuncs' = None

    @classmethod
    @property
    def Instance(cls) -> 'ExifToolGUIFuncs':
        if cls._instance == None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def Exec(cls, func: str, argas: dict[str,]):
        cls.Instance.funcs[func](**argas)

    def __init__(self) -> None:
        self.data: ExifToolGUIData = ExifToolGUIData.Instance
        self.settings: ExifToolGUISettings = ExifToolGUISettings.Instance

        self.funcs = {
            'rename': self.rename,
            'set_value': self.set_value,
            'copy_value': self.copy_value,
            'shift_datetime': self.shift_datetime
        }

    def rename(self, file_indexes: list[int], ref: int, format: str) -> None:

        def fill_value(match, file_index: int):
            tag = match.group(1)
            value = self.data.get(file_index, tag)
            if tag == 'File:FileName':
                value, _ = os.path.splitext(value)
            return value

        for i in file_indexes:
            new_name = re.sub(
                r'<([^>]*)>',
                lambda match: fill_value(match, i),
                format
            )
            self.data.edit(i, 'File:FileName', new_name.replace(':', ''))

    def set_value(self, file_indexes: list[int], ref: int, to_tags:str, value:str) -> None:
        list_to_tags = [tag for tag in to_tags.split(' ') if tag != ""]
        for i in file_indexes:
            for to_tag in list_to_tags:
                self.data.edit(i, to_tag, value)

    def copy_value(self, file_indexes: list[int], ref: int, from_tag: str, to_tags: str, is_datetime: bool, default_timezone: str) -> None:
        if is_datetime:
            self.copy_datetime(file_indexes, ref, from_tag, to_tags, default_timezone)
        else:
            list_to_tags = [tag for tag in to_tags.split(' ') if tag != ""]
            for i in file_indexes:
                value = self.data.get(i, from_tag)
                for to_tag in list_to_tags:
                    self.data.edit(i, to_tag, value)

    def copy_datetime(self, file_indexes: list[int], ref: int, from_tag: str, to_tags: str, default_timezone: str) -> None:
        list_to_tags = [tag for tag in to_tags.split(' ') if tag != ""]
        for i in file_indexes:
            dt_ = self.data.get_datetime(i, from_tag, None, default_timezone=default_timezone)
            for to_tag in list_to_tags:
                resolved: str = self.data.resolve_datetime(i, to_tag, dt_, default_timezone=default_timezone)
                self.data.edit(i, to_tag, resolved)

    def shift_datetime(self, file_indexes: list[int], ref: int, tag: str, to_datetime: str, by_timedelt: str, default_timezone: str) -> None:
        td: timedelta = None
        if to_datetime:
            ref_dt, _ = self.data.get_datetime(ref, tag, None, default_timezone=default_timezone)
            # to_dt = ExifToolGUIAide.Str_to_Datetime(to_datetime, default_timezone)
            to_dt, _ = self.data.get_datetime(ref, tag, to_datetime, default_timezone=default_timezone)
            td = to_dt - ref_dt
        else:
            td = ExifToolGUIAide.Str_to_Timedelt(by_timedelt)

        for i in file_indexes:
            original_dt, has_subsec = self.data.get_datetime(i, tag, None, default_timezone=default_timezone)
            shifted_dt = original_dt + td

            shifted_dt_str = self.data.resolve_datetime(i, tag, (shifted_dt, has_subsec), default_timezone=default_timezone)

            # if shifted_dt_str != original_dt_str:
            self.data.edit(i, tag, shifted_dt_str)

    # def sort_datetime(self, file_indexes: list[int], tag: str):
    #     file_indexes.sort(key=lambda i: ExifToolGUIAide.Str_to_Datetime(self.data.get(i, tag)))
    #     # file_indexes.sort(key=lambda i:self.data.get(i, tag))
    #     print(file_indexes)


if __name__ == "__main__":
    ExifToolGUIFuncs.Instance.data.reload()
    ExifToolGUIFuncs.Instance.sort_datetime([1, 2, 0], 'File:FileModifyDate')
