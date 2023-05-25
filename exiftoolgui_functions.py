from datetime import datetime, timezone, timedelta

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

        }

    def copy_value(self, file_indexes: list[int], from_tag: str, to_tags: str) -> None:
        list_to_tags:list[str] = to_tags.split(' ')
        # [[self.data.edit(i, to_tag, self.data.cache[i][from_tag]) for to_tag in list_to_tags] for i in file_indexes]
        for i in file_indexes:
            value = ExifToolGUIData.Get(self.data.cache[i], from_tag)
            for to_tag in list_to_tags:
                self.data.edit(i, to_tag, value)

    def shift_datetime_to(self, file_indexes: list[int], destination_tag: str, destination_datetime: str, ref: int) -> None:
        ref_datetime = ExifToolGUIData.Parse_Datetime(ExifToolGUIData.Get(self.data.cache[ref], destination_tag))
        dst_datetime = ExifToolGUIData.Parse_Datetime(destination_tag)
        td: timedelta = dst_datetime - ref_datetime

        for i in file_indexes:
            if i == ref:
                continue
            original_value = ExifToolGUIData.Get(self.data.cache[i], destination_tag)
            original_dt = ExifToolGUIData.Parse_Datetime(original_value)
            shifted_dt = original_dt + td
            self.data.edit(i, destination_tag, ExifToolGUIData.Strf_Datetime(shifted_dt))


if __name__ == "__main__":
    date_string = "2008:05:30 15:54:30.01"
    dt = datetime.fromisoformat(date_string)
    # dt = parser.parse(date_string)
    print(dt)
    if dt.tzinfo == None:
        dt = dt.replace(tzinfo=timezone(timedelta(hours=8)))
    print(dt)

    interval_string = "00010110 053022"
    delta = datetime.fromisoformat(interval_string)
    print(delta)

    print("end")
