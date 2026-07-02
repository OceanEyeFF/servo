# Harness Agents Adapters

`product/harness/adapters/agents/` 承接 `agents` backend 的 adapter source。

当前阶段：

- 已落当前 `agents` Harness skills 的 canonical-copy payload descriptor source
- payload 负责声明 `agents` target 应复制哪些 canonical skill 文件
- payload 不承接 deploy target runtime state

当前入口：

- [skills/README.md](./skills/README.md)：`agents` skill payload descriptor source

当前稳定边界：

- canonical truth 仍在 `product/harness/skills/`
- adapter source 只保存 `agents` backend 的 payload descriptor
- target naming 当前固定为 `<skill_id>`；`servo-<skill_id>` 仅作为 legacy target dir 由 payload 显式声明和收敛
- 旧 `servo-<skill_id>` 与 `aw-<skill_id>` 目录只通过 `legacy_target_dirs` 参与受管清理和 update 收敛
- repo-local `.agents/skills/` 是 deploy target，不是 source truth

这里适合放：

- `agents` backend 的 payload descriptor
- backend-specific 的 payload 元数据
- 后续 B4 要消费的 source layer

这里不适合放：

- canonical skill truth
- repo-local / global deploy target
- install state、verify 结果或 runtime hash
