"""Validate the team's CSV interfaces without third-party dependencies."""

from __future__ import annotations

import argparse
import csv
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path


FIELDS = {
    "clean": ["timestamp_utc", "load_kw", "pv_kw", "wind_kw"],
    "forecast": [
        "issue_time_utc", "target_time_utc", "horizon_h",
        "q10_kw", "q50_kw", "q90_kw",
    ],
    "dispatch": [
        "timestamp_utc", "strategy", "load_kw", "pv_kw", "wind_kw",
        "grid_import_kw", "battery_charge_kw", "battery_discharge_kw",
        "electrolyzer_kw", "fuel_cell_kw", "curtailment_kw", "unserved_kw",
        "soc_kwh", "h2_kg", "step_cost", "solver_status",
    ],
}
STRATEGIES = {"rule", "persistence_milp", "q50_milp", "quantile_reserve_milp"}


def utc(value: str, field: str, line: int) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"第 {line} 行 {field} 不是 ISO 8601 时间") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise ValueError(f"第 {line} 行 {field} 必须使用 UTC")
    if parsed.minute or parsed.second or parsed.microsecond:
        raise ValueError(f"第 {line} 行 {field} 必须是整点")
    return parsed.astimezone(timezone.utc)


def number(row: dict[str, str], field: str, line: int, nonnegative: bool = False) -> float:
    try:
        value = float(row[field])
    except (ValueError, TypeError) as exc:
        raise ValueError(f"第 {line} 行 {field} 缺失或不是数值") from exc
    if not math.isfinite(value) or (nonnegative and value < 0):
        raise ValueError(f"第 {line} 行 {field} 必须是有限的{'非负' if nonnegative else ''}数值")
    return value


def validate(kind: str, path: Path) -> int:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != FIELDS[kind]:
            raise ValueError(f"列名或顺序不匹配。应为: {','.join(FIELDS[kind])}")
        seen: set[object] = set()
        previous: datetime | None = None
        count = 0
        for line, row in enumerate(reader, start=2):
            count += 1
            if None in row or any(value is None or value == "" for value in row.values()):
                raise ValueError(f"第 {line} 行有空值或多余列")
            if kind == "clean":
                stamp = utc(row["timestamp_utc"], "timestamp_utc", line)
                if stamp in seen or (previous is not None and stamp - previous != timedelta(hours=1)):
                    raise ValueError(f"第 {line} 行时间重复、乱序或不连续")
                seen.add(stamp)
                previous = stamp
                for field in FIELDS[kind][1:]:
                    number(row, field, line, nonnegative=True)
            elif kind == "forecast":
                issue = utc(row["issue_time_utc"], "issue_time_utc", line)
                target = utc(row["target_time_utc"], "target_time_utc", line)
                try:
                    horizon = int(row["horizon_h"])
                except ValueError as exc:
                    raise ValueError(f"第 {line} 行 horizon_h 不是整数") from exc
                if horizon not in range(1, 25) or target - issue != timedelta(hours=horizon):
                    raise ValueError(f"第 {line} 行预测步长与目标时间不一致")
                key = (issue, horizon)
                if key in seen:
                    raise ValueError(f"第 {line} 行预测键重复")
                seen.add(key)
                q10, q50, q90 = (number(row, f, line) for f in ("q10_kw", "q50_kw", "q90_kw"))
                if not q10 <= q50 <= q90:
                    raise ValueError(f"第 {line} 行分位数交叉")
            else:
                stamp = utc(row["timestamp_utc"], "timestamp_utc", line)
                strategy = row["strategy"]
                if strategy not in STRATEGIES:
                    raise ValueError(f"第 {line} 行 strategy 不在约定集合中")
                key = (stamp, strategy)
                if key in seen:
                    raise ValueError(f"第 {line} 行调度键重复")
                seen.add(key)
                if row["solver_status"] == "":
                    raise ValueError(f"第 {line} 行 solver_status 为空")
                values = {f: number(row, f, line, nonnegative=f != "step_cost") for f in FIELDS[kind][2:-1]}
                left = sum(values[f] for f in (
                    "pv_kw", "wind_kw", "grid_import_kw", "battery_discharge_kw", "fuel_cell_kw", "unserved_kw"))
                right = sum(values[f] for f in (
                    "load_kw", "battery_charge_kw", "electrolyzer_kw", "curtailment_kw"))
                if abs(left - right) > 1e-5:
                    raise ValueError(f"第 {line} 行功率不平衡，误差 {left - right:g} kW")
        if count == 0:
            raise ValueError("文件没有数据行")
        return count


def main() -> None:
    parser = argparse.ArgumentParser(description="校验 AIC AI 能源项目 CSV 接口")
    parser.add_argument("kind", choices=FIELDS)
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    try:
        rows = validate(args.kind, args.path)
    except (ValueError, OSError) as exc:
        parser.exit(1, f"校验失败：{exc}\n")
    print(f"校验通过：{args.kind}，{rows} 行")


if __name__ == "__main__":
    main()
