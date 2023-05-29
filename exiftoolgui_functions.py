from datetime import datetime, timezone, timedelta

from exiftoolgui_aide import ExifToolGUIAide
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

        self.funcs = {
            'copy_value': self.copy_value,
            'shift_datetime': self.shift_datetime
        }

    def copy_value(self, file_indexes: list[int], ref: int, from_tag: str, to_tags: str) -> None:
        list_to_tags: list[str] = to_tags.split(' ')
        # [[self.data.edit(i, to_tag, self.data.cache[i][from_tag]) for to_tag in list_to_tags] for i in file_indexes]
        for i in file_indexes:
            value = ExifToolGUIData.Get(self.data.cache[i], from_tag)
            for to_tag in list_to_tags:
                self.data.edit(i, to_tag, value)

    def shift_datetime(self, file_indexes: list[int], ref: int, tag: str, to_datetime: str, by_timedelt: str, default_timezone: str) -> None:
        # default_tz:timezone = ExifToolGUIAide.Str_to_Timezone(default_timezone)

        td:timedelta = None
        if to_datetime:
            ref_dt = ExifToolGUIAide.Str_to_Datetime(ExifToolGUIData.Get(self.data.cache[ref], tag), default_timezone)
            to_dt = ExifToolGUIAide.Str_to_Datetime(to_datetime, default_timezone)
            td = to_dt - ref_dt
        else:
            td = ExifToolGUIAide.Str_to_Timedelt(by_timedelt)

        for i in file_indexes:
            original_dt_str = ExifToolGUIData.Get(self.data.cache[i], tag)
            original_dt = ExifToolGUIAide.Str_to_Datetime(original_dt_str, default_timezone)
            shifted_dt = original_dt + td
            shifted_dt_str = ExifToolGUIAide.Datetime_to_Str(shifted_dt)
            # if shifted_dt_str != original_dt_str:
            self.data.edit(i, tag, ExifToolGUIAide.Datetime_to_Str(shifted_dt))

    def sort_datetime(self, file_indexes: list[int], tag: str):
        file_indexes.sort(key=lambda i:ExifToolGUIAide.Str_to_Datetime(ExifToolGUIData.Get(self.data.cache[i], tag)))
        # file_indexes.sort(key=lambda i:ExifToolGUIData.Get(self.data.cache[i], tag))
        print(file_indexes)

if __name__ == "__main__":
    ExifToolGUIFuncs.Instance.data.reload()
    ExifToolGUIFuncs.Instance.sort_datetime([1,2,0],'File:FileModifyDate')
