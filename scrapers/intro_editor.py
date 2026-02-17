#!/usr/bin/env python3
"""
Intro Editor - Two-agent editing pipeline for pre-event previews:
  1. Source-checker: validates claims against source articles (no results to check)
  2. Prose editor: style, flow, tone polish
"""

from dotenv import load_dotenv
load_dotenv()

import os
import json
import logging
import anthropic

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
MODEL = "claude-sonnet-4-20250514"


# ============================================================
# AGENT 1: SOURCE-CHECKER
# ============================================================

SOURCECHECK_SYSTEM = """You are a fact-checker for Olympic preview articles. Your ONLY job is verifying that claims are grounded in the source articles provided.

You will receive:
- SOURCES: the articles the writer used for context
- PREVIEW: the written piece to check

For EVERY factual claim in the preview, classify it:

1. SOURCED — explicitly stated in one of the source articles. KEEP.
2. COMMON KNOWLEDGE — widely known Olympic facts (e.g., event format, venue location). KEEP.
3. UNSOURCED — not in any source article and not common knowledge. REMOVE.

CRITICAL RULES:
- Rankings, world records, and season results MUST be sourced. Don't assume they're common knowledge.
- Quotes must appear in the source articles verbatim. Any quote not in sources is UNSOURCED.
- Do not flag reasonable preview language (e.g., "will be looking to" is framing, not a factual claim).
- Predictions framed as opinions or expectations are fine if sourced (e.g., "widely considered the favorite").

OUTPUT FORMAT:
List each issue, then output corrected preview.

ISSUES:
- [UNSOURCED] "Smith holds the world record at 1:23.45" → Not in any source. Removed.
- [SOURCED-OK] "defending champion from 2022 Beijing" → Confirmed in Source 1. Kept.

If no issues: "ISSUES: None found"

Then:
---
[Full preview with only UNSOURCED items fixed.]"""


# ============================================================
# AGENT 2: PROSE EDITOR (same as post-event)
# ============================================================

PROSE_SYSTEM = """You are a prose editor for Olympic sports journalism. Your ONLY job is improving the writing quality. Do not change any facts, names, or claims.

YOUR TASKS:
- Fix awkward phrasing or clunky sentences
- Improve transitions between paragraphs
- Eliminate repetitive sentence structures
- Tighten wordy passages
- Ensure consistent tone (engaged, anticipatory sports journalism)
- Fix grammar and punctuation

CRITICAL — FIRST PARAGRAPH RULE:
- The first paragraph is a standalone card summary shown on the website before users click "read more"
- It MUST make complete sense on its own, without any following text
- Keep it self-contained: WHAT event, KEY storyline, WHY watch (3-5 sentences)
- Do not add references to "below" or "as we'll see" — it must stand alone

DO NOT:
- Add or remove factual claims
- Change any names, times, scores, or rankings
- Alter quotes in any way
- Significantly change the length (stay within ~10% of original)
- Restructure the piece

OUTPUT:
Just output the polished preview. No commentary about your edits."""


# ============================================================
# SHARED HELPERS
# ============================================================

def _call_claude(system_prompt, user_prompt, label="Agent"):
    if not ANTHROPIC_API_KEY or ANTHROPIC_API_KEY == 'your_key_here':
        logger.error("ANTHROPIC_API_KEY not configured")
        return None

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=1536,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )
        content = response.content[0].text
        usage = {
            'input_tokens': response.usage.input_tokens,
            'output_tokens': response.usage.output_tokens,
        }
        cost = (usage['input_tokens'] * 3 + usage['output_tokens'] * 15) / 1_000_000
        usage['estimated_cost'] = round(cost, 4)
        logger.info(f"  {label}: {usage['output_tokens']} tokens, ~${cost:.4f}")
        return {'content': content, 'usage': usage}
    except Exception as e:
        logger.error(f"{label} API call failed: {e}")
        return None


def source_check(preview, consolidated_text):
    """Agent 1: Check preview claims against source articles."""
    prompt = f"""Check this Olympic preview against its source articles.

=== SOURCE ARTICLES THE WRITER USED ===
{consolidated_text}

=== PREVIEW TO CHECK ===
{preview}

Check every factual claim now. Classify each as SOURCED, COMMON KNOWLEDGE, or UNSOURCED."""

    logger.info("  Running source-checker...")
    result = _call_claude(SOURCECHECK_SYSTEM, prompt, "Source-checker")
    if not result:
        return None

    full_output = result['content']
    issues = ""
    checked_text = full_output

    if '---' in full_output:
        parts = full_output.split('---', 1)
        issues = parts[0].strip()
        checked_text = parts[1].strip()

    return {
        'checked_content': checked_text,
        'issues': issues,
        'usage': result['usage'],
    }


def prose_edit(preview):
    """Agent 2: Polish prose."""
    prompt = f"""Polish the prose of this Olympic preview. Do not change any facts.

{preview}"""

    logger.info("  Running prose editor...")
    result = _call_claude(PROSE_SYSTEM, prompt, "Prose editor")
    if not result:
        return None
    return {'polished_content': result['content'], 'usage': result['usage']}


# ============================================================
# MAIN ENTRY POINT
# ============================================================

def edit_intro(preview, consolidated_text=""):
    """
    Two-pass editing for pre-event previews.
    Returns: {proofed_content, corrections, usage, estimated_cost}
    """
    logger.info("Starting two-agent intro edit pipeline...")

    # Pass 1: Source-check
    sc_result = source_check(preview, consolidated_text)
    if not sc_result:
        logger.warning("Source-checker failed, falling back to original")
        return {
            'proofed_content': preview,
            'corrections': 'Source-checker failed',
            'usage': {},
            'estimated_cost': 0,
        }

    # Pass 2: Prose edit
    pe_result = prose_edit(sc_result['checked_content'])
    if not pe_result:
        logger.warning("Prose editor failed, using source-checked version")
        return {
            'proofed_content': sc_result['checked_content'],
            'corrections': sc_result['issues'],
            'usage': sc_result['usage'],
            'estimated_cost': sc_result['usage'].get('estimated_cost', 0),
        }

    total_cost = (
        sc_result['usage'].get('estimated_cost', 0) +
        pe_result['usage'].get('estimated_cost', 0)
    )
    total_usage = {
        'source_checker': sc_result['usage'],
        'prose_editor': pe_result['usage'],
        'total_input_tokens': (
            sc_result['usage'].get('input_tokens', 0) +
            pe_result['usage'].get('input_tokens', 0)
        ),
        'total_output_tokens': (
            sc_result['usage'].get('output_tokens', 0) +
            pe_result['usage'].get('output_tokens', 0)
        ),
    }

    logger.info(f"  Edit pipeline complete. Total cost: ${total_cost:.4f}")
    if sc_result['issues']:
        logger.info(f"  Source-check issues: {sc_result['issues'][:200]}")

    return {
        'proofed_content': pe_result['polished_content'],
        'corrections': sc_result['issues'],
        'usage': total_usage,
        'estimated_cost': round(total_cost, 4),
    }


if __name__ == '__main__':
    print("Intro Editor - Two-agent pipeline for pre-event previews")
    print("  Agent 1: Source-checker (validates claims against articles)")
    print("  Agent 2: Prose editor (polishes writing)")
    print("Normally called via intro_orchestrator.py")
