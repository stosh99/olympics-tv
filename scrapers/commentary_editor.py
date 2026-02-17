#!/usr/bin/env python3
"""
Commentary Editor - Two-agent editing pipeline:
  1. Fact-checker: validates claims against results + sources
  2. Prose editor: style, flow, tone polish

Replaces the single-editor approach for better accuracy.
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
# AGENT 1: FACT-CHECKER
# ============================================================

FACTCHECK_SYSTEM = """You are a sports fact-checker for Olympic coverage. Your ONLY job is factual accuracy. Do not touch prose style, tone, or structure.

You will receive:
- RESULTS: verified data from the official Olympics database (ground truth)
- SOURCES: the articles the writer used
- COMMENTARY: the written piece to check

For EVERY factual claim in the commentary, classify it:

1. VERIFIED — matches the results data exactly. No action needed.
2. SOURCED — not in the results data, but explicitly stated in one of the source articles. KEEP these. They add valuable context (historical facts, quotes, background, records from prior Games, etc.)
3. CONTRADICTS — conflicts with the results data. FIX these. The results data is always correct.
4. UNSOURCED — not in results data AND not in any source article. REMOVE these. The writer hallucinated.

CRITICAL RULES:
- A claim does NOT need to be in the results data to be valid. If a credible source article states it, KEEP it.
- Only flag CONTRADICTS when the claim directly conflicts with a number, name, position, or medal in the results.
- Quotes must appear in the source articles. Any quote not in the sources is UNSOURCED.
- Do not flag reasonable inferences (e.g., "powered through" is color, not a factual claim).
- Historical context from source articles (e.g., "first Dutch gold since 2014") is SOURCED, not UNSOURCED.

OUTPUT FORMAT:
List each factual issue found, then output the corrected commentary.

ISSUES:
- [CONTRADICTS] "Kok finished in 36.50" → Results show 36.49. Fixed.
- [UNSOURCED] "This was her childhood dream" → Not in any source. Removed.
- [SOURCED-OK] "first Dutch medals in the event since 2014" → Confirmed in Source 2 (Olympics.com). Kept.

If no issues: "ISSUES: None found"

Then:
---
[Full commentary with only CONTRADICTS and UNSOURCED items fixed. SOURCED items preserved.]"""


# ============================================================
# AGENT 2: PROSE EDITOR
# ============================================================

PROSE_SYSTEM = """You are a prose editor for Olympic sports journalism. Your ONLY job is improving the writing quality. Do not change any facts, names, times, or claims.

YOUR TASKS:
- Fix awkward phrasing or clunky sentences
- Improve transitions between paragraphs
- Eliminate repetitive sentence structures (e.g., too many sentences starting with "The...")
- Tighten wordy passages
- Ensure consistent tone (engaged, professional sports journalism)
- Fix grammar and punctuation

CRITICAL — FIRST PARAGRAPH RULE:
- The first paragraph is a standalone card summary shown on the website before users click "read more"
- It MUST make complete sense on its own, without any following text
- Keep it self-contained: WHO won, key storyline, WHY it matters (3-5 sentences)
- Do not add references to "below" or "as we'll see" — it must stand alone

DO NOT:
- Add or remove factual claims
- Change any names, times, scores, or positions
- Alter quotes in any way
- Significantly change the length (stay within ~10% of original)
- Restructure the piece (keep the same paragraph order and flow)

OUTPUT:
Just output the polished commentary. No commentary about your edits.
If the prose is already clean, output it unchanged."""


# ============================================================
# SHARED HELPERS
# ============================================================

def _call_claude(system_prompt, user_prompt, label="Agent"):
    """Shared Claude API call."""
    if not ANTHROPIC_API_KEY or ANTHROPIC_API_KEY == 'your_key_here':
        logger.error("ANTHROPIC_API_KEY not configured")
        return None

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=2048,
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


def format_results_for_editor(resolved_data):
    """Format results data for prompts."""
    lines = []
    for r in resolved_data['results']:
        medal = ""
        if r.get('medal_type'):
            medal_map = {'ME_GOLD': 'Gold', 'ME_SILVER': 'Silver', 'ME_BRONZE': 'Bronze'}
            medal = f" [{medal_map.get(r['medal_type'], r['medal_type'])}]"
        pos = f"#{r['position']}" if r.get('position') else (r.get('wlt', ''))
        lines.append(f"{pos} {r['name']} ({r['noc']}) - {r.get('mark', '')}{medal}")
    return '\n'.join(lines)


def format_sources_summary(sources_metadata):
    """Brief summary of sources for editor context."""
    if not sources_metadata:
        return "No external sources were available."
    lines = []
    for i, s in enumerate(sources_metadata, 1):
        lines.append(f"Source {i} ({s['domain']}): {s['title']}")
    return '\n'.join(lines)


# ============================================================
# AGENT FUNCTIONS
# ============================================================

def fact_check(commentary, resolved_data, sources_metadata, consolidated_text=""):
    """Agent 1: Fact-check commentary against results + sources."""
    results_text = format_results_for_editor(resolved_data)
    sources_summary = format_sources_summary(sources_metadata)

    # Give fact-checker the full source articles if available
    source_section = consolidated_text if consolidated_text else sources_summary

    prompt = f"""Fact-check this Olympic commentary.

=== RESULTS (ground truth from official database) ===
{results_text}

=== SOURCE ARTICLES THE WRITER USED ===
{source_section}

=== COMMENTARY TO FACT-CHECK ===
{commentary}

Check every factual claim now. Classify each as VERIFIED, SOURCED, CONTRADICTS, or UNSOURCED."""

    logger.info("  Running fact-checker...")
    result = _call_claude(FACTCHECK_SYSTEM, prompt, "Fact-checker")
    if not result:
        return None

    full_output = result['content']
    
    # Parse issues and corrected text
    issues = ""
    factchecked_text = full_output
    
    if '---' in full_output:
        parts = full_output.split('---', 1)
        issues = parts[0].strip()
        factchecked_text = parts[1].strip()

    return {
        'factchecked_content': factchecked_text,
        'issues': issues,
        'usage': result['usage'],
    }


def prose_edit(commentary):
    """Agent 2: Polish prose without touching facts."""
    prompt = f"""Polish the prose of this Olympic commentary. Do not change any facts.

{commentary}"""

    logger.info("  Running prose editor...")
    result = _call_claude(PROSE_SYSTEM, prompt, "Prose editor")
    if not result:
        return None

    return {
        'polished_content': result['content'],
        'usage': result['usage'],
    }


# ============================================================
# MAIN ENTRY POINT (called by pipeline_orchestrator)
# ============================================================

def edit_commentary(commentary, resolved_data, sources_metadata, consolidated_text=""):
    """
    Two-pass editing pipeline:
      1. Fact-checker validates claims
      2. Prose editor polishes writing
    
    Returns same shape as old single-editor for orchestrator compatibility:
    {proofed_content, corrections, usage, estimated_cost}
    """
    logger.info("Starting two-agent edit pipeline...")

    # Pass 1: Fact-check
    fc_result = fact_check(commentary, resolved_data, sources_metadata, consolidated_text)
    if not fc_result:
        logger.warning("Fact-checker failed, falling back to original")
        return {
            'proofed_content': commentary,
            'corrections': 'Fact-checker failed',
            'usage': {},
            'estimated_cost': 0,
        }

    # Pass 2: Prose edit (on fact-checked version)
    pe_result = prose_edit(fc_result['factchecked_content'])
    if not pe_result:
        logger.warning("Prose editor failed, using fact-checked version only")
        return {
            'proofed_content': fc_result['factchecked_content'],
            'corrections': fc_result['issues'],
            'usage': fc_result['usage'],
            'estimated_cost': fc_result['usage'].get('estimated_cost', 0),
        }

    # Combine costs
    total_cost = (
        fc_result['usage'].get('estimated_cost', 0) + 
        pe_result['usage'].get('estimated_cost', 0)
    )

    total_usage = {
        'fact_checker': fc_result['usage'],
        'prose_editor': pe_result['usage'],
        'total_input_tokens': (
            fc_result['usage'].get('input_tokens', 0) + 
            pe_result['usage'].get('input_tokens', 0)
        ),
        'total_output_tokens': (
            fc_result['usage'].get('output_tokens', 0) + 
            pe_result['usage'].get('output_tokens', 0)
        ),
    }

    logger.info(f"  Edit pipeline complete. Total edit cost: ${total_cost:.4f}")
    if fc_result['issues']:
        logger.info(f"  Fact-check issues: {fc_result['issues'][:200]}")

    return {
        'proofed_content': pe_result['polished_content'],
        'corrections': fc_result['issues'],
        'usage': total_usage,
        'estimated_cost': round(total_cost, 4),
    }


if __name__ == '__main__':
    print("Commentary Editor - Two-agent pipeline")
    print("  Agent 1: Fact-checker (validates claims)")
    print("  Agent 2: Prose editor (polishes writing)")
    print("Normally called via pipeline_orchestrator.py")
