#!/usr/bin/env python3
"""
Intro Writer - Takes consolidated source material and writes
pre-event introduction/preview using Claude API.
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
PROMPT_VERSION = "v1"

SYSTEM_PROMPT = """You are a sports journalist writing a pre-event preview for the 2026 Milan-Cortina Winter Olympics. Your audience is English-speaking fans, primarily American but with international appeal.

WRITING STYLE:
- Build anticipation and excitement for the upcoming event
- Focus on storylines, rivalries, and athletes to watch
- Include relevant context: defending champions, world rankings, recent form, records at stake
- If US athletes are competing, mention their prospects naturally
- Keep a neutral but enthusiastic tone
- Ground claims in the source material — don't invent storylines

STRUCTURE:
- FIRST PARAGRAPH IS CRITICAL: Write a self-contained 3-5 sentence preview that works on its own as a card teaser. It should capture WHAT event is happening, the KEY storyline/rivalry to watch, and WHY fans should tune in. This paragraph must make sense without any of the text that follows it.
- Key athletes/teams to watch (2-3 paragraphs covering favorites, dark horses, US angle)
- What makes this event interesting (format, history, venue, weather factors)
- Length: 300-500 words total (shorter than post-event — previews should be punchy)

CRITICAL RULES:
- Only state facts supported by the source articles
- Do not predict winners — frame as "favored" or "contender" based on sources
- Do not invent quotes — only use quotes from source articles
- If sources are thin, write a shorter but accurate piece rather than speculating
- Include the scheduled date/time if available in the event context
- Attribute notable claims to their source
"""


USER_PROMPT_TEMPLATE = """Write a pre-event preview for the following upcoming Olympic event. Use the source articles for storylines and context.

{consolidated_text}

Write the preview now. Output ONLY the preview text, no headers or metadata."""


def write_intro(consolidated_text):
    """
    Send consolidated source material to Claude, get back pre-event intro.
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
            max_tokens=1536,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}]
        )

        content = response.content[0].text
        usage = {
            'input_tokens': response.usage.input_tokens,
            'output_tokens': response.usage.output_tokens,
            'model': MODEL,
            'prompt_version': PROMPT_VERSION,
        }

        cost = (usage['input_tokens'] * 3 + usage['output_tokens'] * 15) / 1_000_000
        usage['estimated_cost'] = round(cost, 4)

        logger.info(f"  Response: {usage['output_tokens']} tokens, ~${cost:.4f}")
        return {'content': content, 'usage': usage}
    except Exception as e:
        logger.error(f"Claude API call failed: {e}")
        return None


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print("Usage: python intro_writer.py <consolidated_file.txt>")
        sys.exit(1)
    with open(sys.argv[1], 'r', encoding='utf-8') as f:
        consolidated = f.read()
    result = write_intro(consolidated)
    if not result:
        print("Writing failed")
        sys.exit(1)
    print(f"\n{'='*60}")
    print("PREVIEW:")
    print(f"{'='*60}")
    print(result['content'])
    print(f"\nTokens: {result['usage']['input_tokens']} in / {result['usage']['output_tokens']} out")
    print(f"Cost: ${result['usage']['estimated_cost']}")
