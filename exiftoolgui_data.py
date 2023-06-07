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
            for tag_edited in edited:
                value_edited = edited[tag_edited]
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

        self.cache = self.load(self.settings.files)

        for file_index in range(0, len(self.cache)):
            self.cache_edited.append({})
            self.cache_failed.append({})

    def load(self, files: list[str], tags: list[str] = None) -> list[dict[str, ]]:
        results: list[dict[str,]] = []

        for file in files:
            result = self.read_tags(file, tags, self.settings.exiftool_params, 'load')
            results.append(result)

            # handle non-unicode
            self.fix_non_unicode_filename(file, result)

            # handle ExifTool:Warning
            while True:
                tag_w, warning = ExifToolGUIData.Get_Tag_Value(result, 'ExifTool:Warning', None)
                if warning == None:
                    break
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

    def load_thumbnail(self, file: str, default=None) -> bytes:
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
        metadata = self.cache_edited[file_index]
        tag_n = ExifToolGUIData.Normalise_Tag(tag)
        metadata[tag_n] = value
        self.log(self.cache[file_index]['SourceFile'], 'ExifToolGUI:Info:Edit', {tag: value})

        if save:
            self.save()

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
                tags_return_full, values_return = ExifToolGUIData.Get_Tags_Values(result, tag_unsaved)
                tags_cache_full = ExifToolGUIData.Get_Tags(self.cache[file_index], tag_unsaved)
                # assert len(tags_cache_full) > 0 # not true when a tag is newly added
                value_edited = unsaved[file_index][tag_unsaved]

                failed: bool = False

                # update cache
                for tag_cache_full in tags_cache_full:
                    if tag_cache_full not in tags_return_full:
                        self.cache[file_index].pop(tag_cache_full)

                for i in range(0, len(tags_return_full)):
                    tag_return_full = tags_return_full[i]
                    value_return = values_return[i]
                    self.cache[file_index][tag_return_full] = value_return

                    # check
                    if str(value_return) != value_edited:
                        # failed to:
                        # modify the existing tag or
                        # set tag value to '' (delete tag)
                        failed = True

                # check
                if len(tags_return_full) == 0:
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
    def Is_Tag_Equal(tag1: str, tag2: str):
        return ExifToolGUIData.Normalise_Tag(tag1) == ExifToolGUIData.Normalise_Tag(tag2)

    @staticmethod
    def Get_Tag(metadata: dict[str, ], tag: str, default: str = None, strict: bool = False) -> str:
        if tag in metadata:
            return tag  # return the exact tag preferentially
        if strict:
            return default
        tag_n: str = ExifToolGUIData.Normalise_Tag(tag)
        for tag_source in metadata:
            tag_source_n = ExifToolGUIData.Normalise_Tag(tag_source)
            if tag_source_n == tag_n:
                return tag_source
        return default

    @staticmethod
    def Get_Tags(metadata: dict[str, ], tag: str) -> list[str]:
        tag_n: str = ExifToolGUIData.Normalise_Tag(tag)
        tags: list[str] = []
        for tag_source in metadata:
            tag_source_n = ExifToolGUIData.Normalise_Tag(tag_source)
            if tag_source_n == tag_n:
                tags.append(tag_source)
        return tags

    @staticmethod
    def Get(metadata: dict[str, ], tag: str, default=None, strict: bool = False):  # Get_Value
        tag_matched = ExifToolGUIData.Get_Tag(metadata, tag, None, strict)
        if tag_matched == None:
            return default
        return metadata[tag_matched]

    @staticmethod
    def Get_Tag_Value(metadata: dict[str, ], tag: str, default=None):
        tag_matched = ExifToolGUIData.Get_Tag(metadata, tag)
        if tag_matched == None:
            return default, default
        return tag_matched, metadata[tag_matched]

    @staticmethod
    def Get_Tags_Values(metadata: dict[str, ], tag: str):
        tags_matched = ExifToolGUIData.Get_Tags(metadata, tag)
        values: list = []
        for tag_matched in tags_matched:
            values.append(metadata[tag_matched])
        return tags_matched, values

    @staticmethod
    def Set(metadata: dict[str, ], tag: str, value):
        tag_matched = ExifToolGUIData.Get_Tag(metadata, tag)
        if tag_matched == None:
            return
        metadata[tag_matched] = value


if __name__ == "__main__":
    pass
