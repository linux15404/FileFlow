"""FileFlow — быстрый файловый хелпер для терминанала.

Команды:
  find      — быстрый поиск файлов по маске (glob/regex)
  rename    — групповое переименование по шаблону
  dupes     — поиск дубликатов по хешу содержимого
  report    — отчёт о содержимом папки (расширения, размеры)

Автор: Artyom (linux15404)
"""

from .core import (
    find_files,
    rename_files,
    find_duplicates,
    folder_report,
)

__version__ = "1.0.0"
__all__ = ["find_files", "rename_files", "find_duplicates", "folder_report"]
