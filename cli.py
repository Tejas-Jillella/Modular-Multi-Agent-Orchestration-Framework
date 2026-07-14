"""
Minimal CLI entrypoint for the multi-agent framework.

Usage:
    python cli.py run --task "Summarize KV cache techniques" --workflow sequential_research
    python cli.py list-patterns
    python cli.py list-tools --workflow sequential_research
"""
import argparse
import json
import sys


def cmd_run(args):
    """Run a workflow and print the result."""
    from framework import run_workflow

    print(f"Running workflow '{args.workflow}' with task:\n  {args.task}\n")
    result = run_workflow(
        task=args.task,
        workflow_id=args.workflow,
        config_dir=args.config_dir,
    )

    print(f"Status:  {result.status}")
    print(f"Run ID:  {result.run_id}")
    print(f"Latency: {result.latency_ms:.1f}ms")
    print(f"Tokens:  {result.total_tokens}")

    if result.error:
        print(f"\nError: {result.error}", file=sys.stderr)
        sys.exit(1)

    print(f"\n--- Output ---\n{result.output}")

    if args.show_trace:
        print(f"\n--- Trace ({len(result.trace_events)} events) ---")
        for event in result.trace_events:
            print(f"  {event}")

    if args.show_history:
        print(f"\n--- Message History ({len(result.message_history)} messages) ---")
        for msg in result.message_history:
            print(f"  [{msg.agent_id}]: {msg.content[:200]}...")


def cmd_list_patterns(args):
    """List all registered orchestration patterns."""
    # Import all pattern modules to populate PATTERN_REGISTRY
    # (patterns self-register when their module is imported)
    from framework.orchestration.patterns.base import PATTERN_REGISTRY

    if not PATTERN_REGISTRY:
        print("No patterns registered yet.")
        print("Pattern modules must be imported to register themselves.")
        print("Goals 4-9 will add: sequential, router, parallel, hierarchical, orchestrator_worker, evaluator_optimizer")
        return

    print(f"Registered patterns ({len(PATTERN_REGISTRY)}):")
    for name in sorted(PATTERN_REGISTRY.keys()):
        print(f"  - {name}")


def cmd_list_tools(args):
    """List tools registered in a specific workflow config."""
    from framework.runtime.loader import load_workflow_config, _build_tool_registry

    try:
        raw = load_workflow_config(args.workflow, args.config_dir)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    registry = _build_tool_registry(raw.get("tools", []))
    print(f"Tools registered for workflow '{args.workflow}' ({len(registry)}):")
    for name in registry.registered_names():
        tool = registry.get(name)
        print(f"  - {name}: {tool.description[:80]}")


def main():
    parser = argparse.ArgumentParser(
        description="Modular Multi-Agent Orchestration Framework CLI"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # --- run command ---
    run_parser = subparsers.add_parser("run", help="Run a workflow")
    run_parser.add_argument("--task",       required=True, help="The task to run")
    run_parser.add_argument("--workflow",   required=True, help="Workflow ID (maps to configs/<id>.yaml)")
    run_parser.add_argument("--config-dir", default="./configs", help="Config directory (default: ./configs)")
    run_parser.add_argument("--show-trace", action="store_true", help="Print trace events")
    run_parser.add_argument("--show-history", action="store_true", help="Print message history")

    # --- list-patterns command ---
    lp_parser = subparsers.add_parser("list-patterns", help="List registered patterns")

    # --- list-tools command ---
    lt_parser = subparsers.add_parser("list-tools", help="List tools in a workflow config")
    lt_parser.add_argument("--workflow",   required=True, help="Workflow ID")
    lt_parser.add_argument("--config-dir", default="./configs", help="Config directory")

    args = parser.parse_args()

    if args.command == "run":
        cmd_run(args)
    elif args.command == "list-patterns":
        cmd_list_patterns(args)
    elif args.command == "list-tools":
        cmd_list_tools(args)


if __name__ == "__main__":
    main()
