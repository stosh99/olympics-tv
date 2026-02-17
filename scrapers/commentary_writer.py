#!/usr/bin/env python3
"""
Commentary Writer - Takes consolidated source file and writes
post-event commentary using Claude API.
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
PROMPT_VERSION = "v3"

SYSTEM_PROMPT = """You are a sports journalist writing post-event commentary for the 2026 Milan-Cortina Winter Olympics. Your audience is English-speaking fans, primarily American but with international appeal.

WRITING STYLE:
- Engaging, narrative-driven sports journalism
- Lead with the story, not just the results
- Weave in human interest angles from the source material
- Include relevant context (records broken, rivalries, comebacks)
- Mention how the event affects medal standings or national narratives when relevant
- Reference specific details from sources to add color and depth
- Keep a neutral but enthusiastic tone - celebrate great performances from all nations
- If US athletes competed, include their performance naturally (don't force it if irrelevant)

STRUCTURE:
- FIRST PARAGRAPH IS CRITICAL: Write a self-contained 3-5 sentence summary paragraph that works on its own as a card preview. It should capture WHO won, the key storyline/drama, and WHY it matters - compelling enough to make someone click "read more". Include the winner's name, country, and the core narrative hook. This paragraph must make sense without any of the text that follows it.
- Main narrative (3-5 paragraphs covering the key storylines in depth)
- Brief context section if relevant (what this means for the Games, upcoming events)
- Length: 400-700 words total

CRITICAL RULES:
- The RESULTS section is GROUND TRUTH. Never contradict it. If a source conflicts with the results, trust the results.
- Only state facts that are supported by the results data or the source articles
- Do not invent quotes - only use quotes that appear in source articles
- If sources are thin, write a shorter but accurate piece rather than padding with speculation
- Attribute notable claims to their source (e.g., "according to NBC Sports...")
"""


USER_PROMPT_TEMPLATE = """Write post-event commentary for the following Olympic event. Use the results as ground truth and the source articles for narrative color and context.

{consolidated_text}

Write the commentary now. Output ONLY the commentary text, no headers or metadata."""


def write_commentary(consolidated_text):
    """
    Send consolidated source file to Claude, get back commentary.
    Returns dict with content, model, token usage.
    """
    if not ANTHROPIC_API_KEY or ANTHROPIC_API_KEY == 'your_key_here':
        logger.error("ANTHROPIC_API_KEY not configured")
        return None

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    user_prompt = USER_PROMPT_TEMPLATE.format(consolidated_text=consolidated_text)

    logger.info(f"Sending to Claude ({MODEL})...")
    logger.info(f"  Input size: ~{len(consolidated_text) // 4} tokens")

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": user_prompt}
            ]
        )

        content = response.content[0].text
        usage = {
            'input_tokens': response.usage.input_tokens,
            'output_tokens': response.usage.output_tokens,
            'model': MODEL,
            'prompt_version': PROMPT_VERSION,
        }

        # Rough cost calc (Sonnet pricing: $3/M input, $15/M output)
        cost = (usage['input_tokens'] * 3 + usage['output_tokens'] * 15) / 1_000_000
        usage['estimated_cost'] = round(cost, 4)

        logger.info(f"  Response: {usage['output_tokens']} tokens, ~${cost:.4f}")

        return {
            'content': content,
            'usage': usage,
        }
    except Exception as e:
        logger.error(f"Claude API call failed: {e}")
        return None


if __name__ == '__main__':
    import sys

    # Read a consolidated file from disk for testing
    if len(sys.argv) < 2:
        print("Usage: python commentary_writer.py <consolidated_file.txt>")
        sys.exit(1)

    filepath = sys.argv[1]
    with open(filepath, 'r', encoding='utf-8') as f:
        consolidated = f.read()

    result = write_commentary(consolidated)
    if not result:
        print("Writing failed")
        sys.exit(1)

    print(f"\n{'='*60}")
    print("COMMENTARY:")
    print(f"{'='*60}")
    print(result['content'])
    print(f"\n{'='*60}")
    print(f"Tokens: {result['usage']['input_tokens']} in / {result['usage']['output_tokens']} out")
    print(f"Cost: ${result['usage']['estimated_cost']}")
