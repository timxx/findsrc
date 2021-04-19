#!/usr/bin/env python3

from concurrent.futures import ThreadPoolExecutor
from threading import Lock
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


def _can_find(file, exts):
    for ext in exts:
        if file.endswith(ext):
            return True
    return False


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


def find_src(src, pattern: re.Pattern, lock: Lock, color_output=True):
    try:
        result = []
        f = open(src, "r", encoding=_file_encoding(src))
        line_no = 1
        for line in f:
            line_no += 1
            if color_output:
                content = ""
                last_pos = 0
                # sub is too slow
                for m in pattern.finditer(line):
                    content += line[last_pos:m.start()] + "\033[1;31m" + \
                        line[m.start():m.end()] + "\033[m"
                    last_pos = m.end()
                if content:
                    if last_pos < len(line):
                        content += line[last_pos:]
                    result.append("  {}: {}".format(line_no, content))
            elif pattern.search(line):
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


def main():
    #profile = MyProfile()
    args = _setup_args()
    target_dir = args.path or os.getcwd()
    exts = _parse_exts(args.extension)
    pattern = re.compile(args.pattern)

    if not _is_stdout_support_color():
        colorama.init()

    if args.jobs and args.jobs > 1:
        executor = ThreadPoolExecutor(args.jobs)
        lock = Lock()
    else:
        executor = None
        lock = None

    for root, _, files in os.walk(target_dir):
        for file in files:
            if _can_find(file, exts):
                full_path = os.path.join(root, file)
                if executor:
                    executor.submit(
                        find_src,
                        full_path, pattern, lock)
                else:
                    find_src(full_path, pattern, lock)

    #del profile


if __name__ == "__main__":
    main()
