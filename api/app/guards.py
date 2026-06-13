"""Guard composition — a single generic anti-drift guard.

Demonstrates fi-core's drift-pack capability without baking any product policy.
``build_guards`` returns one ``antidrift_guard`` over the default English packs
(catches "as an AI" / assistant-tone leaks) with the generic reinforcement. On
a break the Runner re-runs the turn (RetryPolicy) with the reinforcement
appended, so the persona stays in character.

SEAM: layer in more packs (``packs.DEFAULT_ES``, ``packs.MARKDOWN_DRIFT``,
``packs.STAGE_DIRECTIONS``, …) or add a ``plan_guard`` for pre-execution policy
when your product needs it. Boundary-clean: composes via ``fi_runner.packs`` —
we never import fi_core directly.
"""

from __future__ import annotations

from fi_runner import antidrift_guard, packs


def build_guards() -> list:
    """Build the anti-drift guard chain. One generic English-pack guard by
    default — extend per your persona's needs."""
    return [
        antidrift_guard(
            break_patterns=list(packs.DEFAULT_EN),
            reinforcement=packs.GENERIC_REINFORCEMENT,
        )
    ]
