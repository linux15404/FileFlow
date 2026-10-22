"""Консольный интерфейс FileFlow: цветной вывод и argparse."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .core import (
    build_rename_plan,
    find_duplicates,
    find_files,
    folder_report,
)


class Style:
    """Мини-обёртка над ANSI-цветами (автоотключение при piped-выводе)."""

    enabled = sys.stdout.isatty()

    @classmethod
    def _wrap(cls, code: str, text: str) -> str:
        return f"\033[{code}m{text}\033[0m" if cls.enabled else text

    @classmethod
    def dim(cls, text: str) -> str:
        return cls._wrap("2", text)

    @classmethod
    def bold(cls, text: str) -> str:
        return cls._wrap("1", text)

    @classmethod
    def green(cls, text: str) -> str:
        return cls._wrap("32", text)

    @classmethod
    def yellow(cls, text: str) -> str:
        return cls._wrap("33", text)

    @classmethod
    def cyan(cls, text: str) -> str:
        return cls._wrap("36", text)

    @classmethod
    def red(cls, text: str) -> str:
        return cls._wrap("31", text)


def human_size(size: float) -> str:
    """1536 → '1.5 KB'."""
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024
    return f"{size:.1f} GB"


def cmd_find(args: argparse.Namespace) -> int:
    files = find_files(args.path, args.pattern, use_regex=args.regex, max_depth=args.depth)

    if not files:
        print(Style.dim("Ничего не найдено."))
        return 0

    for entry in files:
        print(f"{Style.green('•')} {entry.path}  {Style.dim(f'({human_size(entry.size)})')}")

    print(Style.bold(f"\n{len(files)} файл(ов), всего {human_size(sum(f.size for f in files))}"))
    return 0


def cmd_rename(args: argparse.Namespace) -> int:
    files = find_files(args.path, args.pattern)
    plan = build_rename_plan(files, args.template)

    if not plan.pairs:
        print(Style.dim("Нет файлов для переименования."))
        return 0

    for src, dst in plan.pairs:
        print(f"{Style.yellow('→')} {src.name}  {Style.dim('⇒')}  {Style.cyan(dst.name)}")

    if args.dry_run:
        count = len(plan.pairs)
        print(Style.bold(f"\n[Dry-run] Будет переименовано: {count}. Файлы не изменены."))
    else:
        count = plan.apply()
        print(Style.bold(f"\n{Style.green('✓')} Переименовано: {count}"))

    return 0


def cmd_dupes(args: argparse.Namespace) -> int:
    dupes = find_duplicates(args.path, min_size=args.min_size)

    if not dupes:
        print(Style.green("Дубликатов не найдено."))
        return 0

    wasted = 0
    for digest, entries in dupes.items():
        print(Style.red(f"\n✖ Группа {digest[:12]}…  ({human_size(entries[0].size)} каждый)"))
        for entry in entries:
            print(f"    {entry.path}")
        wasted += entries[0].size * (len(entries) - 1)

    total = sum(len(e) for e in dupes.values())
    print(
        Style.bold(
            f"\n{len(dupes)} групп(ы), {total} файл(ов). "
            f"Можно освободить: {Style.yellow(human_size(wasted))}"
        )
    )
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    report = folder_report(args.path)

    if not report:
        print(Style.dim("Папка пуста."))
        return 0

    total = report.pop("__total__", {"count": 0, "size": 0})
    width = max((len(ext) for ext in report), default=0)

    print(Style.bold(f"Отчёт по {Path(args.path).expanduser().resolve()}\n"))
    for ext, stats in report.items():
        bar = "█" * max(1, int(stats["size"] / max(total['size'], 1) * 30))
        print(
            f"  {ext.ljust(width)}  "
            f"{str(stats['count']).rjust(5)} файл(ов)  "
            f"{human_size(stats['size']).rjust(9)}  "
            f"{Style.dim(bar)}"
        )

    print(
        Style.bold(
            f"\n  Итого: {total['count']} файл(ов), {human_size(total['size'])}"
        )
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fileflow",
        description="🗂️ FileFlow — быстрый файловый хелпер: поиск, переименование, дубликаты, отчёты.",
    )
    parser.add_argument("--version", action="version", version=f"fileflow {__version__}")

    sub = parser.add_subparsers(dest="command", required=True)

    p_find = sub.add_parser("find", help="Поиск файлов по маске")
    p_find.add_argument("pattern", help="Glob-маска, например '*.py' (или --regex)")
    p_find.add_argument("path", nargs="?", default=".", help="Каталог (по умолчанию: текущий)")
    p_find.add_argument("--regex", action="store_true", help="Искать как регулярное выражение")
    p_find.add_argument("--depth", type=int, default=None, help="Макс. глубина вложенности")
    p_find.set_defaults(func=cmd_find)

    p_rename = sub.add_parser("rename", help="Групповое переименование по шаблону")
    p_rename.add_argument("pattern", help="Какие файлы переименовывать (маска)")
    p_rename.add_argument("template", help="Шаблон: {name} {ext} {n} {date}")
    p_rename.add_argument("path", nargs="?", default=".", help="Каталог")
    p_rename.add_argument("--dry-run", action="store_true", help="Показать план без изменений")
    p_rename.set_defaults(func=cmd_rename)

    p_dupes = sub.add_parser("dupes", help="Поиск дубликатов по хешу")
    p_dupes.add_argument("path", nargs="?", default=".", help="Каталог")
    p_dupes.add_argument("--min-size", type=int, default=1, help="Мин. размер файла в байтах")
    p_dupes.set_defaults(func=cmd_dupes)

    p_report = sub.add_parser("report", help="Отчёт по расширениям и размерам")
    p_report.add_argument("path", nargs="?", default=".", help="Каталог")
    p_report.set_defaults(func=cmd_report)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        return args.func(args)
    except NotADirectoryError as exc:
        print(Style.red(f"Ошибка: {exc}"), file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print(Style.dim("\nОтменено."))
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
