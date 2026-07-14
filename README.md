# Modular-Multi-Agent-Orchestration-Framework

Repository structure

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





### HOW DOES IT WORK Tejas??

cli.py run --task "..." --workflow sequential_research
        │
        ▼
framework/__init__.py  (re-exports run_workflow)
        │
        ▼
framework/runtime/loader.py :: run_workflow()
        │
        ├─ load_workflow_config()      → reads configs/sequential_research.yaml
        ├─ _build_agent_registry()     → builds AgentConfig + StubAgent per entry
        ├─ _build_tool_registry()      → builds real tool instances (search, calc, file io)
        ├─ creates OrchestrationState  → fresh run_id, empty history/artifacts
        │
        ▼
        looks up "sequential" in PATTERN_REGISTRY
        │
        ├─ found   → pattern.execute(state, agent_registry, tool_registry)
        └─ NOT found → returns a failed RunResult with a clear error
                       (this is the current, correct behavior — no patterns
                        are registered yet)
        │
        ▼
RunResult bubbles back up to cli.py and gets printed


### HOW do I use it Tejas??

// install dependencies
pip install -e ".[dev]"

// run the test suite
pytest tests/ -v

// see registered patterns (currently empty — expected)
python cli.py list-patterns

// see tools available to a given workflow config
python cli.py list-tools --workflow sequential_research

// attempt a run (will fail with "pattern not registered" — expected for now)
python cli.py run --task "research KV cache" --workflow sequential_research