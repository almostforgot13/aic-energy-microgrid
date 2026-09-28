# B 模块：15 分钟电池-氢储能固定规则基线

本目录是独立的 15 分钟版本。旧的 `../B_module/` 保留为一小时回归参考；本版不读取它的参数和结果。所有设备容量、效率、初始状态、最低开机功率、爬坡率及购电上限与旧候选方案相同，只有时步改为 `0.25 h`，没有根据失负荷结果调整容量。

## 参数与输入

代码唯一读取 `candidate_parameters_15min.json`（UTF-8 JSON）。`meta.time_step_h` 为 0.25。功率单位 kW、电池能量 kWh、储氢库存 kg、时间为 UTC 的每个 15 分钟区间**起点**。候选值的来源、推导和待确认状态见 `parameter_sources_15min.csv`。

输入为 A 的 `A_15min_virtual_2017_2019.csv`，直接取原始的 `time, split, load_kw, pv_kw, wind_kw`；若存在 `net_load_kw`，还会核对 `load-pv-wind`。程序读取时检查整份输入的非空、有限、非负功率、UTC 时戳、唯一性及严格连续的 15 分钟间隔。不会对四条记录求平均。

## 状态更新与功率平衡

每步 `dt=0.25 h`：

- `E_B,next = E_B + P_charge × η_charge × dt - P_discharge × dt / η_discharge`（kWh）。
- `H_next = H + P_electrolyzer × dt / 55 - P_fuel_cell × dt / 17.875`（kg）。
- `PV + wind + battery_discharge + fuel_cell + grid_import + unserved = load + battery_charge + electrolyzer + curtailment`（kW）。`unserved` 是未满足的客户负荷，不是实际供电。

每步电池有符号功率、制氢槽功率和燃料电池功率相对于上一步最多分别变化 `500×0.25=125 kW`、`300×0.25=75 kW`、`500×0.25=125 kW`。规则在负荷骤降、停机和充放电切换时保留无法立即撤销的出力，并协调 30 kW 制氢槽和 50 kW 燃料电池最低开机功率。设备接近电池/储氢上下限时，还预留之后按爬坡限制降到零所需的容量或库存；无可行状态会明确报错。

风光富余时依次充电、制氢、记录弃电；供电不足时依次放电、燃料电池发电、最多购电 500 kW、记录剩余失负荷。规则不使用预测，也没有优化求解器。`curtailment_kw` 代表电气侧无法吸收的剩余功率；若燃料电池受爬坡约束必须继续出力，这部分可能包含燃料电池功率，因此报告中不能不加核对就称为“弃风弃光”。

## C 的固定结果接口

CSV 列名与顺序固定为：

```text
timestamp_utc,strategy,load_kw,pv_kw,wind_kw,grid_import_kw,battery_charge_kw,battery_discharge_kw,electrolyzer_kw,fuel_cell_kw,curtailment_kw,unserved_kw,battery_energy_start_kwh,battery_energy_end_kwh,hydrogen_start_kg,hydrogen_end_kg,solver_status,step_cost
```

`strategy=fixed_rule_battery_hydrogen_grid_15min`。`solver_status` 为 `rule_ok`、`rule_curtailment` 或 `rule_unserved`。**成本口径尚未定义，`step_cost` 留空，汇总的 `total_cost` 为 null 并写明未实现**；不能把空白理解为成本为零。若 C 确认不同策略名称，可统一改名后重新生成所有结果与报告。

## 运行命令

在本目录下用 Python 3.10+ 执行，代码无需第三方 Python 包。将 `--input` 改为 A 的文件实际位置。

```powershell
python rule_dispatch.py `
  --input 'C:\Users\Huang\Desktop\A_15min_virtual_2017_2019.csv' `
  --params 'candidate_parameters_15min.json' `
  --week-start 2017-01-01 `
  --output 'week_2017-01-01_15min_results.csv' `
  --summary 'week_2017-01-01_metrics.json'

python validate_results.py `
  --results 'week_2017-01-01_15min_results.csv' `
  --params 'candidate_parameters_15min.json' `
  --summary 'week_2017-01-01_metrics.json' `
  --source 'C:\Users\Huang\Desktop\A_15min_virtual_2017_2019.csv' `
  --report 'verification_report.json'

python -m unittest -v test_rule_dispatch.py
```

校验器会重新计算每步功率平衡、电池和氢状态、上下限、最小开机功率、互斥、爬坡、状态连续性、输入时戳、汇总电量与成本空值，并运行边界单元测试。

## 本次样例周

选择 2017 年训练期的 1 月 1 日 00:00 至 1 月 7 日 23:45 UTC，共 **672 步，持续 168 小时**。源 CSV 本周质量标记异常步数为零。当前候选参数下，购电约 38.75 MWh；失负荷约 12.12 MWh，发生在 228 步（累计 57.0 小时）；弃电约 1.27 MWh，发生在 52 步（累计 13.0 小时）。这些值展示规则和容量在该周的局限，不代表全年性能。

后续滚动优化的 24 小时窗口应为 **96 个 15 分钟步长，每次只执行第一步**。当前规则基线保持无预测输入。
