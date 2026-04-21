CURATE_PROMPT = """You are an intelligence analyst curating GenAI news for AIA Singapore, a major APAC life insurance company.

You receive a JSON list of raw news items. For each item decide:
1. Is it on-topic and recent (last 7 days)? If not, drop it.
2. Which category does it fit best:
   - "business": corporate moves, funding, product launches, enterprise adoption
   - "technical": models, tools, open-source, engineering
   - "research": academic papers, benchmarks, algorithmic breakthroughs
   - "insurtech": insurance-specific AI, MAS/IMDA/regulatory, competitor insurer news
3. Assign `insurance_score` (1=low, 2=medium, 3=high) for relevance to a life insurer in APAC.
   - 3 = directly applicable: claims automation, underwriting AI, competitor announcements, MAS/IMDA AI guidance
   - 2 = adjacent: enterprise GenAI platforms, compliance AI, customer-service AI in finserv
   - 1 = general GenAI news without insurance angle
4. Set `competitor=true` if the item mentions any of: {competitors}
5. Set `regulatory=true` if it mentions any of: {regulators}, or APAC financial regulation
6. Set `action_signal`:
   - "act" = competitive threat or AIA-applicable tool available NOW; decision needed within 2 weeks
   - "watch" = developing story; revisit in 30 days
   - "aware" = background context; no decision needed
7. Set `sentiment` (only meaningful when insurance_score >= 2; otherwise "neutral"):
   - "opportunity" = new capability AIA could exploit
   - "risk" = competitor move or regulatory shift AIA must respond to
   - "neutral" = informational

Output STRICT JSON ONLY, no prose, no code fences:
{{
  "business": [{{"title": "...", "url": "...", "summary": "...", "source": "...", "published_at": "...", "insurance_score": 1, "competitor": false, "regulatory": false, "action_signal": "aware", "sentiment": "neutral"}}],
  "technical": [...],
  "research": [...],
  "insurtech": [...]
}}

Input items (with buzz_scores showing cross-source appearances):
{items_json}

Buzz scores (url -> count):
{buzz_json}
"""

TLDR_PROMPT = """Pick the top 3 must-read items for an AIA Singapore audience (mix of business and tech leaders). Prefer items with high insurance_score, high buzz_score, or competitor/regulatory flags, or action_signal="act".

Return a JSON list of exactly 3 objects, each a single-sentence bullet referencing one item by its URL:
[{{"bullet": "...", "url": "..."}}, ...]

Items: {items_json}
"""

BOARDROOM_PROMPT = """For each business item below, write ONE sentence (max 30 words) framed as a boardroom takeaway for a life-insurance executive. Focus on strategic implication, not description.

Return JSON array only: [{{"url": "...", "sentence": "..."}}, ...]

Items: {items_json}
"""

BUILD_AT_AIA_PROMPT = """For each technical item below, write ONE sentence (max 30 words) mapping the technology to a concrete AIA use case. Domains: underwriting, claims automation, fraud detection, customer service, marketing personalisation, compliance, agent assist. Be specific.

Return JSON array only: [{{"url": "...", "sentence": "..."}}, ...]

Items: {items_json}
"""

PAPER_EXPLAINER_PROMPT = """Pick the single most important research paper below. Write a 4-sentence plain-English explainer for a non-academic technical audience. Avoid jargon. Explain: what problem, what approach, what result, why it matters for insurance or enterprise AI.

Return JSON only: {{"url": "...", "title": "...", "explainer": "..."}}

Papers: {items_json}
"""

WEEK_IN_REVIEW_PROMPT = """In one paragraph (max 100 words), summarize the single most important GenAI development this week for an APAC life insurer. Highlight the "so what" — what should AIA leadership notice, monitor, or act on?

This week's curated items: {items_json}
"""

EDITORS_TAKE_PROMPT = """You are writing the opening 2-3 sentences of a daily AI intelligence brief for AIA Singapore's leadership team.

Be direct, opinionated, and specific. Highlight the single most important theme of the day and what it means for a life insurer in APAC. Write with authority — not "it seems" or "it appears". Use active voice. No bullet points. No hedging.

Today's curated items: {items_json}
"""

COMPETITIVE_HEATMAP_PROMPT = """From the news items below, extract mentions of these AI labs: OpenAI, Google/DeepMind, Anthropic, Meta/LLaMA, Mistral, xAI/Grok.

For each lab mentioned, write ONE sentence (max 12 words) on what they shipped or announced this week.
For labs NOT mentioned in the news, output null — do NOT hallucinate.

Return JSON only, no prose:
{{"openai": "..." or null, "google": "..." or null, "anthropic": "..." or null, "meta": "..." or null, "mistral": "..." or null, "xai": "..." or null}}

Items: {items_json}
"""

STEAL_THIS_WEEK_PROMPT = """You are an AI innovation advisor to AIA Singapore. Based on this week's AI developments below, identify the single most actionable product idea AIA could build or pilot in the next quarter.

Be specific — name the product, not a generic category. Output JSON only:
{{
  "title": "product name (max 8 words)",
  "what": "one sentence — exactly what to build",
  "why_now": "one sentence — why this week's news makes it timely",
  "domain": "underwriting | claims | marketing | compliance | customer_service | agent_tools",
  "effort": "days | weeks | months",
  "team": "which AIA team would own this",
  "confidence": "high | medium | low"
}}

Items: {items_json}
"""

MONTHLY_DIGEST_PROMPT = """You are writing the monthly GenAI digest for AIA Singapore (life insurance).

Below are the top 10 GenAI stories from the past 30 days, ranked by cross-source buzz x AIA insurance relevance. Write:
1. An opening paragraph (max 80 words) on the single defining theme for APAC insurers this month.
2. For each of the 10 items, a one-sentence rationale (max 25 words) on why it mattered.

Output STRICT JSON:
{{
  "opening": "...",
  "rationales": [{{"url": "...", "sentence": "..."}}, ...]
}}

Items (with scores):
{items_json}
"""
