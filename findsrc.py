#!/usr/bin/env python3

import multiprocessing as mp
import os
import argparse
import re


DEFAULT_EXTS = [".h", ".cpp", ".hpp", ".cxx", ".c", ".cc", ".inl"]


class MyProfile():

    def __init__(self):
        import cProfile
        self.pr = cProfile.Profile()
        self.pr.enable()

    def __del__(self):
        self.pr.disable()
        import io
        import pstats
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

    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "-e", "--extension",
        metavar="<ext>",
        action="append",
        help="Specify the file extension to find")
    group.add_argument(
        "-n", "--name",
        metavar="<name>",
        help="Find by file name instead of file extension")

    parser.add_argument(
        "-p", "--path",
        metavar="<path>",
        help="The path to find, default to current directory")
    parser.add_argument(
        "-i", "--ignore-case",
        action="store_true",
        help="Case insensitive")
    parser.add_argument(
        "-j", "--jobs",
        metavar="<N>",
        type=int,
        help="Number of jobs to run for finding")
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


# must be global
print_lock = None


def find_src(src, pattern, color_output=True):
    f = open(src, "rb")
    data = f.read()
    f.close()

    encoding = None
    if len(data) > 4:
        if data[0:4] == b"\x00\x00\xFE\xFF":
            encoding = "utf-32be"
        elif data[0:4] == b"\xFF\xFE\x00\x00":
            encoding = "utf-32le"
    if encoding is None and len(data) > 3:
        if data[0:3] == b"\xEF\xBB\xBF":
            encoding = "utf-8"
    if encoding is None and len(data) > 2:
        if data[0:2] == b"\xFF\xFE":
            encoding = "utf-16le"
        elif data[0:2] == b"\xFE\xFF":
            encoding = "utf-16be"

    encodings = ["gb18030", "utf-8", "iso-8859-1"]
    if encoding:
        if encoding in encodings:
            encodings.remove(encoding)
        encodings.insert(0, encoding)

    lines = []
    can_decode = False
    for encoding in encodings:
        try:
            lines = data.decode(encoding).splitlines(True)
            can_decode = True
            break
        except UnicodeDecodeError:
            pass

    if not can_decode:
        print("Unknown encoding for:", src)
        return

    result = []
    line_no = 1
    # call function will slow down the performance
    # so use if else LoL
    is_regexp = isinstance(pattern, re.Pattern)
    if color_output:
        _color_text = lambda text, l, s, e: text[l:s] + "\033[1;31m" + text[s:e] + "\033[m"
        for line in lines:
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
        for line in lines:
            line_no += 1
            if (is_regexp and pattern.search(line)) or (pattern in line):
                result.append("  {}: {}".format(line_no, line))

    if result:
        if print_lock:
            print_lock.acquire()
        print(src)
        for r in result:
            print(r, end="")
        print("")
        if print_lock:
            print_lock.release()


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


def _make_pattern(args):
    if args.ignore_case or _is_regexp(args.pattern):
        flags = 0
        if args.ignore_case:
            flags |= re.IGNORECASE
        return re.compile(args.pattern, flags)
    return args.pattern


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
    pattern = _make_pattern(args)

    if not _is_stdout_support_color():
        import colorama
        colorama.init()

    if args.jobs is None or args.jobs > 1:
        global print_lock
        print_lock = mp.Lock()
        executor = mp.Pool(args.jobs)
    else:
        executor = None

    jobs = []
    add_job = jobs.append

    # if else for performance LoL
    if args.name:
        if os.name == "nt":
            name = args.name.lower()
            name_cmp = lambda n: n.lower() == name
        else:
            name_cmp = lambda n: n == args.name
        for entry in _scan_files(target_dir):
            if name_cmp(entry.name):
                if executor:
                    job = executor.apply_async(
                        find_src, args=(entry.path, pattern))
                    add_job(job)
                else:
                    find_src(entry.path, pattern)
    else:
        for entry in _scan_files(target_dir):
            for ext in exts:
                if entry.name.endswith(ext):
                    if executor:
                        job = executor.apply_async(
                            find_src, args=(entry.path, pattern))
                        add_job(job)
                    else:
                        find_src(entry.path, pattern)
                break

    for job in jobs:
        job.get()

    if args.profile:
        del profile


if __name__ == "__main__":
    main()
