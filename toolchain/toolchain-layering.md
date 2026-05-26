---
title: "Toolchain 分层"
status: active
updated: 2026-05-26
owner: servo-kernel
last_verified: 2026-05-26
---
# Toolchain 分层

> 目的：把 `toolchain/` 的职责、子目录边界和输出落点固定在 `toolchain/` 自身目录内维护。

## 一、职责边界

`toolchain/` 只承载：

- 部署与同步脚本
- 治理检查与 gate 入口
- 打包与分发工具

`toolchain/` 不承载：

- 业务源码
- 文档真相正文
- repo-local mount
- 运行产物

## 二、当前结构

```text
toolchain/
├── README.md
└── scripts/
```

- `scripts/`：动作入口（deploy / test / research / hooks）

硬规则：

- `scripts/` 放动作，不放长期规则正文
- 运行结果写入 repo-local state，不写回 `toolchain/`

## 三、输出落点

`toolchain/` 脚本的运行输出应落到 repo-local state（当前主线为 `.servo/`；`.autoworkflow/` 只作为 legacy / compatibility state 语义保留）。

不要写回 `toolchain/` 的内容：

- 运行日志
- 临时结果
- 交互缓存
- 本地用户配置

## 四、扩展规则

- 保持 `scripts/` 为当前唯一动作入口层
- 子目录按动作类型扩展，不按历史来源堆放
- 新增脚本若说不清属于部署、评测、测试或打包，不应入库

## 五、相关文档

- [根目录分层](../docs/project-maintenance/foundations/root-directory-layering.md)
- [Toolchain 入口](./README.md)
- [Scripts 入口总览](./scripts/README.md)
