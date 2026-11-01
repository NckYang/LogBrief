"""Deterministic compression with lossless protected regions and a hard text budget."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import re
import math
from typing import Protocol

from .prompts import DEFAULT_QUESTION, SYSTEM_PROMPT, user_prompt
from .tokens import TokenCounter

ANSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]|\x1b\][^\x07]*(?:\x07|\x1b\\)")
TIMESTAMP = re.compile(
    r"^\s*\[?(?:\d{4}[-/]\d{2}[-/]\d{2}[T ])?"
    r"\d{2}:\d{2}:\d{2}(?:[.,]\d+)?(?:Z|[+-]\d{2}:?\d{2})?\]?\s*"
)
LEVEL = re.compile(
    r"^(?:[-|:]\s*)?(?:\[(?:DEBUG|INFO|WARNING|WARN|ERROR|CRITICAL|FATAL)\]"
    r"|(?:DEBUG|INFO|WARNING|WARN|ERROR|CRITICAL|FATAL)\b)"
    r"(?:[ \t]*[-|:][ \t]?|[ \t])?"
)
ERROR = re.compile(
    r"\b(?:ERROR|CRITICAL|FATAL)\b|"
    r"\b[A-Za-z_][\w.]*(?:Error|Exception):|"
    r"\b(?:Exception|KeyboardInterrupt|SystemExit):|Traceback \(most recent call last\):"
)
WARNING = re.compile(r"\b(?:WARNING|WARN)\b|\b(?:[A-Za-z_]\w*)?Warning:")
SEVERITY = re.compile(r"^\s*(?:[-|:]\s*)?\[?(DEBUG|INFO|WARNING|WARN|ERROR|CRITICAL|FATAL)\b", re.I)
EXCEPTION_LINE = re.compile(r"^\s*(?:[\w.]+(?:Error|Exception)|Exception|KeyboardInterrupt|SystemExit):")
METRIC = re.compile(r"\b(loss|val_loss|accuracy|val_accuracy|grad_norm|learning_rate|lr)\s*[=:]\s*([-+]?(?:\d+(?:\.\d*)?(?:e[-+]?\d+)?|nan|inf(?:inity)?))\b", re.I)
CONFIG = re.compile(r"\b(config\w*|endpoint|host|port|database|columns?|schema|dataset|batch_size|learning_rate|timeout|workers|input|device)\b", re.I)


def severity(text: str) -> str | None:
    match = SEVERITY.match(TIMESTAMP.sub("", text, count=1))
    return match.group(1).upper() if match else None


def is_error(text: str) -> bool:
    level = severity(text)
    if level is not None:
        return level in {"ERROR", "CRITICAL", "FATAL"}
    return bool(TRACE_START.search(text) or EXCEPTION_LINE.match(text))


def is_warning(text: str) -> bool:
    level = severity(text)
    return level in {"WARN", "WARNING"} if level else bool(re.match(r"^\s*(?:\w+)?Warning:", text))


def salient_records(lines):
    """Explainable candidates, not guaranteed causal evidence or anomaly detection."""
    reasons = {}
    error_words = set(re.findall(r"[a-z_]{3,}", " ".join(
        line.text.lower() for line in lines if is_error(line.text))))
    error_words -= {"error", "failed", "exception", "traceback", "most", "recent", "call", "last"}
    series = {}
    for line in lines:
        if CONFIG.search(line.text) and not is_error(line.text) and not is_warning(line.text):
            words = set(re.findall(r"[a-z_]{3,}", line.text.lower()))
            reasons.setdefault(line.index, []).append(
                "configuration_related_to_error" if words & error_words else "configuration")
        for match in METRIC.finditer(line.text):
            # Keep distinct textual streams apart (e.g. train vs validation / workers).
            template = PROGRESS_COUNTER.sub("<step>", payload(line.text))
            template = METRIC.sub(lambda m: m.group(1).lower() + "=<value>", template)
            series.setdefault((template, match.group(1).lower()), []).append(
                (line.index, float(match.group(2))))
    for (_, name), points in series.items():
        if len(points) < 2:
            continue
        chosen = {points[0][0]: "first", points[-1][0]: "last"}
        finite = [p for p in points if math.isfinite(p[1])]
        if finite:
            chosen[min(finite, key=lambda p: p[1])[0]] = "minimum"
            chosen[max(finite, key=lambda p: p[1])[0]] = "maximum"
        pairs = [(a, b) for a, b in zip(points, points[1:])
                 if math.isfinite(a[1]) and math.isfinite(b[1])]
        if pairs:
            a, b = max(pairs, key=lambda pair: abs(pair[1][1] - pair[0][1]))
            if a[1] != b[1]:
                chosen[a[0]], chosen[b[0]] = "largest_change_before", "largest_change_after"
        for i, value in points:
            if not math.isfinite(value):
                chosen[i] = "nonfinite"
        for i, reason in chosen.items():
            reasons.setdefault(i, []).append(f"metric:{name}:{reason}")
    return reasons
TRACE_START = re.compile(r"(?:Exception Group )?Traceback \(most recent call last\):")
EXCEPTION = re.compile(
    r"^(?:[|+]\s*)?(?:[A-Z]\w*(?:\.[A-Z]\w*)*)(?::.*)?$"
)
PROGRESS_COUNTER = re.compile(
    r"\b(epoch|step|batch|iteration|iter)\s*[:=#]?\s*\d+(?:\s*/\s*\d+)?\b",
    re.IGNORECASE,
)
FRACTION = re.compile(r"\b\d+\s*/\s*\d+\b")
PERCENT = re.compile(r"\b\d+(?:\.\d+)?%")
BAR = re.compile(r"\|[ #=>.\-█▏▎▍▌▋▊▉░▒▓]+\|")
TQDM_TIME = re.compile(r"\[\d+:\d+(?::\d+)?[^\]]*(?:it/s|s/it|<)[^\]]*\]")


class Counter(Protocol):
    name: str

    def count(self, text: str) -> int: ...


class BudgetTooSmall(ValueError):
    """Required evidence is indivisible; callers must raise the budget explicitly."""

    def __init__(self, required: int, budget: int):
        self.required = required
        self.budget = budget
        super().__init__(
            f"Token budget {budget} is too small. At least {required} tokens are "
            "required for all tracebacks, first-error context, prompt and reserve. "
            "Increase --budget; protected evidence was not truncated."
        )


@dataclass(frozen=True)
class Line:
    index: int
    number: int
    part: int
    text: str

    @property
    def ref(self) -> str:
        return f"L{self.number}" + (f".{self.part}" if self.part else "")

    def render(self) -> str:
        return f"[{self.ref}] {self.text}"


@dataclass(frozen=True)
class Item:
    start: int
    priority: int
    kind: str
    text: str
    indices: tuple[int, ...]
    refs: tuple[str, ...]
    mandatory: bool = False


@dataclass
class CompressionResult:
    evidence: str
    system_prompt: str
    user_prompt: str
    stats: dict
    protected_refs: list[str]
    traceback_ranges: list[dict]
    groups: list[dict]
    omitted_refs: list[str]
    selected_refs: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


def parse_lines(text: str) -> list[Line]:
    """Keep physical LF line numbers; CR-only terminal redraws share that number."""
    physical = text.replace("\r\n", "\n").split("\n")
    if physical and physical[-1] == "":
        physical.pop()
    result: list[Line] = []
    for number, raw in enumerate(physical, 1):
        redraws = raw.split("\r")
        for part, content in enumerate(redraws, 1):
            if len(redraws) > 1 and not content:
                continue
            result.append(Line(
                len(result), number, part if len(redraws) > 1 else 0,
                ANSI.sub("", content),
            ))
    return result


def payload(text: str) -> str:
    """Remove only common logging prefixes, not meaningful message numbers."""
    body = TIMESTAMP.sub("", text, count=1)
    return LEVEL.sub("", body, count=1)


def is_log_boundary(text: str) -> bool:
    without_timestamp = TIMESTAMP.sub("", text, count=1)
    return bool(LEVEL.match(without_timestamp) or TIMESTAMP.match(text))


def trace_ranges(lines: list[Line]) -> list[tuple[int, int]]:
    """Conservatively preserve traceback chains, notes and exception groups.

    Tracebacks have no universal end marker. Stop only at a clear new log record
    or progress record; unprefixed trailing text is retained rather than guessed.
    """
    ranges: list[tuple[int, int]] = []
    i = 0
    while i < len(lines):
        if not TRACE_START.search(lines[i].text):
            i += 1
            continue
        start = i
        i += 1
        while i < len(lines):
            body = payload(lines[i].text)
            stripped = body.strip()
            structural = (
                not stripped or body[:1].isspace() or TRACE_START.search(body)
                or stripped.startswith((
                    "File ", "^", "~", "|", "+", "During handling of the above",
                    "The above exception was the direct cause",
                    "[Previous line repeated",
                ))
                or EXCEPTION.fullmatch(stripped)
            )
            if not structural and (
                is_log_boundary(lines[i].text) or progress_key(body) is not None
            ):
                break
            i += 1
        ranges.append((start, i - 1))
    return ranges


def progress_key(text: str) -> str | None:
    body = payload(text)
    if not (
        PROGRESS_COUNTER.search(body)
        or (PERCENT.search(body) and (BAR.search(body) or FRACTION.search(body)))
    ):
        return None
    # Preserve metrics (loss, accuracy, learning rate, etc.) and other numbers.
    key = PROGRESS_COUNTER.sub(lambda m: m.group(1).lower() + " <counter>", body)
    if BAR.search(body) and PERCENT.search(body):
        # Normalize only the fraction directly following the tqdm bar.
        # Paths such as data/12/34.csv and unrelated ratios remain meaningful.
        key = re.sub(
            r"(\|[ #=>.\-█▏▎▍▌▋▊▉░▒▓]+\|)\s*\d+\s*/\s*\d+\b",
            r"\1 <counter>", key,
        )
        key = re.sub(r"\b\d+(?:\.\d+)?%(?=\s*\|)", "<percent>", key)
        key = BAR.sub("|<bar>|", key)
        key = TQDM_TIME.sub("[<timing>]", key)
    return key


def _ranges(indices: set[int]) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    for index in sorted(indices):
        if out and index == out[-1][1] + 1:
            out[-1] = (out[-1][0], index)
        else:
            out.append((index, index))
    return out


def compress_log(
    text: str,
    *,
    token_budget: int = 4000,
    context_lines: int = 3,
    counter: Counter | None = None,
    question: str = DEFAULT_QUESTION,
    message_reserve: int = 32,
) -> CompressionResult:
    if token_budget <= 0 or context_lines < 0 or message_reserve < 0:
        raise ValueError("budget must be positive; context and reserve must be nonnegative")
    if not question.strip():
        raise ValueError("Question must not be empty")
    if not text.strip():
        raise ValueError("Log is empty")
    counter = counter or TokenCounter()
    lines = parse_lines(text)
    traces = trace_ranges(lines)
    trace_indices = {i for a, b in traces for i in range(a, b + 1)}
    first_error = next((line.index for line in lines if is_error(line.text)), None)
    protected = set(trace_indices)
    if first_error is not None:
        protected.update(range(
            max(0, first_error - context_lines),
            min(len(lines), first_error + context_lines + 1),
        ))
    for a, b in traces:
        protected.update(range(
            max(0, a - context_lines), min(len(lines), b + context_lines + 1),
        ))

    salience = salient_records(lines)
    def priority_for(line, default):
        reasons = salience.get(line.index, [])
        if any("nonfinite" in r for r in reasons):
            return max(default, 97)
        if any(r.startswith("metric:") for r in reasons):
            return max(default, 95)
        if "configuration_related_to_error" in reasons:
            return max(default, 94)
        return max(default, 85) if reasons else default

    items: list[Item] = []
    for a, b in _ranges(protected):
        chunk = lines[a:b + 1]
        items.append(Item(
            a, 100, "protected", "\n".join(line.render() for line in chunk),
            tuple(range(a, b + 1)), tuple(line.ref for line in chunk), True,
        ))

    buckets: dict[tuple[str, str], list[Line]] = {}
    ordinary: list[Line] = []
    for line in lines:
        if line.index in trace_indices:
            continue
        if is_warning(line.text):
            key = ("warning", payload(line.text))
        elif not is_error(line.text) and (key_text := progress_key(line.text)) is not None:
            key = ("progress", key_text)
        else:
            ordinary.append(line)
            continue
        buckets.setdefault(key, []).append(line)

    groups: list[dict] = []
    for (kind, _), occurrences in buckets.items():
        optional = [line for line in occurrences if line.index not in protected]
        if len(occurrences) > 1:
            groups.append({
                "kind": kind,
                "count": len(occurrences),
                "refs": [line.ref for line in occurrences],
                "first_text": occurrences[0].text,
                "last_text": occurrences[-1].text,
                "included": False,
            })
        if not optional:
            continue
        if len(occurrences) == 1:
            rendered = occurrences[0].render()
        else:
            first, last = occurrences[0], occurrences[-1]
            rendered = (
                f"[{kind.upper()} x{len(occurrences)}; first={first.ref}; "
                f"last={last.ref}; includes any exact excerpts]\n{first.render()}"
            )
            if kind == "progress" and payload(first.text) != payload(last.text):
                rendered += "\n" + last.render()
        items.append(Item(
            optional[0].index, max(priority_for(line, 80 if kind == "warning" else 30) for line in occurrences),
            kind, rendered, tuple(line.index for line in occurrences),
            tuple(line.ref for line in occurrences),
        ))

    for line in ordinary:
        if line.index in protected:
            continue
        priority = 90 if is_error(line.text) else (
            60 if line.index < 3 else 50 if line.index >= len(lines) - 3 else 10
        )
        items.append(Item(
            line.index, priority_for(line, priority), "line", line.render(), (line.index,), (line.ref,),
        ))

    def render(selected: list[Item]) -> str:
        return "\n\n".join(item.text for item in sorted(selected, key=lambda x: x.start))

    def prompt_count(evidence: str) -> int:
        return (counter.count(SYSTEM_PROMPT)
                + counter.count(user_prompt(evidence, question)) + message_reserve)

    selected = [item for item in items if item.mandatory]
    required = prompt_count(render(selected))
    if required > token_budget:
        raise BudgetTooSmall(required, token_budget)

    # Additive estimates avoid repeatedly tokenizing the entire prompt on huge logs.
    # A final exact recount enforces the selected encoding's budget.
    estimated = required
    optional_items = sorted(
        (item for item in items if not item.mandatory),
        key=lambda item: (-item.priority, item.start),
    )
    for item in optional_items:
        cost = counter.count("\n\n" + item.text)
        if estimated + cost <= token_budget:
            selected.append(item)
            estimated += cost

    evidence = render(selected)
    while prompt_count(evidence) > token_budget:
        removable = [item for item in selected if not item.mandatory]
        if not removable:
            raise BudgetTooSmall(prompt_count(evidence), token_budget)
        selected.remove(min(removable, key=lambda item: (item.priority, -item.start)))
        evidence = render(selected)

    represented = {i for item in selected for i in item.indices}
    selected_group_refs = {
        item.refs for item in selected if item.kind in {"warning", "progress"}
    }
    for group in groups:
        group["included"] = tuple(group["refs"]) in selected_group_refs
        group["exact_excerpt_count"] = sum(
            line.ref in group["refs"] for line in lines if line.index in protected
        )

    full_evidence = "\n".join(line.render() for line in lines)
    full_tokens = prompt_count(full_evidence)
    used_tokens = prompt_count(evidence)
    return CompressionResult(
        evidence=evidence,
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt(evidence, question),
        stats={
            "physical_lines": max((line.number for line in lines), default=0),
            "records": len(lines),
            "represented_records": len(represented),
            "omitted_records": len(lines) - len(represented),
            "protected_records": len(protected),
            "first_error_ref": lines[first_error].ref if first_error is not None else None,
            "traceback_blocks": len(traces),
            "repeat_groups": len(groups),
            "salient_candidates": [{"ref": lines[i].ref, "reasons": reasons,
                                     "included": i in represented}
                                    for i, reasons in sorted(salience.items())],
            "encoding": counter.name,
            "token_budget": token_budget,
            "message_reserve": message_reserve,
            "required_prompt_tokens": required,
            "original_log_tokens": counter.count(text),
            "compressed_evidence_tokens": counter.count(evidence),
            "full_prompt_tokens": full_tokens,
            "compressed_prompt_tokens": used_tokens,
            "prompt_reduction_percent": round((1 - used_tokens / full_tokens) * 100, 2),
            "budget_scope": "system + user text tokens in selected encoding + message reserve",
        },
        protected_refs=[line.ref for line in lines if line.index in protected],
        traceback_ranges=[
            {"start": lines[a].ref, "end": lines[b].ref,
             "refs": [line.ref for line in lines[a:b + 1]]}
            for a, b in traces
        ],
        groups=groups,
        omitted_refs=[line.ref for line in lines if line.index not in represented],
        selected_refs=[line.ref for line in lines if line.index in represented],
    )
