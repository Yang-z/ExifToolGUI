from importlib.metadata import metadata
import locale
import base64
from multiprocessing.sharedctypes import Value
import exiftool

from exiftoolgui_settings import ExifToolGUISettings


class ExifToolGUIData:
    def __init__(self, settings: ExifToolGUISettings) -> None:
        self.settings: ExifToolGUISettings = settings
        self.cache: dict[dict] = None
        self.cache_modified: dict[dict] = {}
        self.reload()

    def reload(self) -> None:
        self.cacheMetaData()

    def cacheMetaData(self) -> None:
        self.cache = {}
        files = self.settings.files
        if (len(files) == 0):
            return
        with exiftool.ExifToolHelper(common_args=None) as et:
            metadata_list: list[dict] = et.get_metadata(
                files,
                self.settings.exiftool_params
            )
        for m in metadata_list:
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
            if (tag_in_source == None):
                continue
            value: str = metadata.get(tag_in_source, None)
            if value and value.startswith('base64:'):
                value_fixed = ExifToolGUIData.fix_unicode(value)
                metadata[tag_in_source] = value_fixed

    @staticmethod
    def fix_unicode(coded: str) -> str:
        b: bytes = base64.b64decode(coded[7:])
        # fixed:str = b.decode('gb2312')
        fixed: str = b.decode(locale.getpreferredencoding(False))  # cp936
        return fixed

    @staticmethod
    def match_tag(tag_dict: dict, tag_target: str) -> str:
        tag_target_n: str = ExifToolGUIData.normalise_tag(tag_target)
        for tag_source in tag_dict:
            tag_source_n = ExifToolGUIData.normalise_tag(tag_source)
            if (tag_source_n == tag_target_n):
                return tag_source
        return None

    @staticmethod
    def normalise_tag(tag: str) -> str:
        if (tag == None or tag == ''):
            return tag
        tag_s: list[str] = tag.split(':')
        # tag_normalised: str = (tag_s[0], tag_s[0] + ':' + tag_s[-1])[len(tag_s) > 1]
        tag_normalised: str = \
            tag_s[0] if len(tag_s) == 1 else tag_s[0] + ':' + tag_s[-1]
        return tag_normalised

    def get(self, file: str, tag: str, default=None):
        metadata = self.cache.get(file, None)
        if (metadata == None):
            return default
        tag_in_source = ExifToolGUIData.match_tag(metadata, tag)
        if (tag_in_source == None):
            return default
        return metadata[tag_in_source]

    def set(self, source_file: str, tag: str, value):
        self.cache_modified[source_file][tag] = value

    def save(self):
        for source_file in self.cache_modified:
            metadata: str = self.cache_modified[source_file]
            with exiftool.ExifToolHelper() as et:
                r = et.set_tags(source_file, metadata,
                                self.settings.exiftool_params)
                # print(r)

    def get_thumbnail(self, source_file: str, default=None) -> bytes:
        s: str = self.get(source_file, 'EXIF:ThumbnailImage')
        if(s == None):
            return default
        b: bytes = base64.b64decode(s[7:])
        return b


if __name__ == '__main__':
    data = ExifToolGUIData(ExifToolGUISettings())
