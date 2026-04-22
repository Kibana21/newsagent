def _load_rss_feeds() -> list[tuple[str, str]]:
    import json
    from pathlib import Path
    feeds_file = Path(__file__).parent.parent / "rss_feeds.json"
    try:
        data = json.loads(feeds_file.read_text())
        return [(f["name"], f["url"]) for f in data]
    except Exception as e:
        print(f"[config] could not load rss_feeds.json: {e}")
        return []

RSS_FEEDS = _load_rss_feeds()

YT_CHANNELS = [
    ("AI Explained", "UCNJ1Ymd5yFuUPqieoHgHS9Q"),
    ("Yannic Kilcher", "UCZHmQk67mSJgfCCTn7xBfew"),
]

HN_KEYWORDS = [
    "ai", "llm", "gpt", "gemini", "claude", "openai", "anthropic",
    "mistral", "langchain", "agent", "rag", "benchmark", "jailbreak",
    "vulnerability", "exploit", "red team", "distillation", "inference",
    "insurance", "fintech", "underwriting", "singapore", "mas", "imda",
    "dbs", "ocbc", "uob", "insurtech", "actuarial", "agentic",
]

INSURANCE_KEYWORDS = [
    "insurance", "underwriting", "claims", "actuarial", "reinsurance",
    "insurtech", "life insurance", "MAS", "IMDA", "finserv", "financial services",
    "DBS", "OCBC", "UOB", "Singapore", "APAC", "Prudential", "Great Eastern",
]

COMPETITOR_INSURERS = [
    "Prudential", "Great Eastern", "Manulife", "FWD",
    "Allianz", "AXA", "Sun Life", "Zurich", "Income Insurance",
    "Tokio Marine", "NTUC Income", "Singlife",
]

SINGAPORE_BANKS = ["DBS", "OCBC", "UOB", "Standard Chartered", "HSBC Singapore", "Citibank Singapore"]

REGULATORS = ["MAS", "HKIA", "OJK", "IMDA", "GovTech", "AISG"]

VERTEX_LOCATION = "us-central1"
VERTEX_MODEL = "gemini-2.5-flash"

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465


def get_serp_query_packs() -> dict[str, list[str]]:  # kept for reference, not wired into graph
    from datetime import date
    d = date.today()
    my = f"{d.strftime('%B')} {d.year}"
    y = str(d.year)
    return {
        # ── Singapore & APAC ─────────────────────────────────────────────────────
        "singapore_banks_ai": [
            f"DBS OCBC UOB artificial intelligence AI deployment {my}",
            f"Singapore bank AI digital transformation announcement {my}",
            f"DBS digital bank AI analytics chatbot use case {y}",
            f"OCBC UOB generative AI production deployment {y}",
            f"Singapore financial services AI strategy investment {my}",
        ],
        "singapore_insurtech": [
            f"Prudential Singapore AI technology digital {my}",
            f"Great Eastern Insurance AI digital transformation {my}",
            f"AXA Singapore Manulife FWD AI technology announcement {y}",
            f"Singapore life insurance generative AI deployment {my}",
            f"NTUC Income Singlife Tokio Marine Singapore AI {y}",
        ],
        "singapore_smart_nation": [
            f"Singapore Smart Nation AI initiative announcement {my}",
            f"GovTech Singapore AI deployment digital government {my}",
            f"AI Singapore AISG programme research {y}",
            f"IMDA Singapore AI roadmap digital economy {my}",
            f"Singapore National AI Strategy generative AI {y}",
        ],
        "apac_finserv_ai": [
            f"APAC bank insurer AI adoption case study {my}",
            f"Asia Pacific fintech insurtech AI production result {y}",
            f"Southeast Asia AI financial services deployment {my}",
            f"Hong Kong MAS HKMA AI regulation financial sector {my}",
            f"APAC digital banking insurance AI transformation {y}",
        ],
        # ── Model Releases ───────────────────────────────────────────────────────
        "model_releases": [
            f"new AI model released {my}",
            f"Claude GPT Gemini Llama model launch {my}",
            f"LLM context window pricing API update {my}",
            f"AI structured output tool use batch API release {y}",
            f"frontier model benchmark capability release {my}",
        ],
        "gemini_google": [
            f"Google Gemini model release developer news {my}",
            f"Gemini API update feature release {my}",
            f"Google DeepMind research announcement {my}",
            f"Google AI Studio Vertex AI update developer {y}",
            "Gemini Flash Pro Ultra benchmark comparison",
        ],
        "open_source_models": [
            f"open source LLM model released Hugging Face {my}",
            f"Llama Mistral Qwen Phi model release {my}",
            f"new open source reasoning model release {y}",
            f"open source multimodal model release {my}",
            "GGUF quantized model release community",
        ],
        "claude_anthropic": [
            f"Claude Anthropic news announcement {my}",
            f"Anthropic model safety research publication {y}",
            f"Claude enterprise API feature update {my}",
            "Anthropic Constitutional AI alignment update",
        ],
        # ── Frameworks & Tooling ─────────────────────────────────────────────────
        "frameworks_tooling": [
            f"new AI agent framework released {my}",
            "new RAG framework retrieval pipeline open source",
            f"LangGraph LlamaIndex DSPy CrewAI smolagents update {y}",
            f"new open source LLM inference serving tool {y}",
            f"AI evaluation orchestration framework release {my}",
        ],
        "dev_libraries": [
            f"LangChain LangGraph release update {my}",
            f"LlamaIndex release new feature {my}",
            f"DSPy optimizer release update {my}",
            f"CrewAI AutoGen smolagents update release {y}",
            f"Haystack Semantic Kernel AI framework update {y}",
        ],
        "databricks_mlflow": [
            f"Databricks AI model announcement {my}",
            f"Databricks Unity Catalog AI governance update {y}",
            f"MLflow release update experiment tracking {my}",
            "Databricks LLM fine-tuning serving feature",
            f"Mosaic AI Databricks update news {y}",
        ],
        # ── Security ─────────────────────────────────────────────────────────────
        "ai_security": [
            f"AI security vulnerability disclosure {my}",
            f"LLM prompt injection jailbreak attack {y}",
            "AI agent supply chain exploit browser agent",
            "MCP tool calling permission security risk",
            f"generative AI red team threat intelligence {my}",
        ],
        # ── Evals & Research ─────────────────────────────────────────────────────
        "evals_benchmarks": [
            f"LLM benchmark evaluation comparison study {my}",
            "AI hallucination measurement reliability research",
            "RAG retrieval quality evaluation enterprise",
            f"agent benchmark reliability reasoning results {y}",
            f"model coding reasoning evaluation new study {y}",
        ],
        "inference_perf": [
            f"LLM inference latency speed optimization {my}",
            f"AI model quantization distillation production cost {y}",
            "small language model SLM performance benchmark",
            "GPU AI inference cost reduction optimization",
            "LLM token caching routing speculative decoding",
        ],
        # ── Regulatory ───────────────────────────────────────────────────────────
        "mas_regulatory": [
            f"MAS AI regulation guidance Singapore {y}",
            f"Monetary Authority Singapore generative AI policy {my}",
            f"EU AI Act financial services implementation {y}",
            "NIST AI risk management framework financial sector",
            f"APAC financial AI governance compliance {my}",
        ],
        # ── Enterprise Stories ───────────────────────────────────────────────────
        "enterprise_stories": [
            f"enterprise AI deployment case study production {my}",
            "AI production failure hallucination incident lesson",
            f"bank insurer hospital AI rollout result {y}",
            "agentic AI enterprise production problem lesson",
            f"generative AI ROI business outcome report {y}",
        ],
        # ── Emerging ─────────────────────────────────────────────────────────────
        "emerging_concepts": [
            f"new AI architecture concept research breakthrough {my}",
            "test time compute scaling reasoning method",
            "compound AI system approach multi-agent",
            f"AI memory architecture agent consistency research {y}",
            f"new multimodal reasoning paradigm technique {my}",
        ],
        "general_ai": [
            f"generative AI enterprise strategy investment {my}",
            f"AI startup funding round announcement {my}",
            f"AI in insurance fintech APAC deployment {y}",
            f"OpenAI Google Meta AI competitive news {my}",
        ],
    }
