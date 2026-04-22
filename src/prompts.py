CURATE_PROMPT = """You are an intelligence analyst curating GenAI news for AIA Singapore, a major APAC life insurance company.

Context: AIA Singapore cares deeply about (a) what AI is doing in Singapore's financial sector —
banks like {sg_banks} and competitor insurers {competitors} — (b) MAS/IMDA/GovTech regulation
signals, and (c) developer tools and models relevant to building insurance AI products.
ALWAYS keep Singapore/APAC financial-sector stories even if they lack global buzz.

You receive a JSON list of raw news items. For each item decide:

1. Is it on-topic and recent (last {days} days)? If not, add to "dropped".
2. Which of these 9 categories fits best:
   - "models": new model releases, API updates, pricing changes, SDK launches, structured output,
     tool use announcements from any AI vendor (OpenAI, Anthropic, Google, Meta, Mistral, xAI, open source)
   - "frameworks": developer frameworks, agent orchestration libraries, RAG tools, eval frameworks,
     inference engines, fine-tuning interfaces, embedding models, open-source AI tooling
   - "security": prompt injection, jailbreaks, model exploits, agent hijacking, supply chain attacks,
     data leakage, tool misuse, AI red teaming, MCP/tool calling security issues
   - "research": academic papers, benchmark studies, hallucination research, model evaluation,
     reasoning studies, RAG quality research (not product announcements)
   - "enterprise": AI deployment case studies, production success or failure stories, AI ROI reports,
     enterprise AI strategy, lessons from pilots, AI in specific verticals (including Singapore banks
     and non-insurer enterprises)
   - "regulatory": MAS guidance, IMDA, GovTech, EU AI Act, NIST AI RMF, model governance,
     explainability, auditability, data residency, responsible AI, financial-sector AI compliance
   - "business": corporate strategy, funding rounds, M&A, product launches, market analysis,
     vendor competition, enterprise adoption announcements (not technical tooling)
   - "insurtech": insurance-specific AI — competitor insurer announcements ({competitors}),
     underwriting/claims/fraud AI, life insurance digital transformation, Singapore/APAC insurer news,
     AIA-relevant deployments. ALSO place Singapore bank AI stories here if insurance-adjacent.
   - "emerging": novel AI architectures, new reasoning paradigms, mental models, concepts not yet
     in mainstream tooling (compound AI, test-time compute, memory architectures, etc.)

3. DROP (add to "dropped") items matching any of:
   - Generic commentary with no specific announcement ("AI will change everything" opinion pieces)
   - Duplicate story already represented by a higher-quality item in the batch
   - Older than {days} days
   NOTE: Do NOT drop Singapore/APAC financial-sector items even if they seem niche.

4. For kept items assign:
   - `insurance_score` (1=low, 2=medium, 3=high) for relevance to a life insurer in APAC.
     Score 3 if it directly concerns Singapore banks/insurers, MAS, or APAC insurance AI.
   - `competitor=true` if mentions any of: {competitors}
   - `regulatory=true` if mentions any of: {regulators}, or APAC financial regulation
   - `action_signal`: "act" = AIA-applicable NOW, decision needed in 2 weeks;
     "watch" = developing story, revisit in 30 days; "aware" = background context
   - `sentiment` (only when insurance_score >= 2): "opportunity" | "risk" | "neutral"
   - `quality_score`: 3 = original source with technical depth; 2 = derivative but adds analysis;
     1 = low-depth summary (keep only if no quality_score=2+ coverage of same story)

Output STRICT JSON ONLY, no prose, no code fences:
{{
  "models": [{{"title":"...","url":"...","summary":"...","source":"...","published_at":"...","insurance_score":1,"competitor":false,"regulatory":false,"action_signal":"aware","sentiment":"neutral","quality_score":2}}],
  "frameworks": [...],
  "security": [...],
  "research": [...],
  "enterprise": [...],
  "regulatory": [...],
  "business": [...],
  "insurtech": [...],
  "emerging": [...],
  "dropped": [{{"url":"...","reason":"..."}}]
}}

Input items (with buzz_scores):
{items_json}

Buzz scores (url -> count):
{buzz_json}
"""

DUAL_TLDR_PROMPT = """Write the opening TL;DR for a daily AI intelligence brief for AIA Singapore.

Produce two separate ranked lists of exactly 3 items each:

FOR YOUR CEO: Prioritise regulatory signals, competitor threats ({competitors}), strategic
opportunities, items with action_signal="act", insurance_score=3, regulatory=true, competitor=true.
Frame each bullet for a business executive — decisions, risks, opportunities. No jargon.
End each bullet with a bracketed action: [Escalate to Legal], [Brief CTO], [Monitor], [Competitive response needed], etc.

FOR YOUR CTO: Prioritise security disclosures, model releases, new frameworks, eval results,
items in categories models/security/frameworks/emerging, action_signal in act/watch.
Frame each bullet for a senior engineer — specific about what changed and why it matters now.
End each bullet with a bracketed decision: [Try today], [Evaluate this sprint], [Alert team], [Watch], etc.

Each bullet = one sentence max 25 words + bracketed action. Different items in each list where
possible; overlap only if the item is genuinely critical for both.

Return JSON only:
{{"ceo":[{{"bullet":"...","url":"...","action":"..."}},...],
  "cto":[{{"bullet":"...","url":"...","action":"..."}},...] }}

Items: {items_json}
"""

MODEL_RELEASE_PROMPT = """For each model/API release item below, extract a structured capability card.
If a field is not mentioned in the article, output null — do NOT infer or hallucinate.

- vendor: releasing company (max 2 words)
- model_name: model or feature name
- key_upgrade: single most important new capability (max 10 words)
- context_window: token count if mentioned, else null
- pricing_change: e.g. "-15% input tokens" if mentioned, else null
- aia_use_case: one specific AIA application this enables or improves (max 15 words)

Return JSON array: [{{"url":"...","vendor":"...","model_name":"...","key_upgrade":"...","context_window":null,"pricing_change":null,"aia_use_case":"..."}}]

Items: {items_json}
"""

SECURITY_BRIEF_PROMPT = """You are an AI security analyst briefing a CISO at a major life insurer.

For each security item below:
- severity: "critical"|"high"|"medium"|"info"
  critical = active exploit, no patch, production AI systems affected NOW
  high = known vulnerability with PoC, patch or workaround available
  medium = theoretical attack, requires specific conditions
  info = awareness, trend signal, no immediate exploit
- attack_vector: one phrase (e.g. "prompt injection via tool output", "supply chain via fine-tune data")
- affected_systems: which AI stacks are affected (max 10 words)
- mitigation: one sentence — what defenders do right now
- aia_relevance: "direct"|"adjacent"|"watch"
  direct = affects Vertex AI, LLM APIs, RAG pipelines, agent frameworks AIA likely uses
  adjacent = affects vendors or ecosystems AIA depends on
  watch = general trend, no immediate AIA exposure

Return JSON array: [{{"url":"...","severity":"...","attack_vector":"...","affected_systems":"...","mitigation":"...","aia_relevance":"..."}}]

Items: {items_json}
"""

FRAMEWORK_BRIEF_PROMPT = """You are a senior AI engineer evaluating frameworks for an enterprise AI team at AIA Singapore.

For each framework/tool item:
- replaces_or_extends: existing tool this replaces or extends (e.g. "LangChain", "FAISS") or null if novel
- primary_language: "Python"|"TypeScript"|"Rust"|"Go"|"other"
- use_case: one phrase (e.g. "RAG pipeline", "agent orchestration", "LLM serving")
- adoption_signal: "production-ready"|"early-beta"|"research-prototype"
- try_today: "yes"|"maybe"|"wait"
  yes = stable API, install in minutes, good docs
  maybe = promising but rough edges or breaking changes likely
  wait = pre-alpha or academic only
- aia_fit: one phrase — how this maps to an AIA engineering use case (underwriting/claims/compliance/customer service)

Return JSON array: [{{"url":"...","replaces_or_extends":null,"primary_language":"...","use_case":"...","adoption_signal":"...","try_today":"...","aia_fit":"..."}}]

Items: {items_json}
"""

EVAL_BRIEF_PROMPT = """For each evaluation, benchmark, or research study item below:
- models_tested: list of models compared (max 5 names) or null
- task_type: one phrase (e.g. "enterprise QA", "coding accuracy", "agent reliability")
- key_finding: the single most important result (max 20 words)
- winner: best-performing approach or model if clear, else null
- aia_takeaway: what AIA's AI team should do differently based on this (max 20 words)

If the item is a paper (not a benchmark), extract: concept_name, what_it_does (1 sentence), practical_horizon ("now"|"6-12 months"|"2-3 years").

Return JSON array: [{{"url":"...","item_type":"benchmark|paper","models_tested":null,"task_type":"...","key_finding":"...","winner":null,"aia_takeaway":"...","concept_name":null,"what_it_does":null,"practical_horizon":null}}]

Items: {items_json}
"""

ENTERPRISE_BRIEF_PROMPT = """For each enterprise AI story below, classify and extract a structured brief.

- story_type: "success"|"failure"|"pilot"|"strategy"
- industry: e.g. "insurance", "banking", "healthcare", "retail"
- use_case: one phrase — the specific AI application
- outcome: one sentence — what happened and the measurable result if stated
- replicable_at_aia: "yes"|"maybe"|"no"
- lesson: one sentence — the single most transferable learning (for failures, frame constructively)

Return JSON array: [{{"url":"...","story_type":"...","industry":"...","use_case":"...","outcome":"...","replicable_at_aia":"...","lesson":"..."}}]

Items: {items_json}
"""

REGULATORY_BRIEF_PROMPT = """You are a regulatory intelligence analyst for AIA Singapore.

For each regulatory item:
- instrument_type: "guidance"|"consultation"|"directive"|"speech"|"policy"|"other"
- jurisdiction: e.g. "Singapore/MAS", "EU/AI Act", "HK/HKMA", "Global/IOSCO"
- deadline: ISO date string if a compliance deadline is mentioned, else null
- aia_action: what AIA's compliance/risk team should do (max 20 words)
- urgency: "act"|"watch"|"aware"
  act = deadline within 60 days OR MAS directive requiring response
  watch = consultation open, AIA should track or respond
  aware = informational, no immediate action

Return JSON array: [{{"url":"...","instrument_type":"...","jurisdiction":"...","deadline":null,"aia_action":"...","urgency":"..."}}]

Items: {items_json}
"""

EMERGING_CONCEPT_PROMPT = """For each emerging concept item below, write for two audiences simultaneously.

- concept_name: short label for the idea (max 5 words)
- tech_explanation: 2 sentences — mechanism and key insight for a senior AI engineer
- business_implication: 1 sentence — what this means for an insurance executive; no jargon
- maturity: "theoretical"|"research"|"early-adoption"|"mainstream"
- horizon: "now"|"6-12 months"|"2-3 years"

Return JSON array: [{{"url":"...","concept_name":"...","tech_explanation":"...","business_implication":"...","maturity":"...","horizon":"..."}}]

Items: {items_json}
"""

BOARDROOM_PROMPT = """For each business item below, write ONE sentence (max 30 words) framed as a boardroom takeaway for a life-insurance executive. Focus on strategic implication, not description.

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
