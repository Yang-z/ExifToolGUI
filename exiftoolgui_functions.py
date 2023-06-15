from datetime import datetime, timezone, timedelta
import re
import os

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
            'rename': self.rename,
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

        standard_timezone_def: dict[str,] = {
            "&QuickTime:CreateDate": "+00:00",
            "&QuickTime:ModifyDate": "+00:00",
            "&QuickTime:GPSTimeStamp": "+00:00",
            "&EXIF:GPSTimeStamp": "+00:00",
        }
        default_timezone = ExifToolGUIAide.Str_to_Timezone(default_timezone)

        for i in file_indexes:
            value = self.data.get(i, from_tag)
            dt = ExifToolGUIAide.Str_to_Datetime(value)

            for to_tag in list_to_tags:
                dt_converted = dt
                to_tag_rn = self.data.resolve_condition_tag(i, to_tag) if to_tag.startswith('?') else ExifToolGUIData.Normalise_Tag(to_tag)
                if to_tag_rn in standard_timezone_def:
                    standard_timezone = ExifToolGUIAide.Str_to_Timezone(standard_timezone_def[to_tag_rn])
                    dt_not_naive = dt
                    if dt.tzinfo == None:
                        dt_not_naive = dt.replace(tzinfo=default_timezone)
                    dt_converted = dt_not_naive.astimezone(standard_timezone)
                self.data.edit(i, to_tag, ExifToolGUIAide.Datetime_to_Str(dt_converted))

    def shift_datetime(self, file_indexes: list[int], ref: int, tag: str, to_datetime: str, by_timedelt: str, default_timezone: str) -> None:
        # default_tz:timezone = ExifToolGUIAide.Str_to_Timezone(default_timezone)

        td: timedelta = None
        if to_datetime:
            ref_dt = ExifToolGUIAide.Str_to_Datetime(ExifToolGUIData.Get(self.data.cache[ref], tag), default_timezone)
            to_dt = ExifToolGUIAide.Str_to_Datetime(to_datetime, default_timezone)
            td = to_dt - ref_dt
        else:
            td = ExifToolGUIAide.Str_to_Timedelt(by_timedelt)

        for i in file_indexes:
            original_dt_str = self.data.get(i, tag)
            original_dt = ExifToolGUIAide.Str_to_Datetime(original_dt_str, default_timezone)
            shifted_dt = original_dt + td
            shifted_dt_str = ExifToolGUIAide.Datetime_to_Str(shifted_dt)
            # if shifted_dt_str != original_dt_str:
            self.data.edit(i, tag, ExifToolGUIAide.Datetime_to_Str(shifted_dt))

    def sort_datetime(self, file_indexes: list[int], tag: str):
        file_indexes.sort(key=lambda i: ExifToolGUIAide.Str_to_Datetime(self.data.get(i, tag)))
        # file_indexes.sort(key=lambda i:self.data.get(i, tag))
        print(file_indexes)


if __name__ == "__main__":
    ExifToolGUIFuncs.Instance.data.reload()
    ExifToolGUIFuncs.Instance.sort_datetime([1, 2, 0], 'File:FileModifyDate')
