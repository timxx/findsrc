#!/usr/bin/env python3

from concurrent.futures import ThreadPoolExecutor
from threading import Lock
import os
import argparse
import re
import cchardet
import colorama


DEFAULT_EXTS = [".h", ".hpp", ".cpp", ".cxx", ".c", ".inl"]


def _can_find(file, exts):
    ext = os.path.splitext(file)[1]
    return ext and ext in exts


def _parse_exts(exts):
    if not exts:
        return DEFAULT_EXTS

    result = []
    for e in exts:
        for ee in e.split(','):
            result.append(ee if ee[0] == "." else ("." + ee))

    return result


def _setup_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-e", "--extension",
        metavar="<ext>",
        action="append",
        help="Specify the file extension to find")
    parser.add_argument(
        "-p", "--path",
        metavar="<path>",
        help="The path to find, default to current directory")
    parser.add_argument(
        "pattern",
        metavar="<pattern>",
        help="The pattern to find")

    args = parser.parse_args()

    return args


class FindResult:

    def __init__(self, content, line_no):
        self.before = []
        self.line = content
        self.line_no = line_no
        self.ranges = []
        self.after = []

    def addRange(self, start, end):
        self.ranges.append((start, end))

    def isValid(self):
        return len(self.ranges) > 0

    def print(self, color_output=True):
        line_no = self.line_no - len(self.before)
        for b in self.before:
            print("  {}:{}".format(line_no, b), end="")
            line_no += 1

        print("  {}:{}".format(
            self.line_no,
            self._pretty_content(color_output)),
            end="")

        line_no = self.line_no + 1
        for a in self.after:
            print("  {}:{}".format(line_no, a), end="")
            line_no += 1

    def _pretty_content(self, color_output):
        if not color_output:
            return self.line

        content = self.line
        for start, end in reversed(self.ranges):
            content = content[:end] + "\033[m" + content[end:]
            content = content[:start] + "\033[1;31m" + content[start:]
        return content


def _file_encoding(path):
    with open(path, "rb") as f:
        bom = f.read(4)
        if len(bom) > 3:
            if bom[0:3] == b"\xEF\xBB\xBF":
                return "utf-8"
        if len(bom) > 2:
            if bom[0:2] == b"\xFF\xFE":
                return "utf-16le"
            if bom[0:2] == b"\xFE\xFF":
                return "utf-16be"

        f.seek(0)
        result = cchardet.detect(f.read())
        enc = result.get("encoding")
        if enc:
            return enc

    return "utf-8"


def find_src(src, pattern: re.Pattern, lock: Lock, color_output=True):
    try:
        result = []
        f = open(src, "r", encoding=_file_encoding(src))
        line_no = 1
        for line in f:
            fr = FindResult(line, line_no)
            line_no += 1
            for m in pattern.finditer(line):
                fr.addRange(m.start(), m.end())
            if fr.isValid():
                result.append(fr)
        f.close()

        if result:
            lock.acquire()
            print(src)
            for r in result:
                r.print(color_output)
            print("")
            lock.release()

    except UnicodeDecodeError:
        print("Unknown encoding for:", src)


def _is_stdout_support_color():
    if os.name == "nt":
        term = os.getenv("TERM", "")
        return term == "xterm"
    else:
        return True


def main():
    args = _setup_args()
    target_dir = args.path or os.getcwd()
    exts = _parse_exts(args.extension)
    pattern = re.compile(args.pattern)

    if not _is_stdout_support_color():
        colorama.init()

    executor = ThreadPoolExecutor()
    lock = Lock()

    for root, _, files in os.walk(target_dir):
        for file in files:
            if _can_find(file, exts):
                full_path = os.path.join(root, file)
                executor.submit(
                    find_src,
                    full_path, pattern, lock)


if __name__ == "__main__":
    main()
