# 数据与文件接口（v0.1）

负责人：成员 C。A/B 在提交首份数据前共同确认。此文档规定文件格式，不预先断言真实数据已经可用。

## 全局规则

- 文件编码 UTF-8，逗号分隔，首行为字段名；小数点用 `.`，缺失值留空并在清洗日志记录，不填 `0` 伪装缺失。
- 时间一律使用 UTC 的 ISO 8601 格式，如 `2025-01-01T00:00:00Z`。处理后的时步为 1 小时。原始 15/30 分钟功率值汇总为小时**平均功率**，不是直接求和。
- 处理后微电网功率单位为 `kW`，能量为 `kWh`，氢量为 `kg`。ENTSO-E 原始功率为 `MW`；从区域曲线到微电网曲线的缩放方式与系数必须写入配置，保留未缩放原始数据。
- 三类真实数据须使用一致的地区口径和时段。记录 `AreaCode`、`AreaTypeCode`、下载日期、源文件名、缺失比例及缩放方法。当前不预设法国就是最终地区。
- 不覆盖原始下载文件。训练/验证/测试按时间顺序划分，测试期与随机种子写入配置；测试期真实未来值不得进入预测特征或优化输入。

## A 输出：`data/processed/clean_hourly.csv`

| 字段 | 类型与单位 | 定义 |
| --- | --- | --- |
| `timestamp_utc` | ISO 8601 UTC | 小时起点，唯一且连续 |
| `load_kw` | 数值，kW | 该小时平均负荷，非负 |
| `pv_kw` | 数值，kW | 该小时平均可用光伏功率，非负 |
| `wind_kw` | 数值，kW | 陆上/海上风电的约定合计，非负 |

净负荷在代码中按 `load_kw - pv_kw - wind_kw` 计算，可为负数。清洗日志另记缺测、插补、异常与原始来源，不应仅在这个文件中默默修改。

## A 输出：`data/processed/forecast_quantiles.csv`

预测目标是未来小时的**净负荷**，不是分别对负荷、光伏和风电做独立分位数再相减。

| 字段 | 类型与单位 | 定义 |
| --- | --- | --- |
| `issue_time_utc` | ISO 8601 UTC | 发出预测时刻，只能使用此前可获得的信息 |
| `target_time_utc` | ISO 8601 UTC | 被预测小时的起点 |
| `horizon_h` | 整数 1—24 | `target_time_utc - issue_time_utc` 的小时数 |
| `q10_kw` | 数值，kW | 净负荷 10% 分位数 |
| `q50_kw` | 数值，kW | 净负荷中位数预测 |
| `q90_kw` | 数值，kW | 净负荷 90% 分位数 |

每个 `(issue_time_utc, horizon_h)` 只出现一次，并满足 `q10_kw ≤ q50_kw ≤ q90_kw`。持续性预测使用相同的前三列和 `prediction_kw`，单独保存为 `persistence_forecast.csv`。

## B 输出：`results/dispatch_<strategy>.csv`

每种策略各一个文件，`strategy` 取 `rule`、`persistence_milp`、`q50_milp`、`quantile_reserve_milp`。一行代表执行的一个小时；未来 24 小时优化计划可另存，不混入执行结果。

| 字段 | 类型与单位 | 定义 |
| --- | --- | --- |
| `timestamp_utc` | ISO 8601 UTC | 实际执行小时起点 |
| `strategy` | 字符串 | 上述四个固定名称之一 |
| `load_kw`, `pv_kw`, `wind_kw` | 数值，kW | 本小时真实观察值，供 C 独立复算 |
| `grid_import_kw` | 非负数，kW | 从外部电网购入功率 |
| `battery_charge_kw`, `battery_discharge_kw` | 非负数，kW | 电池充、放电功率 |
| `electrolyzer_kw`, `fuel_cell_kw` | 非负数，kW | 电解槽耗电、燃料电池发电功率 |
| `curtailment_kw`, `unserved_kw` | 非负数，kW | 弃风弃光、未满足负荷 |
| `soc_kwh`, `h2_kg` | 非负数 | 该小时执行后的状态 |
| `step_cost` | 数值 | 该小时按统一成本口径计算的成本 |
| `solver_status` | 字符串 | `rule`、`optimal`、`fallback` 或具体失败原因 |

本版本默认只允许购电、不考虑向电网售电；若模型需要售电，必须先修订接口与四策略实验规则。B 输出的每小时功率平衡应满足：

`pv + wind + grid_import + battery_discharge + fuel_cell + unserved = load + battery_charge + electrolyzer + curtailment`

允许数值误差不超过 `1e-5 kW`。C 会从输出列独立复算，不以 B 自报的“通过”字段代替检查。

## 变更流程

修改列名、单位、时间定义、策略或目标函数时，先说明原因、影响的文件及迁移方式；A/B/C 确认后更新本文件与样例，再合并代码。临时缺列不能用全零列冒充。
