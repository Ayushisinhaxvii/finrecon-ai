
from pathlib import Path
import shutil

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TARGET_DB = PROJECT_ROOT / "dev.duckdb"

if not TARGET_DB.exists():
    raise FileNotFoundError(
        f"Target database does not exist: {TARGET_DB}"
    )

changes = {
    PROJECT_ROOT / "app.py": (
        'ROOT / "dbt" / "finrecon" / "dev.duckdb"',
        'ROOT / "dev.duckdb"',
    ),
    PROJECT_ROOT / "rag" / "approval_workflow.py": (
        'PROJECT_ROOT / "dbt" / "finrecon" / "dev.duckdb"',
        'PROJECT_ROOT / "dev.duckdb"',
    ),
    PROJECT_ROOT / "rag" / "sql_rag_router.py": (
        'PROJECT_ROOT / "dbt" / "finrecon" / "dev.duckdb"',
        'PROJECT_ROOT / "dev.duckdb"',
    ),
}

for file_path, (old_text, new_text) in changes.items():
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    original = file_path.read_text(encoding="utf-8")

    occurrences = original.count(old_text)

    if occurrences != 1:
        raise RuntimeError(
            f"Expected exactly one old path in {file_path}, "
            f"but found {occurrences}. No changes made to this file."
        )

    backup_path = file_path.with_suffix(
        file_path.suffix + ".bak"
    )

    if backup_path.exists():
        raise FileExistsError(
            f"Backup already exists: {backup_path}\n"
            "Keep the existing backup safe. Rename it manually "
            "before running this script again."
        )

    shutil.copy2(file_path, backup_path)

    updated = original.replace(old_text, new_text, 1)
    file_path.write_text(updated, encoding="utf-8")

    print(f"UPDATED: {file_path}")
    print(f"BACKUP:  {backup_path}")

print("\nAll three database paths were updated.")
print(f"Shared development database: {TARGET_DB}")
