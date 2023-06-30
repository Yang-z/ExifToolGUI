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
    def Str_to_Datetime(datetime_str: str) -> tuple[datetime, int]:
        dt = None
        len_subsec: int = None
        tz = None

        if not datetime_str:
            return dt, len_subsec

        # try common
        if dt == None:
            pattern = (
                r"(?P<year>\d{4})"
                r"(?:[-:]?(?P<month>\d{2}))?"
                r"(?:[-:]?(?P<day>\d{2}))?"

                r"(?:[ _]"
                r"(?P<hour>\d{2})"
                r"(?:[-:]?(?P<minute>\d{2}))"
                r"(?:[-:]?(?P<second>\d{2}))?"
                r"(?P<second_fractional>\.\d+)?"
                r")"

                r"(?:[ ]?"
                r"(?P<tz>[-+]\d{2}(?:[-:]?\d{2})?(?:[-:]?\d{2}(?:\.\d+)?)?)"
                r")?"
            )

            match = re.search(pattern, datetime_str)
            if match:
                # tz = default_tz
                if match.group('tz'):
                    tz = ExifToolGUIAide.Str_to_Timezone(match.group('tz'))

                try:
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
                except Exception as e:
                    print(e)

                # tell the function Datetime_to_Str() whether to print subsec
                len_subsec = 0 if not bool(match.group('second_fractional')) else (len(match.group('second_fractional'))-1)

        # try timestamp
        if dt == None:
            pattern = r'\d{10,16}'
            match = re.search(pattern, datetime_str)
            if match:
                timestamp_str = match.group(0)
                len_ts = len(timestamp_str)
                timestamp = int(timestamp_str)
                if len_ts > 10:
                    timestamp /= pow(10, len_ts-10)
                dt = datetime.fromtimestamp(timestamp, timezone.utc)
                len_subsec = len_ts - 10

        # try iso
        if dt == None:
            try:
                dt = datetime.fromisoformat(datetime_str)
                len_subsec = len(str(dt.microsecond / 1000000.0)[2:])
            except Exception as e:  # ValueError
                print(e)

        return dt, len_subsec

    @staticmethod
    def Datetime_to_Str(dt_: tuple[datetime, int]) -> str:
        dt, len_subsec = dt_

        if dt == None:
            return None

        if len_subsec == 0:
            if dt.microsecond >= 500000:
                dt = dt.replace(second=dt.second+1)
            dt = dt.replace(microsecond=0)
            # SubSecond info lost

        dt_s = dt.strftime('%Y:%m:%d %H:%M:%S')
        if dt.microsecond != 0 or len_subsec > 0:

            subsec = '{:06d}'.format(dt.microsecond)
            while len(subsec) > len_subsec and subsec[-1] == '0':
                subsec = subsec[:-1]
            dt_s += '.' + subsec

            # formatter = "{:." + str(len_subsec) + "f}"
            # subsec = formatter.format(dt.microsecond / 1000000.0)
            # subsec = subsec[1:]
            # dt_s += subsec

        if dt.tzinfo:
            dt_s += ExifToolGUIAide.Timezone_to_Str(dt.tzinfo)

        return dt_s

    @staticmethod
    def Str_to_Timezone(timezone_str: str) -> timezone:
        if not timezone_str:
            return None

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
    def Timezone_to_Str(tz: timezone) -> str:
        if tz == None:
            return None

        tz_str = ''

        # precision upto 1 microsecond(μs), i.e. 0.000001 second
        total_sec: float = tz.utcoffset(None).total_seconds()

        if total_sec >= 0:
            tz_str += '+'
        else:
            tz_str += '-'
            total_sec = abs(total_sec)

        hours, remainder = divmod(total_sec, 3600)
        minutes, seconds = divmod(remainder, 60)
        tz_str += "{:02d}:{:02d}".format(int(hours), int(minutes))

        if seconds > 0:
            seconds, subsec = divmod(seconds, 1)
            tz_str += ":{:02d}".format(int(seconds))
            if subsec > 0:
                tz_str += "{:.6f}".format(subsec)[1:].rstrip('0')

        return tz_str

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
    # date_string = "2023:05:17 15:54:30.00+00:00:00.0000009"
    date_string = "1687806635123"
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

    # print(ExifToolGUIAide.Str_to_Datetime(None))
    # print(ExifToolGUIAide.Datetime_to_Str((None, None)))

    # print(ExifToolGUIAide.Str_to_Datetime(''))
    # print(ExifToolGUIAide.Datetime_to_Str((datetime.min.replace(tzinfo=timezone.utc), None)))

    pass
