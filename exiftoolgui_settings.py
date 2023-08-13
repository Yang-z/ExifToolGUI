from collections import OrderedDict
import json

import os


class ExifToolGUISettings:
    _instance: 'ExifToolGUISettings' = None

    @classmethod
    @property
    def Instance(cls) -> 'ExifToolGUISettings':
        if cls._instance == None:
            cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        self.source_file = 'exiftoolgui_settings.json'
        self.raw: dict = None
        self.load()

    def __getitem__(self, key):
        return self.raw[key]

    @property
    def assets_ui(self) -> str:
        return self.raw['assets']['ui']

    @property
    def dirs(self) -> list:
        return self.raw['dirs']

    @property
    def tags_for_group(self) -> list:
        return self.raw['tags_for_group']

    @property
    def tags_for_single(self) -> dict[str, list[str]]:
        return self.raw['tags_for_single']

    @property
    def files(self) -> list:
        all_files: list = []
        for top in self.dirs:
            for root, dirs, files in os.walk(top):
                for file in files:
                    file_path: str = os.path.join(root, file)
                    all_files.append(file_path)
                break
        return all_files

    '''################################################################
    exiftool_options
    ################################################################'''

    @property
    def exiftool_options(self) -> dict[str, str]:
        return self.raw['exiftool_options']

    @exiftool_options.setter
    def exiftool_options(self, value):
        self.raw['exiftool_options'] = value
        self.save()

    @property
    def exiftool_params(self) -> list:
        return [k.replace(' ', '\n') for k, v in self.exiftool_options.items() if v == 'forced' or v == 'on']

    '''################################################################
    exiftoolgui_options
    ################################################################'''

    @property
    def auto_save(self) -> bool:
        return self.raw['exiftoolgui_options']['auto_save']

    @property
    def max_group_level(self) -> int:
        return self.raw['exiftoolgui_options']['max_group_level']

    @property
    def simplify_group_level(self) -> bool:
        return self.raw['exiftoolgui_options']['simplify_group_level']

    @property
    def default_timezone(self) -> str:
        return self.raw['exiftoolgui_options']['default_timezone']

    @property
    def preview_size(self) -> int:
        return self.raw['exiftoolgui_options']['preview_size']

    @property
    def preview_precision(self) -> int:
        return self.raw['exiftoolgui_options']['preview_precision']

    '''################################################################
    functions
    ################################################################'''

    @property
    def functions(self) -> dict[str, dict[str, dict[str,]]]:
        return self.raw['functions']

    '''################################################################
    tag_defs
    ################################################################'''

    @property
    def composite_tags(self) -> dict[str, dict[str,]]:
        return self.raw['composite_tags']

    @property
    def datetime_tags(self) -> dict[str, dict[str,]]:
        return self.raw['datetime_tags']

    @property
    def conditional_tags(self) -> dict[str, dict[str, dict[str, str]]]:
        return self.raw['conditional_tags']

    '''################################################################
    IO
    ################################################################'''

    def load(self) -> dict:
        with open(self.source_file, encoding='utf-8') as f:
            self.raw: dict = json.load(f, object_pairs_hook=OrderedDict)

    def save(self) -> dict:
        with open(self.source_file, 'w', encoding='utf-8') as f:
            json.dump(self.raw, f, ensure_ascii=False, indent=2)

    def add_dir(self, dir: str):
        self.dirs.append(dir)
        self.save()

    def remove_dir(self, dir: str):
        self.dirs.remove(dir)
        self.save()


if __name__ == "__main__":
    settings: ExifToolGUISettings = ExifToolGUISettings.Instance

    print(settings.functions)
