"""Ядро FileFlow: поиск, переименование, дубликаты, отчёты."""

from __future__ import annotations

import fnmatch
import hashlib
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class FileEntry:
    """Информация о найденном файле."""

    path: Path
    size: int
    mtime: float

    @property
    def name(self) -> str:
        return self.path.name


@dataclass
class RenamePlan:
    """План группового переименования (пары «было → станет»)."""

    pairs: list[tuple[Path, Path]] = field(default_factory=list)

    def apply(self, dry_run: bool = False) -> int:
        """Применяет план. При dry_run только считает."""
        count = 0
        for src, dst in self.pairs:
            if not dry_run:
                # Если цель занята — пропускаем, чтобы ничего не затереть
                if dst.exists():
                    continue
                src.rename(dst)
            count += 1
        return count


def find_files(
    root: str | Path,
    pattern: str = "*",
    *,
    use_regex: bool = False,
    max_depth: int | None = None,
) -> list[FileEntry]:
    """Ищет файлы по маске (glob) или regex, с ограничением глубины.

    Args:
        root: корневая директория.
        pattern: glob-маска ('*.py') или regex при use_regex=True.
        use_regex: трактовать pattern как регулярное выражение.
        max_depth: максимальная глубина вложенности (None — бесконечно).

    Returns:
        Список FileEntry, отсортированный по пути.
    """
    root = Path(root).expanduser().resolve()
    if not root.is_dir():
        raise NotADirectoryError(f"Not a directory: {root}")

    regex = re.compile(pattern) if use_regex else None
    results: list[FileEntry] = []
    base_depth = len(root.parts)

    for dirpath, dirnames, filenames in os.walk(root):
        current = Path(dirpath)

        # Не ныряем в скрытые/служебные папки и не превышаем глубину
        dirnames[:] = [
            d
            for d in dirnames
            if not d.startswith(".")
            and d not in {"node_modules", "__pycache__", ".git"}
            and (max_depth is None or len(current.parts) - base_depth < max_depth)
        ]

        for filename in filenames:
            if filename.startswith("."):
                continue

            if regex is not None:
                if not regex.search(filename):
                    continue
            elif not fnmatch.fnmatch(filename, pattern):
                continue

            path = current / filename
            try:
                stat = path.stat()
            except OSError:
                continue

            results.append(FileEntry(path=path, size=stat.st_size, mtime=stat.st_mtime))

    return sorted(results, key=lambda e: str(e.path))


def build_rename_plan(
    files: list[FileEntry],
    template: str,
    *,
    counter_start: int = 1,
    digits: int = 3,
) -> RenamePlan:
    """Строит план переименования по шаблону.

    Поддерживаемые плейсхолдеры в template:
      {name}   — исходное имя без расширения
      {ext}    — расширение (без точки)
      {n}      — порядковый номер (с ведущими нулями через digits)
      {date}   — дата изменения (YYYY-MM-DD)

    Пример: template='photo_{n}.{ext}' → photo_001.jpg, photo_002.png ...
    """
    plan = RenamePlan()

    for index, entry in enumerate(files, start=counter_start):
        stem = entry.path.stem
        ext = entry.path.suffix.lstrip(".")
        date_str = time.strftime("%Y-%m-%d", time.localtime(entry.mtime))

        new_name = template.format(
            name=stem,
            ext=ext,
            n=str(index).zfill(digits),
            date=date_str,
        )

        # Безопасность: убираем path-сепараторы из нового имени
        new_name = new_name.replace("/", "_").replace("\\", "_")
        new_path = entry.path.parent / new_name

        if new_path != entry.path:
            plan.pairs.append((entry.path, new_path))

    return plan


def rename_files(
    root: str | Path,
    pattern: str,
    template: str,
    *,
    dry_run: bool = False,
) -> RenamePlan:
    """Групповое переименование: ищет по pattern и переименовывает по template."""
    files = find_files(root, pattern)
    plan = build_rename_plan(files, template)
    plan.apply(dry_run=dry_run)
    return plan


def find_duplicates(
    root: str | Path,
    *,
    chunk_size: int = 65536,
    min_size: int = 1,
) -> dict[str, list[FileEntry]]:
    """Находит дубликаты по SHA-256 хешу содержимого.

    Сначала группирует по размеру (дешёвый фильтр),
    затем считает хеш только для файлов с совпадающим размером.

    Returns:
        Словарь {хеш: [файлы]} только для групп с 2+ файлами.
    """
    root = Path(root).expanduser().resolve()

    # Группировка по размеру
    by_size: dict[int, list[FileEntry]] = {}
    for entry in find_files(root):
        if entry.size >= min_size:
            by_size.setdefault(entry.size, []).append(entry)

    # Хешируем только кандидатов
    by_hash: dict[str, list[FileEntry]] = {}
    for entries in by_size.values():
        if len(entries) < 2:
            continue
        for entry in entries:
            digest = _hash_file(entry.path, chunk_size)
            by_hash.setdefault(digest, []).append(entry)

    return {digest: entries for digest, entries in by_hash.items() if len(entries) > 1}


def _hash_file(path: Path, chunk_size: int) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as fh:
        while chunk := fh.read(chunk_size):
            sha.update(chunk)
    return sha.hexdigest()


def folder_report(root: str | Path) -> dict[str, dict[str, int | float]]:
    """Сводка по папке: сколько файлов каждого расширения и общий размер.

    Returns:
        {'.py': {'count': 12, 'size': 34567}, ...} + служебный ключ '__total__'.
    """
    report: dict[str, dict[str, int | float]] = {}
    total_count = 0
    total_size = 0

    for entry in find_files(root):
        ext = entry.path.suffix.lower() or "(без расширения)"
        bucket = report.setdefault(ext, {"count": 0, "size": 0})
        bucket["count"] += 1
        bucket["size"] += entry.size
        total_count += 1
        total_size += entry.size

    report["__total__"] = {"count": total_count, "size": total_size}
    return dict(sorted(report.items(), key=lambda kv: (-kv[1]["size"], kv[0])))
