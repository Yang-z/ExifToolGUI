import locale
import base64
import exiftool

from exiftoolgui_settings import ExifToolGUISettings


class ExifToolGUIData:
    def __init__(self, settings: ExifToolGUISettings) -> None:
        self.settings: ExifToolGUISettings = settings
        self.cache: dict[str, dict[str, ]] = {}
        self.cache_modified: dict[str, dict[str, ]] = {}
        self.cache_failed: dict[str, dict[str, ]] = {}
        self.reload()

    @property
    def cache_unsaved(self) -> dict[str, dict[str, ]]:
        cache_unsaved: dict[str, dict[str, ]] = {}
        for file in self.cache_modified:
            for tag in self.cache_modified[file]:
                value = self.cache_modified[file][tag]
                value_saved = str(self.get(file, tag, ''))
                value_failed = self.get_failed(file, tag, None)
                if(value != value_saved and value != value_failed):
                    if(cache_unsaved.get(file, None) == None):
                        cache_unsaved[file] = {}
                    cache_unsaved[file][tag] = value
        return cache_unsaved

    def reload(self) -> None:
        self.cache.clear()
        # for file in self.settings.files:
        #     self.cache_metadata(file)

        files = self.settings.files
        if(len(files) == 0):
            return
        with exiftool.ExifToolHelper(common_args=None) as et:
            metadata_list: list[dict] = et.get_metadata(
                files,
                self.settings.exiftool_params
            )
        for m in metadata_list:
            ExifToolGUIData.fix_unicode_filename(m)
            self.cache[m['SourceFile']] = m

    def cache_metadata(self, file: str) -> None:
        with exiftool.ExifToolHelper(common_args=None) as et:
            metadata_list: list[dict] = et.get_metadata(
                file,
                self.settings.exiftool_params
            )
        m = metadata_list[0]
        ExifToolGUIData.fix_unicode_filename(m)
        self.cache[m['SourceFile']] = m

    @staticmethod
    def fix_unicode_filename(metadata: dict) -> None:
        tags_to_be_fixed: list = [
            'SourceFile',
            'File:FileName',
            'File:Directory'
        ]
        for tag_to_be_fixed in tags_to_be_fixed:
            tag_in_source = ExifToolGUIData.match_tag(
                metadata, tag_to_be_fixed)
            if(tag_in_source == None):
                continue
            value: str = metadata.get(tag_in_source, None)
            if(value and value.startswith('base64:')):
                value_fixed = ExifToolGUIData.fix_unicode(value)
                metadata[tag_in_source] = value_fixed

    @staticmethod
    def fix_unicode(coded: str) -> str:
        b: bytes = base64.b64decode(coded[7:])
        # fixed:str = b.decode('gb2312')
        fixed: str = b.decode(locale.getpreferredencoding(False))  # cp936
        return fixed

    @staticmethod
    def match_tag(metadata: dict, tag: str) -> str:
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
        tag_s: list[str] = tag.split(':')
        # tag_normalised: str = (tag_s[0], tag_s[0] + ':' + tag_s[-1])[len(tag_s) > 1]
        tag_normalised: str = \
            tag_s[0] if len(tag_s) == 1 else tag_s[0] + ':' + tag_s[-1]
        return tag_normalised

    @staticmethod
    def is_tag_equal(tag1: str, tag2: str):
        return ExifToolGUIData.normalise_tag(tag1) == ExifToolGUIData.normalise_tag(tag2)

    @staticmethod
    def get_from_single(metadata: dict[str, ], tag: str, default=None):
        tag_matched = ExifToolGUIData.match_tag(metadata, tag)
        if(tag_matched == None):
            return default
        return metadata[tag_matched]

    @staticmethod
    def get_from_group(cache: dict[str, dict[str, ]], file: str, tag: str, default=None):
        metadata = cache.get(file, None)
        if(metadata == None):
            return default
        return ExifToolGUIData.get_from_single(metadata, tag, default)

    def get(self, file: str, tag: str, default=''):
        return ExifToolGUIData.get_from_group(self.cache, file, tag, default)
    # def get_unsaved(self, file: str, tag: str, default=None):
    #     return ExifToolGUIData.get_from(self.cache_modified, file, tag, default)

    def get_failed(self, file: str, tag: str, default=''):
        return ExifToolGUIData.get_from_group(self.cache_failed, file, tag, default)

    def set(self, file: str, tag: str, value, save=False):
        tag_n = ExifToolGUIData.normalise_tag(tag)
        if(self.cache_modified.get(file, None) == None):
            self.cache_modified[file] = {}
        self.cache_modified[file][tag_n] = value
        print(
            f"set:\n" +
            f"  source_file: {file}\n" +
            f"  {tag} = {value}"
        )

        if(save):
            self.save()

    def save(self):
        unsaved = self.cache_unsaved
        for file in unsaved:
            with exiftool.ExifToolHelper(common_args=None) as et:
                try:
                    et.set_tags(
                        file,
                        unsaved[file],
                        self.settings.exiftool_params
                    )
                except Exception as e:
                    print(e.stderr)

                result: list[dict[str, ]] = et.get_tags(
                    file,
                    unsaved[file].keys(),
                    self.settings.exiftool_params
                )


            for tag_unsaved in unsaved[file]:
                tag_return = ExifToolGUIData.match_tag(result[0], tag_unsaved)
                tag_ = ExifToolGUIData.match_tag(self.cache[file], tag_unsaved)
                tag = tag_ if tag_ != None else tag_return
                value_modified = unsaved[file][tag_unsaved]
                failed: bool = False

                ''' # an altenative method
                if(value_modified == ''):
                    if(tag_return == None):
                        if(tag_ != None):
                            # successed to delete a tag
                            self.cache[file].pop(tag_)
                    else:  # tag_return != None
                        # update cache
                        self.cache[file][tag] = result[0][tag_return]

                        if(str(result[0][tag_return]) != ''):
                            # failed to delete tag
                            failed = True

                else:  # value_modified != ''
                    if(tag_return == None):
                        if(tag_ != None):
                            # successed to delete tag
                            self.cache[file].pop(tag_)
                        # failed to add new tag
                        failed = True
                    else:  # tag_return != None
                        # update cache
                        self.cache[file][tag] = result[0][tag_return]

                        if(str(result[0][tag_return]) != value_modified):
                            failed = True
                '''

                if(tag_return == None):
                    # update cache
                    if(tag_ != None):
                        self.cache[file].pop(tag_)
                    # check
                    if(value_modified != ''):
                        # failed to add a new tag
                        failed = True
                    # else:  # successed to delete tag
                else:
                    # update cache
                    self.cache[file][tag] = result[0][tag_return]
                    # check
                    if(str(self.cache[file][tag]) != value_modified):
                        # failed to:
                        # modify the existing tag or
                        # set tag value to '' or
                        # delete tag
                        failed = True

                if(failed):
                    if(self.cache_failed.get(file, None) == None):
                        self.cache_failed[file] = {}
                    self.cache_failed[file][tag_unsaved] = value_modified

    # def confirm(self):
    #     for source_file in self.cache_saved:
    #         if
    #     return

    def get_thumbnail(self, source_file: str, default=None) -> bytes:
        s: str = self.get(source_file, 'EXIF:ThumbnailImage', None)
        if(s == None):
            return default
        b: bytes = base64.b64decode(s[7:])
        return b


if __name__ == '__main__':
    data = ExifToolGUIData(ExifToolGUISettings())
