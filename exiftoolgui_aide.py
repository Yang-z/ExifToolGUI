import locale
import base64
import re
from datetime import datetime, timezone, timedelta


class ExifToolGUIAide:

    @staticmethod
    def Base64_to_Str(base64_str: str, encoding=None) -> str:
        if base64_str == None or not base64_str.startswith('base64:'):
            return None
        b: bytes = base64.b64decode(base64_str[7:])
        if encoding == None:
            encoding = locale.getpreferredencoding(False)  # 'cp936' same as 'gb2312'
        fixed: str = b.decode(encoding)
        return fixed

    @staticmethod
    def Str_to_Datetime(datetime_str: str) -> datetime:
        dt = None
        # try common
        pattern = (
            r"(?P<year>\d{4})"
            r"(?:[-:]?(?P<month>\d{2}))?"
            r"(?:[-:]?(?P<day>\d{2}))?"

            r"(?:[ ]"
            r"(?P<hour>\d{2})"
            r"(?:[-:]?(?P<minute>\d{2}))"
            r"(?:[-:]?(?P<second>\d{2}))?"
            r"(?P<second_fractional>\.\d+)?"
            r")?"

            r"(?:[ ]?"
            r"(?P<tz_hour>[-+]\d{2})"
            r"(?:[-:]?(?P<tz_minute>\d{2}))?"
            r"(?:[-:]?(?P<tz_second>\d{2}(?:\.\d+)?))?"
            r")?"
        )

        match = re.match(pattern, datetime_str)
        if match:
            td: timedelta = None
            if match.group('tz_hour'):
                td = timedelta(
                    hours=int(match.group('tz_hour')),
                    minutes=int(match.group('tz_minute')) if match.group('tz_minute') else 0,
                    seconds=float(match.group('tz_second')) if match.group('tz_second') else 0,
                )

            dt = datetime(
                year=int(match.group('year')),
                month=int(match.group('month')) if match.group('month') else 1,
                day=int(match.group('day')) if match.group('day') else 1,
                hour=int(match.group('hour')) if match.group('hour') else 0,
                minute=int(match.group('minute')) if match.group('minute') else 0,
                second=int(match.group('second')) if match.group('second') else 0,
                microsecond=int(float(match.group('second_fractional'))*1000000) if match.group('second_fractional') else 0,
                # microsecond is the highest precision of python datetime,
                # so it wiil lost precision when dealing with some metadate with higher precision,
                # such as windows file system timestamp, wich is 100ns(0.1ms).
                tzinfo=timezone(td) if td else None,
            )

        # try iso
        if dt == None:
            try:
                dt = datetime.fromisoformat(datetime_string)
            except ValueError as e:
                print(e)

        return dt

    @staticmethod
    def Datetime_to_Str(dt: datetime) -> str:
        dt_s = None
        if dt.tzinfo != None:
            dt_s = str(dt).replace('-', ':')
            # dt_s = dt.strftime(%Y:%m:%d %H:%M:%S.%f%z)
            # dt_s = "{:%Y:%m:%d %H:%M:%S.%f%z}".format(dt)
        return dt_s


if __name__ == "__main__":
    date_string = "2023:05:17 15:54:30.02 +08:00:00.1"
    print(date_string)

    dt = ExifToolGUIAide.Str_to_Datetime(date_string)
    print(dt)

    dt_s = ExifToolGUIAide.Datetime_to_Str(dt)
    print(dt_s)
