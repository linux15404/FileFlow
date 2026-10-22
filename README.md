<div align="center">

# 🗂️ FileFlow

**Набор команд для работы с файлами в терминале**

Поиск, переименование пачками, дубликаты, отчёты. Чистый Python, без сторонних библиотек.

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

</div>

---

## Что умеет

- 🔍 **find** — искать файлы по маске (`*.py`) или по regex
- ✏️ **rename** — переименовать много файлов сразу по шаблону, с предпросмотром
- 🔁 **dupes** — найти одинаковые файлы по содержимому
- 📊 **report** — показать, какие файлы лежат в папке и сколько места занимают

## Установка

Нужен Python 3.10+.

```bash
git clone https://github.com/thesl33py/FileFlow.git
cd FileFlow
pip install .
```

Или без установки:

```bash
python3 -m fileflow find "*.py"
```

## Примеры

```bash
# найти логи
fileflow find "*.log" /var/log

# посмотреть, как переименуются файлы (ничего не меняет)
fileflow rename "IMG_*.jpg" "отпуск_{n}.{ext}" ~/Фото --dry-run

# а если всё нравится — применить
fileflow rename "IMG_*.jpg" "отпуск_{n}.{ext}" ~/Фото

# найти одинаковые файлы
fileflow dupes ~/Загрузки

# что лежит в папке
fileflow report ~/Проекты
```

В шаблоне переименования доступны:

| Плейсхолдер | Что подставится | Пример |
|---|---|---|
| `{name}` | имя файла без расширения | `отчёт` |
| `{ext}` | расширение | `txt` |
| `{n}` | порядковый номер | `001` |
| `{date}` | дата изменения | `2026-10-22` |

## Тесты

```bash
python3 -m unittest discover -s tests -v
```

## Лицензия

MIT — см. [LICENSE](LICENSE)

<img width="632" height="537" alt="Screenshot From 2026-10-22 22-09-09" src="https://github.com/user-attachments/assets/4c4b595e-6fe4-4cb0-a41c-4aed59651530" />
