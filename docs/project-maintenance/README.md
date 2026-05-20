# Project Maintenance

`docs/project-maintenance/` 承接 operator-facing 维护文档：结构真相、治理入口、部署 runbook，以及按 backend 聚合的 repo-local usage help。

`project-maintenance/` 不长期承载 `suspended` 文档；暂停中的共享 runbook 转为 `superseded`，非共享草稿移出。

## 当前入口分层

1. `foundations/` — 根目录、truth boundary 与分层规则
2. `governance/` — review/verify/gate 与路径治理检查
3. `deploy/` — destructive reinstall 主流程、drift/conflict/unrecognized 维护、已有项目接入
4. `testing/` — Python 脚本/治理检查/closeout gate 命令、registry `npx`/本地 `.tgz` smoke、Codex/Claude 行为测试
5. `usage-help/` — `agents`、`claude` 的 backend 差异、安装后使用和 source 变更后的 operator 决策

## 从这里怎么进

- [foundations/README.md](./foundations/README.md)
- [governance/README.md](./governance/README.md)
- [deploy/README.md](./deploy/README.md)
- [testing/README.md](./testing/README.md)
- [usage-help/README.md](./usage-help/README.md)

## Operator 常见入口

- 新 repo 接入 Harness：[repo-onboarding.md](./repo-onboarding.md)
- 安装 skill：[deploy/deploy-runbook.md](../aw-installer/runbooks/deploy-runbook.md)
- 已有 mounts 想更新或复验：[deploy/skill-deployment-maintenance.md](../aw-installer/runbooks/skill-deployment-maintenance.md)
- 新增/改名/删除 skill source：[usage-help/README.md](./usage-help/README.md)
- 运行治理检查、`npx` smoke 或行为测试：[testing/README.md](./testing/README.md)
- 确认 `agents`/`claude` 差异：[usage-help/README.md](./usage-help/README.md)

AI 默认阅读顺序以 [AGENTS.md](../../AGENTS.md) 为准。本页只做入口导航。
