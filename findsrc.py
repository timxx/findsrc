#!/usr/bin/env python3

from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from typing import Union
import os
import argparse
import re
import cchardet
import colorama
import cProfile
import io
import pstats


DEFAULT_EXTS = [".h", ".hpp", ".cpp", ".cxx", ".c", ".inl"]


class MyProfile():

    def __init__(self):
        self.pr = cProfile.Profile()
        self.pr.enable()

    def __del__(self):
        self.pr.disable()
        s = io.StringIO()
        ps = pstats.Stats(self.pr, stream=s).sort_stats("cumulative")
        ps.print_stats()
        print(s.getvalue())


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
        "-j", "--jobs",
        metavar="<N>",
        type=int,
        help="Number of threads to run")
    parser.add_argument(
        "--profile",
        action="store_true",
        help="Enable profile")
    parser.add_argument(
        "pattern",
        metavar="<pattern>",
        help="The pattern to find")

    args = parser.parse_args()

    return args


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


def find_src(src, pattern: Union[re.Pattern, str], lock: Lock, color_output=True):
    try:
        result = []
        f = open(src, "r", encoding=_file_encoding(src))
        line_no = 1

        # call function will slow down the performance
        # so use if else LoL
        is_regexp = isinstance(pattern, re.Pattern)
        if color_output:
            _color_text = lambda text, l, s, e: text[l:s] + "\033[1;31m" + text[s:e] + "\033[m"
            for line in f:
                line_no += 1
                content = ""
                last_pos = 0
                if is_regexp:
                    # sub is too slow
                    for m in pattern.finditer(line):
                        content += _color_text(line, last_pos, m.start(), m.end())
                        last_pos = m.end()
                else:
                    start = line.find(pattern)
                    while start != -1:
                        end = start + len(pattern)
                        content += _color_text(line, last_pos, start, end)
                        start = line.find(pattern, end)
                        last_pos = end
                if content:
                    if last_pos < len(line):
                        content += line[last_pos:]
                    result.append("  {}: {}".format(line_no, content))
        else:
            for line in f:
                line_no += 1
                if (is_regexp and pattern.search(line)) or (pattern in line):
                    result.append("  {}: {}".format(line_no, line))
        f.close()

        if result:
            if lock:
                lock.acquire()
            print(src)
            for r in result:
                print(r, end="")
            print("")
            if lock:
                lock.release()

    except UnicodeDecodeError:
        print("Unknown encoding for:", src)


def _is_stdout_support_color():
    if os.name == "nt":
        term = os.getenv("TERM", "")
        return term == "xterm"
    else:
        return True


def _is_regexp(pattern):
    metachars = r".^$*+?{}[]\|()"

    # Not consider the escape case LoL
    for c in pattern:
        if c in metachars:
            return True

    return False


def _scan_files(path):
    for entry in os.scandir(path):
        if entry.is_dir(follow_symlinks=False):
            yield from _scan_files(entry.path)
        else:
            yield entry


def main():
    args = _setup_args()

    if args.profile:
        profile = MyProfile()

    target_dir = args.path or os.getcwd()
    exts = _parse_exts(args.extension)
    pattern = re.compile(args.pattern) \
        if _is_regexp(args.pattern) \
        else args.pattern

    if not _is_stdout_support_color():
        colorama.init()

    if args.jobs and args.jobs > 1:
        executor = ThreadPoolExecutor(args.jobs)
        lock = Lock()
    else:
        executor = None
        lock = None

    for entry in _scan_files(target_dir):
        for ext in exts:
            if entry.name.endswith(ext):
                if executor:
                    executor.submit(
                        find_src,
                        entry.path, pattern, lock)
                else:
                    find_src(entry.path, pattern, lock)
                break

    if args.profile:
        del profile


if __name__ == "__main__":
    main()
