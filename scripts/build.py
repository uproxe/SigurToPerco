#!/usr/bin/env python3
"""Сборка программы под текущую систему.

    python scripts/build.py                     # версия берётся из sigur_perco/__init__.py
    python scripts/build.py --version 3.1.0     # заодно прописать версию в программу
    python scripts/build.py --suffix win7       # добавить метку к имени файла

Нужны: pip install -r requirements.txt pyinstaller

Что получается в папке release/:
    Windows  ->  SigurPerco-<версия>-windows-x64.exe       (один файл, ничего ставить не нужно)
    Linux    ->  sigur-perco_<версия>_amd64.deb            (пакет: sudo apt install ./файл.deb)
                 SigurPerco-<версия>-linux-x64.tar.gz      (то же без установки)
    macOS    ->  SigurPerco-<версия>-macos-<arm64|intel>.dmg
"""

import argparse
import os
import platform
import plistlib
import re
import shutil
import subprocess
import sys
import tarfile
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ASSETS = os.path.join(ROOT, "assets")
BUILD = os.path.join(ROOT, "build")
DIST = os.path.join(ROOT, "dist")
RELEASE = os.path.join(ROOT, "release")
INIT = os.path.join(ROOT, "sigur_perco", "__init__.py")

APP = "SigurPerco"                  # имя программы/файла
PKG = "sigur-perco"                 # имя пакета Linux
BUNDLE_ID = "io.github.sigurperco"  # идентификатор приложения macOS
DESCRIPTION = "Sigur -> PERCo: пересчёт номеров пропусков и выгрузки сотрудников"

IS_WIN = sys.platform == "win32"
IS_MAC = sys.platform == "darwin"


def log(msg):
    print("\n==> " + msg, flush=True)


def run(cmd, **kw):
    print("$ " + " ".join(cmd), flush=True)
    subprocess.check_call(cmd, **kw)


# ---------------------------------------------------------------- версия

def read_version():
    with open(INIT, encoding="utf-8") as f:
        m = re.search(r'__version__\s*=\s*"([^"]+)"', f.read())
    return m.group(1) if m else "0.0.0"


def write_version(version):
    with open(INIT, encoding="utf-8") as f:
        s = f.read()
    s = re.sub(r'__version__\s*=\s*"[^"]*"', '__version__ = "%s"' % version, s)
    with open(INIT, "w", encoding="utf-8") as f:
        f.write(s)


def version_tuple(version):
    nums = [int(x) for x in re.findall(r"\d+", version)[:4]]
    return tuple((nums + [0, 0, 0, 0])[:4])


def write_windows_version_info(path, version):
    """Свойства exe-файла (Подробно -> Версия, Описание)."""
    t = version_tuple(version)
    content = """# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(filevers=%(t)r, prodvers=%(t)r, mask=0x3f, flags=0x0,
                    OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable(u'041904B0', [
      StringStruct(u'FileDescription', u'%(desc)s'),
      StringStruct(u'FileVersion', u'%(v)s'),
      StringStruct(u'InternalName', u'%(app)s'),
      StringStruct(u'OriginalFilename', u'%(app)s.exe'),
      StringStruct(u'ProductName', u'Sigur -> PERCo'),
      StringStruct(u'ProductVersion', u'%(v)s')])]),
    VarFileInfo([VarStruct(u'Translation', [0x0419, 1200])])
  ]
)
""" % {"t": t, "v": version, "app": APP, "desc": DESCRIPTION}
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


# ---------------------------------------------------------------- PyInstaller

def has_module(name):
    try:
        __import__(name)
        return True
    except Exception:
        return False


def pyinstaller(version):
    log("PyInstaller")
    os.makedirs(BUILD, exist_ok=True)
    cmd = [
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--windowed",
        "--name", APP,
        "--distpath", DIST, "--workpath", os.path.join(BUILD, "pyinstaller"), "--specpath", BUILD,
        "--add-data", ASSETS + os.pathsep + "assets",
    ]
    for mod in ("numpy", "pandas", "PIL", "matplotlib", "pytest", "IPython"):
        cmd += ["--exclude-module", mod]
    if has_module("tkinterdnd2"):
        cmd += ["--collect-all", "tkinterdnd2"]
    else:
        print("! tkinterdnd2 не установлен - перетаскивание файлов в окно работать не будет")

    if IS_WIN:
        vi = os.path.join(BUILD, "version_info.txt")
        write_windows_version_info(vi, version)
        cmd += ["--onefile", "--icon", os.path.join(ASSETS, "icon.ico"), "--version-file", vi]
    elif IS_MAC:
        cmd += ["--onedir", "--icon", os.path.join(ASSETS, "icon.icns"), "--osx-bundle-identifier", BUNDLE_ID]
    else:
        cmd += ["--onedir"]

    cmd.append(os.path.join(ROOT, "run.py"))
    run(cmd, cwd=ROOT)


# ---------------------------------------------------------------- упаковка

def package_windows(version, suffix):
    name = "%s-%s-windows-x64%s.exe" % (APP, version, "-" + suffix if suffix else "")
    shutil.copy2(os.path.join(DIST, APP + ".exe"), os.path.join(RELEASE, name))
    return [name]


def _deb_version(version):
    # 3.1.0-beta1 -> 3.1.0~beta1 (так dpkg правильно сравнивает версии)
    return version.replace("-", "~")


def package_linux(version, suffix):
    app_dir = os.path.join(DIST, APP)
    out = []
    tag = "-" + suffix if suffix else ""

    # 1) tar.gz - распаковал и запустил
    tgz = "%s-%s-linux-x64%s.tar.gz" % (APP, version, tag)
    with tarfile.open(os.path.join(RELEASE, tgz), "w:gz") as tar:
        tar.add(app_dir, arcname=APP)
    out.append(tgz)

    # 2) .deb
    if not shutil.which("dpkg-deb"):
        print("! dpkg-deb не найден - .deb пропущен")
        return out
    root = os.path.join(BUILD, "deb", PKG)
    shutil.rmtree(root, ignore_errors=True)
    opt = os.path.join(root, "opt", PKG)
    shutil.copytree(app_dir, opt, symlinks=True)

    os.makedirs(os.path.join(root, "usr", "bin"))
    os.symlink("/opt/%s/%s" % (PKG, APP), os.path.join(root, "usr", "bin", PKG))

    apps = os.path.join(root, "usr", "share", "applications")
    os.makedirs(apps)
    with open(os.path.join(ROOT, "packaging", "linux", PKG + ".desktop"), encoding="utf-8") as f:
        desktop = f.read().replace("@EXEC@", "/opt/%s/%s" % (PKG, APP)).replace("@ICON@", PKG)
    with open(os.path.join(apps, PKG + ".desktop"), "w", encoding="utf-8") as f:
        f.write(desktop)

    for size in (16, 24, 32, 48, 64, 128, 256, 512):
        d = os.path.join(root, "usr", "share", "icons", "hicolor", "%dx%d" % (size, size), "apps")
        os.makedirs(d)
        shutil.copy2(os.path.join(ASSETS, "icons", "%d.png" % size), os.path.join(d, PKG + ".png"))

    size_kb = sum(os.path.getsize(os.path.join(dp, f)) for dp, _d, fs in os.walk(root) for f in fs
                  if not os.path.islink(os.path.join(dp, f))) // 1024

    os.makedirs(os.path.join(root, "DEBIAN"))
    maintainer = os.environ.get("DEB_MAINTAINER", "SigurPerco contributors <noreply@example.com>")
    with open(os.path.join(ROOT, "packaging", "linux", "control"), encoding="utf-8") as f:
        control = (f.read().replace("@VERSION@", _deb_version(version)).replace("@SIZE@", str(size_kb))
                   .replace("@MAINTAINER@", maintainer).replace("@PACKAGE@", PKG))
    with open(os.path.join(root, "DEBIAN", "control"), "w", encoding="utf-8") as f:
        f.write(control)
    for script in ("postinst", "postrm"):
        src = os.path.join(ROOT, "packaging", "linux", script)
        if os.path.exists(src):
            dst = os.path.join(root, "DEBIAN", script)
            shutil.copy2(src, dst)
            os.chmod(dst, 0o755)

    for dp, dirs, files in os.walk(root):          # права, которые ждёт dpkg
        for d in dirs:
            p = os.path.join(dp, d)
            if not os.path.islink(p):
                os.chmod(p, 0o755)
        for fn in files:
            p = os.path.join(dp, fn)
            if os.path.islink(p) or fn in ("postinst", "postrm"):
                continue
            os.chmod(p, 0o755 if os.access(p, os.X_OK) else 0o644)

    deb = "%s_%s_amd64%s.deb" % (PKG, _deb_version(version), tag)
    run(["dpkg-deb", "--build", "--root-owner-group", root, os.path.join(RELEASE, deb)])
    out.append(deb)
    return out


def package_macos(version, suffix):
    app = os.path.join(DIST, APP + ".app")

    # Info.plist: версия, название, умение открывать .xls/.xlsx из Finder
    plist_path = os.path.join(app, "Contents", "Info.plist")
    with open(plist_path, "rb") as f:
        info = plistlib.load(f)
    info.update({
        "CFBundleDisplayName": "Sigur → PERCo",
        "CFBundleShortVersionString": version,
        "CFBundleVersion": version,
        "NSHighResolutionCapable": True,
        "LSMinimumSystemVersion": "11.0",
        "CFBundleDocumentTypes": [{
            "CFBundleTypeName": "Excel",
            "CFBundleTypeRole": "Viewer",
            "LSHandlerRank": "Alternate",
            "LSItemContentTypes": ["com.microsoft.excel.xls", "org.openxmlformats.spreadsheetml.sheet"],
        }],
    })
    with open(plist_path, "wb") as f:
        plistlib.dump(info, f)
    # после правки Info.plist подпись нужно обновить (ad-hoc, без сертификата разработчика)
    try:
        run(["codesign", "--force", "--deep", "--sign", "-", app])
    except Exception as e:
        print("! codesign не удался: %s" % e)

    arch = "arm64" if platform.machine() == "arm64" else "intel"
    name = "%s-%s-macos-%s%s.dmg" % (APP, version, arch, "-" + suffix if suffix else "")
    stage = os.path.join(BUILD, "dmg")
    shutil.rmtree(stage, ignore_errors=True)
    os.makedirs(stage)
    shutil.copytree(app, os.path.join(stage, APP + ".app"), symlinks=True)
    os.symlink("/Applications", os.path.join(stage, "Applications"))
    cmd = ["hdiutil", "create", "-volname", "Sigur PERCo", "-srcfolder", stage, "-ov", "-format", "UDZO",
           os.path.join(RELEASE, name)]
    for attempt in range(1, 4):            # на CI hdiutil иногда отвечает «Resource busy»
        try:
            run(cmd)
            break
        except subprocess.CalledProcessError:
            if attempt == 3:
                raise
            print("! hdiutil не удался, повтор через 10 с")
            time.sleep(10)
    return [name]


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description="Сборка SigurPerco под текущую систему")
    ap.add_argument("--version", help="версия (по умолчанию из sigur_perco/__init__.py)")
    ap.add_argument("--suffix", default="", help="метка в имени файла, например win7")
    args = ap.parse_args()

    version = (args.version or read_version()).lstrip("v")
    if args.version:
        write_version(version)
    log("Версия %s, Python %s, %s %s" % (version, platform.python_version(), platform.system(), platform.machine()))

    for d in (DIST, RELEASE):
        shutil.rmtree(d, ignore_errors=True)
    os.makedirs(RELEASE)

    pyinstaller(version)

    log("Упаковка")
    if IS_WIN:
        files = package_windows(version, args.suffix)
    elif IS_MAC:
        files = package_macos(version, args.suffix)
    else:
        files = package_linux(version, args.suffix)

    log("Готово:")
    for f in files:
        p = os.path.join(RELEASE, f)
        print("  release/%s  (%.1f МБ)" % (f, os.path.getsize(p) / 1048576))


if __name__ == "__main__":
    main()
