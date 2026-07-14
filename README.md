# Modular-Multi-Agent-Orchestration-Framework

Repository structure

```
framework/
├── agents/
│   ├── base.py            # AgentConfig, BaseAgent (abstract worker template)
│   ├── context.py         # AgentContext — bounded slice of state an agent sees
│   ├── registry.py        # AgentRegistry — id -> agent lookup
│   └── concrete/
│       └── stub.py        # StubAgent — fake agent for testing without a real LLM
├── orchestration/
│   ├── state.py           # OrchestrationState, RunRequest, RunResult
│   ├── task.py             # Task, AgentMessage
│   └── patterns/
│       └── base.py        # PATTERN_REGISTRY, @register_pattern, BaseOrchestrationPattern
├── memory/
│   ├── local.py            # AgentLocalMemory — per-agent scratchpad (not wired in yet, Goal 10)
│   ├── shared.py           # SharedWorkflowMemory — structured key/value store (Goal 10)
│   └── artifacts.py        # ArtifactStore — persists artifacts to disk (Goal 10)
├── tools/
│   ├── base.py             # BaseTool, ToolRegistry (enforces per-agent permissions)
│   └── builtin/            # MockSearchTool, CalculatorTool, FileReadTool, FileWriteTool
└── runtime/
    └── loader.py            # THE GLUE — loads YAML, builds registries, fires the pattern

configs/
└── sequential_research.yaml # Example 3-agent workflow (researcher -> analyst -> writer)

tests/unit/                   # 32 tests across state, tools, and pattern registration
cli.py                        # Command-line entrypoint
pyproject.toml                # Dependencies and project metadata
```


### HOW DOES IT WORK Tejas??

```
1. You run this in the terminal:
   python cli.py run --task "research KV cache" --workflow sequential_research

2. cli.py
   → main() parses your args, sees "run", calls cmd_run(args)
   → cmd_run() calls run_workflow(task, workflow_id) 
   
3. framework/__init__.py
   → this is just the "front door" — it re-exports run_workflow
     so cli.py can say `from framework import run_workflow`
     instead of digging into runtime.loader directly

4. framework/runtime/loader.py   ← THE GLUE. Everything routes through here.
   run_workflow() does 4 things in order:

   a) load_workflow_config()
      → opens configs/sequential_research.yaml
      → reads it into a plain Python dict

   b) _build_agent_registry()
      → for each agent listed in the yaml (researcher, analyst, writer):
        - builds an AgentConfig  (from agents/base.py)
        - wraps it in a StubAgent (from agents/concrete/stub.py)
        - stores it in an AgentRegistry (from agents/registry.py)

   c) _build_tool_registry()
      → for each tool listed in the yaml (web_search, calculator, etc.):
        - instantiates the real tool class (tools/builtin/*.py)
        - stores it in a ToolRegistry (from tools/base.py)

   d) creates one OrchestrationState (from orchestration/state.py)
      → this is the blank notebook for this run — empty history,
        empty artifacts, a fresh run_id

5. Still in loader.py:
   → looks up "sequential" inside PATTERN_REGISTRY 
     (that registry lives in orchestration/patterns/base.py)
   → if found: pattern.execute(state, agent_registry, tool_registry)
   → if NOT found: bail out with an error ← THIS IS WHERE WE ARE TODAY.
     No pattern has called @register_pattern yet (that's Goal 4+),
     so PATTERN_REGISTRY is empty and every run currently stops here.

6. (Future — once Goal 4 exists)
   → the sequential pattern would call agent.run(task, context) on
     researcher, then analyst, then writer, in order
   → each .run() call uses:
       - orchestration/task.py       → builds the Task handed to the agent
       - agents/context.py           → builds the bounded AgentContext
       - tools/base.py ToolRegistry  → if the agent calls a tool
       - orchestration/state.py      → logs the message/tool call/artifact

7. loader.py wraps everything into a RunResult (orchestration/state.py)
   and hands it back up to cmd_run()

8. cli.py prints the result to your terminal
```

### HOW do I use it Tejas??

```bash
# install dependencies
pip install -e ".[dev]"

# run the test suite
pytest tests/ -v

# see registered patterns (currently empty — expected)
python cli.py list-patterns

# see tools available to a given workflow config
python cli.py list-tools --workflow sequential_research

# attempt a run (will fail with "pattern not registered" — expected for now)
python cli.py run --task "research KV cache" --workflow sequential_research
```