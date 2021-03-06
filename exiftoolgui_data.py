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
        self.cache_edited: list[dict[str, ]] = []
        self.cache_failed: list[dict[str, ]] = []

        # self.reload()

    @property
    def cache_unsaved(self) -> list[dict[str, ]]:
        unsaved: list[dict[str, ]] = []
        for file_index in range(0, len(self.cache_edited)):
            unsaved.append({})
            edited = self.cache_edited[file_index]
            for tag_edited in edited:
                value_modified = edited[tag_edited]
                value_saved = ExifToolGUIData.Get(self.cache[file_index], tag_edited, '')
                value_failed = ExifToolGUIData.Get(self.cache_failed[file_index], tag_edited, None)
                if(value_modified != str(value_saved) and value_modified != value_failed):
                    unsaved[file_index][tag_edited] = value_modified
        return unsaved

    def reload(self) -> None:
        self.cache.clear()
        self.cache_edited.clear()
        self.cache_failed.clear()

        self.cache = self.load(self.settings.files)

        for file_index in range(0, len(self.cache)):
            self.cache_edited.append({})
            self.cache_failed.append({})

    def load(self, files: list[str], tags: list[str] = None) -> list[dict[str, ]]:
        if(len(files) == 0):
            return []

        with exiftool.ExifToolHelper(common_args=None) as et:
            try:
                result: list[dict[str, ]] = et.get_tags(
                    files,
                    tags,
                    self.settings.exiftool_params
                )
            except ExifToolExecuteError as e:
                self.Log(str(files), 'ExifTool:Error:Get', e.stderr)
                return None

        # if local system encoding is not utf-8
        if(locale.getpreferredencoding(False) != 'UTF-8'):
            tags_b: list = ['File:FileName', 'File:Directory']
            with exiftool.ExifToolHelper(common_args=None) as et:
                temp_b: list[dict[str, ]] = et.get_tags(
                    files,
                    tags_b,
                    self.settings.exiftool_params + ['-b']
                )
            for file_index in range(0, len(result)):
                for tag_b in ['SourceFile'] + tags_b:
                    ExifToolGUIData.Set(result[file_index], tag_b, ExifToolGUIData.Get(temp_b[file_index], tag_b))
                ExifToolGUIData.Fix_Unicode_Filename(result[file_index])

        for file_index in range(0, len(result)):
            # handle warning
            while(True):
                tag_w, warning = ExifToolGUIData.Get_Tag_A_Value(result[file_index], 'ExifTool:Warning', None)
                if(warning == None):
                    break
                self.Log(result[file_index]['SourceFile'], 'ExifTool:Warning:Get', warning)
                result[file_index].pop(tag_w)

        return result

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
    @staticmethod
    def Fix_Unicode_Filename(metadata: dict[str, ]) -> None:
        tags_to_be_fixed: list = [
            'SourceFile',
            'File:FileName',
            'File:Directory'
        ]
        for tag_to_be_fixed in tags_to_be_fixed:
            tag_in_source = ExifToolGUIData.Get_Tag(metadata, tag_to_be_fixed)
            if(tag_in_source == None):
                continue
            value: str = metadata[tag_in_source]
            if(value):
                value_fixed = ExifToolGUIData.Fix_Unicode(value)
                if(value_fixed):
                    metadata[tag_in_source] = value_fixed

    @staticmethod
    def Fix_Unicode(garbled: str) -> str:
        if(garbled == None or not garbled.startswith('base64:')):
            return None
        b: bytes = base64.b64decode(garbled[7:])
        local_encoding = locale.getpreferredencoding(False)  # 'cp936' same as 'gb2312'
        fixed: str = b.decode(local_encoding)
        return fixed

    @staticmethod
    def Get_Tag(metadata: dict[str, ], tag: str, default: str = None, strict: bool = False) -> str:
        if(tag in metadata):
            return tag  # return the exact tag preferentially
        if(strict):
            return default
        tag_n: str = ExifToolGUIData.Normalise_Tag(tag)
        for tag_source in metadata:
            tag_source_n = ExifToolGUIData.Normalise_Tag(tag_source)
            if(tag_source_n == tag_n):
                return tag_source
        return default

    @staticmethod
    def Get_Tags(metadata: dict[str, ], tag: str) -> list[str]:
        tag_n: str = ExifToolGUIData.Normalise_Tag(tag)
        tags: list[str] = []
        for tag_source in metadata:
            tag_source_n = ExifToolGUIData.Normalise_Tag(tag_source)
            if(tag_source_n == tag_n):
                tags.append(tag_source)
        return tags

    @staticmethod
    def Normalise_Tag(tag: str) -> str:
        if(tag == None or tag == ''):
            return tag
        tag_s: list[str] = tag.lower().split(':')
        # tag_normalised: str = (tag_s[0], tag_s[0] + ':' + tag_s[-1])[len(tag_s) > 1]
        tag_normalised: str = tag_s[0] if len(tag_s) == 1 else tag_s[0] + ':' + tag_s[-1]
        return tag_normalised

    @staticmethod
    def Is_Tag_Equal(tag1: str, tag2: str):
        return ExifToolGUIData.Normalise_Tag(tag1) == ExifToolGUIData.Normalise_Tag(tag2)

    @staticmethod
    def Get(metadata: dict[str, ], tag: str, default=None, strict: bool = False):
        tag_matched = ExifToolGUIData.Get_Tag(metadata, tag, None, strict)
        if(tag_matched == None):
            return default
        return metadata[tag_matched]

    @staticmethod
    def Get_Thumbnail(metadata: dict[str, ], default=None) -> bytes:
        # ref: https://exiftool.org/forum/index.php?topic=4216
        tag_thum: list = [
            "ThumbnailImage",
            "PreviewImage",
            "OtherImage",
            "Preview PICT",
            "CoverArt",
        ]

        with exiftool.ExifToolHelper(common_args=None) as et:
            temp: dict[str, ] = et.get_tags(
                metadata['SourceFile'],
                tag_thum,
                ['-b']
            )[0]
        temp.pop('SourceFile')
        s: str = None
        for key in temp:
            s = temp[key]
            break

        if(s == None or not s.startswith('base64:')):
            return default
        b: bytes = base64.b64decode(s[7:])
        return b

    @staticmethod
    def Get_Tag_A_Value(metadata: dict[str, ], tag: str, default=None):
        tag_matched = ExifToolGUIData.Get_Tag(metadata, tag)
        if(tag_matched == None):
            return default, default
        return tag_matched, metadata[tag_matched]

    @staticmethod
    def Get_Tags_A_Values(metadata: dict[str, ], tag: str):
        tags_matched = ExifToolGUIData.Get_Tags(metadata, tag)
        values: list = []
        for tag_matched in tags_matched:
            values.append(metadata[tag_matched])
        return tags_matched, values

    @staticmethod
    def Set(metadata: dict[str, ], tag: str, value):
        tag_matched = ExifToolGUIData.Get_Tag(metadata, tag)
        if(tag_matched == None):
            return
        metadata[tag_matched] = value

    def edit(self, file_index: int, tag: str, value, save=False):
        metadata = self.cache_edited[file_index]
        tag_n = ExifToolGUIData.Normalise_Tag(tag)
        metadata[tag_n] = value
        self.Log(self.cache[file_index]['SourceFile'], 'ExifToolGUI:Info:Edit', {tag: value})
        # print(f"set:\n    file_index: {file_index}\n    {tag} = {value}")

        if(save):
            self.save()

    def save(self):
        unsaved = self.cache_unsaved
        for file_index in range(0, len(unsaved)):
            if(len(unsaved[file_index]) == 0):
                continue
            file = self.cache[file_index]['SourceFile']
            self.Log(file, 'ExifToolGUI:Info:Save', str(unsaved[file_index]))
            # set tags to file
            with exiftool.ExifToolHelper(common_args=None) as et:
                try:
                    r: str = et.set_tags(
                        file,
                        unsaved[file_index],
                        self.settings.exiftool_params
                    )
                    if(r):
                        self.Log(file, 'ExifTool:Info:Set', r)
                except ExifToolExecuteError as e:
                    self.Log(file, 'ExifTool:Error:Set', e.stderr)

            # check whether file name is changed
            file_new = file
            directory_new: str = ExifToolGUIData.Get(unsaved[file_index], 'File:Directory', None)
            filename_new: str = ExifToolGUIData.Get(unsaved[file_index], 'File:FileName', None)
            if(filename_new != None or directory_new != None):
                directory_old = ExifToolGUIData.Get(self.cache[file_index], 'File:Directory', None)
                filename_old = ExifToolGUIData.Get(self.cache[file_index], 'File:FileName', None)
                file_new = os.path.join(
                    directory_new if directory_new != None else directory_old,
                    filename_new if filename_new != None else filename_old
                )
                if(not os.path.exists(file_new)):
                    file_new = file

            # get tags for checking
            result = self.load(
                [file_new],
                list(unsaved[file_index].keys()) + ['ExifTool:Warning'],
            )[0]

            # update source_file
            if(file_new != file):
                file_return: str = result.pop('SourceFile')
                assert os.path.samefile(file_return, file_new)
                file_new = file_return
                self.cache[file_index]['SourceFile'] = file_new

            # check result
            for tag_unsaved in unsaved[file_index]:
                tags_return, values_return = ExifToolGUIData.Get_Tags_A_Values(result, tag_unsaved)
                tags_ = ExifToolGUIData.Get_Tags(self.cache[file_index], tag_unsaved)
                value_edited = unsaved[file_index][tag_unsaved]

                failed: bool = False
                if(tags_return == []):
                    # update cache
                    if(tags_ != []):
                        [self.cache[file_index].pop(tag_) for tag_ in tags_]
                    # check
                    if(value_edited != ''):
                        # failed to add a new tag
                        failed = True
                    # else:  # successed to delete tag
                else:
                    # update cache
                    for tag_ in tags_:
                        if(tag_ not in tags_return):
                            self.cache[file_index].pop(tag_)
                    for i in range(0, len(tags_return)):
                        tag_return = tags_return[i]
                        value_return = values_return[i]
                        self.cache[file_index][tag_return] = value_return

                        # check
                        if(str(value_return) != value_edited):
                            # failed to:
                            # modify the existing tag or
                            # set tag value to '' or
                            # delete tag
                            failed = True

                if(failed):
                    self.cache_failed[file_index][tag_unsaved] = value_edited

    @staticmethod
    def Log(source_file: str, type: str, message: str):
        datetime_str = f"{datetime.datetime.now().astimezone().strftime('%Y-%m-%dT%H:%M:%S.%f%z')}"
        log = f"{datetime_str} [{type}]:\n  SourceFile: {source_file}\n  {message}"
        print(log)
