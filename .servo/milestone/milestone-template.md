---
title: "Milestone 模板"
artifact_type: milestone
generated_from: milestone-template
updated: 2026-05-08
owner: programmer
---

# Milestone 模板

> 这是 Milestone artifact 的初始化模板。创建新 Milestone 实例时，复制此文件并填入实际值。
>
> Milestone 是 RepoScope 下的聚合观测变量，不创建第三 Scope，不接管 version management。
> 完成判定采用双重验收模型：`worktrack_list_finished` AND `purpose_achieved`，两者缺一不可。

---

## milestone_id

<!-- 字段说明: Milestone 的唯一标识符。建议格式: "MS-XXX"，如 MS-001、MS-002。 -->
<!-- 类型: string -->

```yaml
milestone_id: ""
```

---

## title

<!-- 字段说明: Milestone 名称，简洁描述本 Milestone 的目标。 -->
<!-- 类型: string -->

```yaml
title: ""
```

---

## purpose

<!-- 字段说明: Milestone 目的描述，说明本 Milestone 要达成的业务或技术目标。 -->
<!-- 类型: string -->

```yaml
purpose: ""
```

---

## status

<!-- 字段说明: Milestone 当前状态。 -->
<!-- 类型: enum -->
<!-- 可选值: planned | active | completed | superseded -->

```yaml
status: "planned"
```

---

## worktrack_list

<!-- 字段说明: 本 Milestone 包含的 worktrack ID 列表及每个 worktrack 的预期完成状态。 -->
<!-- 类型: array[object] -->
<!-- 每个元素包含: worktrack_id (string), expected_status (string) -->

```yaml
worktrack_list:
  # - worktrack_id: ""
  #   expected_status: ""
```

---

## completion_signals

<!-- 字段说明: 完成信号列表，每个信号是一个可观察的事实，用于判定 Milestone 目的是否达成。 -->
<!-- 类型: array[string] -->

```yaml
completion_signals:
  # - ""
```

---

## acceptance_criteria

<!-- 字段说明: Milestone 级别的验收标准列表，用于在 Milestone 退出前验证。 -->
<!-- 类型: array[string] -->

```yaml
acceptance_criteria:
  # - ""
```

---

## completion_threshold_pct

<!-- 字段说明: goal-driven milestone 的完成阈值百分比。 -->
<!-- 类型: integer -->
<!-- 默认值: 100 -->

```yaml
completion_threshold_pct: 100
```

---

## progress_counter

<!-- 字段说明: 进度计数器，由 milestone-status-skill 在运行时计算和更新。 -->
<!-- 类型: object -->
<!-- 结构: total (number), completed (number), blocked (number), deferred (number) -->

```yaml
progress_counter:
  total: 0
  completed: 0
  blocked: 0
  deferred: 0
```

---

## environment_probe

<!-- 字段说明: 环境探测要求，定义在进度评估时需要检查的环境条件。 -->
<!-- 类型: object -->

```yaml
environment_probe:
  # checks:
  #   - name: ""
  #     description: ""
  #     probe_command: ""
```

---

## aggregated_evidence

<!-- 字段说明: 聚合的 evidence 引用列表，收集各 worktrack 产生的关键 evidence。 -->
<!-- 类型: array[string] -->

```yaml
aggregated_evidence:
  # - ""
```

---

## release_version_consideration

<!-- 字段说明: 对 version/release 的提示信息。不接管 decision，仅作为参考标注。 -->
<!-- 类型: string -->

```yaml
release_version_consideration: ""
```

---

## developer_decision_boundary

<!-- 字段说明: 标记哪些决定必须由 developer 做出，不允许自动化系统自行判定。 -->
<!-- 类型: array[string] -->

```yaml
developer_decision_boundary:
  # - ""
```

---

## depends_on_milestones

<!-- 字段说明: 前置 Milestone ID 列表，本 Milestone 激活前必须满足其完成条件。 -->
<!-- 类型: array[string] -->

```yaml
depends_on_milestones:
  # - ""
```

---

## updated

<!-- 字段说明: 最后更新时间。每次修改 Milestone 文件时更新。 -->
<!-- 类型: date (ISO 8601) -->

```yaml
updated: ""
```
