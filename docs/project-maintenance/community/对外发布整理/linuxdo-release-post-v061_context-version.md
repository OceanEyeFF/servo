---
title: "Linux Do v0.6.1 发布推广帖管理上下文"
status: active
updated: 2026-06-19
owner: servo-kernel
last_verified: 2026-06-19
source_platform: "Linux Do"
source_url: "TBD"
copy_status: "managed-platform-sample"
published_status: "published"
canonical_copy: "platform-original"
derivative_policy: "derive-by-platform-from-technical-architecture"
protected_copy: "linuxdo-release-post-v061.md"
protected_copy_sha256: "412f5e7c140b074f382c053f026cd465537eb5c5364ab66105043755a9546bbd"
frontmatter_exemption: "literal-platform-copy"
---
# Linux Do v0.6.1 发布推广帖管理上下文

> 本文只承接仓内管理上下文。受保护正文见 [linuxdo-release-post-v061.md](./linuxdo-release-post-v061.md)，没有明确授权不得修改正文。

## 仓内管理说明

`linuxdo-release-post-v061.md` 是 Linux Do 平台语境下的 v0.6.1 发布推广帖仓内正文副本，定位是 `managed-platform-sample`。

- **原帖正文**：保留 Linux Do 的平台语气、梗和发布语境；没有明确授权不得修改正文。
- **管理上下文**：本文解释正文在仓库中的管理方式，不代表实际平台正文的一部分。
- **事实校准来源**：技术侧和架构侧叙事看 [Servo 对外技术与架构叙事](../external-technical-architecture.md)；项目定位和适用场景看 [Servo 对外技术定位与适用场景](../external-positioning.md)；release、install、runtime 事实回到对应 owner 文档，不由正文副本单独承接。
- **source_url**：发布帖实际 URL 确认后补入 frontmatter；未确认前保持 `TBD`，不得伪造。

## 保护规则

正文副本没有 frontmatter，属于 `literal-platform-copy` 例外。`path_governance_check.py` 通过本文 frontmatter 确认例外合法性；`governance_semantic_check.py` 通过 `protected_copy_sha256` 校验正文哈希。

正文变更必须满足全部条件：

1. 使用者明确授权修改 Linux Do 正文副本。
2. 修改后同步更新本文 `protected_copy_sha256`。
3. 在本节或后续授权记录中说明修改原因。
4. 运行路径与语义治理检查。

## 平台派生规则

后续写知乎、小红书、Reddit 或其他平台版本时，不从 Linux Do 正文逐句改写，而是按下面顺序取材：

1. 先使用 [Servo 对外技术与架构叙事](../external-technical-architecture.md) 保留需求侧、技术侧、架构侧骨架。
2. 再用 [Servo 对外技术定位与适用场景](../external-positioning.md) 校准适用场景、安装入口和基础边界。
3. 最后参考 Linux Do 正文的语气和案例，但按目标平台重写叙事节奏、标题、例子密度和互动方式。

平台派生版本不应反向改写 Linux Do 正文；若派生版本发现事实变化，应回到对应 owner 文档更新，再决定是否申请修改正文副本。

## 授权记录

- 2026-06-19：使用者说明已移动 Linux Do 宣发文档，且该文档不允许更改；仓内补充 sidecar 管理上下文与 hash guard，不修改正文副本。
