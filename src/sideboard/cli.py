"""CLI entry point for sideboard — argparse-based dispatcher."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from sideboard import __version__


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments and return a Namespace.

    When no subcommand is given, ``args.command`` defaults to ``"play"``.
    """
    parser = argparse.ArgumentParser(
        prog="sideboard",
        description="Chess in your terminal. Play against Chesster while your coding agent thinks.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"sideboard {__version__}",
    )
    parser.add_argument(
        "--difficulty",
        choices=["casual", "club", "shark"],
        default="club",
        help="Engine difficulty (default: club)",
    )

    color_group = parser.add_mutually_exclusive_group()
    color_group.add_argument(
        "--white",
        dest="color",
        action="store_const",
        const="white",
        default=None,
        help="Play as white",
    )
    color_group.add_argument(
        "--black",
        dest="color",
        action="store_const",
        const="black",
        help="Play as black",
    )

    subparsers = parser.add_subparsers(dest="command")

    # resume
    subparsers.add_parser("resume", help="Resume the last saved game")

    # stats
    subparsers.add_parser("stats", help="Show win/loss/draw statistics")

    # export
    subparsers.add_parser("export", help="Export last game to PGN on stdout")

    # install-skill
    subparsers.add_parser(
        "install-skill",
        help="Install SKILL.md into ~/.claude/commands/sideboard.md",
    )

    # bridge
    bridge_parser = subparsers.add_parser(
        "bridge",
        help="Skill bridge for Claude Code integration",
    )
    bridge_parser.add_argument(
        "bridge_command",
        nargs="?",
        default="state",
        help="Bridge sub-command (default: state)",
    )
    bridge_parser.add_argument(
        "--bridge-difficulty",
        default=None,
        help="Difficulty override for bridge",
    )
    bridge_parser.add_argument(
        "--bridge-color",
        default=None,
        help="Color override for bridge",
    )
    bridge_parser.add_argument(
        "move_arg",
        nargs="?",
        default=None,
        help="Move argument for bridge (UCI or SAN)",
    )

    args = parser.parse_args(argv)

    # Default command when no subcommand is provided
    if args.command is None:
        args.command = "play"

    return args


def _install_skill() -> None:
    """Copy the bundled SKILL.md into ~/.claude/commands/sideboard.md."""
    skill_text: str | None = None

    # Try importlib.resources first (works when installed as a package)
    try:
        import importlib.resources as pkg_resources

        try:
            # Python 3.9+ path
            ref = pkg_resources.files("sideboard") / "data" / "SKILL.md"
            skill_text = ref.read_text(encoding="utf-8")
        except (AttributeError, FileNotFoundError, TypeError):
            pass
    except ImportError:
        pass

    # Fall back to sibling data/ directory
    if skill_text is None:
        fallback = Path(__file__).parent / "data" / "SKILL.md"
        if fallback.exists():
            skill_text = fallback.read_text(encoding="utf-8")

    if skill_text is None:
        print("Error: SKILL.md not found in package data.", file=sys.stderr)
        sys.exit(1)

    dest = Path.home() / ".claude" / "commands" / "sideboard.md"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(skill_text, encoding="utf-8")
    print(f"Installed skill to {dest}")


def main(argv: Sequence[str] | None = None) -> None:
    """Main entry point — parse args and dispatch to the appropriate handler."""
    args = parse_args(argv)

    if args.command == "play":
        from sideboard.game import run_game

        run_game(difficulty=args.difficulty, player_color=args.color)

    elif args.command == "resume":
        from sideboard.game import run_game

        run_game(resume=True)

    elif args.command == "stats":
        from rich.console import Console

        from sideboard.state import load_stats

        console = Console()
        stats = load_stats()
        console.print(f"[bold]Sideboard Stats[/bold]")
        console.print(f"  Games played : {stats.games_played}")
        console.print(f"  Wins         : {stats.total_wins}")
        console.print(f"  Losses       : {stats.total_losses}")
        console.print(f"  Draws        : {stats.total_draws}")
        if stats.by_difficulty:
            console.print("\n[bold]By difficulty:[/bold]")
            for diff, counts in stats.by_difficulty.items():
                console.print(
                    f"  {diff:8s}  W:{counts.get('wins', 0)} "
                    f"L:{counts.get('losses', 0)} D:{counts.get('draws', 0)}"
                )
        if stats.last_played:
            console.print(f"\n  Last played  : {stats.last_played}")

    elif args.command == "export":
        from sideboard.state import export_pgn, load_game

        state = load_game()
        if state is None:
            print("No saved game found.", file=sys.stderr)
            sys.exit(1)
        board = state.to_board()
        print(export_pgn(board, difficulty=state.difficulty, player_color=state.player_color))

    elif args.command == "install-skill":
        _install_skill()

    elif args.command == "bridge":
        from sideboard.skill_bridge import handle_bridge

        handle_bridge(args)

    else:
        print(f"Unknown command: {args.command}", file=sys.stderr)
        sys.exit(1)
