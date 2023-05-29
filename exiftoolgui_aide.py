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
    def Str_to_Datetime(datetime_str: str, default_timezone: str) -> datetime:
        # default_tz, a option for users to avoid naive datetime
        tz = ExifToolGUIAide.Str_to_Timezone(default_timezone)

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
            r"(?P<tz>[-+]\d{2}(?:[-:]?\d{2})?(?:[-:]?\d{2}(?:\.\d+)?)?)"
            r")?"
        )

        match = re.match(pattern, datetime_str)
        if match:
            # tz = default_tz
            if match.group('tz'):
                tz = ExifToolGUIAide.Str_to_Timezone(match.group('tz'))
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
                tzinfo=tz,
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

        # dt_s = str(dt).replace('-', ':')
        # dt_s = dt.strftime('%Y:%m:%d %H:%M:%S.%f%z')
        # dt_s = "{:%Y:%m:%d %H:%M:%S.%f%z}".format(dt)

        # dt_s = dt.strftime('%Y:%m:%d %H:%M:%S.%f') + str(dt.tzinfo).replace('UTC', '')
        dt_s = str(dt.replace(tzinfo=None)).replace('-', ':')
        if dt.tzinfo:
            dt_s += str(dt.tzinfo).replace('UTC', '')

        return dt_s

    @staticmethod
    def Str_to_Timezone(timezone_str: str) -> timezone:
        tz = None
        pattern = (
            r"(?:(?P<positive>[-+])[ ]?)"

            r"(?:(?P<tz_hour>\d{2}))"
            r"(?:[:]?(?P<tz_minute>\d{2}))?"
            r"(?:[:]?(?P<tz_second>\d{2}(?:\.\d+)?))?"
        )
        match = re.match(pattern, timezone_str)
        if match:
            positive: int = -1 if match.group('positive') and match.group('positive') == '-' else 1
            td = timedelta(
                hours=int(match.group('tz_hour')) * positive,
                minutes=int(match.group('tz_minute')) * positive if match.group('tz_minute') else 0,
                seconds=float(match.group('tz_second')) * positive if match.group('tz_second') else 0,
            )
            tz = timezone(td)
            
        return tz

    @staticmethod
    def Str_to_Timedelt(td_str: str) ->timezone:
        td: timedelta = None
        pattern = (
            r"(?:(?P<positive>[-+])[ ]?)?"

            r"(?:(?P<day>\d+)[ ])?"

            r"(?:(?=\d+:\d+:\d+)(?P<hour>\d+)[-:])?"
            r"(?:(?=\d+:\d+)(?P<minute>\d+)[-:])?"
            r"(?:(?P<second>\d+(?:\.\d+)?))"
        )
        match = re.match(pattern, td_str)
        if match:
            positive: int = -1 if match.group('positive') and match.group('positive') == '-' else 1
            td = timedelta(
                days=int(match.group('day')) * positive if match.group('day') else 0,
                hours=int(match.group('hour')) * positive if match.group('hour') else 0,
                minutes=int(match.group('minute')) * positive if match.group('minute') else 0,
                seconds=float(match.group('second')) * positive,
            )
        return td


if __name__ == "__main__":
    date_string = "2023:05:17 15:54:30.00 -08:00:00"
    print(date_string)

    dt = ExifToolGUIAide.Str_to_Datetime(date_string)
    print(dt)

    dt_s = ExifToolGUIAide.Datetime_to_Str(dt)
    print(dt_s)

    td_str = "-1.5"
    print(ExifToolGUIAide.Str_to_Timedelt(td_str))

    tz_str = "+0800"
    tz = ExifToolGUIAide.Str_to_Timezone(tz_str)
    print(str(tz))
    
