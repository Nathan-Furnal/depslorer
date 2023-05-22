import site
from pathlib import Path
from collections import defaultdict
import ast
from typing import Any, Iterable
import re
import tomllib
import yaml

DEFAULT_PKGS = {'pip', 'setuptools', 'wheel', 'python', 'python_version'}

def _dep_from_toml(d: dict[str, Any]) -> Iterable[str]:
    if d.get('tool', {}).get('poetry', None):
        return d['tool']['poetry']['dependencies'].keys()
    if d.get('project', {}).get('dependencies', None):
        pat = re.compile(r'[\[=<>]')
        return [re.split(pat, el.strip('^'))[0] for el in d['project']['dependencies']]
    return []

def deps_from_depfiles(filepaths: Path | Iterable[Path]):
    if isinstance(filepaths, Path):
        filepaths = [filepaths]
    deps: set[str] = set()
    for fp in filepaths:
        match(fp.suffix):
            case '.toml':
                with open(fp, 'rb') as f:
                    out = tomllib.load(f)
                    deps.update(_dep_from_toml(out))
            case '.txt':
                with open(fp) as f:
                    # Find all lines starting with a character and with zero or
                    # more letters separated by hyphens/underscores Note that
                    # this doesn't enforce any 'correct' naming for the packages
                    # it just makes sure to catch possible packages names
                    deps.update(re.findall(r'^\w+[-_\w+]*', fp.read_text().strip(), re.MULTILINE))
            case '.yml' | '.yaml':
                pat = re.compile(r'[\[=<>]')
                pat_git = re.compile(r'[@#\.]')
                with open(fp) as f:
                    out = yaml.safe_load(f)
                    for dep in out.get('dependencies', []):
                        # Check that the first char is alpha
                        # to avoid commands or invalid names
                        if isinstance(dep, str) and dep[0].isalpha():
                        # split on any of '[=<>' and get only the pkg name
                            deps.add(re.split(pat, dep)[0])
                        if isinstance(dep, dict) and dep.get('pip', None):
                            for el in dep['pip']:
                                # dependency like 'git+<...>'
                                if isinstance(el, str) and el.startswith('git'):
                                    # get the last element of the URL with a '/' split
                                    # and try to remove .git extension as well as @ or # details
                                    deps.add(re.split(pat_git, el.split('/')[-1])[0])
                                elif isinstance(el, str) and el[0].isalpha():
                                    deps.add(re.split(pat, el)[0])
            case _:
                raise ValueError(f"Unknown file extensions: {fp.suffix}")
    return deps

def get_installed_deps() -> dict[str, set[str]]:
    name_imports_mapping = defaultdict(set)
    for d in site.getsitepackages():
        info_dirs = Path(d).glob('*-info')
        for info_dir in info_dirs:
            # pkgs are named like pkg-<version>
            pkg_name = info_dir.stem.split("-")[0]
            if (fn := (info_dir / 'top_level.txt')).exists():
                import_names = fn.read_text().strip().splitlines()
                name_imports_mapping[pkg_name].update(import_names)
            else:
                name_imports_mapping[pkg_name].add(pkg_name)
    return name_imports_mapping


def get_used_imports(filepaths: str | Path | Iterable[str | Path]) -> set[str]:
    if isinstance(filepaths, (str, Path)):
        filepaths = [filepaths]
    imports: set[str] = set()
    for fp in filepaths:
        with open(fp, 'r') as f:
            tree = ast.parse(f.read(), filename=fp)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.add(alias.name)
                if isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.add(node.module)
    return imports

def gen_unused_pkgs(deps: dict[str, set[str]],
                    used_imports: set[str],
                    depfiles: Path | Iterable[Path] | None = None):
    has_issue = False
    file_deps = None
    if depfiles:
        file_deps = deps_from_depfiles(depfiles)

    for dep, import_names in deps.items():
        if not any(imp in used_imports for imp in import_names) and dep not in DEFAULT_PKGS:
            if not file_deps:
                has_issue = True
                print(f"'{dep}' is probably unused.")
            else:
                if dep.lower() in file_deps:
                    has_issue = True
                    print(f"'{dep}' is probably unused.")
    if not has_issue:
        print("No unused dependencies were found.")
