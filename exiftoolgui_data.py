from typing import Union, Any

import base64
import re

from datetime import datetime, timezone

import os
import atexit
import locale

# import exiftool
from exiftool.helper import ExifToolHelper, ExifToolExecuteError

from exiftoolgui_aide import ExifToolGUIAide
from exiftoolgui_settings import ExifToolGUISettings
from exiftoolgui_log import ExifToolGUILog


class ExifToolGUIData:
    _instance: 'ExifToolGUIData' = None

    @classmethod
    @property
    def Instance(cls) -> 'ExifToolGUIData':
        if cls._instance == None:
            cls._instance = cls()
        return cls._instance

    '''################################################################
    Cache
    ################################################################'''

    cache_pool: dict[str, dict[str, ]] = {}
    cache_pool_edited: dict[str, dict[str, ]] = {}
    cache_pool_failed: dict[str, dict[str, ]] = {}

    @staticmethod
    def Get_Metadata(cache_pool: dict[str, dict[str, ]], file: str) -> dict[str, ]:
        metadata = cache_pool.get(file, None)
        if metadata == None:
            metadata = {}
            cache_pool[file] = metadata
        return metadata

    '''################################################################
    Init
    ################################################################'''

    def __init__(self) -> None:
        '''
        Notice:

        Only windows users encounter problems of local codepage and 'utf-8'.
        Other OS always use 'utf-8'.

        ExifTool's default encoding for tag values is 'utf-8', 
        while default for file names depends on system settings (i.e. local codepage)
            [https://exiftool.org/forum/index.php?topic=9717]


        Supporting for local codepage is really a challenge for windows:

            - In terms of reading, json requires vaild utf-8, non-utf-8 values 
              are not possible to be extracted via json directly.
                [https://exiftool.org/forum/index.php?topic=13473]
              Non-utf-8 value is able to be extrcted by using '-b' option via json.
              Reading without json is OK but expensive.

            - In terms of writting, ExifTool seems unspportable for non-utf-8 values,
              and the fellowing warning will be thrown if try:
                "Warning: Malformed UTF-8 character(s)"
              ExifTool do have a '-charset' option, which might be helpful, but not all 
              local codepages are supported.


        Supporting for 'utf-8' could be simple:
            - set pyExifTool's encoding property to 'utf-8'. (pyExiftool)
            - use ExifTool's option of '-charset\nfilename=utf8' at each execution. (ExifTool)
            - no matter what local codepage is, it works.


        Supporting for 'utf-8', and compatible with reading existing non-utf-8 values:
            - Invaild utf-8 bytes will be replaced by "\x3F\x3F..." in json, 
              and the original value is irreversibly lost.
            - So, "\x3F\x3F" (??) could used to detect if invaild utf-8 values are encountered.
              And use ExifTool option '-b' to re-extract the values.

        More discussions:
            [https://github.com/sylikc/pyexiftool/issues/70]

        Here, we adopt the supporting for 'utf-8',
        and keep the compatibility of reading existing non-utf-8 values.
        '''
        self.exiftool: ExifToolHelper = ExifToolHelper(common_args=None)
        self.exiftool.encoding = 'utf-8'

        '''
        Notice:
        There is a bug in CPython 3.8+ on Windows where terminate() does not work during __del__()
        See CPython issue `starting a thread in __del__ hangs at interpreter shutdown`_ for more info.
        _starting a thread in __del__ hangs at interpreter shutdown: https://bugs.python.org/issue43784
        Use 'atexit' instead.
        (Please make sure to create instances of the class and run the main loop in the main thread of the program, to ensure that 'atexit' works properly.)
        '''
        atexit.register(self.exiftool.terminate)

        self.settings: ExifToolGUISettings = ExifToolGUISettings.Instance
        self.log: ExifToolGUILog = ExifToolGUILog.Instance

        self.cache: list[dict[str, ]] = []
        self.cache_edited: list[dict[str, ]] = []
        self.cache_failed: list[dict[str, ]] = []

    @property
    def cache_unsaved(self) -> list[dict[str, ]]:
        unsaved: list[dict[str, ]] = []
        for file_index in range(0, len(self.cache_edited)):
            unsaved.append({})
            edited = self.cache_edited[file_index]
            for tag_edited, value_edited in edited.items():
                value_saved = ExifToolGUIData.Get(self.cache[file_index], tag_edited, default='')
                value_failed = ExifToolGUIData.Get(self.cache_failed[file_index], tag_edited)
                if value_edited != str(value_saved) and value_edited != value_failed:
                    unsaved[file_index][tag_edited] = value_edited
        return unsaved

    '''################################################################
    Load
    ################################################################'''

    def reload(self):
        self.cache.clear()
        self.cache_edited.clear()
        self.cache_failed.clear()

        for file in self.settings.files:
            metadata = ExifToolGUIData.Get_Metadata(ExifToolGUIData.cache_pool, file)
            self.cache.append(metadata)
            if len(metadata) == 0:
                metadata['SourceFile'] = file

            self.cache_edited.append(ExifToolGUIData.Get_Metadata(ExifToolGUIData.cache_pool_edited, file))
            self.cache_failed.append(ExifToolGUIData.Get_Metadata(ExifToolGUIData.cache_pool_failed, file))

    def refresh(self, file_index: int) -> None:
        file = self.cache[file_index]['SourceFile']
        metadata = self.load(file)
        self.cache[file_index] = metadata
        ExifToolGUIData.cache_pool[file] = metadata

    def reset(self, file_index: int) -> None:
        self.cache_edited[file_index].clear()
        self.cache_failed[file_index].clear()

    def rebuild(self, file_index: int):
        commd: str = '-exif:all= -tagsfromfile @ -all:all -unsafe -charset filename=utf8'
        params = commd.split(' ')
        file = self.cache[file_index]['SourceFile']
        self.execute(file, params)
        self.refresh(file_index)

    def load(self, file: str, tags: list[str] = None) -> dict[str, ]:

        # load from file
        result: dict[str,] = self.read_tags(file, tags, self.settings.exiftool_params, 'load', fix_non_utf8=True)

        # handle ExifTool:Warning
        for tag_w, warning in ExifToolGUIData.Get_Item(result, 'ExifTool:Warning', findall=True).items():
            self.log.append('ExifTool:Warning:load', result['SourceFile'], warning)
            result.pop(tag_w)

        return result

    def load_thumbnail(self, file_index: int) -> bytes:
        file = self.cache[file_index]['SourceFile'] if (type(file_index) == int) else file_index

        # ref: https://exiftool.org/forum/index.php?topic=4216
        tag_thum: list[str] = [
            "ThumbnailImage",
            "PreviewImage",
            "OtherImage",
            "PreviewPICT",
            "CoverArt",

            "Preview",
        ]
        result = self.read_tags(file, tag_thum, ['-b'], 'load_thumbnail')
        result.pop('SourceFile')

        for key in result:
            s: str = result[key]
            if s.startswith('base64:'):
                b: bytes = base64.b64decode(s[7:])
                return b

    '''################################################################
    Edit and Save
    ################################################################'''

    def edit(self, file_index: int, tag: str, value, save: bool = False, normalise: bool = False):
        if tag == None or tag == '' or (' ' in tag) or value == None:
            return

        if normalise:
            if self.is_datetime(tag):
                value_n = self.normalise_datetime(file_index, tag, value)
                if value_n != None:
                    value = value_n
            elif isinstance(value, str):
                # remove space(s) at the beginning and end
                value = value.strip()
                pass

        if tag.startswith('?'):
            self.edit_condition(file_index, tag, value)
        elif tag.startswith('&'):
            self.edit_composite(file_index, tag, value)
        elif tag.startswith('('):
            # casted tag is readonly
            pass
        else:
            self.edit_normal(file_index, tag, value)

        if save:
            self.save()

    def edit_normal(self, file_index: int, tag: str, value):
        metadata = self.cache_edited[file_index]
        tag_n = ExifToolGUIData.Normalise_Tag(tag)
        if tag_n == ExifToolGUIData.Normalise_Tag('File:FileName'):
            if not value:
                return
            value = self.anti_duplicate_file_name(file_index, value)
        metadata[tag_n] = value
        self.log.append('ExifToolGUI:Info:Edit', self.cache[file_index]['SourceFile'], {tag: value})

    def anti_duplicate_file_name(self, file_index: int, value: str, suffix='_') -> str:
        tag_n = ExifToolGUIData.Normalise_Tag('File:FileName')
        file_name, ext = os.path.splitext(value)

        i = 0
        duplicated: bool = True
        while duplicated:
            for file_index_ in range(len(self.cache_edited)):
                if file_index_ == file_index:
                    duplicated = False
                    continue

                metadata = self.cache_edited[file_index_]
                if value.lower() == metadata.get(tag_n, '').lower():
                    duplicated = True
                    i += 1
                    value = file_name + suffix + str(i) + ext
                    break
                else:
                    duplicated = False

        return value

    def edit_composite(self, file_index: int, tag: str, value):
        resolved = self.resolve_composite_value(tag, value)
        for tag_r, value_r in resolved.items():
            self.edit(file_index, tag_r, value_r, save=False)

    def edit_condition(self, file_index: int, tag: str, value):
        tag_r = self.resolve_conditional_tag(file_index, tag)
        if tag_r:
            self.edit(file_index, tag_r, value, save=False)

    def save(self):
        unsaved = self.cache_unsaved
        for file_index in range(0, len(unsaved)):
            if len(unsaved[file_index]) == 0:
                continue
            file = self.cache[file_index]['SourceFile']
            self.log.append('ExifToolGUI:Info:Save', file, str(unsaved[file_index]))
            # set tags to file

            self.write_tags(file, unsaved[file_index], self.settings.exiftool_params, 'save')

            # check whether file name is changed
            file_new = file
            directory_new: str = ExifToolGUIData.Get(unsaved[file_index], 'File:Directory')
            filename_new: str = ExifToolGUIData.Get(unsaved[file_index], 'File:FileName')
            if filename_new != None or directory_new != None:
                directory_old = ExifToolGUIData.Get(self.cache[file_index], 'File:Directory')
                filename_old = ExifToolGUIData.Get(self.cache[file_index], 'File:FileName')
                file_new = os.path.join(
                    directory_new if directory_new != None else directory_old,
                    filename_new if filename_new != None else filename_old
                )
                if not os.path.exists(file_new):
                    # error happens, unhandled
                    file_new = file

            # get tags for checking
            result = self.load(
                file_new,
                list(unsaved[file_index].keys()) + ['ExifTool:Warning']
            )

            # update source_file
            if file_new != file:
                file_return: str = result.pop('SourceFile')
                assert os.path.samefile(file_return, file_new)
                file_new = file_return
                self.cache[file_index]['SourceFile'] = file_new

            # check result
            for tag_unsaved in unsaved[file_index]:

                items_return = ExifToolGUIData.Get_Item(result, tag_unsaved, findall=True)  # tags with full path
                item_cache = ExifToolGUIData.Get_Item(self.cache[file_index], tag_unsaved, findall=True)  # tags with full path

                # assert len(item_cache) > 0 # not true when a tag is newly added
                value_edited = unsaved[file_index][tag_unsaved]

                failed: bool = False

                # update cache
                for tag_cache_full in item_cache.keys():
                    if tag_cache_full not in items_return.keys():
                        self.cache[file_index].pop(tag_cache_full)

                for tag_return_full, value_return in items_return.items():
                    self.cache[file_index][tag_return_full] = value_return

                    # check
                    if str(value_return) != value_edited:
                        # failed to:
                        # modify the existing tag or
                        # set tag value to '' (delete tag)
                        failed = True

                # check
                if len(items_return) == 0:
                    if value_edited != "":
                        # failed to add a new tag
                        failed = True
                    # else:  # successed to delete tag

                if failed:
                    self.cache_failed[file_index][tag_unsaved] = value_edited

    '''################################################################
    Get and Set
    ################################################################'''

    @staticmethod
    def Normalise_Tag(tag: str) -> str:
        if tag == None or tag == '':
            return tag
        tag_s: list[str] = tag.lower().split(':')
        # tag_normalised: str = (tag_s[0], tag_s[0] + ':' + tag_s[-1])[len(tag_s) > 1]
        tag_normalised: str = tag_s[0] if len(tag_s) == 1 else tag_s[0] + ':' + tag_s[-1]
        return tag_normalised

    @staticmethod
    def Get_Item(metadata: dict[str, ], tag: str, strict: bool = False, findall: bool = False) -> dict[str,]:
        result: dict[str,] = {}
        tag_n: str = tag if strict else ExifToolGUIData.Normalise_Tag(tag)
        for tag_source, value in metadata.items():
            tag_source_n = tag_source if strict else ExifToolGUIData.Normalise_Tag(tag_source)
            if tag_source_n == tag_n:
                result.update({tag_source: value})
                if findall == False:
                    break
        return result

    @staticmethod
    def Get(metadata: dict[str, ], tag: str, default=None, strict: bool = False) -> Union[str, Any]:  # Get_Value
        item = ExifToolGUIData.Get_Item(metadata, tag, strict=strict, findall=False)
        return next(iter(item.values()), default)

    @staticmethod
    def Set(metadata: dict[str, ], tag: str, value, strict: bool = False) -> None:
        item = ExifToolGUIData.Get_Item(metadata, tag, strict=strict, findall=False)
        tag_matched = next(iter(item.keys()), None)
        if tag_matched != None:
            metadata[tag_matched] = value

    def get(self, file_index: int, tag: str, default=None, strict: bool = False, editing: bool = False) -> Union[str, tuple[str, str, bool]]:
        if tag == None:
            return default if editing != True else (default, None, None)

        if tag.startswith('?'):
            return self.get_conditional(file_index, tag, default, strict, editing)
        elif tag.startswith('&'):
            return self.get_composite(file_index, tag, default, strict, editing)
        elif tag.startswith('('):
            return self.get_casted(file_index, tag, default, strict, editing)
        else:
            return self.get_normal(file_index, tag, default, strict, editing)

    def get_normal(self, file_index: int, tag: str, default=None,  strict: bool = False, editing: bool = False) -> Union[str, tuple[str, str, bool]]:
        value = ExifToolGUIData.Get(self.cache[file_index], tag, strict=strict)

        if editing == True:
            status: bool = None
            value_edited = ExifToolGUIData.Get(self.cache_edited[file_index], tag)
            if value_edited != None:
                if value == None:
                    if value_edited == '':
                        status = True
                elif value_edited == str(value):
                    status = True

                if status != True:
                    value_failed = ExifToolGUIData.Get(self.cache_failed[file_index], tag)
                    if value_edited == value_failed:
                        status = False

        value = value if value != None else default
        return value if editing != True else (value, value_edited, status)

    def get_composite(self, file_index: int, tag: str, default=None, strict: bool = False, editing: bool = False) -> Union[str, tuple[str, str, bool]]:
        composite_tag_def = ExifToolGUIData.Get(self.settings.composite_tags, tag)

        if composite_tag_def == None:
            return default if editing != True else (default, None, None)

        # composite_tag_def != None now

        result = ""
        keep_overall = False

        if editing == True:
            result_edited = ""
            keep_overall_edited = False
            status_overall = True

        fields = re.finditer(r"\((.*?)\)", composite_tag_def['format'])
        for field in fields:
            to_be_replaced = field.group(1)
            keep_field = False

            if editing == True:
                to_be_replaced_edited = field.group(1)
                keep_field_edited = False

            tags = re.finditer(r'<(.*?)>', field.group(1))
            for tag in tags:

                if editing != True:
                    value = self.get(file_index, tag.group(1))
                else:  # editing == True:
                    value, value_edited, status = self.get(file_index, tag.group(1), editing=True)

                # not None or ''
                # empty string dont't seem to exist, because exiftool deletes tag with the value of empty string
                if value != None and str(value):
                    to_be_replaced = to_be_replaced.replace(tag.group(), str(value))
                    keep_field = True
                    keep_overall = True
                else:
                    to_be_replaced = to_be_replaced.replace(tag.group(), '')

                if editing == True:
                    if value_edited != None:
                        keep_overall_edited = True
                        if status == None:
                            status_overall = None
                        elif status == False:
                            if status_overall != None:
                                status_overall = False

                    value_fallback = value_edited if value_edited != None else value

                    if value_fallback != None and str(value_fallback):  # not None or ''
                        to_be_replaced_edited = to_be_replaced_edited.replace(tag.group(), str(value_fallback))
                        keep_field_edited = True
                    else:
                        to_be_replaced_edited = to_be_replaced_edited.replace(tag.group(), '')

            if keep_field:
                result += to_be_replaced

            if editing == True:
                if keep_field_edited:
                    result_edited += to_be_replaced_edited

        if keep_overall == False:
            result = default

        if editing == True:
            if keep_overall_edited == False:
                result_edited = None

        # compositing finished

        return result if editing != True else (result, result_edited, status_overall)

    def resolve_composite_value(self, tag: str, value) -> dict[str,]:
        composite_tag_def = ExifToolGUIData.Get(self.settings.composite_tags, tag)
        if composite_tag_def:
            pattern = composite_tag_def['pattern']

            # empty string will not match, but deleting value should be supported
            # none-empty but non-matching string will not delete value.
            if value == "":
                empty_value_dict = {}
                tags = re.finditer(r'<(.*?)>', pattern)
                for tag in tags:
                    empty_value_dict[tag.group(1)] = ""
                return empty_value_dict

            # python regular expression does not support colon in group name
            pattern_n = re.sub(
                r'<([^>]*)>',
                lambda match: match.group(0).replace(':', '__COLON__'),
                pattern
            )

            match = re.match(pattern_n, value)
            if match:
                match_dict_n = match.groupdict()

                # return the original keys' names
                match_dict = {key.replace('__COLON__', ':'): value if value != None else '' for key, value in match_dict_n.items()}

                return match_dict
        return {}

    def get_conditional(self, file_index: int, tag: str, default=None, strict: bool = False, editing: bool = False) -> Union[str, tuple[str, str, bool]]:
        tag_r = self.resolve_conditional_tag(file_index, tag)
        return self.get(file_index, tag_r, default=default, strict=strict, editing=editing)

    def resolve_conditional_tag(self, file_index: int, tag: str) -> str:
        # condition_tag_def = self.settings.condition_tags.get(tag, None)
        condition_tag_defs = ExifToolGUIData.Get(self.settings.conditional_tags, tag)
        if condition_tag_defs:
            for candidate_tag, tag_def in condition_tag_defs.items():

                condition = re.sub(
                    r'<(.*?)>',
                    lambda match: self.get(file_index, match.group(1), default=""),
                    tag_def['condition']
                )

                match = re.match(tag_def['pattern'], condition)
                if match:
                    # print(f"{tag}->{candidate_tag}")
                    if candidate_tag.startswith('?'):
                        return self.resolve_conditional_tag(file_index, tag)
                    else:
                        return candidate_tag

    def get_casted(self, file_index: int, tag: str, default=None, strict: bool = False, editing: bool = False) -> Union[str, tuple[str, str, bool]]:
        type_evaled, tag_o = self.resolve_casted_tag(tag)

        if type_evaled != None and tag_o != None:
            value_o_ = self.get(file_index, tag_o, strict=strict, editing=editing)

            if editing != True:
                value_o = value_o_
            else:
                value_o, value_o_edited, status = value_o_

            if type_evaled == datetime:
                dt_ = ExifToolGUIAide.Str_to_Datetime(str(value_o))
                value = ExifToolGUIAide.Datetime_to_Str(dt_)

                if editing == True:
                    dt_e = ExifToolGUIAide.Str_to_Datetime(value_o_edited)
                    value_e = ExifToolGUIAide.Datetime_to_Str(dt_e)

                if value == None:
                    value = default

                return value if editing != True else (value, value_e, status)

            elif type_evaled == timezone:
                pass

        return default if editing != True else (default, None, None)

    def resolve_casted_tag(self, tag: str) -> tuple[Any, str]:
        # tag started with '(type)'
        pattern = r"\((?P<type>.*?)\)(?P<tag>.*)"
        match = re.match(pattern, tag)
        if match:
            type_str = match.group('type')
            tag_o = match.group('tag')

            type_evaled = eval(type_str)

            return type_evaled, tag_o

        return None, None

    '''################################################################
    Datetime
    ################################################################'''

    def is_datetime(self, tag: str) -> bool:
        if tag.startswith('('):
            type_evaled, tag_o = self.resolve_casted_tag(tag)
            return type_evaled == datetime
            # return True if tag.startswith(f"({datetime.__name__})") else False

        detatime_tag_def = ExifToolGUIData.Get(self.settings.datetime_tags, tag)
        return (detatime_tag_def != None)

    def normalise_datetime(self, file_index: int, tag: str, value: str = None) -> str:
        dt_ = self.get_datetime(file_index, tag, value)
        value_r = self.resolve_datetime(file_index, tag, dt_)
        return value_r

    def get_datetime(self, file_index: int, tag: str, value: str = None, default_timezone: str = None) -> tuple[datetime, int]:
        # resolve tag to normal tag or composite tag
        tag_r = self.resolve_conditional_tag(file_index, tag) if tag.startswith('?') else tag

        # value could be specified or got from cache
        value = value if value != None else self.get(file_index, tag)

        # if user does not specify a default timezone, leave it undefined here
        # default_timezone = default_timezone if default_timezone else self.settings.default_timezone

        if value:
            dt, len_subsec = ExifToolGUIAide.Str_to_Datetime(value)
            if dt and dt.tzinfo == None:
                detatime_tag_def = ExifToolGUIData.Get(self.settings.datetime_tags, tag_r)
                if detatime_tag_def:
                    # some tags may implicit specify timezone info as UTC, i.e. QuickTime:CreateDate
                    as_utc: bool = detatime_tag_def.get('as_utc', None)
                    if as_utc:
                        dt = dt.replace(tzinfo=timezone.utc)
                elif not tag_r.startswith(f"({datetime.__name__})"):
                    self.log.append(
                        "ExifToolGUI:Warnning:get_datetime",
                        self.cache[file_index]['SourceFile'],
                        f"{tag_r}: datetime tag is not defined"
                    )

                if dt.tzinfo == None:
                    # fix by user specified timezone
                    default_tz = ExifToolGUIAide.Str_to_Timezone(default_timezone)
                    if default_tz:
                        dt = dt.replace(tzinfo=default_tz)

                if dt.tzinfo == None:
                    self.log.append("ExifToolGUI:Warnning:get_datetime", self.cache[file_index]['SourceFile'], f"{tag_r}: naive datetime is returned")
            return dt, len_subsec

        return None, None

    def resolve_datetime(self, file_index: int, tag: str, dt_: tuple[datetime, int], default_timezone: str = None) -> str:
        dt, len_subsec = dt_

        if dt == None:
            return None

        tag_r = self.resolve_conditional_tag(file_index, tag) if tag.startswith('?') else tag
        detatime_tag_def = ExifToolGUIData.Get(self.settings.datetime_tags, tag_r)

        if detatime_tag_def:

            if dt.tzinfo:
                as_utc: bool = detatime_tag_def.get('as_utc', None)
                if as_utc == True:
                    dt = dt.astimezone(timezone.utc)
                else:
                    # keep the original tzinfo, unless default_timezone is valid
                    default_tz = ExifToolGUIAide.Str_to_Timezone(default_timezone)
                    if default_tz:
                        dt = dt.astimezone(default_tz)

                is_timezone_explicit: bool = detatime_tag_def.get('is_timezone_explicit', None)
                if is_timezone_explicit == False:
                    dt = dt.replace(tzinfo=None)

                if as_utc != True and is_timezone_explicit == False:
                    self.log.append(
                        "ExifToolGUI:Warnning:resolve_datetime",
                        self.cache[file_index]['SourceFile'],
                        f"{tag_r}: Timezone info is losing"
                    )

            else:
                self.log.append(
                    "ExifToolGUI:Warnning:resolve_datetime",
                    self.cache[file_index]['SourceFile'],
                    f"{tag_r}: naive datetime is passed"
                )

            support_subsec: bool = detatime_tag_def.get('support_subsec', None)
            if support_subsec == False:
                len_subsec = 0
                if dt.microsecond != 0:
                    self.log.append(
                        "ExifToolGUI:Warnning:resolve_datetime",
                        self.cache[file_index]['SourceFile'],
                        f"{tag_r}: SubSecond info is losing"
                    )

        else:
            self.log.append(
                "ExifToolGUI:Warnning:resolve_datetime",
                self.cache[file_index]['SourceFile'],
                f"{tag_r}: datetime tag is not defined"
            )

        return ExifToolGUIAide.Datetime_to_Str((dt, len_subsec))

    '''################################################################
    IO and Log
    ################################################################'''

    def execute(self, file: str, params: list):
        params.append(file)
        self.exiftool.execute(*params)

    def read_tags(self, file: str, tags: list[str], params: list[str], process_name, fix_non_utf8: bool = False) -> dict[str, ]:
        result: dict[str,] = None
        try:
            result = self.exiftool.get_tags(file, tags, params)[0]
        except ExifToolExecuteError as e:
            self.log.append(f'ExifTool:Error:{type(e).__name__}:Read:{process_name}', file, e.stderr)
        except Exception as e:  # UnicodeEncodeError
            self.log.append(f'ExifToolGUI:Error:{type(e).__name__}:Read:{process_name}', file, str(e))

        if fix_non_utf8:
            self.fix_non_utf8_values(file, result)

        return result if result else {'SourceFile': file}

    def write_tags(self, file: str, tags: dict[str, Any], params: list[str], process_name) -> bool:
        if not tags:
            return True

        try:
            r = self.exiftool.set_tags(file, tags, params)
            if r:
                self.log.append(f'ExifTool:Info:Write:{process_name}', file, r)
            return True
        except ExifToolExecuteError as e:
            self.log.append(f'ExifTool:Error:{type(e).__name__}:Write:{process_name}', file, e.stderr)
        except Exception as e:  # UnicodeEncodeError UnicodeDecodeError
            self.log.append(f'ExifToolGUI:Error:{type(e).__name__}:Write:{process_name}', file, str(e))

        return False

    def fix_non_utf8_values(self, file: str, metadata: dict[str, str], encodings: list[str] = []) -> None:
        '''
        If non-utf8 values exist, Exiftool will not recode these values from local encoding 
        to UTF-8 before passing them to json. That could causes non-utf8 values to be garbled.

        Non-utf8 value could be encoded by local codepage or others. If the non-utf8 value is 
        not local codepage encoded, let user to specify one.

        ExifTool option of '-b' should be specified, and in this way ExifTool will encode the 
        non-utf8 values with base64. Then by decoding base64 string, the raw local codepage 
        encoded bytes could be obtained, and a correct decoding process according to local 
        codepage (or user specified encodings) could be done.

        Otherwise, python can't get the raw local codepage encoded values from json, and what
        json provides is a irreversibly damaged value. Actually, invaild utf-8 bytes will be 
        replaced by "\x3F\x3F..." ("??...") in json, and the original value is lost permanently.

        Here is a way to fix this problem to keep the compatibility of reading non-utf-8 values 
        existing in metadata.
        '''
        garbled: dict[str, str] = {}
        for tag, value in metadata.items():
            if isinstance(value, str) and '??' in value:  # how about non str value?
                garbled[tag] = value

        if len(garbled) <= 0:
            return

        '''
        (a zip file with 608 duplicated tags of '-ZIP:ZipFileName' causes reading with no response.)
        (duplicated tags of '-ZIP:ZipFileName' look like: -ZIP:ZIP:Other:Doc2:Copy1:ZIP::ID-15:ZipFileName)

        normalise tags to avoid duplicated tags making cmd_params too huge.
        cmd_params with too huge size could cause reading fdout unresponsive.
        os.read(fd, block_size) freezed at the very first block.

        (should also let reading funcion split a single call into batches?)
        '''
        tags_garbled_n: list = []
        for tag in garbled.keys():
            tag_n = ExifToolGUIData.Normalise_Tag(tag)
            if tag_n not in tags_garbled_n:
                tags_garbled_n.append(tag_n)

        result_b: dict[str, ] = self.read_tags(
            file,
            tags_garbled_n,
            self.settings.exiftool_params + ['-b'],
            'fix_non_utf8_values'
        )

        if not result_b:
            return

        # encoding candidates to decode the original value
        encodings: list[str] = [locale.getpreferredencoding(False)] + encodings
        for tag_garbled, value_garbled in garbled.items():

            maybe_base64: str = ExifToolGUIData.Get(result_b, tag_garbled, strict=True)
            if not isinstance(maybe_base64, str) or not maybe_base64.startswith('base64:'):
                continue

            # test if "\x3F\x3F..." ("??...") is as the normal chars
            value_b: bytes = base64.b64decode(maybe_base64[7:])
            value_garbled_b: bytes = value_garbled.encode(encoding='utf-8')
            if value_b == value_garbled_b:
                # vaild utf-8 value contians "??" as normal chars.
                print('"\x3F\x3F..." ("??...") is as normal chars')
                continue

            # guess the right encoding
            fixed: str = None
            for encoding in encodings:
                if encoding == None:
                    continue
                try:
                    fixed = value_b.decode(encoding)
                    break
                except Exception as e:
                    # print(f"Base64_to_Str:Error:{type(e).__name__}:{encoding}: " + str(e))
                    pass

            if fixed == None:
                # keep base64 string instead
                fixed = maybe_base64
                self.log.append('ExifToolGUI:Warning:Non-UTF8:', file, f"{tag_garbled}: unknown encoding")
            else:
                self.log.append('ExifToolGUI:Warning:Non-UTF8:', file, f"{tag_garbled}: {encoding} value found")

            if fixed == value_garbled:
                # Is it possible?
                # fixed value is the same as the value garbled by utf-8!
                self.log.append('ExifToolGUI:Report:Non-UTF8:', file, f"{tag_garbled}: fixed value is the same as value garbled by utf-8!")
            else:
                ExifToolGUIData.Set(metadata, tag_garbled, fixed, strict=True)


if __name__ == "__main__":
    # data:ExifToolGUIData = ExifToolGUIData.Instance
    # data.reload()
    # tag_value = data.get_composite(0, "&EXIF:DateTimeOriginal")
    # print(ctag_value)

    # tag= "&EXIF:DateTimeOriginal"
    # value = "2008:05:30 15:56:01.5311+08:00"
    # result= ExifToolGUIData.resolve_composite_tag(vtag, value)
    # print(result)

    data: ExifToolGUIData = ExifToolGUIData.Instance
    data.reload()
    value = data.get(0, "?Timeline", editing=True)
    print(value)

    print(data.is_datetime('?ModifyDate'))

    print(data.is_datetime('(datetime)test'))

    pass
