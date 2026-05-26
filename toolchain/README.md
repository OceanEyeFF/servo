# Toolchain

`toolchain/` 是当前仓库第三块正式内容区。

它只负责：

- 执行动作的脚本入口
- 轻量测试与治理入口
- 后续按需准入的打包、分发或测量工具

它不负责：

- 业务源码
- 文档真相
- repo-local mount
- 运行产物

当前主线：

- `scripts/deploy/`
- `scripts/test/`

AI 先读什么：

1. `toolchain/toolchain-layering.md`
2. `toolchain/scripts/README.md`
3. 需要部署时进入 `scripts/deploy/`
4. 需要做轻量治理回归时进入 `scripts/test/`

暂时不要先读什么：

- `product/` 下的业务源码，除非当前任务需要交叉核对实现
- `.servo/` 下的运行产物，除非当前任务明确是 Harness runtime 结果分析
- legacy `.autoworkflow/` 下的运行产物，除非当前任务明确是旧状态兼容性分析

二级入口：

- `scripts/README.md`
- `scripts/deploy/README.md`
- `scripts/test/README.md`

治理说明见 `toolchain/toolchain-layering.md`。
