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
    def Exec(cls, func:str, argas: dict[str,]):
        cls.Instance.funcs[func](**argas)
    

    def __init__(self) -> None:
        self.data: ExifToolGUIData = ExifToolGUIData.Instance

        self.funcs = {
        'copy_value':self.copy_value,
        'shift_datetime':self.shift_datetime
        }

    def copy_value(self, file_indexes: list[int], from_tag: str, to_tags: str) -> None:
        list_to_tags:list[str] = to_tags.split(' ')
        # [[self.data.edit(i, to_tag, self.data.cache[i][from_tag]) for to_tag in list_to_tags] for i in file_indexes]
        for i in file_indexes:
            value = ExifToolGUIData.Get(self.data.cache[i], from_tag)
            for to_tag in list_to_tags:
                self.data.edit(i, to_tag, value)

    def shift_datetime(self, file_indexes: list[int], ref: int, tag: str, to_datetime: str, by_timedelt:str) -> None:
        ref_datetime = ExifToolGUIAide.Str_to_Datetime(ExifToolGUIData.Get(self.data.cache[ref], tag))
        dst_datetime = ExifToolGUIAide.Str_to_Datetime(tag)
        td: timedelta = dst_datetime - ref_datetime

        for i in file_indexes:
            if i == ref:
                continue
            original_value = ExifToolGUIData.Get(self.data.cache[i], tag)
            original_dt = ExifToolGUIAide.Str_to_Datetime(original_value)
            shifted_dt = original_dt + td
            self.data.edit(i, tag, ExifToolGUIAide.Datetime_to_Str(shifted_dt))


if __name__ == "__main__":
    pass
