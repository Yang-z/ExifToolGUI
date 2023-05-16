import json
import os


class ExifToolGUISettings:
    def __init__(self) -> None:
        self.source_file = 'exiftoolgui_settings.json'
        self.raw: dict = None
        self.load()

    @property
    def ui(self) -> str:
        return self.raw['ui']

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

    def load(self) -> dict:
        with open(self.source_file, encoding='utf-8') as f:
            self.raw: dict = json.load(f)

    def save(self) -> dict:
        with open(self.source_file, 'w', encoding='utf-8') as f:
            json.dump(self.raw, f, ensure_ascii=False, indent=2)

    def add_dir(self, dir: str):
        self.dirs.append(dir)
        self.save()

    def remove_dir(self, dir: str):
        self.dirs.remove(dir)
        self.save()
