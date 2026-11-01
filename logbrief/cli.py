"""Local, key-free log compression command."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .compressor import BudgetTooSmall, compress_log
from .prompts import DEFAULT_QUESTION
from .tokens import TokenCounter


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog='logbrief', description=__doc__)
    commands = root.add_subparsers(dest='command', required=True)
    command = commands.add_parser('compress', help='Compress a UTF-8 log without calling a model')
    command.add_argument('input', type=Path, help='UTF-8 log file')
    command.add_argument('--budget', type=int, default=4000,
                         help='system + user text token budget including message reserve')
    command.add_argument('--context', type=int, default=3,
                         help='protected records before/after the first error and tracebacks')
    command.add_argument('--encoding', default='cl100k_base', help='explicit tiktoken encoding')
    command.add_argument('--message-reserve', type=int, default=32,
                         help='allowance for message framing')
    command.add_argument('--question', default=DEFAULT_QUESTION)
    command.add_argument('--output', '-o', type=Path, help='write compressed evidence to a file')
    command.add_argument('--json', dest='json_output', type=Path,
                         help='save stats, prepared prompts, groups and source references')
    return root


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text + '\n', encoding='utf-8')


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        paths = [p.resolve() for p in (args.input, args.output, args.json_output) if p is not None]
        if len(paths) != len(set(paths)):
            raise ValueError('Input, output and JSON report must use different paths')
        with args.input.open('r', encoding='utf-8-sig', newline='') as handle:
            text = handle.read()
        result = compress_log(text, token_budget=args.budget, context_lines=args.context,
                              counter=TokenCounter(args.encoding), question=args.question,
                              message_reserve=args.message_reserve)
        if args.output:
            _write(args.output, result.evidence)
        else:
            print(result.evidence)
        if args.json_output:
            _write(args.json_output, json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        stats = result.stats
        print(f"Prompt tokens: {stats['full_prompt_tokens']} -> "
              f"{stats['compressed_prompt_tokens']} / {stats['token_budget']} "
              f"({stats['encoding']}; reserve={stats['message_reserve']}). "
              f"Protected records: {stats['protected_records']}; omitted: {stats['omitted_records']}.",
              file=sys.stderr)
        return 0
    except BudgetTooSmall as exc:
        print(f'Budget error: {exc}', file=sys.stderr)
        return 2
    except (OSError, ValueError) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
