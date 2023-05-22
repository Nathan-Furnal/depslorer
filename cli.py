import argparse
from deps_explorer import (
    deps_from_depfiles,
    get_installed_deps,
    get_used_imports,
    gen_unused_pkgs,
)
from pathlib import Path
import glob

def fnames(string):
    if string == ".":
        return ["**/*.py"]
    else:
        return string

def parse_fnames(inp: list[str], recur: bool):
    if len(inp) > 1:
        return [Path(p) for p in inp]
    else:
        el = inp[0]
        if '*' in el:
            return [Path(p) for p in glob.glob(el, recursive=recur)]
        else: return Path(el)
    

parser = argparse.ArgumentParser(prog="Dependencies explorer")
parser.add_argument("-f", "--filenames", default=".", type=fnames, nargs='+')
parser.add_argument("-r", "--recursive", choices=["true", "false"], default="true")
parser.add_argument("-d", "--depfiles", nargs="*", default=None)

def main():
    args = parser.parse_args()
    recur = True if args.recursive == "true" else False
    filenames = parse_fnames(args.filenames, recur=recur)
    depfiles = parse_fnames(args.depfiles, recur=False) if args.depfiles else None
    try:
        gen_unused_pkgs(
            get_installed_deps(),
            get_used_imports(filenames),
            depfiles
        )
    except FileNotFoundError as fnfe:
        print(f"No such file: {fnfe.filename}")
        print("CLI interrupted!")

if __name__ == '__main__':
    main()
