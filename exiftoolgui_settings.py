import json
import os

from collections import OrderedDict


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
    def ui(self) -> str:
        return self.raw['ui']

    @property
    def assets_no_preview(self) -> str:
        return self.raw['assets']['no_preview']

    @property
    def dirs(self) -> list:
        return self.raw['dirs']

    @property
    def tags_for_group(self) -> list:
        return self.raw['tags_for_group']

    @property
    def tags_for_single_custom(self) -> list:
        return self.raw['tags_for_single_custom']

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

    @property
    def exiftool_options(self) -> dict[str, str]:
        return self.raw['exiftool_options']

    @property
    def exiftool_params(self) -> list:
        return [k.replace(' ', '\n') for k, v in self.exiftool_options.items() if v == 'forced' or v == 'on']

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
    def functions(self) -> dict[str, dict[str, dict[str,]]]:
        return self.raw['functions']

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
