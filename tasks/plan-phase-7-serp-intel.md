# Phase 7 — SerpAPI Intelligence Expansion + 14-Bucket Coverage

## Goal

Add SerpAPI as a ninth source and expand the curated intelligence surface from 4 generic categories to **9 high-signal developer + business buckets**. Each bucket has purpose-built query packs, a dedicated rendering format, and audience-split output so tech readers and business readers each see content shaped for their decision-making context.

**Done looks like:** running `python -m src.main --days 2` produces a report with section coverage across Model Releases, Security, Frameworks, Evals, Enterprise Stories, Regulatory, and Emerging Concepts — with noise filtered out, severity-rated security items, capability-unlock model cards, and a CEO/CTO split TL;DR.

---

## The 9 Intelligence Categories

Mapped from the 14 developer intelligence buckets. Consolidation rationale in parentheses.

| # | Category key | Developer buckets covered | Primary audience |
|---|---|---|---|
| 1 | `models` | Model releases, API/SDK changes, pricing (buckets 1, 10) | Tech + Business |
| 2 | `frameworks` | Frameworks, RAG, agentic systems, open source, inference/perf (buckets 2, 6, 7, 11) | Tech |
| 3 | `security` | Security, safety, agent hijacking, supply chain (bucket 3) | Tech + Risk |
| 4 | `research` | Benchmarks, evals, breakthroughs, new concepts (buckets 4, 9, 14) | Tech + Strategy |
| 5 | `enterprise` | Case studies, failure stories, production lessons (buckets 12, 13) | Business + Tech |
| 6 | `regulatory` | MAS, EU AI Act, NIST, governance, compliance (bucket 8) | Business + Legal |
| 7 | `business` | Funding, M&A, product launches, strategy (existing) | Business |
| 8 | `insurtech` | Insurance-specific AI, AIA relevance (existing) | Both |
| 9 | `emerging` | Novel paradigms, mental models, research-to-practice bridge (bucket 14 depth) | Tech + Strategy |

`technical` (old category) is retired — replaced by the more precise `models`, `frameworks`, `research`. Items that were `technical` now route to one of those three.

---

## Noise Filter (new)

The `CURATE_PROMPT` gains an explicit `drop_reason` escape hatch. The LLM is instructed to **exclude** — not categorize — items that match the following patterns:

```
DROP if any of these are true:
- Generic commentary with no specific announcement ("AI will change everything")
- Thin opinion piece, no technical substance (< 3 concrete facts)
- Clickbait benchmark summary with no methodology link
- Vendor press release repeated verbatim across 3+ sources with no new information
- Older than {days} days based on published_at
Output these as a separate "dropped" list for audit, not in any category.
```

Items not dropped get a `quality_score: 1 | 2 | 3`:
- 3 = original source, technical depth, concrete announcement or finding
- 2 = derivative reporting but adds context or analysis
- 1 = low-depth summary, include only if no higher-quality coverage of the same story exists

---

## SerpAPI Query Packs (expanded to 10 packs)

```python
SERP_QUERY_PACKS: dict[str, list[str]] = {
    # Bucket 1 + 10: Model releases + Dev experience
    "model_releases": [
        "new AI model released 2025",
        "Claude GPT Gemini Llama model launch",
        "LLM context window pricing update 2025",
        "AI API structured output tool use release",
        "frontier model benchmark release 2025",
    ],
    # Bucket 2 + 6 + 7 + 11: Frameworks, RAG, agents, open source
    "frameworks_tooling": [
        "new AI agent framework released 2025",
        "new RAG framework vector database retrieval",
        "LangGraph LlamaIndex DSPy CrewAI update",
        "new open source LLM tool released",
        "AI orchestration evaluation framework 2025",
    ],
    # Bucket 3: Security
    "ai_security": [
        "AI security vulnerability latest news",
        "LLM prompt injection jailbreak attack 2025",
        "AI agent supply chain exploit",
        "MCP tool calling security risk",
        "generative AI red team security disclosure",
    ],
    # Bucket 4: Evals and benchmarks
    "evals_benchmarks": [
        "LLM benchmark evaluation study 2025",
        "AI hallucination measurement research",
        "RAG retrieval quality evaluation",
        "agent reliability benchmark results",
        "model reasoning evaluation new study",
    ],
    # Bucket 5: Inference, cost, perf
    "inference_perf": [
        "LLM inference latency optimization 2025",
        "AI model quantization distillation production",
        "small language model performance cost",
        "GPU AI inference cost reduction",
        "LLM token caching routing optimization",
    ],
    # Bucket 8: Regulation
    "mas_regulatory": [
        "MAS AI regulation guidance 2025",
        "Monetary Authority Singapore generative AI",
        "EU AI Act financial services implementation",
        "NIST AI risk management framework update",
        "APAC financial AI governance compliance",
    ],
    # Buckets 12 + 13: Enterprise + Failure stories
    "enterprise_stories": [
        "enterprise AI deployment case study 2025",
        "AI production failure hallucination incident",
        "bank insurer AI rollout lesson learned",
        "agentic AI enterprise production problem",
        "generative AI ROI enterprise result",
    ],
    # Claude / Anthropic dedicated
    "claude_anthropic": [
        "Claude Anthropic news announcement 2025",
        "Anthropic model safety research release",
        "Claude enterprise API feature update",
        "Anthropic Constitutional AI update",
    ],
    # Bucket 9 + 14: Research breakthroughs + new concepts
    "emerging_concepts": [
        "new AI architecture concept research 2025",
        "agentic AI paradigm memory reasoning new",
        "test time compute scaling method",
        "compound AI system approach research",
        "multimodal LLM new technique 2025",
    ],
    # General AI (catch-all for business + strategy)
    "general_ai": [
        "generative AI enterprise strategy 2025",
        "AI startup funding investment round",
        "AI in insurance fintech deployment 2025",
        "AI regulation policy APAC update",
    ],
}
```

**Total: 10 packs × 5 queries × 8 results = up to 400 raw items** before dedup. After dedup and the 25-item curate cap, expect 20–30 items in the final report.

---

## New State Fields

### `NewsItem` additions
```python
quality_score: int   # 1 | 2 | 3 — signal quality (3=high)
severity: str        # "critical"|"high"|"medium"|"info" — security items only
topic_pack: str      # which SERP query pack sourced this item
```

### `AgentState` addition
```python
serp_news: List[NewsItem]
```

### `CategorizedNews` expansion
```python
class CategorizedNews(TypedDict, total=False):
    business: List[NewsItem]
    models: List[NewsItem]       # NEW
    frameworks: List[NewsItem]   # NEW
    security: List[NewsItem]     # NEW
    research: List[NewsItem]
    enterprise: List[NewsItem]   # NEW
    regulatory: List[NewsItem]   # NEW
    insurtech: List[NewsItem]
    emerging: List[NewsItem]     # NEW
```

---

## New Report Sections — Rendered Format Per Audience

### ⚡ For Your CEO / For Your CTO (replaces single TL;DR)

Two parallel 3-bullet panels. CEO bullets use business language (risk, opportunity, decision). CTO bullets use engineering language (specific tool, concrete change, measurable improvement).

```
## ⚡ For Your CEO — Today's 3 Must-Knows
- [🔴 Act] MAS has opened consultation on GenAI model governance...  [→]
- [📈] OpenAI's new batch pricing cuts GenAI project budgets by...  [→]
- [⚠️] Prudential piloting AI underwriting in APAC...  [→]

## ⚡ For Your CTO — Today's 3 Must-Knows
- [🔴 Act] Critical prompt injection in enterprise LLM assistants...  [→]
- [🔵] Claude 3.7 adds 200k context with native tool streaming...  [→]
- [✅ Try] New RAG reranker cuts retrieval noise by 35% vs BM25...  [→]
```

---

### 🚀 Model Releases — What Just Became Possible

**Format: capability-unlock card**

Each model release gets a structured card rather than a prose bullet:

```
### Claude 3.7 Sonnet — Anthropic
| Spec | Value |
|---|---|
| Context | 200k tokens |
| Key upgrade | Native tool streaming, improved coding |
| Pricing vs prior | -15% input, same output |
| AIA use case | Claims document review (200k = full policy) |

[Release notes →](url) · [API changelog →](url)
```

The LLM fills `key_upgrade`, `aia_use_case`, `pricing_change` from the item text. Fields it cannot extract are omitted (no hallucination).

**Signal:** "What can I build today that I couldn't build last week?"

---

### 🔐 Security Threat Intel

**Format: CVSS-inspired severity card**

Items sorted by severity (critical → high → medium → info). Each card:

```
🔴 CRITICAL  **[Prompt injection bypass in enterprise agent pipelines](url)**
Attack vector: system-prompt override via user-controlled tool output
Affected: LangGraph, CrewAI agents using unrestricted tool schemas  
Mitigation: sandbox tool outputs; never interpolate tool results into system prompt
AIA relevance: DIRECT — affects any agent using external data retrieval
```

Followed by a **"This Week in Attacks"** one-liner aggregated from the briefs:
> *4 AI security incidents this week — prompt injection (×2), tool misuse (×1), data leakage (×1)*

---

### 🧰 Framework Watch

**Format: comparison row + adoption signal**

```
**[FrameworkName](url)** `v2.1` — agent orchestration
↳ Replaces: LangChain LCEL · Language: Python · Stars: 8.2k (+1.4k this week)
↳ Adoption: ✅ Production-ready · Try today: YES
↳ AIA fit: Multi-step claims workflow automation
```

Adoption signal key:
- ✅ Production-ready — stable API, active maintainers, good docs
- ⏳ Early beta — promising, breaking changes likely
- 🔬 Research prototype — interesting, not for prod

---

### 📊 Evals & Benchmarks — What's Actually Better?

**Format: scorecard summary**

```
**[New RAG benchmark shows hybrid retrieval +35% vs vector-only](url)**
↳ Models tested: GPT-4o, Claude 3.5, Gemini 1.5
↳ Task: Enterprise QA on financial documents  
↳ Winner: BM25 + dense hybrid with cross-encoder reranker
↳ Takeaway for AIA: Switch retrieval stack before next underwriting RAG build
```

Items with `quality_score < 3` (thin benchmark summaries) are collapsed into a brief "Also noted" list at the bottom of this section.

---

### 🏭 Enterprise Stories — What Works (and What Doesn't)

**Format: success card vs failure post-mortem**

Success card:
```
✅ **[How a bank cut document review time 60% with GenAI](url)**
Industry: Financial services · Use case: Compliance review
What worked: RAG on policy docs + human-in-loop for exceptions  
Replicable at AIA: YES — Policy compliance review team
```

Failure post-mortem (framed as learning, not criticism):
```
⚠️ **[AI pilot cancelled after hallucination in claims output](url)**
Industry: Insurance · Failure mode: LLM fabricated coverage amounts
Root cause: No grounding — model relied on parametric memory only
Lesson for AIA: Always ground claims-related responses in policy documents
```

---

### 🏛️ Regulatory Radar

**Format: instrument card with deadline badge**

```
📅 DEADLINE: 2025-06-30
**[MAS consults on model governance for financial AI](url)**
Instrument: Consultation paper · Jurisdiction: Singapore/MAS
Who it affects: All MAS-regulated entities deploying GenAI
AIA action: Legal + Risk team should review and respond by deadline
```

Items without a deadline and with `urgency="aware"` are grouped into a compact "Regulatory Background" list below the priority items.

---

### 🔬 Research Frontiers + 💡 Emerging Concepts

**Format: dual-audience card**

```
**[Test-time compute scaling: doing more thinking, not more training](url)**
*For engineers:* Instead of larger models, allocate more inference compute to iterative 
self-critique. Produces GPT-4 class results from smaller models at serving time.
*For leadership:* Better AI answers by "thinking longer" — enables cost-quality trade-off 
per decision, not per model.
Maturity: Early adoption · Horizon: 6–12 months
```

---

## New LLM Prompts

### `MODEL_RELEASE_PROMPT`

```
For each model/API release item below, extract a structured capability card:
- vendor: the releasing company (max 2 words)
- model_name: the model or feature name
- key_upgrade: the single most important new capability (max 10 words)
- context_window: token count if mentioned, else null
- pricing_change: e.g. "-15% input" if mentioned, else null
- aia_use_case: one specific AIA application that this enables or improves (max 15 words)

If a field is not mentioned in the article, output null — do NOT infer or hallucinate.

Return JSON array: [{"url":"...","vendor":"...","model_name":"...","key_upgrade":"...","context_window":null,"pricing_change":null,"aia_use_case":"..."}]

Items: {items_json}
```

### `SECURITY_BRIEF_PROMPT`

```
You are an AI security analyst briefing a CISO at a major life insurer.

For each security item below:
- severity: "critical"|"high"|"medium"|"info"
  critical = active exploit, no patch, production systems affected
  high = known vulnerability with PoC, patch or workaround available  
  medium = theoretical attack, requires specific conditions
  info = awareness, trend signal, no immediate exploit
- attack_vector: one phrase — e.g. "prompt injection via tool output", "supply chain via fine-tune data"
- affected_systems: which AI stacks are affected (max 10 words)
- mitigation: one sentence — what defenders do right now
- aia_relevance: "direct"|"adjacent"|"watch"
  direct = affects Vertex AI, LLM APIs, RAG pipelines, agent frameworks AIA likely uses
  adjacent = affects vendors/ecosystems AIA depends on
  watch = general trend, no immediate AIA exposure

Return JSON array: [{"url":"...","severity":"...","attack_vector":"...","affected_systems":"...","mitigation":"...","aia_relevance":"..."}]

Items: {items_json}
```

### `FRAMEWORK_BRIEF_PROMPT`

```
You are a senior AI engineer evaluating frameworks for an enterprise AI team.

For each framework/tool item:
- replaces_or_extends: existing tool this replaces or extends (e.g. "LangChain", "FAISS") or null
- primary_language: "Python"|"TypeScript"|"Rust"|"Go"|"other"
- use_case: one phrase — e.g. "RAG pipeline", "agent orchestration", "LLM serving"
- adoption_signal: "production-ready"|"early-beta"|"research-prototype"
- try_today: "yes"|"maybe"|"wait"
  yes = stable API, install in minutes, good docs
  maybe = promising, rough edges
  wait = pre-alpha or academic only
- aia_fit: one phrase — how this maps to an AIA engineering use case

Return JSON array: [{"url":"...","replaces_or_extends":null,"primary_language":"...","use_case":"...","adoption_signal":"...","try_today":"...","aia_fit":"..."}]

Items: {items_json}
```

### `EVAL_BRIEF_PROMPT`

```
For each evaluation or benchmark item below:
- models_tested: list of models compared (max 5 names) or null
- task_type: one phrase — e.g. "enterprise QA", "coding", "agent reliability"
- key_finding: one sentence — the single most important result (max 20 words)
- winner: the best-performing approach/model if clear, else null
- aia_takeaway: one sentence — what AIA's AI team should do differently based on this

Return JSON array: [{"url":"...","models_tested":null,"task_type":"...","key_finding":"...","winner":null,"aia_takeaway":"..."}]

Items: {items_json}
```

### `ENTERPRISE_BRIEF_PROMPT`

```
For each enterprise AI story below, classify it and extract a structured brief:
- story_type: "success"|"failure"|"pilot"|"strategy"
- industry: e.g. "insurance", "banking", "healthcare"
- use_case: one phrase — the specific AI application
- outcome: one sentence — what happened and the measurable result if stated
- replicable_at_aia: "yes"|"maybe"|"no" — can AIA replicate this?
- lesson: one sentence — the single most transferable learning

For failure stories specifically: frame the lesson constructively (what to do, not what went wrong).

Return JSON array: [{"url":"...","story_type":"...","industry":"...","use_case":"...","outcome":"...","replicable_at_aia":"...","lesson":"..."}]

Items: {items_json}
```

### `REGULATORY_BRIEF_PROMPT`

```
You are a regulatory intelligence analyst for AIA Singapore.

For each regulatory item:
- instrument_type: "guidance"|"consultation"|"directive"|"speech"|"policy"|"other"
- jurisdiction: e.g. "Singapore/MAS", "EU/AI Act", "Global/IOSCO"
- deadline: ISO date if a compliance deadline is mentioned, else null
- aia_action: one sentence — what AIA's compliance/risk team should do (max 20 words)
- urgency: "act"|"watch"|"aware"
  act = deadline within 60 days OR MAS directive
  watch = consultation open, AIA should track or respond
  aware = informational, no immediate action

Return JSON array: [{"url":"...","instrument_type":"...","jurisdiction":"...","deadline":null,"aia_action":"...","urgency":"..."}]

Items: {items_json}
```

### `EMERGING_CONCEPT_PROMPT`

```
For each emerging concept item below, write for two audiences simultaneously:
- concept_name: short label for the idea (max 5 words)
- tech_explanation: 2 sentences — mechanism and key insight for a senior AI engineer
- business_implication: 1 sentence — what this means for an insurance executive; no jargon
- maturity: "theoretical"|"research"|"early-adoption"|"mainstream"
- horizon: "now"|"6-12 months"|"2-3 years"

Return JSON array: [{"url":"...","concept_name":"...","tech_explanation":"...","business_implication":"...","maturity":"...","horizon":"..."}]

Items: {items_json}
```

### `DUAL_TLDR_PROMPT`

```
Write the opening TL;DR for a daily AI intelligence brief for AIA Singapore.

Two separate ranked lists:

FOR YOUR CEO (3 items):
Prioritise: regulatory signals, competitor threats (Prudential/Great Eastern/Manulife/FWD), 
strategic opportunities, items with action_signal="act", insurance_score=3, regulatory=true.
Frame each bullet for a business executive — decisions, risks, and opportunities. No jargon.
End each bullet with the recommended action in brackets: [Escalate to Legal], [Brief CTO], [Monitor], etc.

FOR YOUR CTO (3 items):
Prioritise: security disclosures, model releases, new frameworks, eval results, 
items in categories models/security/frameworks/emerging, action_signal in {act,watch}.
Frame each bullet for a senior engineer — be specific about what changed, why it matters now.
End each bullet with the decision signal: [Try today], [Evaluate this sprint], [Watch], [Alert team].

Each bullet = one sentence max 25 words + bracketed action signal.
Different items in each list where possible; overlap allowed only if genuinely critical for both.

Return JSON only:
{
  "ceo": [{"bullet":"...","url":"...","action":"..."},...],
  "cto": [{"bullet":"...","url":"...","action":"..."},...] 
}

Items: {items_json}
```

---

## Updated `CURATE_PROMPT` Category Routing

Extended routing rules for 9 categories:

```
Categories:
- "models": new model releases, API updates, pricing changes, SDK launches, structured output,
  tool use announcements from any AI vendor (OpenAI, Anthropic, Google, Meta, Mistral, xAI, open source)
- "frameworks": developer frameworks, agent orchestration libraries, RAG tools, eval frameworks,
  inference engines, fine-tuning interfaces, embedding models, open-source AI tooling
- "security": prompt injection, jailbreaks, model exploits, agent hijacking, supply chain attacks,
  data leakage, tool misuse, AI red teaming, MCP/tool calling security issues
- "research": academic papers, benchmark studies, hallucination research, model evaluation,
  reasoning studies, RAG quality research (not product announcements)
- "enterprise": AI deployment case studies, production success or failure stories, AI ROI reports,
  enterprise AI strategy, lessons from pilots, AI in specific verticals
- "regulatory": MAS guidance, EU AI Act, NIST AI RMF, model governance, explainability,
  auditability, data residency, responsible AI, any financial-sector AI compliance item
- "business": corporate strategy, funding rounds, M&A, product launches, market analysis,
  AI vendor competition, enterprise adoption announcements (not technical tooling)
- "insurtech": insurance-specific AI applications, competitor insurer announcements,
  underwriting/claims/fraud AI, AIA-relevant deployments, APAC insurance technology
- "emerging": novel AI architectures, new reasoning paradigms, mental models, concepts not yet
  in mainstream tooling (compound AI, test-time compute, memory architectures, etc.)

NOISE: exclude items matching any of these patterns — list in "dropped" key:
- Generic commentary with no specific announcement ("AI will change everything")
- Thin opinion piece with fewer than 3 concrete facts
- Vendor press release identical across 5+ outlets, no new information
- Older than {days} days

For kept items, also assign quality_score:
- 3 = original source, technical depth, concrete announcement or verified finding
- 2 = derivative but adds analysis or regional context
- 1 = low-depth summary, include only if no quality_score=2+ coverage of the same story
```

---

## LLM Call Map (summarize_node)

| # | Prompt | Condition | Replaces |
|---|---|---|---|
| 1 | `EDITORS_TAKE_PROMPT` | always | existing |
| 2 | `DUAL_TLDR_PROMPT` | always | existing `TLDR_PROMPT` |
| 3 | `MODEL_RELEASE_PROMPT` | `cat.get("models")` non-empty | new |
| 4 | `SECURITY_BRIEF_PROMPT` | `cat.get("security")` non-empty | new |
| 5 | `REGULATORY_BRIEF_PROMPT` | `cat.get("regulatory")` non-empty | new |
| 6 | `FRAMEWORK_BRIEF_PROMPT` | `cat.get("frameworks")` non-empty | existing `BUILD_AT_AIA_PROMPT` |
| 7 | `EVAL_BRIEF_PROMPT` | `cat.get("research")` non-empty | replaces `PAPER_EXPLAINER_PROMPT` for non-paper research |
| 8 | `ENTERPRISE_BRIEF_PROMPT` | `cat.get("enterprise")` non-empty | new |
| 9 | `EMERGING_CONCEPT_PROMPT` | `cat.get("emerging")` non-empty | new |
| 10 | `BOARDROOM_PROMPT` | `cat.get("business")` non-empty | existing |
| 11 | `COMPETITIVE_HEATMAP_PROMPT` | always | existing |
| 12 | `STEAL_THIS_WEEK_PROMPT` | always | existing |
| 13 | `WEEK_IN_REVIEW_PROMPT` | Friday only | existing |

**Typical day: 9–11 calls** (all gated on non-empty sections). Up from current 7.

---

## Full Email Layout (final)

```
┌──────────────────────────────────────────────────────────────┐
│  AIA GenAI Intelligence — YYYY-MM-DD                         │
│  X min read                                                  │
│                                                              │
│  📌 Editor's Take   (2-3 opinionated sentences)              │
│                                                              │
│  ⚡ For Your CEO — Today's 3 Must-Knows                       │
│     • [Strategic bullet + action] [→]                        │
│     • ...                                                    │
│                                                              │
│  ⚡ For Your CTO — Today's 3 Must-Knows                       │
│     • [Technical bullet + decision signal] [→]               │
│     • ...                                                    │
│                                                              │
│  🌡️ AI Lab Pulse   (one-line per lab, nulls hidden)          │
│                                                              │
│  🚀 Model Releases  (capability-unlock cards)                │
│     Model · Key upgrade · Context · Price · AIA use case     │
│                                                              │
│  🔐 Security Threat Intel  (severity-sorted cards)           │
│     🔴 CRITICAL  Attack vector · Mitigation · AIA relevance  │
│     "This Week in Attacks" micro-summary                     │
│                                                              │
│  🧰 Framework Watch  (comparison rows)                       │
│     Name · replaces · language · adoption · try today        │
│                                                              │
│  📊 Evals & Benchmarks  (scorecard summaries)                │
│     Models tested · Key finding · AIA takeaway               │
│                                                              │
│  🏭 Enterprise Stories                                        │
│     ✅ Success card — replicable at AIA?                      │
│     ⚠️ Failure post-mortem — lesson                          │
│                                                              │
│  🏛️ Regulatory Radar  (deadline-sorted cards)               │
│     📅 DEADLINE  Instrument · Jurisdiction · AIA action      │
│                                                              │
│  🏢 Business & Strategy  (existing section)                  │
│                                                              │
│  🔬 Research Frontiers  (paper of the day + others)          │
│                                                              │
│  💡 Emerging Concepts  (dual-audience cards)                 │
│     [Tech] mechanism · [Business] implication · horizon      │
│                                                              │
│  🛡️ InsurTech & AIA Relevance  (existing section)           │
│                                                              │
│  💡 Steal This Week  (existing)                              │
│                                                              │
│  Source Health · Feedback footer                             │
│  <details> Raw Intelligence Index </details>                 │
└──────────────────────────────────────────────────────────────┘
```

---

## Files Created / Modified

| Path | Change |
|---|---|
| `src/nodes/serp_node.py` | **NEW** — SerpAPI source node, 10 query packs in parallel threads |
| `src/config.py` | Add `SERP_QUERY_PACKS` (10 packs), extend `HN_KEYWORDS` |
| `src/state.py` | Add `serp_news` to `AgentState`; `severity`, `quality_score`, `topic_pack` to `NewsItem`; expand `CategorizedNews` to 9 keys |
| `src/prompts.py` | Add 7 new prompts; update `CURATE_PROMPT` for 9 categories + noise filter; replace `TLDR_PROMPT` with `DUAL_TLDR_PROMPT` |
| `src/nodes/curate_node.py` | Update category routing; pass `quality_score`, `severity`, `topic_pack` through |
| `src/nodes/summarize_node.py` | Add 5 new rendered sections; new render helpers for each format |
| `src/graph.py` | Wire `serp_node` into fan-out |
| `src/nodes/aggregate_node.py` | Add `serp_news` to merge list |
| `.env` / `.env.example` | Add `SERPAPI_KEY` |
| `requirements.txt` | Add `google-search-results~=2.4.2` |
| `tests/test_serp_node.py` | **NEW** |
| `tests/conftest.py` | Extend `mock_llm` for 7 new prompt patterns |
| `tests/test_summarize_node.py` | Tests for 5 new sections + dual TL;DR |

---

## Implementation Steps

### Step 1 — `requirements.txt` + `.env`
Add `google-search-results~=2.4.2`. Add `SERPAPI_KEY=` to `.env.example` and `.env`.

### Step 2 — `src/config.py`
Add `SERP_QUERY_PACKS` dict (10 packs as above). Extend `HN_KEYWORDS` with `"jailbreak", "vulnerability", "exploit", "red team", "benchmark", "distillation"`.

### Step 3 — `src/state.py`
- Add `severity: str`, `quality_score: int`, `topic_pack: str` to `NewsItem`
- Add `serp_news: List[NewsItem]` to `AgentState`
- Expand `CategorizedNews` with `models`, `frameworks`, `security`, `enterprise`, `regulatory`, `emerging` keys

### Step 4 — `src/nodes/serp_node.py`
```python
from serpapi import GoogleSearch
from concurrent.futures import ThreadPoolExecutor

def _fetch_pack(pack_name: str, queries: list[str], key: str, days: int) -> list[NewsItem]:
    items: list[NewsItem] = []
    for q in queries:
        try:
            results = GoogleSearch({
                "q": q, "tbm": "nws", "num": 8, "api_key": key,
                "tbs": f"qdr:d{days}",  # date filter
            }).get_dict().get("news_results", [])
            for r in results:
                items.append({
                    "title": r.get("title", ""),
                    "url": r.get("link", "#"),
                    "summary": r.get("snippet", ""),
                    "source": r.get("source", "serp"),
                    "published_at": r.get("date", ""),
                    "topic_pack": pack_name,
                })
        except Exception as e:
            print(f"[serp] pack={pack_name} query failed: {e}")
    return items

def serp_node(state: AgentState) -> dict[str, Any]:
    key = os.environ.get("SERPAPI_KEY", "")
    if not key:
        print("[serp] SERPAPI_KEY not set — skipping")
        return {"serp_news": []}
    days = state.get("days", 2)
    all_items: list[NewsItem] = []
    with ThreadPoolExecutor(max_workers=5) as ex:
        futures = {ex.submit(_fetch_pack, name, queries, key, days): name
                   for name, queries in SERP_QUERY_PACKS.items()}
        for f in futures:
            try:
                all_items.extend(f.result())
            except Exception as e:
                print(f"[serp] pack {futures[f]} failed: {e}")
    print(f"[serp] collected {len(all_items)} raw items across {len(SERP_QUERY_PACKS)} packs")
    return {"serp_news": all_items}
```

### Step 5 — `src/graph.py`
Add `serp_node` to the `parallel_nodes` list in `build_graph()`.

### Step 6 — `src/nodes/aggregate_node.py`
Add `"serp_news"` to the list of source fields merged into `raw_news`.

### Step 7 — `src/prompts.py`
Add all 7 new prompts. Replace `TLDR_PROMPT` with `DUAL_TLDR_PROMPT`. Update `CURATE_PROMPT` with 9-category routing + noise filter.

### Step 8 — `src/nodes/curate_node.py`
The 9-category JSON structure from the LLM now has additional keys. Pass `quality_score`, `severity`, `topic_pack` through from raw items into curated items. No other logic change needed.

### Step 9 — `src/nodes/summarize_node.py`
Add render helpers and new LLM calls as per the call map above. New render functions:
```python
def _render_models(items, model_briefs) -> list[str]
def _render_security(items, security_briefs) -> list[str]
def _render_frameworks(items, framework_briefs) -> list[str]
def _render_evals(items, eval_briefs) -> list[str]
def _render_enterprise(items, enterprise_briefs) -> list[str]
def _render_regulatory(items, regulatory_briefs) -> list[str]
def _render_emerging(items, emerging_briefs) -> list[str]
def _render_dual_tldr(dual_data) -> list[str]
```

### Step 10 — Tests
`tests/test_serp_node.py` (3 tests). Update `conftest.py` mock_llm. Add 12 new tests to `tests/test_summarize_node.py` covering all new sections.

---

## Verification

```bash
pip install google-search-results~=2.4.2

# Smoke-test SerpAPI key
python -c "
import os; from dotenv import load_dotenv; load_dotenv()
from serpapi import GoogleSearch
r = GoogleSearch({'q':'MAS AI regulation','tbm':'nws','num':3,'api_key':os.environ['SERPAPI_KEY']}).get_dict()
print([x['title'] for x in r.get('news_results',[])][:3])
"

# Full run
python -m src.main --days 2

# Section presence
for section in "For Your CEO" "For Your CTO" "Model Releases" "Security Threat Intel" \
               "Framework Watch" "Evals" "Enterprise Stories" "Regulatory Radar" "Emerging Concepts"; do
  count=$(grep -c "$section" reports/$(date -I)_report.md 2>/dev/null || echo 0)
  echo "$section: $count"
done

# Noise filter working
cat state/$(date -I)_state.json | python -c "
import sys, json
s = json.load(sys.stdin)
cat = s.get('categorized_news', {})
print('Categories:', {k: len(v) for k, v in cat.items()})
"

pytest tests/test_serp_node.py tests/test_summarize_node.py -v
```

---

## Risks / Open Items

| Risk | Mitigation |
|---|---|
| SerpAPI free tier = 100 searches/month. 10 packs × 5 queries = 50/run. Free tier lasts 2 days. | Paid plan needed for daily use. Evaluate tier at $50/mo (5k searches) or $130/mo (15k). The node skips gracefully if key is missing. |
| 9 categories + 13 LLM calls is a significant jump from 4 categories + 7 calls | All new section calls gated on `if cat.get(category)`. Slow news days may fire only 7-8 calls. |
| `CURATE_PROMPT` now routes into 9 categories — higher chance of miscategorisation | Add a `confidence` field to curation output; items with `confidence < 2` stay in their category but are rendered smaller. |
| SerpAPI `tbm=nws` (Google News) returns fewer results for niche queries | Fall back to `tbm` omitted (web search) if `news_results` is empty. |
| `quality_score` filtering may drop genuinely useful items on slow days | Never drop `quality_score=1` items from insurtech/regulatory — those are always surfaced regardless of quality. |
| 400 raw items cap → 25-item curate cap means 375 items dropped before LLM sees them | The 25-item cap sorts by `buzz_score`. Add `topic_pack` as a secondary sort key to ensure at least 1-2 items from each pack survive into the curate prompt. |
| Model release card: LLM may hallucinate specs not in article | `MODEL_RELEASE_PROMPT` explicitly says "if not mentioned, output null". Render helper skips null fields. |
