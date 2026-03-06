"""Demonstrate each CompactionMethod: none, middle_out_truncate, summarize.

Shows how budget and message size control which method runs:
- none: tokens ≤ budget
- middle_out_truncate: over budget, overage (tokens/budget) < 1.5
- summarize: overage ≥ 1.5 and > 4 non-system messages

Uses ContextCompactor directly (no agent) so results are deterministic.
Run: python -m examples.11_context.context_compaction_methods_demo
"""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

from syrin.context import CompactionMethod, ContextCompactor
from syrin.context.counter import get_counter

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def _make_messages(
    n_user_assistant_pairs: int, chars_per_message: int = 80
) -> list[dict[str, str]]:
    """Build a message list: system + n user/assistant pairs with ~chars_per_message each."""
    msgs: list[dict[str, str]] = [{"role": "system", "content": "You are helpful."}]
    for i in range(n_user_assistant_pairs):
        msgs.append(
            {
                "role": "user",
                "content": f"User message {i}. " + "x" * max(0, chars_per_message - 20),
            }
        )
        msgs.append(
            {
                "role": "assistant",
                "content": f"Assistant reply {i}. " + "y" * max(0, chars_per_message - 22),
            }
        )
    return msgs


def main() -> None:
    print("=" * 60)
    print("COMPACTION METHODS — none, middle_out_truncate, summarize")
    print("=" * 60)
    print("\nAll methods: ", [m.value for m in CompactionMethod])
    print()

    counter = get_counter()
    compactor = ContextCompactor()

    # -------------------------------------------------------------------------
    # 1. CompactionMethod.NONE — messages already fit
    # -------------------------------------------------------------------------
    print("1. CompactionMethod.NONE")
    print("   When: tokens_before ≤ budget (no compaction needed).")
    messages_small = _make_messages(2, 30)
    tokens_small = counter.count_messages(messages_small).total
    budget_large = tokens_small * 2
    result = compactor.compact(messages_small, budget_large)
    assert result.method == CompactionMethod.NONE, result.method
    print(f"   Messages: {len(messages_small)}, tokens={tokens_small}, budget={budget_large}")
    print(f"   → method = {result.method!s}")
    print()

    # -------------------------------------------------------------------------
    # 2. CompactionMethod.MIDDLE_OUT_TRUNCATE — over budget, overage < 1.5
    # -------------------------------------------------------------------------
    print("2. CompactionMethod.MIDDLE_OUT_TRUNCATE")
    print("   When: over budget and overage (tokens/budget) < 1.5 → keep start/end, drop middle.")
    messages_medium = _make_messages(12, 60)
    tokens_medium = counter.count_messages(messages_medium).total
    budget_medium = int(tokens_medium / 1.3)  # overage = 1.3 < 1.5
    result = compactor.compact(messages_medium, budget_medium)
    assert result.method == CompactionMethod.MIDDLE_OUT_TRUNCATE, result.method
    print(
        f"   Messages: {len(messages_medium)}, tokens={tokens_medium}, budget={budget_medium} (overage={tokens_medium / budget_medium:.2f})"
    )
    print(f"   → method = {result.method!s}, tokens_after = {result.tokens_after}")
    print()

    # -------------------------------------------------------------------------
    # 3. CompactionMethod.SUMMARIZE — overage ≥ 1.5 and > 4 non-system messages
    # -------------------------------------------------------------------------
    print("3. CompactionMethod.SUMMARIZE")
    print("   When: overage ≥ 1.5 and > 4 non-system messages → summarize older, keep last 4.")
    messages_many = _make_messages(10, 50)  # 1 system + 20 non-system
    tokens_many = counter.count_messages(messages_many).total
    budget_small = int(tokens_many / 2.0)  # overage = 2.0 ≥ 1.5
    result = compactor.compact(messages_many, budget_small)
    assert result.method == CompactionMethod.SUMMARIZE, result.method
    print(
        f"   Messages: {len(messages_many)}, tokens={tokens_many}, budget={budget_small} (overage={tokens_many / budget_small:.2f})"
    )
    print(f"   → method = {result.method!s}, tokens_after = {result.tokens_after}")
    print()

    print("=" * 60)
    print(
        "Tweak: budget (smaller → more compaction), message count/length (more → higher overage)."
    )
    print("Summarize needs overage ≥ 1.5 and > 4 non-system messages.")
    print("=" * 60)


if __name__ == "__main__":
    main()
