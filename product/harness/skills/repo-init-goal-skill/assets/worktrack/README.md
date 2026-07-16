# Harness Init Assets / Worktrack

这里承接 `repo-init-goal-skill` 自带的 Worktrack control-state seed。

Repo init 不预建 Worktrack 运行 artifact。Candidate PlanWork 按具体
`worktrack_id` create-only 物化 `initial-requirement.yaml`，Close 成功后生成
`finished-handback.yaml`；临时 round chain 位于 `.servo/tmp/`。
