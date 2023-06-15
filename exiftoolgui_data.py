import os
import locale
import base64

from datetime import datetime, timezone, timedelta
import re

import exiftool
from exiftool.helper import ExifToolHelper, ExifToolExecuteError

from exiftoolgui_aide import ExifToolGUIAide
from exiftoolgui_settings import ExifToolGUISettings

import atexit


class ExifToolGUIData:
    _instance: 'ExifToolGUIData' = None

    @classmethod
    @property
    def Instance(cls) -> 'ExifToolGUIData':
        if cls._instance == None:
            cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        self.exiftool = exiftool.ExifToolHelper(common_args=None)
        '''
        note:
        There is a bug in CPython 3.8+ on Windows where terminate() does not work during __del__()
        See CPython issue `starting a thread in __del__ hangs at interpreter shutdown`_ for more info.
        _starting a thread in __del__ hangs at interpreter shutdown: https://bugs.python.org/issue43784
        Use 'atexit' instead.
        (Please make sure to create instances of the class and run the main loop in the main thread of the program, to ensure that 'atexit' works properly.)
        '''
        atexit.register(self.exiftool.terminate)

        self.settings: ExifToolGUISettings = ExifToolGUISettings.Instance

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
                value_saved = ExifToolGUIData.Get(self.cache[file_index], tag_edited, '')
                value_failed = ExifToolGUIData.Get(self.cache_failed[file_index], tag_edited, None)
                if value_edited != str(value_saved) and value_edited != value_failed:
                    unsaved[file_index][tag_edited] = value_edited
        return unsaved

    def read_tags(self, file: str, tags: list[str], params: list[str], process_name) -> dict[str, ]:
        result: dict[str,] = {'SourceFile': file}
        try:
            result.update(self.exiftool.get_tags(file, tags, params)[0])
        except ExifToolExecuteError as e:
            self.log(file, f'ExifTool:Error:ExifToolExecuteError:Read:{process_name}', e.stderr)
        except UnicodeEncodeError as e:
            self.log(file, f'ExifToolGUI:Error:UnicodeEncodeError:Read:{process_name}', str(e))
        except Exception as e:
            self.log(file, f'ExifToolGUI:Error:Unknow:Read:{process_name}', str(e))
        return result

    def write_tags(self, file: str, tags: list[str], params: list[str], process_name) -> bool:
        try:
            r: str = self.exiftool.set_tags(file, tags, params)
            if r:
                self.log(file, f'ExifTool:Info:Write:{process_name}', r)
            return True
        except ExifToolExecuteError as e:
            self.log(file, f'ExifTool:Error:ExifToolExecuteError:Write:{process_name}', e.stderr)
        except UnicodeEncodeError as e:
            self.log(file, f'ExifToolGUI:Error:UnicodeEncodeError:Write:{process_name}', str(e))
        except Exception as e:
            self.log(file, f'ExifToolGUI:Error:Unknow:Write:{process_name}', str(e))
        return False

    def log(self, source_file: str, type: str, message: str):
        message = str(message).strip()
        datetime_str = f"{datetime.now().astimezone().strftime('%Y-%m-%dT%H:%M:%S.%f%z')}"
        log = f"{datetime_str} [{type}]:\n  SourceFile: {source_file}\n  {message}"
        print(log)

    def reload(self) -> None:
        self.cache.clear()
        self.cache_edited.clear()
        self.cache_failed.clear()

        self.cache += self.load(self.settings.files)

        for file_index in range(0, len(self.cache)):
            self.cache_edited.append({})
            self.cache_failed.append({})

    def load(self, files: list[str], tags: list[str] = None) -> list[dict[str, ]]:
        results: list[dict[str,]] = []

        for file in files:
            result: dict[str,] = self.read_tags(file, tags, self.settings.exiftool_params, 'load')
            results.append(result)

            # handle non-unicode
            self.fix_non_unicode_filename(file, result)

            # handle ExifTool:Warning
            for tag_w, warning in ExifToolGUIData.Get_Item(result, 'ExifTool:Warning', findall=True).items():
                self.log(result['SourceFile'], 'ExifTool:Warning:load', warning)
                result.pop(tag_w)

        return results

    def fix_non_unicode_filename(self, file: str, metadata: dict[str, ]) -> None:
        '''
        # On Windows, if the system code page is not UTF-8, filename related values will be garbled.
        # Exiftool doesn't recode these tags from local encoding to UTF-8 before passing them to json. 
        # See: https://exiftool.org/forum/index.php?topic=13473
        # Here is a temporary method to fix this problem.
        # Notice: 
        # '-b' should be specified, and in this way ExifTool will code the non-utf8 values with base64,
        # and by decoding base64 string, we get the raw local-encoding-coded bytes, and a correct 
        # decoding process according to local encoding could be done.
        # Otherwise, python can't get the raw local-encoding-coded values from json, and what json
        # provides is a UTF-8 'validated' but irreversibly damaged value.
        '''
        # if local system encoding is not utf-8
        if locale.getpreferredencoding(False) != 'utf-8':
            tags_b: list = ['File:FileName', 'File:Directory']
            result_b: dict[str, ] = self.read_tags(file, tags_b, self.settings.exiftool_params + ['-b'], 'fix_unicode_filename')
            if result_b:
                for tag_b in ['SourceFile'] + tags_b:
                    maybe_base64 = ExifToolGUIData.Get(result_b, tag_b)
                    fixed = ExifToolGUIAide.Base64_to_Str(maybe_base64)
                    if fixed:
                        ExifToolGUIData.Set(metadata, tag_b, fixed)

    def load_thumbnail(self, file_index: int, default=None) -> bytes:
        file = self.cache[file_index]['SourceFile']

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
        return default

    def edit(self, file_index: int, tag: str, value, save=False):
        if tag == None or tag == '' or (' ' in tag):
            return

        if tag.startswith('?'):
            self.edit_condition(file_index, tag, value)
        elif tag.startswith('&'):
            self.edit_composite(file_index, tag, value)
        else:
            self.edit_normal(file_index, tag, value)

        if save:
            self.save()

    def edit_normal(self, file_index: int, tag: str, value):
        metadata = self.cache_edited[file_index]
        tag_n = ExifToolGUIData.Normalise_Tag(tag)
        metadata[tag_n] = value
        self.log(self.cache[file_index]['SourceFile'], 'ExifToolGUI:Info:Edit', {tag: value})

    def edit_composite(self, file_index: int, tag: str, value):
        resolved = self.resolve_composite_value(tag, value)
        for tag_r, value_r in resolved.items():
            self.edit(file_index, tag_r, value_r, save=False)

    def edit_condition(self, file_index: int, tag: str, value):
        tag_r = self.resolve_condition_tag(file_index, tag)
        self.edit(file_index, tag_r, value, save=False)

    def save(self):
        unsaved = self.cache_unsaved
        for file_index in range(0, len(unsaved)):
            if len(unsaved[file_index]) == 0:
                continue
            file = self.cache[file_index]['SourceFile']
            self.log(file, 'ExifToolGUI:Info:Save', str(unsaved[file_index]))
            # set tags to file

            self.write_tags(file, unsaved[file_index], self.settings.exiftool_params, 'save')

            # check whether file name is changed
            file_new = file
            directory_new: str = ExifToolGUIData.Get(unsaved[file_index], 'File:Directory', None)
            filename_new: str = ExifToolGUIData.Get(unsaved[file_index], 'File:FileName', None)
            if filename_new != None or directory_new != None:
                directory_old = ExifToolGUIData.Get(self.cache[file_index], 'File:Directory', None)
                filename_old = ExifToolGUIData.Get(self.cache[file_index], 'File:FileName', None)
                file_new = os.path.join(
                    directory_new if directory_new != None else directory_old,
                    filename_new if filename_new != None else filename_old
                )
                if not os.path.exists(file_new):
                    # error happens, unhandled
                    file_new = file

            # get tags for checking
            result = self.load(
                [file_new],
                list(unsaved[file_index].keys()) + ['ExifTool:Warning'],
            )[0]

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
    def Get(metadata: dict[str, ], tag: str, default=None, strict: bool = False):  # Get_Value
        item = ExifToolGUIData.Get_Item(metadata, tag, strict=strict, findall=False)
        return next(iter(item.values()), default)

    @staticmethod
    def Set(metadata: dict[str, ], tag: str, value):
        item = ExifToolGUIData.Get_Item(metadata, tag, findall=False)
        tag_matched = next(iter(item.keys()), None)
        if tag_matched != None:
            metadata[tag_matched] = value

    def get(self, file_index: int, tag: str, default=None, strict: bool = False, editing: bool = False):
        if tag != None and tag.startswith('?'):
            return self.get_condition(file_index, tag, default, strict, editing)
        elif tag != None and tag.startswith('&'):
            return self.get_composite(file_index, tag, default, strict, editing)
        else:
            return self.get_normal(file_index, tag, default, strict, editing)

    def get_normal(self, file_index: int, tag: str, default=None,  strict: bool = False, editing: bool = False):
        value = ExifToolGUIData.Get(self.cache[file_index], tag, None, strict)

        if editing == True:
            status: bool = None
            value_edited = ExifToolGUIData.Get(self.cache_edited[file_index], tag, None)
            if value_edited != None:
                if value == None:
                    if value_edited == '':
                        status = True
                elif value_edited == str(value):
                    status = True

                if status != True:
                    value_failed = ExifToolGUIData.Get(self.cache_failed[file_index], tag, None)
                    if value_edited == value_failed:
                        status = False

            return value if value != None else default, value_edited, status

        return value if value != None else default

    def get_composite(self, file_index: int, tag: str, default=None, strict: bool = False, editing: bool = False):
        composite_tag_def = self.settings.composite_tags.get(tag, None)
        if composite_tag_def:

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
                        value = self.get(file_index, tag.group(1), None)
                    if editing == True:
                        value, value_edited, status = self.get(file_index, tag.group(1), None, editing=True)

                    if value != None and str(value):  # not None or ''
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

        if editing == True:
            return result, result_edited, status_overall

        return result

    def resolve_composite_value(self, tag: str, value) -> dict[str,]:
        composite_tag_def = self.settings.composite_tags.get(tag, None)
        if composite_tag_def:
            pattern = composite_tag_def['pattern']

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

    def get_condition(self, file_index: int, tag: str, default=None, strict: bool = False, editing: bool = False):
        tag_r = self.resolve_condition_tag(file_index, tag)
        return self.get(file_index, tag_r, default, strict, editing)

    def resolve_condition_tag(self, file_index: int, tag: str):
        condition_tag_def = self.settings.condition_tags.get(tag, None)
        if condition_tag_def:
            for candidate_tag, condition in condition_tag_def.items():

                to_be_tested = re.sub(
                    r'<(.*?)>',
                    lambda match: self.get(file_index, match.group(1), ""),
                    condition['to_be_tested']
                )

                match = re.match(condition['pattern'], to_be_tested)
                if match:
                    # print(f"{tag}->{candidate_tag}")
                    if candidate_tag.startswith('?'):
                        return self.resolve_condition_tag(file_index, tag)
                    else:
                        return candidate_tag


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

    pass
