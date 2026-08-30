# Context Efficiency for Codex Swarm

## Why this matters

最新版大模型对噪音更耐受，但在以下场景，token 仍然非常昂贵：

- 同时加载多份 references / AGENTS / long chat history
- 需要浏览器、截图、日志等高体积输入
- 需要多个子代理时，每个子代理都可能重复读取同类上下文

## Rules

1. 只读取当前决策所需的 reference。
2. 同一条经验尽量沉淀到文件，不在每轮提示词重复。
3. 规则性动作优先 CLI / 脚本，避免把长工具描述注入上下文。
4. 子任务 prompt 必须是摘录版，不转发整轮 transcript。
5. 结果优先写文件，再由 controller 做总结。

## Practical Heuristics

- 研究任务：先 explorer 汇总，再交 controller 合并。
- 写代码任务：先 explorer 明确边界，再 worker 实现。
- 审查任务：实现者与 reviewer 分离，避免同一上下文自审。
- 多工具场景：只在必要时打开相关工具；不要默认全开。
