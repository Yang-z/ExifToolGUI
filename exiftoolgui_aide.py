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
            encoding = locale.getpreferredencoding(False)  # 'cp936' same as 'gb2312'?
        fixed: str = b.decode(encoding)
        return fixed

    @staticmethod
    def Str_to_Datetime(datetime_str: str) -> tuple[datetime, bool]:
        # if not datetime_str:
        #     return None, None

        tz = None
        dt = None
        has_subsec: bool = None

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

            # tell the function Datetime_to_Str() whether to print subsec
            has_subsec = bool(match.group('second_fractional'))

        # try iso
        if dt == None:
            try:
                dt = datetime.fromisoformat(datetime_str)
            except ValueError as e:
                print(e)

        return dt, has_subsec

    @staticmethod
    def Datetime_to_Str(dt_: tuple[datetime, bool]) -> str:
        dt, has_subsec = dt_

        if dt == None:
            return None

        dt_s = None

        # dt_s = str(dt).replace('-', ':')
        # dt_s = dt.strftime('%Y:%m:%d %H:%M:%S.%f%z')
        # dt_s = "{:%Y:%m:%d %H:%M:%S.%f%z}".format(dt)

        # dt_s = dt.strftime('%Y:%m:%d %H:%M:%S.%f') + str(dt.tzinfo).replace('UTC', '')

        # dt_s = str(dt.replace(tzinfo=None)).replace('-', ':') # will not print microsecond if its value is 0
        # if dt.tzinfo:
        #     dt_s += str(dt.tzinfo).replace('UTC', '')

        # subsec = '{:06d}'.format(dt.microsecond)
        # while len(subsec) > 2 and subsec[-1] == '0':
        #     subsec = subsec[:-1]

        # dt_s = '{}.{}{}'.format(
        #     dt.strftime('%Y:%m:%d %H:%M:%S'),
        #     subsec,
        #     str(dt.tzinfo).replace('UTC', '') if dt.tzinfo else ''
        # )

        dt_s = dt.strftime('%Y:%m:%d %H:%M:%S')
        if dt.microsecond != 0 or has_subsec == True:
            subsec = '{:06d}'.format(dt.microsecond)
            while len(subsec) > 2 and subsec[-1] == '0':
                subsec = subsec[:-1]
            dt_s += '.'+subsec
        if dt.tzinfo:
            dt_s += str(dt.tzinfo).replace('UTC', '')

        return dt_s

    @staticmethod
    def Str_to_Timezone(timezone_str: str) -> timezone:
        if not timezone_str:
            return

        if timezone_str == 'local':
            local_offset = datetime.now(timezone.utc).astimezone().utcoffset()
            local_tz = timezone(local_offset)
            return local_tz

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
    def Str_to_Timedelt(td_str: str) -> timedelta:
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
    date_string = "2023:05:17 15:54:30.00-08:00"
    print(date_string)

    dt_ = ExifToolGUIAide.Str_to_Datetime(date_string)
    print(dt_[0], dt_[1])

    dt_s = ExifToolGUIAide.Datetime_to_Str(dt_)
    print(dt_s)

    # td_str = "-1.5"
    # print(ExifToolGUIAide.Str_to_Timedelt(td_str))

    # tz_str = "+0800"
    # tz = ExifToolGUIAide.Str_to_Timezone(tz_str)
    # print(str(tz))

    # print(ExifToolGUIAide.Str_to_Timezone('local'))
