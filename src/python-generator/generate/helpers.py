#!/usr/bin/env python3

import logging
import sys


def get_lines(filename):
    with open(filename) as file:
        for line in file:
            yield line.strip()


def check_magic(word: str, magic: str):
    if word != magic:
        logging.error("Failed to match magic word %s. Got %s.", magic, word)
        if magic == "begin_version":
            logging.error(
                "Possible cause: you are running the planner on a translator output file from an older version.")
        sys.exit("Search input error")


def in_bounds(index: int, container: list) -> bool:
    return (index >= 0) and (index < len(container))


class FunctionStr:
    def __init__(self, ret_type: str, name: str, params: list[str]):
        self.ret_type = ret_type
        self.name = name
        self.params = params
        self.body = ""

    def add_body(self, to_add: str):
        self.body += to_add + "\n"

    def _make_param_str(self):
        res = ', '.join(self.params)
        return res

    def make_str(self):
        param_str = self._make_param_str()
        res = f"{self.ret_type} {self.name}({param_str}) " + "{\n"
        res += self.body
        res += "}\n"

        return res
