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
    def exiftool_params(self) -> list:
        return self.raw['exiftool_params']['forced'] + self.raw['exiftool_params']['optional']

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
