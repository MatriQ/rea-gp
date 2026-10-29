#!/usr/bin/env python3
"""Discover analysis tools; optionally probe versions. Never installs or selects a device."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys


# None means discovery only: do not launch interactive analyzers or device binaries.
SPECS = {
    'python': ([], ['--version']), 'node': (['node'], ['--version']),
    'java': (['java'], ['-version']), 'keytool': (['keytool'], None),
    'rea': (['rea'], ['--version']), 'adb': (['adb'], ['version']),
    'aapt2': (['aapt2'], ['version']), 'apksigner': (['apksigner'], ['version']),
    'zipalign': (['zipalign'], ['-h']), 'jadx': (['jadx'], ['--version']),
    'apktool': (['apktool'], ['--version']), 'd8': (['d8'], ['--version']),
    'llvm-readelf': (['llvm-readelf'], ['--version']),
    'llvm-objdump': (['llvm-objdump'], ['--version']),
    'llvm-nm': (['llvm-nm'], ['--version']), 'llvm-mc': (['llvm-mc'], ['--version']),
    'clang': (['clang'], ['--version']), 'readelf': (['readelf'], ['--version']),
    'objdump': (['objdump'], ['--version']), 'lldb': (['lldb'], ['--version']),
    'frida': (['frida'], ['--version']), 'frida-server': ([], None),
    'lldb-server': ([], None), 'dotnet': (['dotnet'], ['--version']),
    'ilspycmd': (['ilspycmd'], ['--version']), 'cpp2il': (['Cpp2IL', 'cpp2il'], None),
    'il2cppdumper': (['Il2CppDumper', 'il2cppdumper'], None),
    'ghidra': (['analyzeHeadless'], None), 'ida': (['idat64', 'ida64', 'idat'], None),
    'sdkmanager': (['sdkmanager'], None), 'avdmanager': (['avdmanager'], None),
    'emulator': (['emulator'], ['-version']), 'mitmproxy': (['mitmproxy'], ['--version']),
    'curl': (['curl'], ['--version'])
}
MODULES = {'frida':'frida', 'frida_tools':'frida-tools', 'elftools':'pyelftools',
           'capstone':'capstone', 'keystone':'keystone-engine', 'lief':'lief',
           'UnityPy':'UnityPy', 'flatbuffers':'flatbuffers', 'lz4':'lz4',
           'fastapi':'fastapi', 'uvicorn':'uvicorn', 'httpx':'httpx'}


def unique_paths(values):
    result = []
    for value in values:
        if not value:
            continue
        p = Path(value).expanduser().absolute()
        if p.is_dir() and p not in result:
            result.append(p)
    return result


def versions(path):
    return sorted(path.glob('*'), key=lambda p: tuple(int(x) for x in re.findall(r'\d+', p.name)), reverse=True) if path.is_dir() else []


def locate(name, roots, explicit):
    if name in explicit:
        p = Path(explicit[name]).expanduser().absolute()
        return str(p) if p.is_file() else None
    if name == 'python':
        return sys.executable
    for candidate in SPECS[name][0]:
        p = shutil.which(candidate)
        if p:
            return p
    for root in roots:
        for suffix in ['', '.exe', '.bat', '.cmd']:
            p = root/(name+suffix)
            if p.is_file():
                return str(p)
    return None


def command_for(name, path, tools):
    suffix = Path(path).suffix.lower()
    runner = 'java' if suffix == '.jar' else 'dotnet' if suffix == '.dll' else 'node' if suffix in ('.js', '.mjs') else None
    if runner:
        executable = tools[runner]['path']
        if not executable:
            return None, runner
        return [executable]+(['-jar'] if runner == 'java' else [])+[path], None
    if SPECS[name][1] is not None and os.name != 'nt' and not os.access(path, os.X_OK):
        return None, 'execute_permission'
    return [path], None


def probe(item):
    name, record = item
    args = SPECS[name][1]
    if not record['command'] or args is None:
        return name, None
    env = dict(os.environ, DOTNET_CLI_TELEMETRY_OPTOUT='1', DOTNET_SKIP_FIRST_TIME_EXPERIENCE='1')
    try:
        r = subprocess.run(record['command']+args, capture_output=True, text=True,
                           errors='replace', timeout=5, env=env)
        accepted = (0, 1, 2) if name == 'zipalign' else (0,)
        return name, {'ok':r.returncode in accepted, 'exit_code':r.returncode,
                      'output':(r.stdout+'\n'+r.stderr).strip()[:1600]}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return name, {'ok':False, 'error':str(exc)[:600]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--probe', action='store_true')
    parser.add_argument('--sdk-root', action='append', default=[])
    parser.add_argument('--ndk-root', action='append', default=[])
    parser.add_argument('--tool', action='append', default=[], metavar='NAME=PATH')
    parser.add_argument('--require', action='append', default=[], choices=sorted(SPECS))
    args = parser.parse_args()
    explicit = {}
    for value in args.tool:
        name, separator, path = value.partition('=')
        name = name.lower()
        if not separator or name not in SPECS or not path:
            parser.error('--tool requires a known NAME=PATH; names: '+', '.join(sorted(SPECS)))
        explicit[name] = path
    home = Path.home()
    sdks = unique_paths([*args.sdk_root, os.getenv('ANDROID_SDK_ROOT'), os.getenv('ANDROID_HOME'),
                         home/'Library/Android/sdk', home/'Android/Sdk',
                         Path(os.getenv('LOCALAPPDATA', str(home/'AppData/Local')))/'Android/Sdk'])
    roots = []
    for sdk in sdks:
        roots.extend([sdk/'platform-tools', sdk/'emulator'])
        roots.extend(p for p in versions(sdk/'build-tools') if p.is_dir())
        roots.extend(p/'bin' for p in versions(sdk/'cmdline-tools') if p.is_dir())
    ndks = unique_paths([*args.ndk_root, os.getenv('ANDROID_NDK_HOME'), os.getenv('NDK_HOME'),
                         *(p for sdk in sdks for p in versions(sdk/'ndk'))])
    host = 'darwin' if sys.platform == 'darwin' else 'windows' if os.name == 'nt' else 'linux'
    for ndk in ndks:
        roots.extend(p/'bin' for p in (ndk/'toolchains/llvm/prebuilt').glob(host+'*'))
    java_home = os.getenv('JAVA_HOME')
    if java_home:
        roots.append(Path(java_home)/'bin')
    ghidra_home = os.getenv('GHIDRA_INSTALL_DIR')
    if ghidra_home:
        roots.append(Path(ghidra_home)/'support')
    # SDK/NDK discovery is only a fallback; explicit paths override PATH.
    tools = {name:{'path':locate(name, roots, explicit)} for name in SPECS}
    if ghidra_home and not tools['ghidra']['path']:
        for suffix in ['', '.bat']:
            p = Path(ghidra_home)/'support'/('analyzeHeadless'+suffix)
            if p.is_file():
                tools['ghidra']['path'] = str(p)
                break
    for name, record in tools.items():
        record['found'] = record['path'] is not None
        record['command'], record['missing_runner'] = command_for(name, record['path'], tools) if record['path'] else (None, None)
    if args.probe:
        with ThreadPoolExecutor(max_workers=4) as pool:
            for name, result in pool.map(probe, tools.items()):
                if result is not None:
                    tools[name]['probe'] = result
    modules = {}
    for module, distribution in MODULES.items():
        try:
            found = importlib.util.find_spec(module) is not None
        except (ImportError, ValueError):
            found = False
        try:
            version = importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError:
            version = None
        modules[module] = {'found':found, 'version':version}
    missing = [n for n in args.require if not tools[n]['command']]
    unusable = [n for n in args.require if tools[n].get('probe', {}).get('ok') is False]
    result = {'status':'missing_required' if missing else 'unusable_required' if unusable else 'inventory_complete',
              'host':{'platform':platform.system(),'machine':platform.machine()},
              'sdk_roots':[str(p) for p in sdks], 'ndk_roots':[str(p) for p in ndks],
              'tools':tools, 'python_packages':{'interpreter':sys.executable,'modules':modules},
              'required_missing':missing, 'required_unusable':unusable,
              'limits':['Discovery does not prove target format or ABI compatibility.',
                        'MCP capabilities and other Python environments require separate discovery.',
                        'No tools installed, devices contacted, or target applications executed.']}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 2 if missing or unusable else 0


if __name__ == '__main__':
    sys.exit(main())
