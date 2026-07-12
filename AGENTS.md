# AGENTS.md

## 指令优先级

- 本项目所有任务默认不调用 superpowers skill，除非用户明确要求。
- 直接执行代码修改、排查、验证，不进入 plan mode、brainstorming、systematic-debugging、verification-before-completion 等 skill 流程。
- 如果任务复杂需要结构化流程，先由用户明确说“用 skill”或“走 plan mode”再进入。
