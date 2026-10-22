"""Тесты ядра FileFlow (stdlib unittest, без зависимостей)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fileflow.core import (
    build_rename_plan,
    find_duplicates,
    find_files,
    folder_report,
)


class FileFlowTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

        # Раскладываем тестовые файлы
        (self.root / "a.py").write_text("print('a')")
        (self.root / "b.py").write_text("print('bb')")
        (self.root / "notes.txt").write_text("hello")
        (self.root / "sub").mkdir()
        (self.root / "sub" / "c.py").write_text("print('a')")  # дубликат a.py
        (self.root / ".hidden.py").write_text("secret")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    # ---------- find ----------

    def test_find_glob(self) -> None:
        files = find_files(self.root, "*.py")
        names = {f.name for f in files}
        self.assertEqual(names, {"a.py", "b.py", "c.py"})  # скрытые игнорируются

    def test_find_regex(self) -> None:
        files = find_files(self.root, r"^a\.py$", use_regex=True)
        self.assertEqual([f.name for f in files], ["a.py"])

    def test_find_max_depth(self) -> None:
        files = find_files(self.root, "*.py", max_depth=0)
        names = {f.name for f in files}
        self.assertEqual(names, {"a.py", "b.py"})  # sub/c.py слишком глубоко

    def test_find_missing_dir(self) -> None:
        with self.assertRaises(NotADirectoryError):
            find_files(self.root / "nope", "*")

    # ---------- rename ----------

    def test_rename_plan_placeholders(self) -> None:
        files = find_files(self.root, "*.py")
        plan = build_rename_plan(files, "code_{n}.{ext}")
        new_names = [dst.name for _, dst in plan.pairs]
        self.assertIn("code_001.py", new_names)
        self.assertIn("code_002.py", new_names)

    def test_rename_dry_run_changes_nothing(self) -> None:
        before = sorted(p.name for p in self.root.iterdir())
        build_rename_plan(find_files(self.root, "*.py"), "x_{n}.{ext}").apply(dry_run=True)
        after = sorted(p.name for p in self.root.iterdir())
        self.assertEqual(before, after)

    def test_rename_real(self) -> None:
        (self.root / "sub" / "photo1.jpg").write_bytes(b"\xff")
        plan = build_rename_plan(find_files(self.root, "photo*.jpg"), "shot_{n}.{ext}")
        count = plan.apply()
        self.assertEqual(count, 1)
        self.assertTrue((self.root / "sub" / "shot_001.jpg").exists())

    # ---------- dupes ----------

    def test_duplicates_found(self) -> None:
        dupes = find_duplicates(self.root)
        sizes = {len(entries) for entries in dupes.values()}
        self.assertIn(2, sizes)  # a.py и sub/c.py одинаковые

    def test_duplicates_min_size(self) -> None:
        dupes = find_duplicates(self.root, min_size=10_000)
        self.assertEqual(dupes, {})

    # ---------- report ----------

    def test_report_counts(self) -> None:
        report = folder_report(self.root)
        self.assertEqual(report["__total__"]["count"], 4)
        self.assertEqual(report[".py"]["count"], 3)
        self.assertEqual(report[".txt"]["count"], 1)


if __name__ == "__main__":
    unittest.main()
