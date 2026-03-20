# Deep Research

English version: [README.md](./README.md)

Deep Research 是一个多智能体系统，旨在自主对任何主题进行高保真研究。该系统基于 [Deep Agents](https://github.com/deepagents/deepagents) 框架构建，通过协调专业的 AI 智能体团队，实现信息的规划、搜索、验证并最终合成专业报告。

本系统超越了简单的“搜索并总结”循环，将研究视为结构化的工程流水线。它能将模糊的用户查询转化为明确的研究简报（research briefs），执行并行搜索任务，审计调研质量，并在极少人工干预的情况下生成带有引用的专业报告。

## 🛠️ 技术栈

- **框架**: Python 3.12+, Deep Agents (`>=0.4.5`)
- **编排**: LangChain + LangGraph
- **智能**: LangChain OpenAI（支持任何兼容 OpenAI 的 API）
- **搜索**: Tavily Search API（用于获取高质量网页数据并进行 Markdown 转换）
- **MCP 集成**: `langchain-mcp-adapters`（可选，用于数据库/知识库/内部系统）
- **界面**: 基于 Rich 的命令行界面（CLI），提供结构化的终端反馈

## 🏗️ 系统架构

系统采用层次化的“中心辐射”（Hub and Spoke）模型。中央编排器负责管理流程，并将具体的技术任务委派给四个专业的子智能体。

| 智能体 | 模型角色 | 主要职责 |
| :--- | :--- | :--- |
| **编排器 (Orchestrator)** | `MAIN_MODEL_ID` | 高层规划、任务委派和状态管理。 |
| **范围界定 (Scoping)** | `SUBAGENT_MODEL_ID` | 意图分析和子问题生成，并等待人工审批。 |
| **研究员 (Researcher)** | `SUBAGENT_MODEL_ID` | 通过 Tavily 进行深度网页搜索并提取原始数据。 |
| **验证器 (Verification)** | `SUBAGENT_MODEL_ID` | 根据初始研究简报审计调研结果的质量。 |
| **报告撰写员 (Report Writer)** | `SUBAGENT_MODEL_ID` | 将验证后的数据合成最终的、带有引用的 Markdown 文档。 |

## 🔄 工作流程

Deep Research 遵循严格的 8 步执行流水线，以确保研究的深度和一致性。

```text
[1. 规划] --> [2. 界定范围] --> [3. 任务分解] --> [4. 执行研究]
                                                        |
[8. 完成] <-- [7. 撰写报告] <-- [6. 迭代优化] <-- [5. 质量验证]
```

### 第 1 步：规划 (Plan)
编排器初始化线程级虚拟工作区（StateBackend），通过 `write_todos` 创建任务列表，并将原始请求记录到 `/research_request.md`。

### 第 2 步：界定范围 (Scope)
范围界定智能体将主题分解为 2 到 5 个核心子问题。此时系统会触发 **人机协作 (Human-in-the-Loop)** 中断，在执行任何研究任务之前等待人工确认研究方向。Rich CLI 会以 `Pending Research Brief` 专用面板展示待审批简报，便于终端直接审阅并决定通过/拒绝。

### 第 3 步：分解研究任务 (Decompose)
编排器分析研究简报以确定所需的并行度。系统会根据主题复杂度动态扩展，从简单的单任务模式到复杂主题的多个并行任务（默认最多 3 个）。

### 第 4 步：执行研究 (Research)
每个子问题由独立的系统研究员处理。智能体会抓取完整的 Markdown 格式网页内容并保存到 `/research_findings/`。搜索调用由中间件计数并设置硬上限（`RESEARCH_SEARCH_TOOL_LIMIT`，默认 `15`）。

### 第 5 步：质量验证 (Verify)
专门的验证智能体会对调研结果进行审计。它负责检查覆盖范围的缺失，并将研究质量评定为 `COMPLETE`（完成）、`NEEDS_MINOR_ADDITIONS`（需要少量补充）或 `NEEDS_MAJOR_REWORK`（需要重大重做）。

### 第 6 步：迭代优化 (Iterate)
如果审计发现高优先级的缺失，编排器会分派针对性的补充研究任务。系统会在现有文件基础上进行增量构建，而非从零开始。

### 第 7 步：撰写报告 (Report)
报告撰写智能体合成所有验证后的调研结果。它会根据内容选择合适的结构模板（如对比、分析、概述等），并在 `/final_report.md` 生成带有文中引用的专业报告。

### 第 8 步：最终检查 (Finish)
编排器进行最后的通读，确保用户的原始问题已得到充分解答，最后呈现研究总结和文件路径。

## ✨ 核心设计亮点

- **自适应任务分解**：系统根据主题复杂度动态调整研究员数量，而非使用硬编码的线程数。针对具体问题使用单个智能体；而对宽泛主题，则调用多达三个智能体并行工作。

- **StateBackend 共享工作区**：中间产物（`/research_brief.md`、`/research_findings/*`、`/research_verification.md`、`/final_report.md`）保存在线程状态而不是本地磁盘。这样更适合服务端多用户部署，并可避免多次运行时的文件冲突。

- **无状态子智能体设计**：每次子智能体调用都是自包含的。编排器在调用时传递完整的上下文（子问题、文件路径、约束条件），确保了系统的可靠性，并使单个智能体的替换变得非常简单。

- **验证关卡**：所有数据在通过专门的审计步骤前不会进入最终报告。验证智能体会对照研究简报中的子问题检查覆盖情况，并在合成开始前标记未经验证或存在矛盾的观点。

- **人机协作界定范围**：利用 LangGraph 的中断机制（`request_approval`）暂停执行，在搜索开始前获取人工对研究简报的确认，有效防止因理解偏差导致的 API 调用浪费。CLI 会同时展示审批元信息和完整待审批简报内容。

- **搜索与完整内容获取**：系统不仅依赖搜索摘要，`tavily_search` 工具还会抓取完整的网页内容并转换为 Markdown，为研究智能体提供更丰富的素材。

- **可选 MCP 数据源**：research 子智能体可从 JSON 配置文件加载 MCP 工具。只有在 MCP 工具实际可用时才会注入 MCP 提示词，避免在纯 Web 模式下引入噪声。

- **多模型架构**：强模型驱动推理密集的编排器；多种模型处理执行子智能体。这让你能在关键环节使用强大模型，在批量搜索环节使用更快速且经济的模型。

- **按角色加载领域技能（Skills）**：支持按 `orchestrator/scoping/research/verification/report` 五个角色配置领域技能。启用后，CLI 会把角色 `SKILL.md` 注入 StateBackend 虚拟文件系统，并在执行中以技能指引优先于通用研究流程。

- **兼容 OpenAI 接口**：支持任何兼容 OpenAI 的 API 端点。只需设置 `BASE_URL`，即可无缝对接 OpenAI、Azure OpenAI、Ollama、vLLM 或其他服务商。

## 📁 文件结构

```text
deep-research/
├── src/
│   ├── agent.py              # 编排器定义
│   ├── prompts.py            # 五个智能体的系统提示词
│   ├── skills.py             # 技能发现、校验与状态注入辅助逻辑
│   ├── tools.py              # tavily_search, think_tool, request_approval
│   ├── llm.py                # ChatOpenAI 模型实例
│   ├── config.py             # 环境变量加载与限制配置
│   └── subagents/
│       ├── research_agent.py
│       ├── scoping_agent.py
│       ├── verification_agent.py
│       └── report_agent.py
├── .env.example
├── mcp_config.example.json
├── pyproject.toml
├── DOMAIN_SKILL_AUTHORING_GUIDE.md  # 领域角色技能编写指南
└── langgraph.json
```

## 🚀 快速开始

### 1. 前置条件

- Python 3.12+
- [Tavily API key](https://tavily.com)
- 兼容 OpenAI 的 API 密钥及端点

### 2. 安装

```bash
# 使用 uv (推荐)
uv sync

```

### 3. 配置

将 `.env.example` 复制为 `.env` 并填写相关凭据：

```env
API_KEY=your-api-key-here
BASE_URL=https://api.openai.com/v1        # 任何兼容 OpenAI 的端点
MAIN_MODEL_ID=gpt-4o                      # 编排器模型
SUBAGENT_MODEL_ID=gpt-4o-mini            # 研究/验证/报告模型
TAVILY_API_KEY=tvly-your-key-here
RESEARCH_SEARCH_TOOL_LIMIT=15          # 可选：每个 research-agent 任务的 tavily_search 最大调用次数
MCP_CONFIG_FILE=mcp_config.json        # 可选：MCP 服务配置文件
```

可选 MCP 配置：

1. 将 `mcp_config.example.json` 复制为 `mcp_config.json`。
2. 填写 `mcp_servers` 和 `mcp_capabilities`。
3. 启动 CLI。系统会在启动阶段显式初始化 MCP，并显示 `MCP Configuration` 面板：
   - `enabled`：MCP 工具加载成功并可用
   - `configured but load failed`：已配置但加载失败（提示词中的 MCP 指引保持关闭）
   - `disabled`：未提供 MCP 配置
### 4. 运行

推荐的 async-first 入口（无需安装成库）：

```bash
python main.py "请研究 2026 年美国 AI 芯片出口管制最新变化"
```
可选的直接脚本方式：

```bash
python src/cli.py "请研究 2026 年美国 AI 芯片出口管制最新变化"
```
交互模式：

```bash
python main.py
```
交互模式下会先让你选择技能域（也可选择 `None`），然后再输入研究问题。

常用参数：

```bash
python main.py --thread-id my-session "你的问题"
python main.py --plain "你的问题"
python main.py --skills finance "你的问题"
```
--thread-id 用于续跑/延续同一会话，--plain 用于纯文本输出最终答案，--skills 用于加载一个领域技能目录（`./skills/<skill>/<role>/`）。
在 `StateBackend` 下，这些本地 `SKILL.md` 会在异步调用时自动注入到线程状态的 `/skills/<skill>/<role>/SKILL.md`。
如何编写领域角色技能，请参考 DOMAIN_SKILL_AUTHORING_GUIDE.md。

如果你更偏好 LangGraph 开发模式，也可以继续使用：

```bash
langgraph dev
```
流程会在范围界定阶段暂停一次等待审批，审批后继续生成研究产物。
Agent 构造仍保持同步，但执行、状态读取、外部网络 I/O 和 MCP 生命周期都已改为异步。

## 输出文件说明

使用 `StateBackend` 时，研究过程文件保存在当前 thread 的状态中（虚拟路径，例如 `/research_brief.md`）。

CLI 现已在任务完成后将最终报告从 state 落盘：

| 产物 | 持久化位置 |
| :--- | :--- |
| `/research_request.md`、`/research_brief.md`、`/research_findings/<topic>.md`、`/research_verification.md`、`/final_report.md` | 线程状态（`StateBackend`） |
| `research/final_report.md` | CLI 结束时写入本地磁盘 |

English version: [README.md](./README.md)



