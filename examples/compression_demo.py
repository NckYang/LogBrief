"""Run the bundled compression example."""
from pathlib import Path

from logbrief.cli import main


def run() -> int:
    root = Path(__file__).resolve().parents[1]
    output = root / 'outputs/compressed.txt'
    report = root / 'outputs/report.json'
    status = main(['compress', str(root / 'examples/training.log'), '--budget', '1200',
                   '--output', str(output), '--json', str(report)])
    if status:
        return status
    print(output.read_text(encoding='utf-8'))
    print(f'Compressed log: {output}')
    print(f'Detailed report: {report}')
    return 0


if __name__ == '__main__':
    raise SystemExit(run())
