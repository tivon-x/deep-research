# Deep Research Agent 评估 Pipeline 构建任务文档

## 1. 文档目的

本文档用于指导 Codex、Claude Code 等编码智能体，为当前 `Deep Research` 项目实现一套 **最小可用（MVP）但功能相对完善** 的 Agent 测试与评估 pipeline。

该 pipeline 的目标不是构建一个庞大而复杂的评测平台，而是在 **尽量少改动现有系统结构** 的前提下，为项目补齐以下关键能力：

1. **离线回归测试**：在提示词、工具、模型、工作流调整后，快速发现行为退化。
2. **多粒度评估**：同时覆盖单步决策、完整单轮执行，以及有限的多轮会话行为。
3. **状态产物评估**：不仅评估最终回复，还评估 `StateBackend` 中生成的研究文件与审计文件。
4. **LangSmith 对接**：所有测试尽量可记录到 LangSmith，便于查看 trace、实验结果与失败样例。
5. **工程可维护性**：测试代码优先采用 pytest + 少量辅助工具函数实现，避免引入过重框架。

---

## 2. 背景与现状理解（基于当前 README）

当前项目是一个基于 Deep Agents / LangChain / LangGraph 的多智能体 Deep Research 系统，采用 Hub-and-Spoke 架构，包含五个角色：

- `Orchestrator`
- `Scoping`
- `Researcher`
- `Verification`
- `Report Writer`

系统当前已经具备较清晰的 8 步流水线：

1. Plan
2. Scope
3. Decompose
4. Research
5. Verify
6. Iterate
7. Report
8. Final Check

同时，项目具有如下与评估直接相关的结构性特征：

- 使用 **StateBackend** 作为线程级共享工作区，而非直接依赖本地磁盘。
- 研究过程会产出稳定的中间文件路径，例如：
  - `/research_request.md`
  - `/research_brief.md`
  - `/research_findings/*`
  - `/research_verification.md`
  - `/final_report.md`
- `Scoping` 阶段存在 **Human-in-the-Loop approval interrupt**。
- `Researcher` 默认依赖 Tavily 搜索，并有 `RESEARCH_SEARCH_TOOL_LIMIT` 限制。
- `Verification` 会输出 `COMPLETE` / `NEEDS_MINOR_ADDITIONS` / `NEEDS_MAJOR_REWORK`。
- 系统支持可选 MCP 工具与 role-based domain skills。

这些设计意味着：

1. 本项目非常适合做 **轨迹评估（tool calls / execution path）**。
2. 本项目非常适合做 **状态评估（文件内容 / 审核结果 / 最终报告）**。
3. 本项目不适合一上来就做非常重的 benchmark 平台，更适合先做一套 **pytest + LangSmith experiment** 风格的评估基础设施。

---

## 3. 设计原则

实现评估 pipeline 时，必须遵循以下原则：

### 3.1 优先支持三种评估粒度

参考 LangChain / LangSmith 当前最佳实践，至少支持以下三类评估：

1. **Single-step eval**
   - 只运行到某个关键决策点。
   - 重点看：是否选择了正确工具、是否生成了合理的下一步动作。
   - 用途：快速、便宜、适合做“单元测试”。

2. **Full-turn eval**
   - 让 agent 完成一次完整研究请求。
   - 重点看：最终报告质量、关键轨迹是否出现、状态文件是否正确生成。
   - 用途：最核心的端到端离线回归测试。

3. **Limited multi-turn eval**
   - 仅实现最小可用的多轮测试，不追求复杂对话树。
   - 重点看：线程状态延续、第二轮是否能够基于第一轮研究成果继续推进。
   - 用途：验证 thread / state continuity。

### 3.2 优先评估“可观测行为”，不要依赖隐式推理

不要尝试评估模型的私有思维过程。优先评估：

- 是否调用了正确工具
- 是否产生了预期文件
- 文件内容是否满足结构要求
- 最终报告是否引用了研究结果
- 审核结果是否与研究完整性一致

### 3.3 尽量使用“确定性断言 + LLM-as-judge”混合方案

每个测试优先采用以下顺序：

1. **确定性断言**：是否存在某文件、是否包含某状态、是否调用某工具、是否超出搜索次数。
2. **轻量启发式规则**：例如标题、Markdown 结构、引用数量、段落数。
3. **LLM-as-judge**：用于判断研究完整性、引用有效性、总结深度等难以纯规则判断的维度。

### 3.4 环境必须可复现

每个 eval case 都必须在干净环境中运行，避免线程状态、缓存、文件残留相互污染。

实现上至少要做到：

- 每个 case 使用独立 `thread_id`
- 每个 case 独立配置状态空间或临时目录
- 外部搜索调用在可行时支持 mock / replay

### 3.5 不要把评估体系和主业务逻辑强耦合

评估 pipeline 应尽量通过：

- 对公开入口函数的调用
- LangGraph interrupt / tracing
- 状态读取函数
- 工具调用 trace

来完成，而不是大规模侵入现有 agent 内部实现。

---

## 4. MVP 范围与非目标

## 4.1 MVP 必做

本阶段必须交付：

1. `pytest` 测试套件
2. LangSmith tracing / experiment 集成
3. 至少三类 eval：
   - single-step
   - full-turn
   - limited multi-turn
4. 至少三类 evaluator：
   - trajectory/tool evaluator
   - artifact/state evaluator
   - final report evaluator
5. 至少一份小型 eval dataset（10–20 条测试样例）
6. 能输出本地测试结果，并在启用 LangSmith 时可查看 trace / feedback

## 4.2 本阶段不做

以下内容明确不作为第一阶段目标：

- 完整在线生产监控系统
- 复杂 UI dashboard
- 自动生成海量 benchmark 数据
- 覆盖所有 MCP 场景
- 极复杂的人类评分工作流
- 完整的 conversation tree 多分支测试框架

---

## 5. 推荐的总体架构

建议新增一个独立评估目录，例如：

```text
evals/
├── README.md
├── conftest.py
├── helpers/
│   ├── runner.py
│   ├── traces.py
│   ├── state.py
│   ├── assertions.py
│   ├── judges.py
│   └── fixtures.py
├── datasets/
│   ├── single_step.yaml
│   ├── full_turn.yaml
│   └── multi_turn.yaml
├── test_single_step.py
├── test_full_turn.py
├── test_multi_turn.py
└── smoke/
    └── test_pipeline_smoke.py
```

另建议在项目根目录增加：

```text
src/
  ...

scripts/
├── run_evals.py
└── export_eval_summary.py
```

如需更清晰地隔离配置，可增加：

```text
.env.eval.example
```

---

## 6. 技术选型要求

评估 pipeline 优先采用以下栈：

- **测试框架**：`pytest`
- **LangSmith 集成**：`langsmith` Python SDK + pytest integration
- **轨迹评估**：优先使用 `agentevals`（若与当前依赖兼容）
- **LLM judge**：使用项目当前 OpenAI-compatible 模型接入，封装成独立 judge helper
- **数据文件格式**：推荐 `yaml`，便于人工维护
- **Mock / Replay（可选但推荐）**：
  - HTTP 层可考虑 `vcrpy`
  - 或对 Tavily 搜索工具做 monkeypatch / fake provider

要求：

1. 测试能在没有 LangSmith 的情况下本地运行。
2. 设置 `LANGSMITH_TRACING=true` 和 `LANGSMITH_API_KEY` 后，自动把测试 run 记录到 LangSmith。
3. 若用户未配置 LangSmith，不得导致测试框架崩溃。

---

## 7. 数据集设计

## 7.1 数据集原则

测试集不要追求“大”，而要追求“覆盖关键失败模式”。

建议初始数据集控制在 **10–20 个 case**，覆盖：

1. 简单事实型研究
2. 需要拆分子问题的研究
3. 需要 follow-up research 的研究
4. 易产生伪引用/错误引用的研究
5. 需要 human approval 的 scoping
6. 多轮延续型研究
7. 带 domain skill 的研究
8. 搜索预算敏感场景

## 7.2 推荐数据格式

每条 case 建议包含以下字段：

```yaml
id: full_turn_basic_ai_policy
category: full_turn
input: Research the latest changes to ...
skills: null
approval_mode: auto_approve
thread_reuse: false
expectations:
  required_tools_any_order:
    - tavily_search
  forbidden_tools: []
  required_files:
    - /research_request.md
    - /research_brief.md
    - /research_verification.md
    - /final_report.md
  verification_status_allowed:
    - COMPLETE
    - NEEDS_MINOR_ADDITIONS
  final_report:
    min_headings: 3
    min_citations: 3
    must_answer_user_question: true
  findings:
    min_files: 1
  budgets:
    max_search_calls: 15
judge:
  enabled: true
  rubric: report_quality_basic
```

对于多轮 case：

```yaml
id: multi_turn_refine_report
category: multi_turn
turns:
  - user: Research topic X
    approval_mode: auto_approve
    assertions:
      required_files:
        - /final_report.md
  - user: Revise the report to focus more on Y
    assertions:
      report_must_include:
        - Y
      should_reuse_existing_context: true
```

---

## 8. 三类测试的具体设计

## 8.1 Single-step eval

### 8.1.1 目标

验证 agent 在某个关键节点上的即时决策是否正确。

### 8.1.2 在当前项目中的重点场景

优先实现以下 single-step case：

1. **Scoping 输出质量**
   - 给定用户问题，是否产出 2–5 个聚焦子问题。
   - 是否形成合理 research brief。

2. **Researcher 首次工具选择**
   - 对需要联网研究的问题，第一步是否调用 `tavily_search`。
   - 参数中是否包含与 query 强相关的关键词。

3. **Verification 决策**
   - 给定故意不完整的 findings，是否输出 `NEEDS_MAJOR_REWORK` 或 `NEEDS_MINOR_ADDITIONS`。

4. **Report Writer 结构选择**
   - 给定不同类型 findings，是否生成合理的报告结构雏形。

### 8.1.3 实现建议

如果当前 LangGraph / Deep Agents 入口支持 interrupt 或 stop-before-tool 节点，则优先采用：

- 运行到指定节点前停止
- 抽取最新消息中的 tool call / structured output
- 对工具名、参数、草稿内容进行断言

如果做不到，则退而求其次：

- 直接对对应 subagent 的入口函数做调用
- 将输出解析为结构化对象或文本，再做断言

### 8.1.4 断言类型

优先使用：

- 是否调用正确工具
- 是否未调用不该调用的工具
- 参数是否包含关键实体
- 子问题数量范围是否正确
- verification status 是否符合预期

---

## 8.2 Full-turn eval

### 8.2.1 目标

验证一次完整研究流程是否能正确完成。

### 8.2.2 这是本项目最重要的测试层

每个 full-turn case 至少要评估三个维度：

#### A. 轨迹维度

至少验证：

- 是否经过了 scoping approval
- 是否发生了 research 阶段工具调用
- 是否执行了 verification
- 是否生成了 report

不要求每个 case 都精确匹配完整工具序列，但至少应验证关键节点存在。

#### B. 状态维度

至少验证以下文件是否存在并有内容：

- `/research_request.md`
- `/research_brief.md`
- `/research_verification.md`
- `/final_report.md`

并视场景检查：

- `/research_findings/*` 文件数量
- verification 文件中是否有状态字段
- final report 是否引用 findings 中信息

#### C. 最终输出维度

至少验证：

- 最终摘要或报告是否回答了原问题
- 是否有基本 Markdown 结构
- 是否包含引用或来源痕迹
- 是否没有明显“未完成占位符”

### 8.2.3 推荐 evaluator 组合

每个 full-turn case 推荐组合：

1. **deterministic trajectory assertions**
2. **artifact assertions**
3. **LLM judge on final report**

### 8.2.4 对当前项目最关键的 full-turn case

至少实现以下 case：

1. **基础研究成功 case**
   - 普通开放主题
   - 一轮完成

2. **需要迭代补充的 case**
   - 初始 findings 故意不足
   - 验证阶段应触发补充研究

3. **搜索预算约束 case**
   - 验证搜索调用数不超过 `RESEARCH_SEARCH_TOOL_LIMIT`

4. **引用质量 case**
   - 报告中应包含多处来源引用或明确来源痕迹

5. **skills case**
   - 在启用某个 role-based skill 时，验证其对研究产物结构产生可见影响

---

## 8.3 Limited multi-turn eval

### 8.3.1 目标

验证 thread state 能否在连续两轮或三轮交互中正确延续。

### 8.3.2 本阶段只做有限多轮

只实现最小必要模式：

1. 第一轮：完成某主题研究
2. 第二轮：要求聚焦某子主题、改写报告或追加比较维度

### 8.3.3 关键断言

- 第二轮是否复用先前 thread state
- 第二轮是否不必从零开始重新构建全部研究流程（允许局部补充）
- 第二轮最终报告是否体现新增指令
- 若第一轮输出不满足预期，应提前 fail，不要盲目进入下一轮

### 8.3.4 推荐实现方式

多轮测试采用“条件推进”模式：

1. 执行 turn 1
2. 对 turn 1 做关键断言
3. 仅当 turn 1 通过时，执行 turn 2
4. turn 2 继续使用相同 `thread_id`

---

## 9. Evaluator 设计

## 9.1 Trajectory / Tool Evaluator

实现一个通用 evaluator，至少支持：

- 提取所有工具调用名称
- 统计各工具调用次数
- 提取工具参数
- 判断某工具是否出现
- 判断某工具是否未出现
- 判断调用次数是否超预算

建议暴露接口：

```python
def collect_tool_calls(run) -> list[dict]:
    ...

def assert_required_tools(run, required: list[str]) -> None:
    ...

def assert_tool_budget(run, tool_name: str, max_calls: int) -> None:
    ...
```

若能接入 `agentevals`，可进一步支持：

- exact trajectory match
- unordered required-tools match
- trajectory LLM judge

但这不是 MVP 的硬性要求。

## 9.2 Artifact / State Evaluator

这是当前项目最重要的自定义 evaluator。

至少实现：

- 读取 thread state 中的虚拟文件
- 检查文件存在性
- 检查内容非空
- 检查 Markdown 标题数量
- 检查是否包含特定字段 / 关键词
- 检查 findings 文件数量
- 检查 verification status

建议暴露接口：

```python
def read_state_file(state, path: str) -> str | None:
    ...

def assert_file_exists(state, path: str) -> None:
    ...

def extract_verification_status(text: str) -> str | None:
    ...
```

## 9.3 Final Report Evaluator

对 `/final_report.md` 做评估。

至少实现两层：

### 规则层

- 字数下限
- 标题数量下限
- 引用痕迹数量下限
- 不得包含占位文本：
  - `TODO`
  - `TBD`
  - `lorem ipsum`
  - `citation needed`

### LLM judge 层

定义一个统一 rubric，至少评分：

1. 是否回答用户问题
2. 是否基于已有 findings 而不是凭空生成
3. 结构是否清晰
4. 是否指出不确定性或证据边界
5. 是否存在明显幻觉/无来源断言

judge 输出建议使用结构化 schema，例如：

```python
class ReportJudgeResult(BaseModel):
    answers_question: bool
    grounded_in_findings: bool
    structure_clear: bool
    cites_sources: bool
    hallucination_risk: Literal["low", "medium", "high"]
    score: int
    rationale: str
```

---

## 10. Human-in-the-Loop scoping 的测试策略

由于当前流程在 scoping 阶段需要 approval，中间会有 interrupt，因此评估 pipeline 必须支持自动化处理该环节。

实现要求：

1. 提供统一的 `approval_mode` 测试参数：
   - `auto_approve`
   - `auto_reject`
   - `manual`（可选）

2. MVP 阶段至少支持 `auto_approve`。

3. 至少增加一个测试 case 验证：
   - 当 scoping 被 reject 时，流程不会继续消耗搜索调用。

如果当前 CLI 层不利于自动测试，优先从底层 graph / agent invoke 层接入 interrupt 恢复逻辑。

---

## 11. 搜索与外部依赖的测试策略

## 11.1 分层运行模式

建议实现两种模式：

### 模式 A：Live eval

- 使用真实 Tavily
- 使用真实模型
- 用于少量高价值回归测试

### 模式 B：Mocked / Replay eval

- 对 Tavily 或外部 HTTP 请求进行 mock/replay
- 用于 CI 和快速开发循环

## 11.2 要求

至少实现以下之一：

1. 对 `tavily_search` 进行 monkeypatch，返回稳定伪造结果。
2. 录制 HTTP 结果并回放。

优先目标是：

- 让 smoke tests 与 single-step tests 尽量不依赖真实外部服务。
- 让 full-turn 关键样例可以选择 live 模式单独运行。

---

## 12. 与 LangSmith 的集成要求

## 12.1 最低要求

当环境变量存在时，测试必须能把结果记录到 LangSmith：

- `LANGSMITH_TRACING=true`
- `LANGSMITH_API_KEY=...`

建议支持：

- 自定义 `LANGSMITH_PROJECT=deep-research-evals`
- 每个测试 case 带 `id/category/tags`

## 12.2 推荐做法

- 使用 `@pytest.mark.langsmith`
- 在测试中记录输入、输出、关键 feedback 分数
- 对失败样例保留 trace 链接或至少打印可定位信息

## 12.3 反馈记录

对于 LLM judge 或自定义评分，统一记录为 LangSmith feedback：

- `answers_question`
- `grounded_in_findings`
- `citation_quality`
- `verification_status_correct`
- `search_budget_ok`

---

## 13. 代码组织与实现步骤

按以下顺序实施，不要并行乱改：

### 阶段 1：搭脚手架

1. 新建 `evals/` 目录
2. 新建 `evals/README.md`
3. 添加 `conftest.py`
4. 添加 dataset loader
5. 添加基础 runner
6. 添加 state/file helper

### 阶段 2：打通 smoke test

实现一个最简单的 smoke case，验证：

- 能调用主入口执行一次 research
- 能自动 approve scoping
- 能读到 `/final_report.md`

### 阶段 3：实现 artifact evaluator

先把以下断言做稳定：

- 文件存在
- 文件非空
- verification status 可提取
- final report 基本结构正确

### 阶段 4：实现 trajectory evaluator

实现：

- 工具调用提取
- 工具预算检查
- 必需工具存在性检查

### 阶段 5：实现 full-turn tests

至少实现 3–5 个高价值 full-turn case。

### 阶段 6：实现 single-step tests

至少实现：

- scoping
- researcher first tool
- verification decision

### 阶段 7：实现 limited multi-turn tests

至少实现一个 2-turn continuity case。

### 阶段 8：接入 LLM judge

在已有确定性断言稳定后，再增加 report judge。

### 阶段 9：脚本化运行

增加：

- `scripts/run_evals.py`
- 支持 `--live` / `--mocked`
- 支持只跑某一类：
  - `single-step`
  - `full-turn`
  - `multi-turn`

---

## 14. 必须实现的辅助抽象

编码智能体必须优先抽象以下接口，避免测试代码重复：

### 14.1 统一运行入口

```python
@dataclass
class EvalRunResult:
    final_output: str | None
    state: Any
    thread_id: str
    trace_ref: str | None
    raw_result: Any

async def run_case(case: dict, *, mode: str = "live") -> EvalRunResult:
    ...
```

### 14.2 统一状态读取入口

```python
def get_virtual_file(state: Any, path: str) -> str | None:
    ...
```

### 14.3 统一断言入口

```python
def assert_required_artifacts(result: EvalRunResult, case: dict) -> None:
    ...


def assert_required_trajectory(result: EvalRunResult, case: dict) -> None:
    ...


def assert_final_report(result: EvalRunResult, case: dict) -> None:
    ...
```

### 14.4 统一 judge 入口

```python
async def judge_report(case: dict, report_text: str, findings_text: str) -> ReportJudgeResult:
    ...
```

---

## 15. 示例测试清单

## 15.1 Single-step

1. `test_scoping_generates_2_to_5_questions`
2. `test_researcher_calls_tavily_first_for_web_research`
3. `test_verifier_marks_major_rework_when_findings_missing_key_subquestions`

## 15.2 Full-turn

1. `test_full_turn_generates_required_artifacts`
2. `test_full_turn_respects_search_budget`
3. `test_full_turn_report_has_citations_and_structure`
4. `test_full_turn_can_trigger_minor_additional_research`

## 15.3 Multi-turn

1. `test_multi_turn_refines_existing_report_using_same_thread`

## 15.4 Smoke

1. `test_pipeline_smoke_auto_approve`
2. `test_pipeline_smoke_reject_stops_before_search`

---

## 16. 验收标准

实现完成后，必须满足以下验收条件：

### 16.1 基础功能

- 可以通过 `pytest` 启动评估
- 无 LangSmith 时可本地运行
- 有 LangSmith 时可记录 traces / feedback

### 16.2 覆盖范围

至少具备：

- 3 个 single-step case
- 3 个 full-turn case
- 1 个 multi-turn case
- 1 个 smoke reject case

### 16.3 评估能力

至少能检查：

- 工具调用存在性
- 搜索预算限制
- 必需研究文件生成
- verification status 合法性
- 最终报告基本结构
- 最终报告是否基本回答问题

### 16.4 工程质量

- helper 抽象清晰
- 测试数据与测试逻辑分离
- 不把大量 case 硬编码到单个测试函数中
- mock/live 模式切换明确
- README 说明如何运行

---

## 17. 推荐的最小实现顺序（非常重要）

编码智能体严格按如下顺序实现：

1. 新增 `evals/README.md`，说明目标与运行方式。
2. 打通一个最简单的 `full-turn smoke case`。
3. 实现 `artifact/state` 读取与断言。
4. 实现 `trajectory/tool` 读取与断言。
5. 将 smoke case 扩展为 3 个 full-turn case。
6. 增加 3 个 single-step case。
7. 增加 1 个 multi-turn case。
8. 最后再引入 LLM judge。

不要在第一步就尝试：

- 复杂 DSL
- 自动 benchmark 生成
- 复杂 GUI
- 大规模 case 工厂

先做对，再做大。

---

## 18. 实现备注与约束提醒

1. 当前项目存在 `request_approval` interrupt，测试代码需要显式处理。
2. 当前项目依赖 `StateBackend`，测试不要假设所有文件都在本地磁盘。
3. `final_report.md` 是最关键的最终产物，但不能只测它。
4. `verification` 是当前工作流最有价值的质量闸门，必须纳入测试。
5. 由于项目支持 role skills，测试时要保证：
   - 无 skill 模式是默认基线
   - skill 模式至少有一个 case
6. 如果 MCP 测试太重，可以先跳过，但代码结构要为后续扩展留接口。

---

## 19. 最终交付物

本任务完成后，应至少新增以下内容：

```text
evals/
  README.md
  conftest.py
  helpers/
  datasets/
  test_single_step.py
  test_full_turn.py
  test_multi_turn.py
  smoke/test_pipeline_smoke.py
scripts/
  run_evals.py
```

并确保：

1. `pytest -q evals` 可运行
2. 可选支持：
   - `pytest -q evals -m single_step`
   - `pytest -q evals -m full_turn`
   - `pytest -q evals -m multi_turn`
3. `scripts/run_evals.py` 可以作为统一入口
4. 文档写清楚：
   - 本地运行方式
   - LangSmith 配置方式
   - live / mocked 模式区别

---

## 20. 一句话总结给编码智能体

为当前 Deep Research 项目实现一套 **pytest + LangSmith 驱动的多粒度评估 pipeline**：先保证 **single-step、full-turn、limited multi-turn** 三类测试可运行，再补齐 **trajectory、artifact/state、final report** 三类 evaluator，并通过 **小型 YAML 数据集 + 可复现运行环境** 形成稳定的离线回归能力。
