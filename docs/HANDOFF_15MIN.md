# A 数据与 B 规则基线交付

2026-09-28，由成员 C 授权同步至私有仓库。文件按交付原貌复制，未改动 B 的算法、参数或结果，也未改动 A 的数据值。

## 文件位置

- A 数据：`data/processed/A_15min_virtual_2017_2019.csv`。
- B 完整包：`src/dispatch/b_module_15min/`，包括设备模型、规则调度、参数及来源表、测试、专用校验器、一周结果和 B 的验证报告。
- 原来的小时级样例、规范和通用校验器继续保留，尚未迁移至15分钟接口。

## 数据与用途

数据为基于德国区域负荷、风光时序缩放构造的虚拟园区，不是真实园区测量。2017年为训练集、2018年为验证集、2019年为测试集。时间为 UTC 区间起点，间隔15分钟，功率单位 kW；完整文件共105,120行。

负荷采用固定训练期缩放系数，使2017年平均负荷为1,000 kW；光伏与风电暂按3,200 kW和1,600 kW装机缩放。这些容量仍是竞赛场景假设。原始下载出处、清洗脚本和完整来源说明仍需 A 补交。

三年连续运行仅用于检查程序能否运行，不用于选择参数、调优或报告测试期算法优劣。正式比较须保留训练、验证、测试边界。

## 从仓库根目录运行

需要 Python 3.10+，B 模块无第三方 Python 依赖。以下命令将新生成结果写入已被忽略的 `results/`，不覆盖包内样例。

```powershell
python src/dispatch/b_module_15min/rule_dispatch.py --input data/processed/A_15min_virtual_2017_2019.csv --week-start 2017-01-01 --output results/b_rule_15min/week_2017-01-01_results.csv --summary results/b_rule_15min/week_2017-01-01_metrics.json

python src/dispatch/b_module_15min/validate_results.py --results results/b_rule_15min/week_2017-01-01_results.csv --summary results/b_rule_15min/week_2017-01-01_metrics.json --source data/processed/A_15min_virtual_2017_2019.csv --report results/b_rule_15min/verification_report.json

python -m unittest discover -s src/dispatch/b_module_15min -p test_rule_dispatch.py -v
```

注意：B 的单元测试仍写死作者电脑的数据路径，直接运行会跳过真实数据测试。上面的校验命令已显式提供仓库内数据，执行源数据比对；需要 B 后续将测试数据路径改为可配置。包内原始验证报告来自 B，本次验收情况见下文。

## C 的接收验收

- 重跑2017-01-01样例周：672步、168小时，生成 CSV 数值与交付 CSV 完全一致。
- 独立复算功率平衡、电池能量、氢库存、状态连续性、互斥、功率和爬坡限制：该周通过；最大平衡残差约2.27e-13 kW。
- 临时指定真实数据路径后，13项单元测试全部通过；直接按原始路径运行时1项跳过。
- A 的三年数据连续运行105,120步，未触发设备约束异常。这不是正式跨年性能评估。
- 样例周购电38,754.31 kWh，失负荷12,122.79 kWh（总负荷的7.03%），弃电1,268.75 kWh。

## 已知问题和边界

1. 固定规则不使用预测，尚无 MILP、滚动优化、成本或 SOH/退化模型。`step_cost` 留空、汇总成本为 null，不能按零成本统计。
2. 当前策略名为 `fixed_rule_battery_hydrogen_grid_15min`，状态为 `rule_ok`、`rule_curtailment`、`rule_unserved`。C 需统一策略命名；此次不自行改名。
3. 极端骤降下可能不可行：初始状态起，连续4步负荷0、光伏800 kW、风电0，使电池充电达到500 kW、制氢达到300 kW；下一步负荷及风光均为0时，受爬坡限制仍需充电375 kW、制氢225 kW，合计600 kW超过500 kW购电上限。规则给出100 kW失负荷，但客户负荷为0，设备模型会正确拒绝该动作。需 B 补专门的不可行状态报告及双方认可的应急处理，不能取消失负荷校验。
4. `curtailment_kw` 可能包含受爬坡限制未能撤销的燃料电池功率，未经分解不能直接当作弃风弃光电量。
5. 不同策略比较须使用相同初始状态，并明确终端库存处理。样例周终态为电池300 kWh、氢气约60 kg，不能忽略初始库存消耗。
6. 下一阶段预测窗口为96步（24小时），滚动调度每次仅执行第一步；全队接口规范仍需统一迁移。
