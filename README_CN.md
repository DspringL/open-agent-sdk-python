# Open Agent SDK（Python）

[![PyPI version](https://img.shields.io/pypi/v/open-agent-sdk)](https://pypi.org/project/open-agent-sdk/)
[![Python](https://img.shields.io/badge/python-%3E%3D3.10-brightgreen)](https://python.org)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue)](./LICENSE)

开源 Agent SDK，**在进程内**运行完整的 Agent 循环 —— 无需子进程或 CLI。可部署到任何环境：云端、Serverless、Docker、CI/CD。

同时提供 **TypeScript** 版本：[open-agent-sdk-typescript](https://github.com/codeany-ai/open-agent-sdk-typescript) · **Go** 版本：[open-agent-sdk-go](https://github.com/codeany-ai/open-agent-sdk-go)

## 功能特性

- **多模型提供商** — 通过统一的 Provider 抽象支持 Anthropic 及 OpenAI 兼容 API（DeepSeek、Qwen、vLLM、Ollama）
- **Agent 循环** — 支持工具执行、多轮对话和费用追踪的流式 Agent 循环
- **35 个内置工具** — Bash、Read、Write、Edit、Glob、Grep、WebFetch、WebSearch、Agent（子 Agent）、Skill 等
- **技能系统** — 可复用的提示词模板，内置 5 个技能（commit、review、debug、simplify、test）
- **MCP 支持** — 通过 stdio、HTTP 和 SSE 传输协议连接 MCP 服务器
- **权限系统** — 可配置的工具审批机制，支持允许/拒绝规则和自定义回调
- **Hook 系统** — 20 个生命周期事件，用于拦截 Agent 行为
- **会话持久化** — 保存/加载/分叉对话会话
- **自定义工具** — 使用 Pydantic 模型或原始 JSON Schema 定义工具
- **扩展思考** — Claude 思考预算配置
- **费用追踪** — 按模型统计 Token 用量，支持精确计费（Anthropic + OpenAI + DeepSeek + Qwen）

## 快速安装

```bash
pip install open-agent-sdk
```

设置 API Key：

```bash
export CODEANY_API_KEY=your-api-key
```

通过 `CODEANY_BASE_URL` 支持第三方提供商（如 OpenRouter）：

```bash
export CODEANY_BASE_URL=https://openrouter.ai/api
export CODEANY_API_KEY=sk-or-...
export CODEANY_MODEL=anthropic/claude-sonnet-4
```

## 快速上手

### 单次查询（流式）

```python
import asyncio
from open_agent_sdk import query, AgentOptions, SDKMessageType

async def main():
    async for message in query(
        prompt="读取 pyproject.toml 并告诉我项目名称。",
        options=AgentOptions(
            allowed_tools=["Read", "Glob"],
            permission_mode="bypassPermissions",
        ),
    ):
        if message.type == SDKMessageType.ASSISTANT:
            print(message.text)

asyncio.run(main())
```

### 简单阻塞式提示

```python
import asyncio
from open_agent_sdk import create_agent, AgentOptions

async def main():
    agent = create_agent(AgentOptions(model="claude-sonnet-4-5"))
    result = await agent.prompt("这个项目里有哪些文件？")

    print(result.text)
    print(f"轮次：{result.num_turns}，Token 数：{result.usage.input_tokens + result.usage.output_tokens}")
    await agent.close()

asyncio.run(main())
```

### 多轮对话

```python
import asyncio
from open_agent_sdk import create_agent, AgentOptions

async def main():
    agent = create_agent(AgentOptions(max_turns=5))

    r1 = await agent.prompt('创建文件 /tmp/hello.txt，内容为 "Hello World"')
    print(r1.text)

    r2 = await agent.prompt("读取你刚刚创建的文件")
    print(r2.text)

    print(f"会话消息数：{len(agent.get_messages())}")
    await agent.close()

asyncio.run(main())
```

### OpenAI 兼容模型

```python
import asyncio
from open_agent_sdk import create_agent, AgentOptions

async def main():
    # 根据模型前缀自动检测 openai-completions
    agent = create_agent(AgentOptions(
        model="gpt-4o",
        api_key="sk-...",
    ))
    print(f"API 类型：{agent.get_api_type()}")  # openai-completions

    result = await agent.prompt("2+2 等于多少？")
    print(result.text)
    await agent.close()

    # DeepSeek、Qwen 等
    agent2 = create_agent(AgentOptions(
        model="deepseek-chat",
        api_key="sk-...",
        base_url="https://api.deepseek.com/v1",
    ))

    # 或显式指定 api_type
    agent3 = create_agent(AgentOptions(
        api_type="openai-completions",
        model="my-custom-model",
        base_url="http://localhost:8000/v1",
    ))

asyncio.run(main())
```

### 自定义工具（Pydantic Schema）

```python
import asyncio
from pydantic import BaseModel
from open_agent_sdk import query, create_sdk_mcp_server, AgentOptions, SDKMessageType
from open_agent_sdk.tool_helper import tool, CallToolResult

class CityInput(BaseModel):
    city: str

async def get_weather_handler(input: CityInput, ctx):
    return CallToolResult(
        content=[{"type": "text", "text": f"{input.city}：22°C，晴天"}]
    )

get_weather = tool("get_weather", "获取城市气温", CityInput, get_weather_handler)
server = create_sdk_mcp_server("weather", tools=[get_weather])

async def main():
    async for msg in query(
        prompt="东京的天气怎么样？",
        options=AgentOptions(mcp_servers={"weather": server}),
    ):
        if msg.type == SDKMessageType.RESULT:
            print(f"完成：${msg.total_cost:.4f}")

asyncio.run(main())
```

### 自定义工具（底层方式）

```python
import asyncio
from open_agent_sdk import create_agent, AgentOptions
from open_agent_sdk.tool_helper import define_tool
from open_agent_sdk.types import ToolResult, ToolContext

async def calc_handler(input: dict, ctx: ToolContext) -> ToolResult:
    result = eval(input["expression"], {"__builtins__": {}})
    return ToolResult(tool_use_id="", content=f"{input['expression']} = {result}")

calculator = define_tool(
    name="Calculator",
    description="计算数学表达式",
    input_schema={
        "properties": {"expression": {"type": "string"}},
        "required": ["expression"],
    },
    handler=calc_handler,
    read_only=True,
)

async def main():
    agent = create_agent(AgentOptions(tools=[calculator]))
    r = await agent.prompt("计算 2**10 * 3")
    print(r.text)
    await agent.close()

asyncio.run(main())
```

### 技能系统

```python
import asyncio
from open_agent_sdk import create_agent, AgentOptions, SDKMessageType
from open_agent_sdk.skills import register_skill, get_all_skills, init_bundled_skills, SkillDefinition
from open_agent_sdk.types import ToolContext

async def main():
    # 自动初始化 5 个内置技能：commit、review、debug、simplify、test
    init_bundled_skills()
    print(f"技能列表：{[s.name for s in get_all_skills()]}")

    # 注册自定义技能
    async def explain_prompt(args, ctx):
        return [{"type": "text", "text": f"简单解释：{args}"}]

    register_skill(SkillDefinition(
        name="explain", description="用简单语言解释一个概念",
        aliases=["eli5"], user_invocable=True, get_prompt=explain_prompt,
    ))

    # Agent 可通过 Skill 工具调用技能
    agent = create_agent(AgentOptions(max_turns=5))
    result = await agent.prompt('使用 "explain" 技能解释 git rebase')
    print(result.text)
    await agent.close()

asyncio.run(main())
```

### MCP 服务器集成

```python
import asyncio
from open_agent_sdk import create_agent, AgentOptions, McpStdioConfig

async def main():
    agent = create_agent(AgentOptions(
        mcp_servers={
            "filesystem": McpStdioConfig(
                command="npx",
                args=["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
            ),
        },
    ))

    result = await agent.prompt("列出 /tmp 目录下的文件")
    print(result.text)
    await agent.close()

asyncio.run(main())
```

### 子 Agent

```python
import asyncio
from open_agent_sdk import query, AgentOptions, AgentDefinition, SDKMessageType

async def main():
    async for msg in query(
        prompt="使用 code-reviewer Agent 审查 src/ 目录",
        options=AgentOptions(
            agents={
                "code-reviewer": AgentDefinition(
                    description="专业代码审查员",
                    prompt="分析代码质量，重点关注安全性和性能。",
                    tools=["Read", "Glob", "Grep"],
                ),
            },
        ),
    ):
        if msg.type == SDKMessageType.RESULT:
            print("完成")

asyncio.run(main())
```

### 权限控制

```python
import asyncio
from open_agent_sdk import query, AgentOptions, SDKMessageType

async def main():
    # 只读 Agent —— 只能分析，不能修改
    async for msg in query(
        prompt="审查 src/ 目录中的代码最佳实践。",
        options=AgentOptions(
            allowed_tools=["Read", "Glob", "Grep"],
            permission_mode="dontAsk",
        ),
    ):
        pass

asyncio.run(main())
```

### Web UI

内置 Web 聊天界面，方便测试：

```bash
python examples/web/server.py
# 打开 http://localhost:8083
```

## API 参考

### 顶层函数

| 函数 | 描述 |
| ---- | ---- |
| `query(prompt, options)` | 单次流式查询，返回 `AsyncGenerator` |
| `create_agent(options)` | 创建支持会话持久化的可复用 Agent |
| `tool(name, desc, model, handler)` | 使用 Pydantic Schema 验证创建工具 |
| `define_tool(name, ...)` | 底层工具定义辅助函数 |
| `create_sdk_mcp_server(name, tools)` | 将工具打包为进程内 MCP 服务器 |
| `create_provider(api_type, ...)` | 创建 LLM Provider（Anthropic 或 OpenAI） |
| `get_all_base_tools()` | 获取全部 35 个内置工具 |
| `register_skill(definition)` | 注册自定义技能 |
| `get_all_skills()` | 列出所有已注册技能 |
| `init_bundled_skills()` | 初始化 5 个内置技能 |
| `list_sessions()` | 列出持久化会话 |
| `get_session_messages(id)` | 获取会话消息记录 |
| `fork_session(id)` | 分叉会话以创建分支 |

### Agent 方法

| 方法 | 描述 |
| ---- | ---- |
| `await agent.query(prompt)` | 流式查询，返回 `AsyncGenerator[SDKMessage]` |
| `await agent.prompt(text)` | 阻塞式查询，返回 `QueryResult` |
| `agent.get_messages()` | 获取对话历史 |
| `agent.get_api_type()` | 获取已解析的 API 类型（`anthropic-messages` / `openai-completions`） |
| `agent.clear()` | 重置会话 |
| `await agent.interrupt()` | 中止当前查询 |
| `await agent.set_model(model)` | 会话中途切换模型 |
| `await agent.set_permission_mode(mode)` | 修改权限模式 |
| `await agent.close()` | 关闭 MCP 连接并持久化会话 |

### 配置项（`AgentOptions`）

| 选项 | 类型 | 默认值 | 描述 |
| ---- | ---- | ------ | ---- |
| `model` | `str` | `claude-sonnet-4-5` | LLM 模型 ID（或设置 `CODEANY_MODEL` 环境变量） |
| `api_type` | `str` | 自动 | `anthropic-messages` 或 `openai-completions`（根据模型自动检测） |
| `api_key` | `str` | `CODEANY_API_KEY` | API Key |
| `base_url` | `str` | — | 自定义 API 端点 |
| `cwd` | `str` | `os.getcwd()` | 工作目录 |
| `system_prompt` | `str` | — | 覆盖系统提示词 |
| `append_system_prompt` | `str` | — | 追加到默认系统提示词 |
| `tools` | `list[BaseTool]` | 全部内置 | 额外自定义工具 |
| `allowed_tools` | `list[str]` | — | 工具白名单 |
| `disallowed_tools` | `list[str]` | — | 工具黑名单 |
| `permission_mode` | `PermissionMode` | `bypassPermissions` | `default` / `acceptEdits` / `dontAsk` / `bypassPermissions` / `plan` |
| `can_use_tool` | `CanUseToolFn` | — | 自定义权限回调 |
| `max_turns` | `int` | `10` | 最大 Agent 轮次 |
| `max_budget_usd` | `float` | — | 费用上限（美元） |
| `max_tokens` | `int` | `16000` | 最大输出 Token 数 |
| `thinking` | `ThinkingConfig` | — | 扩展思考配置 |
| `mcp_servers` | `dict[str, McpServerConfig]` | — | MCP 服务器连接 |
| `agents` | `dict[str, AgentDefinition]` | — | 子 Agent 定义 |
| `hooks` | `dict[str, list[dict]]` | — | 生命周期 Hook |
| `resume` | `str` | — | 通过 ID 恢复会话 |
| `continue_session` | `bool` | `False` | 继续最近的会话 |
| `persist_session` | `bool` | `False` | 将会话持久化到磁盘 |
| `session_id` | `str` | 自动 | 显式指定会话 ID |
| `json_schema` | `dict` | — | 结构化输出 |
| `sandbox` | `bool` | `False` | 文件系统/网络沙箱 |
| `env` | `dict[str, str]` | — | 环境变量 |
| `debug` | `bool` | `False` | 启用调试输出 |

### 环境变量

| 变量 | 描述 |
| ---- | ---- |
| `CODEANY_API_KEY` | API Key（必填） |
| `CODEANY_MODEL` | 默认模型覆盖 |
| `CODEANY_BASE_URL` | 自定义 API 端点 |
| `CODEANY_API_TYPE` | `anthropic-messages` 或 `openai-completions` |

## 多 Provider 支持

SDK 使用统一的 Provider 抽象。内部所有消息以 Anthropic 格式作为标准表示，Provider 层自动处理格式转换：

```
你的代码 → Agent → QueryEngine → Provider 层 → LLM API
                                      │
                       ┌──────────────┴──────────────┐
                       │   AnthropicProvider          │
                       │   直接透传                    │
                       ├─────────────────────────────┤
                       │   OpenAIProvider             │
                       │   Anthropic ↔ OpenAI 格式转换 │
                       └─────────────────────────────┘
```

**消息格式转换（OpenAI Provider）：**

| Anthropic（内部格式） | OpenAI（传输格式） |
| --------------------- | ----------------- |
| `system` 提示词字符串 | `{"role": "system", "content": "..."}` |
| `tool_use` 内容块 | `tool_calls[].function` |
| `tool_result` 内容块 | `{"role": "tool", "tool_call_id": "..."}` |
| `stop_reason: "end_turn"` | `finish_reason: "stop"` |
| `stop_reason: "tool_use"` | `finish_reason: "tool_calls"` |
| `stop_reason: "max_tokens"` | `finish_reason: "length"` |

**自动检测**：以 `gpt-`、`deepseek-`、`qwen-`、`o1-`、`o3-`、`o4-` 开头的模型自动使用 `openai-completions`。可通过 `api_type` 选项或 `CODEANY_API_TYPE` 环境变量覆盖。

## 内置工具

| 工具 | 描述 |
| ---- | ---- |
| **Bash** | 执行 Shell 命令 |
| **Read** | 读取带行号的文件 |
| **Write** | 创建/覆盖文件 |
| **Edit** | 精确字符串替换 |
| **Glob** | 按模式查找文件 |
| **Grep** | 正则搜索文件内容 |
| **WebFetch** | 抓取并解析网页内容 |
| **WebSearch** | 网络搜索 |
| **NotebookEdit** | 编辑 Jupyter Notebook 单元格 |
| **Agent** | 生成子 Agent 并行工作 |
| **Skill** | 按名称调用已注册技能 |
| **TaskCreate/List/Update/Get/Stop/Output** | 任务管理系统 |
| **TeamCreate/Delete** | 多 Agent 团队协调 |
| **SendMessage** | Agent 间消息传递 |
| **EnterWorktree/ExitWorktree** | Git Worktree 隔离 |
| **EnterPlanMode/ExitPlanMode** | 结构化规划工作流 |
| **AskUserQuestion** | 向用户提问 |
| **ToolSearch** | 发现懒加载工具 |
| **ListMcpResources/ReadMcpResource** | MCP 资源访问 |
| **CronCreate/Delete/List** | 定时任务管理 |
| **RemoteTrigger** | 远程 Agent 触发 |
| **LSP** | 语言服务器协议（代码智能） |
| **Config** | 动态配置 |
| **TodoWrite** | 会话待办事项列表 |

## 内置技能

| 技能 | 别名 | 描述 |
| ---- | ---- | ---- |
| **commit** | `ci` | 创建规范的 Git 提交信息 |
| **review** | `review-pr`、`cr` | 审查代码变更的正确性、安全性和风格 |
| **debug** | `investigate`、`diagnose` | 结构化调试与系统性排查 |
| **simplify** | — | 审查变更代码的复用性、质量和效率 |
| **test** | `run-tests` | 运行测试并分析/修复失败 |

## 架构

```
┌──────────────────────────────────────────────────────┐
│                     你的应用程序                       │
│                                                       │
│   from open_agent_sdk import create_agent              │
└────────────────────────┬─────────────────────────────┘
                         │
              ┌──────────▼──────────┐
              │       Agent         │  会话状态、工具池、
              │ query() / prompt()  │  MCP 连接、技能
              └──────────┬──────────┘
                         │
              ┌──────────▼──────────┐
              │    QueryEngine      │  Agent 循环：
              │  submit_message()   │  API 调用 → 工具 → 重复
              └──────────┬──────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
   ┌─────▼─────┐  ┌─────▼─────┐  ┌─────▼─────┐
   │  Provider │  │  35 工具  │  │    MCP     │
   │ Anthropic │  │ Bash,Read │  │   服务器   │
   │  OpenAI   │  │ Edit,...  │  │ stdio/SSE/ │
   │ DeepSeek  │  │ Skill,... │  │ HTTP/SDK   │
   └───────────┘  └───────────┘  └───────────┘
```

**核心组件：**

| 组件 | 描述 |
| ---- | ---- |
| **Provider 层** | Anthropic + OpenAI 兼容（DeepSeek、Qwen、vLLM、Ollama） |
| **QueryEngine** | 核心 Agent 循环，含自动压缩、重试、工具编排 |
| **技能系统** | 5 个内置技能（commit、review、debug、simplify、test）+ 自定义 |
| **自动压缩** | 上下文窗口满时自动摘要对话 |
| **微压缩** | 截断过大的工具返回结果 |
| **重试** | 针对限流和瞬时错误的指数退避重试 |
| **Token 估算** | 用于预算和压缩阈值的粗略 Token 计数 |
| **文件缓存** | 文件读取的 LRU 缓存 |
| **Hook 系统** | 20 个生命周期事件（PreToolUse、PostToolUse、SessionStart 等） |
| **会话存储** | 在磁盘上持久化/恢复/分叉会话 |
| **上下文注入** | 自动将 Git 状态和 AGENT.md 注入系统提示词 |

## 示例

| 编号 | 文件 | 描述 |
| ---- | ---- | ---- |
| 01 | `examples/01_simple_query.py` | 带事件处理的流式查询 |
| 02 | `examples/02_multi_tool.py` | 多工具编排（Glob + Bash） |
| 03 | `examples/03_multi_turn.py` | 多轮会话持久化 |
| 04 | `examples/04_prompt_api.py` | 阻塞式 `prompt()` API |
| 05 | `examples/05_custom_system_prompt.py` | 自定义系统提示词 |
| 06 | `examples/06_mcp_server.py` | MCP 服务器集成 |
| 07 | `examples/07_custom_tools.py` | 使用 `define_tool()` 自定义工具 |
| 08 | `examples/08_official_api_compat.py` | `query()` API 模式 |
| 09 | `examples/09_subagents.py` | 子 Agent 委托 |
| 10 | `examples/10_permissions.py` | 带工具限制的只读 Agent |
| 11 | `examples/11_custom_mcp_tools.py` | `tool()` + `create_sdk_mcp_server()` |
| 12 | `examples/12_skills.py` | 技能系统用法（注册、调用、列出） |
| 13 | `examples/13_hooks.py` | 生命周期 Hook 配置与执行 |
| 14 | `examples/14_openai_compat.py` | OpenAI/兼容模型支持（DeepSeek 等） |
| web | `examples/web/` | 用于测试的 Web 聊天 UI |

运行任意示例：

```bash
python examples/01_simple_query.py
```

启动 Web UI：

```bash
python examples/web/server.py
# 打开 http://localhost:8083
```

## 项目结构

```
open-agent-sdk-python/
├── src/open_agent_sdk/
│   ├── __init__.py         # 公共导出
│   ├── agent.py            # Agent 高层 API
│   ├── engine.py           # QueryEngine Agent 循环
│   ├── types.py            # 核心类型定义
│   ├── session.py          # 会话持久化
│   ├── hooks.py            # Hook 系统（20 个生命周期事件）
│   ├── tool_helper.py      # 基于 Pydantic 的工具创建
│   ├── sdk_mcp_server.py   # 进程内 MCP 服务器工厂
│   ├── providers/
│   │   ├── types.py        # LLMProvider 接口
│   │   ├── anthropic_provider.py  # Anthropic 实现
│   │   ├── openai_provider.py     # OpenAI 兼容（无 SDK 依赖）
│   │   └── factory.py     # create_provider() 工厂函数
│   ├── skills/
│   │   ├── types.py        # SkillDefinition、SkillResult
│   │   ├── registry.py     # 技能注册表（注册、查找、格式化）
│   │   └── bundled/        # 5 个内置技能（commit、review、debug、simplify、test）
│   ├── mcp/
│   │   └── client.py       # MCP 客户端（stdio/SSE/HTTP）
│   ├── tools/              # 35 个内置工具
│   │   ├── bash.py, read.py, write.py, edit.py
│   │   ├── glob_tool.py, grep.py, web_fetch.py, web_search.py
│   │   ├── agent_tool.py, skill_tool.py, send_message.py
│   │   ├── task_tools.py, team_tools.py, worktree_tools.py
│   │   ├── plan_tools.py, cron_tools.py, lsp_tool.py
│   │   └── config_tool.py, todo_tool.py, ...
│   └── utils/
│       ├── messages.py     # 消息创建与规范化
│       ├── tokens.py       # Token 估算与计费（Anthropic + OpenAI + DeepSeek + Qwen）
│       ├── compact.py      # 自动压缩逻辑
│       ├── retry.py        # 指数退避重试
│       ├── context.py      # Git 与项目上下文注入
│       └── file_cache.py   # LRU 文件状态缓存
├── tests/                  # 265 个测试
├── examples/               # 14 个示例 + Web UI
└── pyproject.toml
```

## 相关链接

- 官网：[codeany.ai](https://codeany.ai)
- TypeScript SDK：[github.com/codeany-ai/open-agent-sdk-typescript](https://github.com/codeany-ai/open-agent-sdk-typescript)
- Go SDK：[github.com/codeany-ai/open-agent-sdk-go](https://github.com/codeany-ai/open-agent-sdk-go)
- 问题反馈：[github.com/codeany-ai/open-agent-sdk-python/issues](https://github.com/codeany-ai/open-agent-sdk-python/issues)

## 许可证

MIT
