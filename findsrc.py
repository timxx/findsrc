#!/usr/bin/env python3

from concurrent.futures import ThreadPoolExecutor
import os
import argparse


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


def find_src(src, pattern, color_output=True):
    pass


def main():
    args = _setup_args()
    target_dir = args.path or os.getcwd()
    exts = _parse_exts(args.extension)

    executor = ThreadPoolExecutor()

    for root, _, files in os.walk(target_dir):
        for file in files:
            if _can_find(file, exts):
                full_path = os.path.join(root, file)
                executor.submit(
                    find_src,
                    full_path, args.pattern)


if __name__ == "__main__":
    main()
