from collections import OrderedDict
import json

import re

from exiftoolgui_configs import ExifToolGUIConfigs


class ExifToolOptionDefs:
    _instance: 'ExifToolOptionDefs' = None

    @classmethod
    @property
    def Instance(cls) -> 'ExifToolOptionDefs':
        if cls._instance == None:
            cls._instance = cls()
        return cls._instance

    pattern_tag: str = (
        r"(?P<tag>-{1,2}[A-Za-z\d_:]*)"

        r"(?:"
        r"(?P<oprator>[+-^<=]+)"
        r"(?P<value>[^\s]*)"
        r")?"
    )

    pattern_non_tag: str = (
        r"(?P<main>-{1,2}[A-Za-z_@:]*)"

        r"(?P<extension>\d+(?::\d+)*)?"

        r"(?:"
        r"(?P<oprator>[+=!.]+)"
        r"(?P<value>[^\s]*)"
        r")?"

        r"(?:"
        r"[ \n]"
        r"(?P<para>[^\s]+)"
        r")?"
    )

    def __init__(self) -> None:
        self.source_file = ExifToolGUIConfigs.Instance.file_exiftool_option_defs
        self.raw: dict[str,] = None
        with open(self.source_file, mode="r", encoding='utf-8') as f:
            self.raw = json.load(f, object_pairs_hook=OrderedDict)

    def get_options_non_tag_name(self):
        option_list: OrderedDict[str, str] = {}

        option_defs: OrderedDict[str, dict[str, str]] = self.raw['options']
        for cat in option_defs.values():
            for hint, describe in cat.items():
                if hint.startswith('-TAG') or hint.startswith('--TAG'):
                    continue
                option_list[hint] = describe

        return option_list

    def find_option(self, option: str):
        option_main = self.get_option_main(option)
        result: tuple[str, str] = None

        option_defs: dict[str, dict[str, str]] = self.raw['options']
        for cat in option_defs.values():
            for hint, describe in cat.items():
                hint_main = self.get_option_main(hint)
                if option_main == hint_main:
                    result = hint, describe
                    break
            if result:
                break

        # Unrecognized options are interpreted as tag names

        return result

    def get_option_main(self, option: str) -> str:
        pattern_main: str = r"^-{1,2}(?:[A-Za-z_@]+|(?<=--)$)"
        match = re.search(pattern_main, option)

        result = None

        if match:
            result = match.group(0)
            #
            pattern_main_list: str = r"^-list(?:w|f|wf|g|d|x)"
            match_list = re.match(pattern_main_list, result)
            if match_list:
                result = '-list'

        return result


if __name__ == "__main__":
    o = ExifToolOptionDefs.Instance

    # main = o.get_option_main("--")
    # print(main)

    # match = o.find_option("-listwf")
    # print(match)

    options_list = o.get_options_non_tag_name()
    print(options_list)

    pass
