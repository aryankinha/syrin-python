"""PromptClassifier evaluation — task detection, alignment, and limitations.

Answers:
1. Which model is good for that prompt (task type → router picks model)
2. Does it align with system prompt? (Current: NO - classifier never sees system prompt)
3. Developer optimization: cost, context window, fallbacks
4. Can it distinguish higher vs lower model need? (Current: NO - only task type, not complexity)

Requires: uv sync --extra classifier-embeddings && uv run python -m examples.17_routing.classifier_evaluation
"""

from __future__ import annotations

from syrin.router import PromptClassifier, TaskType

# Diverse prompts + complex stress-test prompts
PROMPTS = [
    # CODE — simple
    ("Implement a quicksort in Python", "CODE"),
    ("Fix the syntax error in line 42", "CODE"),
    ("Write unit tests for this function", "CODE"),
    ("Refactor this into a class", "CODE"),
    ("Create a FastAPI endpoint for /users", "CODE"),
    ("What's wrong with my async/await here?", "CODE"),
    # CODE — complex
    (
        "Given this 500-line legacy C++ module with circular deps, suggest a refactor "
        "to separate concerns and add dependency injection. Include a migration plan.",
        "CODE",
    ),
    (
        "Implement a thread-safe LRU cache with O(1) get/put. Add eviction policy tests.",
        "CODE",
    ),
    (
        "Review this PR: the new auth middleware bypasses rate limiting. Suggest fixes.",
        "CODE",
    ),
    # GENERAL — simple
    ("Hello", "GENERAL"),
    ("What is the capital of France?", "GENERAL"),
    ("Thanks for your help", "GENERAL"),
    ("Can you explain how this works?", "GENERAL"),
    ("Summarize the meeting notes", "GENERAL"),
    ("What time is it?", "GENERAL"),
    # GENERAL — complex
    (
        "I'm building a SaaS product. What are the top 5 compliance considerations "
        "for GDPR and SOC2 when storing user PII? Give a concise checklist.",
        "GENERAL",
    ),
    (
        "What's the difference between eventual consistency and strong consistency "
        "in distributed systems? When would you choose each?",
        "GENERAL",
    ),
    # REASONING — simple
    ("Solve: if x+2=5, what is x?", "REASONING"),
    ("Prove that sqrt(2) is irrational", "REASONING"),
    ("Analyze the logical fallacy in this argument", "REASONING"),
    ("What's the probability of drawing two aces?", "REASONING"),
    ("Compare pros and cons of microservices", "REASONING"),
    # REASONING — complex
    (
        "Given a deck of 52 cards, we draw 5. What's the probability exactly 2 are hearts "
        "and 1 is a face card? Show the combinatorial argument.",
        "REASONING",
    ),
    (
        "Is the following argument valid? If all A are B, and no B are C, then no A are C. "
        "Provide a formal proof or counterexample.",
        "REASONING",
    ),
    # CREATIVE — simple
    ("Write a haiku about coding", "CREATIVE"),
    ("Brainstorm 10 startup names for a pet app", "CREATIVE"),
    ("Compose a short story about a robot", "CREATIVE"),
    # CREATIVE — complex
    (
        "Write a 3-paragraph product launch announcement for an AI-powered code review tool. "
        "Tone: professional but approachable. Include a tagline and CTA.",
        "CREATIVE",
    ),
    # VISION — simple
    ("Describe what you see in this image", "VISION"),
    ("Extract the text from this screenshot", "VISION"),
    ("What objects are in the photo?", "VISION"),
    # VISION — complex
    (
        "This diagram shows our current architecture. Identify bottlenecks, single points "
        "of failure, and suggest a redesign for horizontal scaling. [attached image]",
        "VISION",
    ),
    (
        "OCR the handwritten notes in this scan and structure them as markdown sections.",
        "VISION",
    ),
    # VIDEO
    ("Summarize this video", "VIDEO"),
    ("Transcribe this clip and extract action items", "VIDEO"),
    # PLANNING — simple
    ("Plan a 3-day trip to Tokyo", "PLANNING"),
    ("Break down building an e-commerce site", "PLANNING"),
    ("Create a migration strategy from monolith to microservices", "PLANNING"),
    # PLANNING — complex
    (
        "We're moving from Jenkins to GitHub Actions. Outline a phased rollout: parallel "
        "runs, validation, cutover. Include rollback steps.",
        "PLANNING",
    ),
    (
        "Design a 6-month roadmap to transition our monolith to microservices. "
        "Include risk mitigation and team capacity assumptions.",
        "PLANNING",
    ),
    # TRANSLATION
    ("Translate 'hello world' to Japanese", "TRANSLATION"),
    ("Convert this to Spanish", "TRANSLATION"),
    (
        "Localize these 50 UI strings for zh-CN. Preserve placeholders like {count}.",
        "TRANSLATION",
    ),
    # EDGE / AMBIGUOUS
    ("Fix this", "AMBIGUOUS"),
    ("Help me", "AMBIGUOUS"),
    ("Do the thing", "AMBIGUOUS"),
    ("Explain the code above", "AMBIGUOUS"),
    ("Write a Python script to translate French to English", "AMBIGUOUS"),
    (
        "Can you help? I have a bug. It crashes when I run it. The stack trace mentions "
        "null. Not sure where to start.",
        "AMBIGUOUS",
    ),
]


def main() -> None:
    classifier = PromptClassifier(
        min_confidence=0.6,
        low_confidence_fallback=TaskType.GENERAL,
    )
    classifier.warmup()

    print("=" * 70)
    print("PromptClassifier evaluation")
    print("=" * 70)
    print()

    correct = 0
    total = 0
    low_confidence_count = 0

    for prompt, expected in PROMPTS:
        task, conf = classifier.classify(prompt)
        expected_task = expected if expected != "AMBIGUOUS" else None
        match = expected_task and task.value == expected_task.lower()
        if expected_task:
            total += 1
            if match:
                correct += 1
        if conf < 0.6:
            low_confidence_count += 1

        status = "✓" if match else ("?" if expected == "AMBIGUOUS" else "✗")
        conf_str = f"{conf:.2f}"
        if conf < 0.6:
            conf_str += " (→ fallback)"
        print(f"  {status} {prompt[:55]!r}")
        print(f"      -> {task.value} (conf={conf_str})  expected={expected}")

    print()
    print("=" * 70)
    print("Summary")
    print("=" * 70)
    if total > 0:
        print(f"  Correct (non-ambiguous): {correct}/{total} ({100 * correct / total:.0f}%)")
    print(f"  Low-confidence fallbacks (< 0.6): {low_confidence_count}")
    print()

    print("=" * 70)
    print("PromptClassifier features")
    print("=" * 70)
    print("""
  DOES:
  - Embed user prompt with sentence-transformers
  - Return (TaskType, confidence). Router maps TaskType → Model
  - classify_extended(): complexity_score, complexity_tier (LOW/MEDIUM/HIGH)
  - classify_extended(): system_alignment_score when system_prompt provided
  - LRU cache (enable_cache, max_cache_size) for production
  - When complexity_tier=HIGH, router prefers highest-priority model

  Developer optimization:
  - Custom examples: PromptClassifier(examples={TaskType.CODE: [...]})
  - min_confidence + low_confidence_fallback
  - RoutingConfig: routing_mode, budget thresholds
  - routing_rule_callback for manual overrides
  - Production: enable_cache=True, classify_extended(prompt, system_prompt)
""")


if __name__ == "__main__":
    main()
