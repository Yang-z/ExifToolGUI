import os
import locale
import base64

import datetime

import exiftool
from exiftool.helper import ExifToolExecuteError

from exiftoolgui_settings import ExifToolGUISettings


class ExifToolGUIData:
    def __init__(self, settings: ExifToolGUISettings) -> None:
        self.settings: ExifToolGUISettings = settings
        self.cache: list[dict[str, ]] = []
        self.cache_modified: list[dict[str, ]] = []
        self.cache_failed: list[dict[str, ]] = []

        self.reload()

    @property
    def cache_unsaved(self) -> list[dict[str, ]]:
        unsaved: list[dict[str, ]] = []
        for file_index in range(0, len(self.cache_modified)):
            unsaved.append({})
            modified = self.cache_modified[file_index]
            for tag_modified in modified:
                value_modified = modified[tag_modified]
                value_saved = ExifToolGUIData.find(self.cache[file_index], tag_modified, '')
                value_failed = ExifToolGUIData.find(self.cache_failed[file_index], tag_modified, None)
                if(value_modified != str(value_saved) and value_modified != value_failed):
                    unsaved[file_index][tag_modified] = value_modified

        return unsaved

    def reload(self) -> None:
        self.cache.clear()
        self.cache_modified.clear()
        self.cache_failed.clear()

        files = self.settings.files
        if(len(files) == 0):
            return
        with exiftool.ExifToolHelper(common_args=None) as et:
            self.cache = et.get_metadata(
                files,
                self.settings.exiftool_params
            )
        for file_index in range(0, len(self.cache)):
            ExifToolGUIData.fix_unicode_filename(self.cache[file_index])
            self.cache_modified.append({})
            self.cache_failed.append({})

            # handle warning
            warning_tag = ExifToolGUIData.match_tag(self.cache[file_index], 'ExifTool:Warning')
            message = self.cache[file_index].get(warning_tag, None)
            if(message != None):
                self.log(file_index, 'Warning', message)
                self.cache[file_index].pop(warning_tag)
        return

    '''
    # On Windows, if the system code page is not UTF-8, filename related values will be garbled.
    # Exiftool doesn't recode these tags from local encoding to UTF-8 before passing them to json. 
    # See: https://exiftool.org/forum/index.php?topic=13473
    # Here is a temporary method to fix this problem.
    # Notice: 
    # '-b' should be specified, and in this way ExifTool will code the non-utf8 values with base64,
    # and by decoding base64 string, we get the raw local-encoding-coded bytes, and a correct 
    # decoding process according to local encoding could be done.
    # Otherwise, if python get the raw local-encoding-coded values from json, these values will be
    # treated as UTF-8 bytes (because they come from a UTF-8 json file), and wrong decoding processes 
    # will be carried out. And theoretically speaking, (maybe) it is still damagelessly reversible 
    # but not implemented here.
    '''
    @staticmethod
    def fix_unicode_filename(metadata: dict[str, ]) -> None:
        tags_to_be_fixed: list = [
            'SourceFile',
            'File:FileName',
            'File:Directory'
        ]
        for tag_to_be_fixed in tags_to_be_fixed:
            tag_in_source = ExifToolGUIData.match_tag(metadata, tag_to_be_fixed)
            if(tag_in_source == None):
                continue
            value: str = metadata[tag_in_source]
            if(value and value.startswith('base64:')):
                value_fixed = ExifToolGUIData.fix_unicode(value)
                metadata[tag_in_source] = value_fixed

    @staticmethod
    def fix_unicode(coded: str) -> str:
        # if(coded == None or not coded.startswith('base64:')): return coded
        b: bytes = base64.b64decode(coded[7:])
        # fixed:str = b.decode('gb2312')
        fixed: str = b.decode(locale.getpreferredencoding(False))  # cp936
        return fixed

    @staticmethod
    def match_tag(metadata: dict[str, ], tag: str) -> str:
        tag_n: str = ExifToolGUIData.normalise_tag(tag)
        for tag_source in metadata:
            tag_source_n = ExifToolGUIData.normalise_tag(tag_source)
            if(tag_source_n == tag_n):
                return tag_source
        return None

    @staticmethod
    def normalise_tag(tag: str) -> str:
        if(tag == None or tag == ''):
            return tag
        tag_s: list[str] = tag.lower().split(':')
        # tag_normalised: str = (tag_s[0], tag_s[0] + ':' + tag_s[-1])[len(tag_s) > 1]
        tag_normalised: str = tag_s[0] if len(tag_s) == 1 else tag_s[0] + ':' + tag_s[-1]
        return tag_normalised

    @staticmethod
    def is_tag_equal(tag1: str, tag2: str):
        return ExifToolGUIData.normalise_tag(tag1) == ExifToolGUIData.normalise_tag(tag2)

    @staticmethod
    def find(metadata: dict[str, ], tag: str, default=None):
        tag_matched = ExifToolGUIData.match_tag(metadata, tag)
        if(tag_matched == None):
            return default
        return metadata[tag_matched]

    @staticmethod
    def get_thumbnail(metadata: list[dict[str, ]], default=None) -> bytes:
        s: str = ExifToolGUIData.find(metadata, 'EXIF:ThumbnailImage', None)
        if(s == None or not s.startswith('base64:')):
            return default
        b: bytes = base64.b64decode(s[7:])
        return b

    def set(self, file_index: int, tag: str, value, save=False):
        metadata = self.cache_modified[file_index]
        tag_n = ExifToolGUIData.normalise_tag(tag)
        metadata[tag_n] = value
        self.log(file_index, 'Info:Set', {tag: value})
        # print(f"set:\n    file_index: {file_index}\n    {tag} = {value}")

        if(save):
            self.save()

    def save(self):
        unsaved = self.cache_unsaved
        for file_index in range(0, len(unsaved)):
            if(len(unsaved[file_index]) == 0):
                continue
            self.log(file_index, 'Info:Save', str(unsaved[file_index]))
            file = self.cache[file_index]['SourceFile']
            # set tags to file
            with exiftool.ExifToolHelper(common_args=None) as et:
                try:
                    r: str = et.set_tags(
                        file,
                        unsaved[file_index],
                        self.settings.exiftool_params
                    )
                    if(r):
                        self.log(file_index, 'Info', r)  # nothing returns?
                except ExifToolExecuteError as e:
                    self.log(file_index, 'Error', e.stderr)

            # check whether file name is changed
            file_new = file
            directory_new: str = ExifToolGUIData.find(unsaved[file_index], 'File:Directory', None)
            filename_new: str = ExifToolGUIData.find(unsaved[file_index], 'File:FileName', None)
            if(filename_new != None or directory_new != None):
                directory_old = ExifToolGUIData.find(self.cache[file_index], 'File:Directory', None)
                filename_old = ExifToolGUIData.find(self.cache[file_index], 'File:FileName', None)
                file_new = os.path.join(
                    directory_new if directory_new != None else directory_old,
                    filename_new if filename_new != None else filename_old
                )
                if(not os.path.exists(file_new)):
                    file_new = file

            # get tags for checking
            with exiftool.ExifToolHelper(common_args=None) as et:
                try:
                    result: dict[str, ] = et.get_tags(
                        file_new,
                        list(unsaved[file_index].keys()) + ['ExifTool:Warning'],
                        self.settings.exiftool_params
                    )[0]
                except ExifToolExecuteError as e:
                    self.log(file_index, 'Error', e.stderr)
            ExifToolGUIData.fix_unicode_filename(result)

            # update source_file
            if(file_new != file):
                file_return: str = result.get('SourceFile', None)
                assert os.path.samefile(file_return, file_new)
                file_new = file_return
                self.cache[file_index]['SourceFile'] = file_new

            # handle warning
            warning = ExifToolGUIData.find(result, 'ExifTool:Warning', None)
            if(warning):
                self.log(file_index, 'Warning', warning)

            # check result
            for tag_unsaved in unsaved[file_index]:
                tag_return = ExifToolGUIData.match_tag(result, tag_unsaved)
                value_return = result.get(tag_return, None)

                tag_ = ExifToolGUIData.match_tag(self.cache[file_index], tag_unsaved)
                tag = tag_ if tag_ != None else tag_return

                value_modified = unsaved[file_index][tag_unsaved]

                failed: bool = False

                if(tag_return == None):
                    # update cache
                    if(tag_ != None):
                        self.cache[file_index].pop(tag_)
                    # check
                    if(value_modified != ''):
                        # failed to add a new tag
                        failed = True
                    # else:  # successed to delete tag
                else:
                    # update cache
                    self.cache[file_index][tag] = value_return
                    # check
                    if(str(self.cache[file_index][tag]) != value_modified):
                        # failed to:
                        # modify the existing tag or
                        # set tag value to '' or
                        # delete tag
                        failed = True

                if(failed):
                    self.cache_failed[file_index][tag_unsaved] = value_modified

    def log(self, file_index: int, type: str, message: str):
        datetime_str = f"{datetime.datetime.now().astimezone().strftime('%Y-%m-%dT%H:%M:%S.%f%z')}"
        source_file = 'None' if file_index == None else self.cache[file_index]['SourceFile']
        log = f"{datetime_str} [{type}]:\n  SourceFile: {source_file}\n  {message}"
        print(log)
