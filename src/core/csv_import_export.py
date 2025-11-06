"""CSV import/export helpers for tasks and KanBan data."""

from __future__ import annotations

import csv
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from loguru import logger

# Export/import specification -------------------------------------------------


@dataclass(frozen=True)
class TableSpec:
	"""Describe how a SQLite table should be exported/imported."""

	name: str
	filename: str
	filter_by_user: bool = True
	require_sequence_sync: bool = True
	# Custom SQL overrides default SELECT/DELETE statements when required.
	select_sql: Optional[str] = None
	delete_sql: Optional[str] = None
	order_by: Optional[str] = None


TABLE_SPECS: Sequence[TableSpec] = (
	TableSpec(
		name="tasks",
		filename="tasks.csv",
		order_by="id",
	),
	TableSpec(
		name="task_tags",
		filename="task_tags.csv",
		order_by="id",
	),
	TableSpec(
		name="task_custom_lists",
		filename="task_custom_lists.csv",
		order_by="id",
	),
	TableSpec(
		name="kanban_items",
		filename="kanban_items.csv",
		order_by="id",
	),
	TableSpec(
		name="kanban_settings",
		filename="kanban_settings.csv",
		require_sequence_sync=False,
	),
	TableSpec(
		name="task_tag_assignments",
		filename="task_tag_assignments.csv",
		filter_by_user=False,
		order_by="id",
		select_sql=(
			"SELECT tta.* FROM task_tag_assignments tta "
			"JOIN tasks t ON t.id = tta.task_id "
			"WHERE t.user_id = ? ORDER BY tta.id"
		),
		delete_sql=(
			"DELETE FROM task_tag_assignments WHERE task_id IN "
			"(SELECT id FROM tasks WHERE user_id = ?)"
		),
	),
)

# Utility helpers -------------------------------------------------------------


def _normalise_value(value: object) -> object:
	"""Convert SQLite values to CSV-friendly values."""

	if value is None:
		return ""
	if isinstance(value, (dict, list)):
		return json.dumps(value, ensure_ascii=False)
	if isinstance(value, (datetime,)):
		return value.isoformat()
	return value


def _parse_value(col_type: str, raw: str) -> object:
	"""Cast string values read from CSV back to SQLite friendly types."""

	if raw == "":
		return None
	col_type = (col_type or "").upper()
	if col_type in {"INTEGER", "INT"}:
		try:
			return int(raw)
		except ValueError:
			return raw
	if col_type in {"REAL", "FLOAT", "DOUBLE"}:
		try:
			return float(raw)
		except ValueError:
			return raw
	if col_type in {"BOOLEAN", "BOOL"}:
		return raw in {"1", "true", "True", "TRUE"}
	# Keep JSON payloads untouched, let SQLite store as TEXT.
	return raw


def _get_table_columns(cursor: sqlite3.Cursor, table_name: str) -> List[Tuple[str, str]]:
	cursor.execute(f"PRAGMA table_info({table_name})")
	return [(row[1], row[2]) for row in cursor.fetchall()]


def _select_rows(
	cursor: sqlite3.Cursor,
	spec: TableSpec,
	user_id: Optional[int],
) -> Tuple[List[str], List[sqlite3.Row]]:
	if spec.select_sql:
		cursor.execute(spec.select_sql, (user_id,))
		rows = cursor.fetchall()
		field_names = [desc[0] for desc in cursor.description]
		return field_names, rows

	columns = _get_table_columns(cursor, spec.name)
	field_names = [name for name, _ in columns]

	sql = f"SELECT {', '.join(field_names)} FROM {spec.name}"
	params: Tuple[object, ...] = ()
	if spec.filter_by_user and user_id is not None and "user_id" in field_names:
		sql += " WHERE user_id = ?"
		params = (user_id,)
	if spec.order_by:
		sql += f" ORDER BY {spec.order_by}"

	cursor.execute(sql, params)
	rows = cursor.fetchall()
	return field_names, rows


def _delete_existing(cursor: sqlite3.Cursor, spec: TableSpec, user_id: Optional[int]) -> None:
	if spec.delete_sql and user_id is not None:
		cursor.execute(spec.delete_sql, (user_id,))
		return

	if not spec.filter_by_user or user_id is None:
		# Fall back to full wipe of table when user scoping is undefined.
		cursor.execute(f"DELETE FROM {spec.name}")
		return

	cursor.execute(f"DELETE FROM {spec.name} WHERE user_id = ?", (user_id,))


def _sync_autoincrement(cursor: sqlite3.Cursor, table_name: str) -> None:
	cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sqlite_sequence'")
	if not cursor.fetchone():
		return

	cursor.execute(f"SELECT MAX(id) FROM {table_name}")
	max_id = cursor.fetchone()[0]
	if max_id is None:
		max_id = 0
	cursor.execute(
		"UPDATE sqlite_sequence SET seq = ? WHERE name = ?",
		(max_id, table_name),
	)


# Public API -----------------------------------------------------------------


def export_tasks_and_kanban_to_csv(local_db, target_directory: str) -> Dict[str, int]:
	"""Export task and KanBan tables to CSV files stored in *target_directory*."""

	if local_db is None:
		raise ValueError("Local database handle is required for CSV export")

	target_path = Path(target_directory).expanduser().resolve()
	target_path.mkdir(parents=True, exist_ok=True)

	exported_rows: Dict[str, int] = {}

	with sqlite3.connect(local_db.db_path) as conn:
		conn.row_factory = sqlite3.Row
		cursor = conn.cursor()

		for spec in TABLE_SPECS:
			field_names, rows = _select_rows(cursor, spec, getattr(local_db, "user_id", None))
			file_path = target_path / spec.filename

			with file_path.open("w", newline="", encoding="utf-8") as handle:
				writer = csv.DictWriter(handle, fieldnames=field_names)
				writer.writeheader()
				for row in rows:
					payload = {name: _normalise_value(row[name]) for name in field_names}
					writer.writerow(payload)

			exported_rows[spec.name] = len(rows)
			logger.info(
				f"[CSV Export] Exported {exported_rows[spec.name]} rows from {spec.name} into {file_path}"
			)

	return exported_rows


def import_tasks_and_kanban_from_csv(local_db, source_directory: str) -> Dict[str, int]:
	"""Import task and KanBan tables from CSV files located in *source_directory*."""

	if local_db is None:
		raise ValueError("Local database handle is required for CSV import")

	source_path = Path(source_directory).expanduser().resolve()
	if not source_path.exists():
		raise FileNotFoundError(f"Import directory does not exist: {source_path}")

	imported_rows: Dict[str, int] = {}

	with sqlite3.connect(local_db.db_path) as conn:
		conn.row_factory = sqlite3.Row
		cursor = conn.cursor()
		cursor.execute("PRAGMA foreign_keys = OFF")

		try:
			for spec in TABLE_SPECS:
				file_path = source_path / spec.filename
				if not file_path.exists():
					logger.warning(
						f"[CSV Import] File {file_path} missing, skipping table {spec.name}"
					)
					continue

				with file_path.open("r", newline="", encoding="utf-8") as handle:
					reader = csv.DictReader(handle)
					field_names = reader.fieldnames or []
					rows = list(reader)

				if not field_names:
					logger.warning(
						f"[CSV Import] File {file_path} does not contain a header row; skipping {spec.name}"
					)
					continue

				_delete_existing(cursor, spec, getattr(local_db, "user_id", None))

				if not rows:
					imported_rows[spec.name] = 0
					continue

				column_types = dict(_get_table_columns(cursor, spec.name))
				placeholders = ", ".join([":" + name for name in field_names])
				insert_sql = (
					f"INSERT OR REPLACE INTO {spec.name} "
					f"({', '.join(field_names)}) VALUES ({placeholders})"
				)

				bound_rows = []
				for raw in rows:
					payload = {
						name: _parse_value(column_types.get(name, ""), raw.get(name, ""))
						for name in field_names
					}
					bound_rows.append(payload)

				cursor.executemany(insert_sql, bound_rows)
				imported_rows[spec.name] = len(bound_rows)

				if spec.require_sequence_sync:
					_sync_autoincrement(cursor, spec.name)

				logger.info(
					f"[CSV Import] Imported {imported_rows[spec.name]} rows into {spec.name} from {file_path}"
				)

			conn.commit()
			logger.info(f"[CSV Import] Successfully committed all changes")
		except Exception as e:
			conn.rollback()
			logger.error(f"[CSV Import] Error during import, rolling back all changes: {e}")
			raise
		finally:
			cursor.execute("PRAGMA foreign_keys = ON")

	return imported_rows

