# AIC AI＋能源：风光荷预测下的电池—氢储能协同调度

三人团队的统一工作仓库。目标是用同一测试时段比较四种策略：阈值规则、持续性预测＋滚动优化、q50 预测＋滚动优化、分位数预测＋动态备用＋滚动优化。

当前状态：**已接收 A 的 2017–2019 年15分钟虚拟园区数据和 B 的15分钟固定规则调度基线。** 数据在 `data/processed/A_15min_virtual_2017_2019.csv`，B 的完整交付在 `src/dispatch/b_module_15min/`。运行方法、验收情况与已知问题见 [15分钟交付说明](docs/HANDOFF_15MIN.md)。`data/sample/` 仍仅含人工构造的旧版小时级格式示例，不能用于报告实验。

注意：现有 `docs/DATA_CONTRACT.md`、`docs/EXPERIMENT_PROTOCOL.md` 和 `tools/validate_contract.py` 为最初的小时级规范，尚未迁移，不能用于验收此次15分钟交付。当前 B 的结果格式和专用校验器以交付目录为准；预测模型、滚动优化、成本及退化模型尚未交付。

## 先做什么

1. 全员阅读 [交付格式](docs/DATA_CONTRACT.md) 和 [实验规则](docs/EXPERIMENT_PROTOCOL.md)。任何字段或单位的变更先在仓库讨论，再更新文档。
2. 成员 A 先提交选定的 ENTSO-E 地区、历史时段、三类数据的可用性检查，以及连续 48 小时的清洗样本；成员 B 同时提交设备参数及来源。具体责任见 [任务分工](docs/TEAM_TASKS.md)。
3. 交付前运行 `python tools/validate_contract.py clean <文件>`、`forecast <文件>` 或 `dispatch <文件>`，确认格式通过。示例文件可用于试运行校验器。

## 目录约定

```text
config/                  参数和实验配置；真实取值需标明来源
data/sample/             可提交的人工样例，仅用于接口测试
data/raw/                原始下载文件，不提交 Git
data/processed/          默认忽略；经 C 授权提交此次 A 的完整15分钟数据
docs/                    字段、实验和任务约定
results/                 完整模型输出，不提交 Git；最终成果另行打包
src/forecast/            A：清洗、特征、预测
src/dispatch/            B：设备模型、规则、优化
src/evaluation/          C：指标、画图、流程集成
tests/                   可重复运行的小样本测试
tools/                   数据格式校验等工具
```

## 协作规则

- 默认分支 `main` 保持可运行；A/B/C 分别从 `feat/data-forecast`、`feat/dispatch`、`feat/integration` 开始工作。合并前至少由另一名队员检查。
- 提交代码、配置、必要的小样本和运行说明；不要提交原始大数据、模型权重、账号令牌、个人路径或临时结果。
- 此次由 C 明确授权共享 A 的处理后数据和 B 的完整交付包（含样例结果）。B 包内个人路径保留为交付原貌，替代运行命令见15分钟交付说明；其他数据仍默认忽略。
- 每次交付在 Pull Request 中写明输入、输出、运行命令、通过的检查和未解决的问题。模板见 `.github/pull_request_template.md`。
- 重要假设写入配置或文档，不能只存在于聊天记录；实验结束后保存配置、代码版本和结果文件校验值。

## 数据边界

ENTSO-E 的负荷和发电数据是区域/市场级时序。若按比例缩放用于微电网，应在配置与报告中明确为“基于真实区域时序构造的微电网仿真场景”，不得称为真实微电网运行数据。装机容量页面不能替代逐小时实际发电数据。
