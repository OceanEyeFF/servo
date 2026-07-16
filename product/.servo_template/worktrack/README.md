# AW Template / Worktrack

`product/.servo_template/worktrack/` 只提供 Worktrack 控制状态 seed。

Candidate Worktrack 的持久 handoff 位于 `.servo/worktrack/<worktrack-id>/`：

- `initial-requirement.yaml` 由 PlanWork 从上层已批准输入 create-only 物化。
- `finished-handback.yaml` 仅在 Close 成功后 create-only 生成。

两者都不是 repo-init 预生成模板；round chain 位于 gitignored `.servo/tmp/<worktrack-id>/`。
