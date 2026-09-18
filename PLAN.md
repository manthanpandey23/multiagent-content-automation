# Multi-Agent Social Media Content Pipeline — Detailed Plan

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Architecture Diagram](#2-architecture-diagram)
3. [Tech Stack](#3-tech-stack)
4. [Project Structure](#4-project-structure)
5. [Core Components](#5-core-components)
6. [Agent Specifications](#6-agent-specifications)
7. [Telegram Interface](#7-telegram-interface)
8. [Review & Guardrail System](#8-review--guardrail-system)
9. [Scheduling Engine](#9-scheduling-engine)
10. [Data Models & Persistence](#10-data-models--persistence)
11. [Evaluation System](#11-evaluation-system)
12. [Local UI Dashboard](#12-local-ui-dashboard)
13. [Implementation Roadmap](#13-implementation-roadmap)
14. [Dependencies](#14-dependencies)
15. [Environment Configuration](#15-environment-configuration)
16. [Risk Mitigation](#16-risk-mitigation)

---

## 1. System Overview

A controlled multi-agent pipeline that:

- **Ingests** technology news from the web (daily at 9 AM IST)
- **Generates** social media content from that news (text + image guidance)
- **Validates** and refines content for originality
- **Reviews** content through both automated agent review and human approval
- **Publishes** approved content to Instagram, LinkedIn, and Twitter
- **Enforces guardrails** at every stage to keep agents bounded and safe

### Pipeline Flow

```
[Scheduler Trigger]
        |
        v
[Agent 1: News Researcher]  →  fetch top 10 tech news
        |
        v
[Agent Reviewer]  →  automated quality gate
        |
        v
[Human Review via Telegram]  →  approve/reject/modify
        |
        v
[Agent 2: Content Creator]  →  generate social media posts + image prompts
        |
        v
[Agent Reviewer]  →  automated quality gate
        |
        v
[Human Review via Telegram]  →  approve/reject/modify
        |
        v
[Agent 3: Content Validator]  →  fact-check, refine, ensure originality
        |
        v
[Agent Reviewer]  →  automated quality gate
        |
        v
[Human Review via Telegram]  →  final approve/reject
        |
        v
[Agent 4: Publisher]  →  post to Instagram, LinkedIn, Twitter
        |
        v
[Report to Telegram]  →  confirmation with links
```

**Schedule:**
| Time (IST) | Time (UTC) | Action |
|---|---|---|
| 9:00 AM | 3:30 AM | Agent 1 runs — fetch news |
| 10:00 AM | 4:30 AM | Agents 2–4 run + publish (if all approvals given) |

---

## 2. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     ORCHESTRATOR (pipeline.py)                                  │
│  - State machine management                                                       │
│  - Agent dispatch & data routing                                                  │
│  - Review gate enforcement                                                          │
│  - Error handling & retry                                                           │
│  - Intercepts ALL agent calls for Guardian monitoring                             │
│  - Routes ALL LLM calls through Token Manager                                     │
└────────┬──────────┬──────────┬──────────┬──────────┬──────────┬──────────┬─────┘
         │          │          │          │          │          │          │
    ┌────▼───┐ ┌───▼────┐ ┌───▼────┐ ┌───▼────┐ ┌───▼────┐ ┌────▼────┐ ┌───▼─────┐
    │ Agent 1│ │Agent 2 │ │Agent 3 │ │Agent 4 │ │Reviewer│ │Guardian │ │Token    │
    │ Researcher│Creator│ │Validator│ │Publisher│ │(Agent) │ │(Safeguard)│ │Manager  │
    │         │        │        │        │        │        │         │ │(Agent 6)│
    └────┬───┘ └───┬────┘ └───┬────┘ └───┬────┘ └───┬────┘ └───┬─────┘ └───┬─────┘
         │         │          │          │          │          │           │
         │         │          │          │          │          │           │  ┌──────────────────────────────┐
         │         │          │          │          │          │           │  │ TOKEN MANAGEMENT ENGINE       │
         │         │          │          │          │          │           │  │                               │
         │         │          │          │          │          │           │  │ ┌──────────────────────────┐ │ │
         │         │          │          │          │          │           │  │ │ Token Budget Tracker     │ │ │
         │         │          │          │          │          │           │  │ │ (per-agent, per-provider) │ │ │
         │         │          │          │          │          │           │  │ └──────────────────────────┘ │ │
         │         │          │          │          │          │           │  │ ┌──────────────────────────┐ │ │
         │         │          │          │          │          │           │  │ │ Provider/Model Switcher  │ │ │
         │         │          │          │          │          │           │  │ │ (auto-failover)          │ │ │
         │         │          │          │          │          │           │  │ └──────────────────────────┘ │ │
         │         │          │          │          │          │           │  │ ┌──────────────────────────┐ │ │
         │         │          │          │          │          │           │  │ │ Context Optimizer        │ │ │
         │         │          │          │          │          │           │  │ │ (prune/compress/cache)   │ │ │
         │         │          │          │          │          │           │  │ └──────────────────────────┘ │ │
         │         │          │          │          │          │           │  │ ┌──────────────────────────┐ │ │
         │         │          │          │          │          │           │  │ │ Token Counter            │ │ │
         │         │          │          │          │          │           │  │ │ (tiktoken + tokenizers)  │ │ │
         │         │          │          │          │          │           │  │ └──────────────────────────┘ │ │
         │         │          │          │          │          │           │  └──────────────────────────────┘ │
         │         │          │          │          │          │           │                                   │
    ┌────▼───┐ ┌───▼────┐ ┌───▼────┐ ┌───▼────┐ ┌───▼──────────┐ ┌───▼──────────┐ ┌──────────────────┐
    │ Web    │ │Image   │ │ Fact-  │ │ IG/    │ │ Quality    │ │ Activity     │ │ GitHub Tools   │
    │ Search │ │Prompt  │ │ check  │ │ LinkedIn│ │ Scoring    │ │ Monitoring   │ │ (tiktoken,     │
    │ RSS    │ │Gen     │ │ Plag   │ │ Twitter│ │            │ │              │ │  tokenizers,  │
    └────────┘ └────────┘ └────────┘ └────────┘ └────────────┘ └──────────────┘ │  transformers) │
                                                                                 └──────────────────┘
    ┌───────────────────────────────────────────────────────────────────────────┘
    │                    ┌──────────────┐
    │  ┌────────────────│  GUARDRAILS  │
    │  │ Word Limits    │  - Content   │
    │  │ Category Scope │    Safety    │
    │  │ Source Trust   │  - Bias      │
    │  │ No Fabrication │    Detection │
    │  │ Brand Safety   │  - Compliance│
    │  └────────────────└──────────────┘
    │
    │  ┌──────────────────────────────────────┐
    │  │  HUMAN REVIEW (Telegram Bot)         │
    │  │  - approve / reject / edit           │
    │  │  - Guardian violation alerts         │
    │  │  - Token budget alerts               │
    │  │  - audit trail                       │
    │  └──────────────────────────────────────┘
    │
    │  ┌──────────────────────────────────────┐
    │  │  EVALUATION ENGINE                     │
    │  │  - Workflow accuracy scoring           │
    │  │  - Content quality rubrics             │
    │  │  - Daily/Weekly/Monthly reports        │
    │  └──────────────────────────────────────┘
    │
    └───────────────────────────────────────────────────────────────────
                        │
              ┌─────────▼─────────┐
              │  DATA LAYER        │
              │  PostgreSQL        │
              │  Redis (cache/     │
              │   queue/session/   │
              │   eval results/    │
              │   token usage)     │
              └───────────────────┘
```

---

## 3. Tech Stack

| Component | Technology | Purpose |
|---|---|---|
| **LLM** | Hermes 3 via NVIDIA NIM **OR** OpenRouter free-tier models | Core reasoning & text generation |
| **NIM Provider** | NVIDIA NIM API (`api.nvidia.com`) | Hosted inference endpoints (primary) |
| **OpenRouter Provider** | OpenRouter API (`openrouter.ai/api/v1`) | Fallback + free-tier model access |
| **Free Tier Models** | `meta/llama-3.1-8b-instruct` (NVIDIA/NR), `google/gemma-2-9b-it`, `meta/llama-3.1-8b-instruct` (OpenRouter) | 40–1000 tokens/min free tier |
| **Provider Abstraction** | Dual-provider with automatic failover | Best-available model, cost-free |
| **Agent Framework** | Custom lightweight orchestrator (Python) | Full control over pipeline flow and guardrails |
| **Telegram** | `python-telegram-bot` v21 | Request source, human review, status updates, Guardian alerts |
| **Web Search** | `duckduckgo-search` + `beautifulsoup4` | News aggregation |
| **Scheduling** | `APScheduler` | Cron-like daily triggers |
| **Database** | PostgreSQL (via `psycopg2`) | Persistent storage: news, content, audit logs, evaluations |
| **Cache/Queue** | Redis (via `redis-py`) | Session state, inter-agent data, rate limiting, eval cache |
| **Image Generation** | NVIDIA NIM (FLUX) or open-source via HuggingFace | Image prompt generation |
| **Social APIs** | Platform REST APIs (IG Graph, LinkedIn, X/Twitter) | Publishing |
| **HTTP** | `httpx` (async) | All API calls |
| **Dashboard UI** | `Streamlit` | Local web UI for monitoring agents (daily/weekly/monthly) |
| **Evaluation** | Custom Eval Engine + `rubrics` scoring | Workflow accuracy & content quality scoring |
| **Token Management** | `tiktoken` + `tokenizers` + `transformers` | Token counting, model-agnostic tokenization |
| **Semantic Cache** | Custom semantic cache layer | Reuse cached LLM responses for similar queries |
| **Config** | `python-dotenv` | Environment variable management |
| **Validation** | Pydantic v2 | Data models and schema validation |

---

## 4. Project Structure

```
hermes-social-agent/
├── .env                          # Secrets and config (git-ignored)
├── .gitignore
├── docker-compose.yml            # Postgres + Redis
├── PLAN.md                       # This document
├── requirements.txt              # Python dependencies
├── run.py                        # Entry point — starts orchestrator + scheduler + UI
├── config.py                     # Config loader from .env
│
├── agents/                       # Agent definitions
│   ├── __init__.py
│   ├── base.py                   # BaseAgent class (shared interface)
│   ├── researcher.py             # Agent 1: News Researcher
│   ├── creator.py                # Agent 2: Content Creator
│   ├── validator.py              # Agent 3: Content Validator
│   ├── publisher.py              # Agent 4: Publisher
│   ├── reviewer.py               # Agent Reviewer (automated quality gate)
│   ├── guardian.py               # Agent 5: Guardian/Safeguard (monitors all agents)
│   └── token_manager.py          # Agent 6: LLM Token Manager (token budget, provider switching)
│
├── guardrails/                   # Guardrail module
│   ├── __init__.py
│   ├── base.py                   # Guardrail base class
│   ├── word_limit.py             # Word count enforcement
│   ├── category_filter.py        # Category scope enforcement
│   ├── content_safety.py         # Harmful content filter
│   ├── source_verifier.py        # Source trust scoring
│   └── bias_detector.py          # Bias/factuality check
│
├── providers/                    # LLM provider abstraction
│   ├── __init__.py
│   ├── base.py                   # LLMProvider interface
│   ├── nvidia_nim.py             # NVIDIA NIM provider implementation
│   ├── openrouter.py             # OpenRouter provider implementation (free tier)
│   ├── router.py                 # Dual-provider with Token Manager integration
│   └── token_aware.py            # Token-aware LLM call wrapper
│
├── llm_manager/                  # Token Management Engine
│   ├── __init__.py
│   ├── budget.py                 # Token budget tracking per agent/provider/model
│   ├── counter.py                # Token counting (tiktoken + tokenizers)
│   ├── switcher.py               # Provider/model auto-switching logic
│   ├── optimizer.py              # Context optimization (prune/compress/cache)
│   ├── cache.py                  # Semantic caching layer
│   ├── predictor.py              # Token cost prediction before execution
│   ├── reporter.py               # Token usage reports (daily/weekly/monthly)
│   └── save_token_jev.py         # save-token-jev tool — token optimization for all agents
│
├── tools/                        # Shared agent tools
│   ├── __init__.py
│   └── save_token_jev.py         # save-token-jev tool (exposed to all agents)
│
├── integrations/                 # External integrations
│   ├── __init__.py
│   ├── telegram_bot.py           # Telegram bot (review + commands + alerts)
│   ├── web_search.py             # Web search + RSS reader
│   ├── social_publisher.py       # IG/LinkedIn/Twitter API clients
│   ├── image_generator.py        # Image generation client
│   └── eval_engine.py            # Evaluation & rubric scoring engine
│
├── models/                       # Data models
│   ├── __init__.py
│   ├── news.py                   # NewsArticle, NewsBatch schemas
│   ├── content.py                # SocialContent, PostVariant schemas
│   ├── review.py                 # ReviewResult, ApprovalStatus schemas
│   ├── pipeline.py               # PipelineState, Stage enum
│   ├── guardian.py               # GuardianAlert, ActivityLog schemas
│   ├── evaluation.py             # EvalResult, RubricScore, ReportPeriod schemas
│   └── token.py                  # TokenUsage, TokenBudget, ProviderCapacity schemas
│
├── ui/                           # Local Dashboard
│   ├── __init__.py
│   ├── app.py                    # Streamlit main app
│   ├── pages/
│   │   ├── dashboard.py          # Overview: active pipelines, stats
│   │   ├── agents.py             # Per-agent activity logs & status
│   │   ├── news.py               # News feed monitoring
│   │   ├── content.py            # Content created/published
│   │   ├── reviews.py            # Review history & decisions
│   │   ├── guardian.py           # Guardian alerts & violations
│   │   ├── token_manager.py      # Token usage & provider switching monitor
│   │   ├── evaluations.py        # Eval reports (daily/weekly/monthly)
│   │   └── settings.py           # Config & feature flags
│   └── components/
│       ├── charts.py             # Chart.js / Streamlit charts
│       └── filters.py            # Date range, agent, category filters
│
├── scheduler/                    # Scheduling engine
│   ├── __init__.py
│   └── tasks.py                  # Scheduled task definitions
│
├── utils/                        # Shared utilities
│   ├── __init__.py
│   ├── text_utils.py             # Word count, truncation, etc.
│   └── logger.py                 # Structured logging
│
└── db/                           # Database layer
    ├── __init__.py
    ├── connection.py             # Connection pool setup
    ├── repositories/             # Repository pattern
    │   ├── news_repo.py
    │   ├── content_repo.py
    │   ├── review_repo.py
    │   ├── pipeline_repo.py
    │   ├── guardian_repo.py      # Guardian alerts & activity logs
    │   ├── eval_repo.py          # Evaluation results
    │   └── token_repo.py         # Token usage & budget records
    └── migrations/               # SQLAlchemy migrations (Alembic)
        └── ...
```

---

## 5. Core Components

### 5.1 Orchestrator (`pipeline.py`)

The central brain. Implements a **state machine** that manages all agents, review gates, and the Token Manager integration.

**Responsibilities:**
- Advance state only after gate checks pass
- Route data between agents
- Handle timeouts and retries (max 3 per agent)
- **Intercepts every agent call to Guardian for monitoring** (see §6.5)
- **Routes every LLM call through Token Manager / save-token-jev** (see §6.6)
- Publish status updates to Telegram at each stage transition
- Record audit trail in PostgreSQL
- Trigger Eval Engine at end of each pipeline run

```python
class PipelineStage(Enum):
    IDLE = "idle"
    RESEARCHING = "researching"          # Agent 1
    RESEARCH_REVIEW = "research_review"  # Agent Reviewer
    HUMAN_REVIEW_RESEARCH = "human_research"  # Telegram approval
    CREATING = "creating"                # Agent 2
    CREATING_REVIEW = "creating_review"  # Agent Reviewer
    HUMAN_REVIEW_CREATING = "human_creating"
    VALIDATING = "validating"            # Agent 3
    VALIDATING_REVIEW = "validating_review"
    HUMAN_REVIEW_VALIDATING = "human_validating"
    PUBLISHING = "publishing"            # Agent 4
    GUARDIAN_CHECK = "guardian_check"    # Agent 5 post-task
    COMPLETE = "complete"
    FAILED = "failed"
```

### 5.2 Base Agent (`agents/base.py`)

```python
class BaseAgent(ABC):
    """All agents implement this interface."""
    
    @property
    @abstractmethod
    def name(self) -> str: ...
    
    @property
    @abstractmethod
    def description(self) -> str: ...
    
    @property
    @abstractmethod
    def allowed_tools(self) -> list[str]: ...  # Bounded tool set
    
    @abstractmethod
    async def execute(self, input_data: dict) -> dict: ...
    
    async def pre_check(self, input_data: dict) -> bool: ...  # Guardrail pre-check
    async def post_check(self, output_data: dict) -> bool: ... # Guardrail post-check
    
    async def optimize_tokens(self, messages: list[dict]) -> list[dict]:
        """Use save-token-jev tool to optimize token usage before LLM call."""
        from tools.save_token_jev import optimize_messages
        return await optimize_messages(messages)
```

### 5.3 Provider Router with Token Manager (`providers/router.py`)

The Provider Router now integrates directly with the LLM Token Manager (Agent 6). Every LLM call goes through the Token Manager first, which decides which provider/model to use based on current budgets.

```python
class TokenAwareRouter(LLMProvider):
    """
    Provider Router that consults Token Manager before each LLM call.
    
    Decision flow:
    1. Token Manager checks: Is there budget remaining for this agent+provider?
    2. If YES → Route to the configured provider
    3. If NO → Token Manager triggers provider/model switch
    4. Log the switch and continue
    """
    
    def __init__(self, token_manager: TokenManager, providers: list[LLMProvider]):
        self.token_manager = token_manager
        self.providers = providers
    
    async def generate(self, messages: list[dict], agent_name: str, **kwargs) -> str:
        # Step 1: Check token budget
        budget = self.token_manager.get_budget(agent_name)
        estimated = self.token_manager.estimate_tokens(messages)
        
        if budget.remaining < estimated * 1.2:  # 20% safety margin
            await self.token_manager.request_switch(agent_name, estimated)
        
        # Step 2: Get current provider from Token Manager
        provider = self.token_manager.get_active_provider(agent_name)
        
        # Step 3: Execute call and report usage
        try:
            result = await provider.generate(messages, **kwargs)
            actual_tokens = self.token_manager.count_tokens(result)
            self.token_manager.record_usage(agent_name, actual_tokens)
            return result
        except RateLimitError:
            await self.token_manager.handle_provider_exhausted(agent_name)
            raise
```

**GitHub Tools for Token Management:**

| Tool | Repository | Purpose |
|---|---|---|
| `tiktoken` | `github.com/openai/tiktoken` | Fast BPE tokenization; model-agnostic token counting for GPT, Gemini, Llama |
| `tokenizers` | `github.com/huggingface/tokenizers` | Fast, multilingual tokenizers; supports SentencePiece, BPE, WordPiece |
| `transformers` | `github.com/huggingface/transformers` | Model-specific tokenizers, context window utilities, model config |
| Context pruning patterns | `github.com/ggerganov/llama.cpp` (attention mechanisms) | Key-value cache pruning, context compression strategies |
| Semantic caching | Community repos (various) | Hash-based response caching for similar prompts; avoids redundant LLM calls |
| Context window management | `github.com/langchain-ai/langchain` | Context window helpers, document chunking, token-aware document loaders |

**Context Optimization Techniques (used by Token Manager):**

1. **Prioritized Context Retention**: When approaching context limits, keep system prompt + most recent N tokens + summary, prune older conversational turns
2. **Semantic Summarization**: Use a smaller model to compress older context into key points
3. **Relevance Scoring**: Embed context chunks; only retain top-K most relevant to current task
4. **Response Caching**: Hash the prompt; return cached response if similarity > 95% (via `tiktoken` + locality-sensitive hashing)
5. **Chunked Processing**: Break large inputs into token-sized chunks, process independently, merge results
6. **Instruction Compression**: Detect and remove redundant instructions from prompt templates

**Token Budgets (Free Tier Limits):**

| Provider | Model | Tokens/Min | Requests/Day | Daily Budget |
|---|---|---|---|---|
| NVIDIA NIM | `meta/llama-3.1-8b-instruct` | 40 | 200 | 500,000 |
| NVIDIA NIM | `nvidia/nemotron-4-340b-instruct` | Varies | Varies | 200,000 |
| OpenRouter | `google/gemma-2-9b-it` | Varies | Varies | 500,000 |
| OpenRouter | `microsoft/phi-3-mini-4k-instruct` | Varies | Varies | 500,000 |

### 5.4 LLM Provider — Legacy Reference

Individual provider implementations remain as before:
- `providers/nvidia_nim.py` — NVIDIA NIM hosted models
- `providers/openrouter.py` — OpenRouter free-tier models

Both providers implement the same `LLMProvider` interface and are managed by `TokenAwareRouter`.

---

## 6. Agent Specifications

### Agent 1: News Researcher

**Input:** None (triggered by scheduler) or category list from Telegram command
**Output:** `NewsBatch` — 10 articles
**Tools:** `save-token-jev` (via BaseAgent.optimize_tokens) — optimizes prompt tokens before web search and content generation

**Behavior:**
1. Query DuckDuckGo for each category: AI, ML, IT Sector, Automation, Cloud, Cybersecurity, etc.
2. Fetch top 5 results per category (scrape title, snippet, URL, source)
3. Filter and deduplicate to 10 most relevant/recent stories
4. For each story, generate:
   - **Title**: max 100 words (concise headline summary)
   - **Description**: max 300 words (key points, context, implications)
   - Source name, URL, published time, assigned category

**Guardrails:**
- No fabricated URLs or sources — every article must link to real domain
- Title ≤ 100 words, Description ≤ 300 words (hard enforcement via text_utils)
- Only stories published within last 7 days
- Category must be from allowed list
- Source diversity: no more than 2 articles from same domain
- No clickbait or conspiracy content (content_safety guardrail)

**Prompt engineering:** System prompt instructs the model to extract factual summaries only, never fabricate, attribute all claims to sources.

### Agent 2: Content Creator

**Input:** `NewsBatch` from Agent 1
**Output:** `SocialContent` — variants for each platform
**Tools:** `save-token-jev` (via BaseAgent.optimize_tokens) — optimizes prompt tokens before content generation; reduces repeated prompt tokens via caching

**Behavior:**
1. Select top 3–5 most "shareable" news items (based on engagement scoring via LLM)
2. For each item, create platform-specific content:
   - **Instagram**: Image prompt (detailed description for DALL-E/FLUX) + caption (max 2200 chars, ≤150 words for caption body)
   - **LinkedIn**: Professional post (max 300 words) with hashtags (≤5)
   - **Twitter/X**: Thread of 3–4 tweets (each ≤280 chars) or single post (≤280 chars)
3. Include relevant emojis sparingly for Instagram, minimal for LinkedIn
4. Attach URLs/sources as links

**Guardrails:**
- No copyrighted material reproduced verbatim
- Brand voice: professional but engaging (bias_detector)
- Image prompts: no violent, NSFW, or offensive imagery (content_safety)
- Hashtag count ≤ 5 per post
- No misinformation — cross-reference with source URLs
- Plagiarism check against source articles (similarity < 30%)

### Agent 3: Content Validator

**Input:** `SocialContent` from Agent 2
**Output:** `SocialContent` (refined) + `ValidationReport`
**Tools:** `save-token-jev` (via BaseAgent.optimize_tokens) — optimizes validation prompt tokens; caches validation patterns for reuse

**Behavior:**
1. **Factuality check**: Verify claims against source articles
2. **Originality score**: Compute text similarity to sources, flag >30%
3. **Refinement**: Rewrite sections that are too close to source material
4. **Tone check**: Ensure consistent professional tone across all platforms
5. **Format validation**: Verify all platform constraints are met
6. **Score the content**: Quality score 0–100; reject if <70

**Guardrails:**
- Auto-fix word limit violations
- Remove unverified claims
- Flag and quarantine content that fails factuality threshold
- Ensure all URLs are reachable (health check)

### Agent 4: Publisher

**Input:** Approved `SocialContent`
**Output:** `PublishResult` — status per platform
**Tools:** `save-token-jev` (via BaseAgent.optimize_tokens) — optimizes API call parameter tokens; caches platform API templates

**Behavior:**
1. Authenticate with each platform API using stored credentials
2. Post content:
   - **Instagram**: Upload image (from URL or generate via image API), set caption
   - **LinkedIn**: Post article/Update API
   - **Twitter/X**: Post tweet or thread
3. Capture post URLs/IDs as proof
4. Handle errors with retry (3 attempts, exponential backoff)
5. Return results with links

**Guardrails:**
- Never publish if ANY prior stage has unresolved rejection
- Rate limit awareness per platform
- Dry-run mode available for testing
- Rollback capability if one platform fails mid-batch
- Log everything for audit

### Agent Reviewer

**Input:** Output from any agent
**Output:** `ReviewResult` — score, flags, recommendation
**Tools:** `save-token-jev` (via BaseAgent.optimize_tokens) — optimizes review prompt tokens; caches review rubric templates across all agents

**Behavior:**
1. Run all guardrails against the output
2. Score quality on dimensions: Accuracy (0–100), Originality (0–100), Relevance (0–100), Safety (0–100)
3. If total score ≥ 75 AND no critical flags → **PASS**
4. If score 50–74 → **WARN** (proceed with note)
5. If score < 50 OR critical flag → **FAIL** (block pipeline)
6. Return structured feedback for human reviewer

### Agent 5: Guardian (Safeguard Agent)

**Input:** Every agent's activity log (input, output, tools called, tokens used, timestamps)
**Output:** `GuardianAlert` (if violation) or `GuardianClear` (if all checks pass)
**Tools:** `save-token-jev` (via BaseAgent.optimize_tokens) — optimizes monitoring prompt tokens; caches agent behavior patterns for efficient violation analysis

**Purpose:** The Guardian is a meta-agent that continuously monitors all other agents to ensure they operate within their prescribed bounds. It acts as an independent auditor that reports unauthorized or risky activity to the Telegram bot connected with the Hermes orchestrator.

**Behavior:**
1. **Intercepts every agent call** via the orchestrator (pre-execution hook)
2. For each agent execution, validates:
   - **Scope check**: Did the agent only use its `allowed_tools`?
   - **Instruction adherence**: Did the agent stay within its system prompt instructions?
   - **Data flow check**: Did the agent access data it shouldn't have? (e.g., Researcher shouldn't access social APIs)
   - **Token usage check**: Is the agent within its daily token budget?
   - **Time check**: Is the agent operating during allowed hours?
   - **Loop check**: Is the agent stuck in a loop or repeating the same action?
   - **Escalation check**: Did the agent try to escalate its permissions?
3. Generates a `GuardianReport` after each agent run with:
   - Agent name and execution ID
   - Checklist of all checks (PASS/FAIL)
   - Any violations with severity (INFO, WARN, CRITICAL)
   - Recommended action (ALLOW, WARN, BLOCK)
4. **On CRITICAL violation**: Immediately sends Telegram alert with full details
5. **On WARN violation**: Logs and reports in next Telegram status update
6. **Maintains a running audit trail** of all agent behaviors per session
7. Generates daily/weekly/monthly compliance reports

**Guardian's Own Guardrails:**
- Guardian cannot modify any agent's output — read-only monitor
- Guardian cannot approve or reject content — only observe and report
- Guardian alerts are advisory; human in Telegram has final authority
- Guardian's own prompts are version-controlled and tamper-evident
- Guardian activity is itself monitored by an external watchdog timer

**Guardian Alert Telegram Message Format:**
```
🚨 GUARDIAN ALERT — CRITICAL

Agent: Agent 2 (Content Creator)
Session: abc-123-def
Timestamp: 2026-09-18 10:15:30 IST

Violation: Agent attempted to access tool NOT in allowed list
Attempted Tool: "file_system_write"
Allowed Tools: ["web_search", "text_generate", "image_prompt_gen"]

Execution Context:
  Input received: { news_ids: [...] }
  Agent attempted: file_system_write("/app/data/override.txt")

Recommended Action: BLOCK + Investigate

🔗 View in Dashboard: http://localhost:8501/session/abc-123-def

This is an automated alert from the Guardian Safeguard Agent.
```

**What the Guardian Monitors Per Agent:**

| Check | Agent 1 | Agent 2 | Agent 3 | Agent 4 | Agent Reviewer | Agent 5 | Agent 6 |
|---|---|---|---|---|---|---|---|
| Allowed tools only | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Stayed in scope | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Token budget OK | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| No loop detection | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Data access right | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| No self-modify | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| No permission escalation | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Output matches input | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

### Agent 6: LLM Token Manager — NEW

**Input:** Every LLM call from all agents (messages, model preference, estimated token count)
**Output:** Route decision (which provider/model to use) + usage tracking + context optimization
**Primary Tool:** `save-token-jev` — the core token optimization tool managed by this agent for all other agents

**Purpose:** The Token Manager is the central hub for all LLM resource management. It ensures no provider or model is exhausted, optimizes context windows to minimize token waste, and enables intelligent provider/model switching — all while maintaining accuracy and efficiency.

#### 6.6.1 Core Responsibilities

**A. Token Budget Management**
1. Track tokens consumed per agent, per provider, per model, per day
2. Maintain configurable daily budgets per agent (default: 500K tokens)
3. When budget reaches 80% → send Telegram notification to admin
4. When budget reaches 95% → hard stop, require manual override
5. Reset budgets at midnight IST daily
6. Store all usage data in PostgreSQL for historical analysis

**B. Provider & Model Switching**
1. Before each LLM call, consult Token Manager for best available provider
2. Decision matrix:
   | Condition | Action |
   |---|---|
   | NVIDIA within budget, model available | Use NVIDIA NIM (preferred) |
   | NVIDIA at 80% budget | Warn, prepare to switch |
   | NVIDIA at 95% budget | Auto-switch to OpenRouter equivalent |
   | OpenRouter at 80% budget | Use smallest available model |
   | Both at 95%+ | Queue request, notify admin, wait for reset |
3. Model downgrade strategy: `8B → 2B` for non-critical tasks (e.g., simple classification)
4. All switches are logged with reason, time, and impact assessment
5. Telegram notification on every provider/model switch

**C. Context Optimization**
1. **Token Counting**: Use `tiktoken` (OpenAI) + `tokenizers` (HuggingFace) for accurate model-specific token counts
2. **Context Pruning**: When conversation history approaches context limit:
   - Keep system prompt intact (highest priority)
   - Keep last N tokens (configurable, default 60% of context window)
   - Compress older turns into summary using a smaller model
   - Discard fully summarized content
3. **Semantic Caching**: 
   - Hash prompt using SHA-256 of `tiktoken`-encoded tokens
   - Check Redis cache before calling LLM
   - Cache hit rate target: >30% for repeated queries
   - TTL: 1 hour for news queries, 24 hours for content templates
4. **Relevance Scoring**: Embed context chunks, rank by similarity to current task, prune bottom 20%
5. **Instruction Compression**: Deduplicate system prompt instructions across agents; share common templates

**D. Token Cost Prediction**
1. Estimate token cost of any planned LLM call before execution
2. Predict based on: message count, average token per message, expected output length (model-specific)
3. If estimated cost > remaining budget × 0.5, trigger proactive switch
4. Report predictions in daily Telegram summary

**E. Reporting & Monitoring**
1. Real-time token usage dashboard (Streamlit UI page: `/token_manager`)
2. Token consumption charts: per-agent, per-provider, per-model
3. Provider health status (green/yellow/red)
4. Daily token usage report via Telegram at midnight IST
5. Weekly/Monthly trend reports showing:
   - Total tokens consumed per provider
   - Switch frequency and reasons
   - Cache hit rate
   - Cost savings from optimization

#### 6.6.2 Token Manager Architecture

```python
# llm_manager/

class TokenManager:
    """Central token management for all agents."""
    
    def __init__(self, db, redis, config):
        self.budgets = BudgetTracker(db, config)     # Per-agent daily budgets
        self.counter = TokenCounter()                # tiktoken + tokenizers
        self.switcher = ProviderSwitcher(self.budgets)  # Provider/model decisions
        self.optimizer = ContextOptimizer(self.cache) # Context pruning + caching
        self.predictor = TokenPredictor(self.counter) # Cost estimation
        self.reporter = TokenReporter(db, config)     # Reports & alerts
    
    # --- Core API (called by orchestrator) ---
    
    async def before_llm_call(self, agent_name: str, messages: list, model_pref: str) -> RouteDecision:
        """Called before every LLM call. Returns route decision."""
        budget = self.budgets.get(agent_name)
        estimated = self.counter.estimate(messages, model_pref)
        
        if budget.remaining < estimated * SAFETY_MARGIN:
            await self.reporter.alert_budget_exhausting(agent_name, budget, estimated)
        
        provider, model = self.switcher.decide(agent_name, model_pref)
        return RouteDecision(provider=provider, model=model)
    
    async def after_llm_call(self, agent_name: str, tokens_used: int):
        """Called after every LLM call. Records usage."""
        self.budgets.record(agent_name, tokens_used)
        if self.budgets.is_critical(agent_name):
            await self.reporter.alert_budget_critical(agent_name)
    
    def count_tokens(self, text: str, model: str) -> int:
        """Accurate token counting using tiktoken + tokenizers."""
        return self.counter.count(text, model)
    
    def optimize_context(self, conversation: Conversation) -> OptimizedContext:
        """Prune, compress, and cache context."""
        if self.counter.count(conversation) > CONTEXT_WARNING_THRESHOLD:
            return self.optimizer.prune(conversation)
        return conversation
    
    async def get_cached_response(self, prompt_hash: str) -> Optional[str]:
        """Check semantic cache before LLM call."""
        return await self.cache.get(prompt_hash)
    
    async def store_cached_response(self, prompt_hash: str, response: str, ttl: int):
        """Store response in semantic cache."""
        await self.cache.set(prompt_hash, response, ttl=ttl)
    
    # --- Reporting ---
    
    async def daily_report(self) -> TokenReport:
        """Generate daily token usage report."""
        return await self.reporter.daily()
    
    async def weekly_report(self) -> TokenReport:
        """Generate weekly token usage report."""
        return await self.reporter.weekly()
    
    async def monthly_report(self) -> TokenReport:
        """Generate monthly token usage report."""
        return await self.reporter.monthly()
```

#### 6.6.3 Token Manager Data Models

```python
# models/token.py

class TokenUsage(Base):
    __tablename__ = "token_usage"
    
    id: UUID
    agent_name: VARCHAR(100)
    provider: ENUM(nvidia, openrouter)
    model: VARCHAR(200)
    input_tokens: INTEGER
    output_tokens: INTEGER
    total_tokens: INTEGER                    # input + output
    cached: BOOLEAN                          # Was this a cache hit?
    response_time_ms: INTEGER
    estimated_cost: FLOAT                    # In USD equivalent
    session_id: UUID
    timestamp: TIMESTAMP

class TokenBudget(Base):
    __tablename__ = "token_budgets"
    
    id: UUID
    agent_name: VARCHAR(100) (unique)
    provider: ENUM(nvidia, openrouter)
    model: VARCHAR(200)
    daily_limit: INTEGER                     # Default: 500,000
    spent_today: INTEGER
    remaining_today: INTEGER
    last_reset: TIMESTAMP
    status: ENUM(healthy, warning, critical, exhausted)
    updated_at: TIMESTAMP

class ProviderCapacity(Base):
    __tablename__ = "provider_capacities"
    
    id: UUID
    provider: ENUM(nvidia, openrouter)
    model: VARCHAR(200)
    tokens_per_minute: INTEGER
    requests_per_day: INTEGER
    currently_available: BOOLEAN
    health_status: ENUM(healthy, degraded, offline)
    last_checked: TIMESTAMP
```

#### 6.6.4 Token Manager GitHub Tools Integration

```python
# llm_manager/counter.py

import tiktoken               # github.com/openai/tiktoken
from tokenizers import Tokenizer  # github.com/huggingface/tokenizers

class TokenCounter:
    """
    Multi-model token counting using industry-standard tools.
    
    - tiktoken for OpenAI/GPT/Gemini models
    - tokenizers for HuggingFace/SentencePiece models
    - transformers for full model-specific tokenizers
    """
    
    MODEL_ENCODERS = {
        "meta/llama-3.1-8b-instruct": "gpt-4",  # tiktoken fallback
        "google/gemma-2-9b-it": "gemma-2",       # tiktoken supports
        "microsoft/phi-3-mini-4k-instruct": "gpt-4",
        "nvidia/nemotron-4-340b-instruct": "gpt-4",
    }
    
    def count(self, text: str, model: str) -> int:
        encoder_name = self.MODEL_ENCODERS.get(model, "gpt-4")
        encoder = tiktoken.encoding_for_model(encoder_name)
        return len(encoder.encode(text))
    
    def count_messages(self, messages: list[dict], model: str) -> int:
        """Count tokens for a full conversation (with message overhead)."""
        encoder = tiktoken.encoding_for_model(self.MODEL_ENCODERS.get(model, "gpt-4"))
        # tiktoken's chat_completions_message_token_cost handles message framing
        return sum(
            tiktoken.chat_completions_message_token_cost(m["content"], role=m["role"])
            for m in messages
        ) + self._overhead(len(messages))
    
    def estimate_response(self, input_tokens: int, model: str) -> int:
        """Estimate output tokens based on model and input length (heuristic)."""
        ratios = {
            "8b": 0.3,    # 8B models tend to produce ~30% of input
            "9b": 0.3,
            "2b": 0.2,    # Smaller models produce shorter responses
            "340b": 0.4,
        }
        ratio = ratios.get(self._size_category(model), 0.3)
        return int(input_tokens * ratio)
```

---

## 7. Telegram Interface

### Commands

| Command | Description |
|---|---|
| `/start` | Welcome message + available commands |
| `/pipeline status` | Current pipeline stage & status |
| `/news` | Manual trigger: Agent 1 fetch news |
| `/create` | Trigger: Agent 2 create content (requires news) |
| `/validate` | Trigger: Agent 3 validate content |
| `/publish` | Trigger: Agent 4 publish (requires approvals) |
| `/run all` | Run full pipeline from current state |
| `/review` | Show pending review items |
| `/approve <id>` | Approve a specific item |
| `/reject <id> <reason>` | Reject with reason |
| `/edit <id> <text>` | Suggest edits (for human modification) |
| `/history` | Show pipeline run history |
| `/config` | Show current settings |
| `/set category <cats>` | Override default categories |
| `/dryrun` | Toggle dry-run mode |
| `/guardian` | Show Guardian status and recent alerts |
| `/guardian report` | Generate Guardian compliance report |
| `/eval status` | Show evaluation status for current run |
| `/eval report <period>` | Show eval report (daily/weekly/monthly) |
| `/dashboard` | Get link to local UI dashboard |
| `/agents` | List all agents and their current status |
| `/tokens` | Show current token usage and budgets (Agent 6) |
| `/tokens budget <agent>` | Show token budget for specific agent |
| `/tokens report <period>` | Show token usage report (daily/weekly/monthly) |
| `/providers` | Show provider status and active models |
| `/switch <agent> <provider/model>` | Manually switch provider/model for agent |

### Human Review Flow

1. When pipeline reaches a review gate, bot sends a Telegram message:
    ```
    📋 CONTENT FOR REVIEW
    
    Stage: Content Creation
    Quality Score: 82/100
    
    [LinkedIn Post]:
    "AI is transforming..."
    
    [Twitter Thread]:
    Tweet 1: ...
    
    🔍 Source: [Link]
    
    ✅ /approve <id>
    ❌ /reject <id> <reason>
    ✏️ /edit <id> <suggestion>
    ```
2. User responds with approve/reject/edit
3. If edit: Agent 2 re-runs with edit instructions as input
4. Bot confirms action and advances pipeline

### Guardian Alert Flow

1. Guardian detects a violation during agent execution
2. **CRITICAL**: Immediate Telegram alert sent to admin
3. **WARN**: Alert queued for next scheduled Telegram status update
4. User can view all alerts with `/guardian` command
5. User can request full compliance report with `/guardian report`
6. All Guardian alerts are logged in PostgreSQL for audit trail

### Token Manager Alert Flow

1. Token Manager detects budget approaching limit (80%)
2. Telegram notification: "⚠️ Token Budget Warning: Agent 1 has used 80% of daily NVIDIA budget"
3. At 95%: Hard stop notification, auto-switch to fallback provider
4. At exhaustion: Queue LLM calls, notify admin for manual decision
5. User can check current usage anytime with `/tokens` command
6. User can force a switch with `/switch <agent> <provider/model>`
7. Daily summary report sent at midnight IST

### Session Management
- Each Telegram chat = one pipeline session (using chat_id)
- Redis stores session state for multi-user support
- Conversation history kept for context

---

## 8. Review & Guardrail System

### Multi-Layer Review Architecture

```
Agent Output
    │
    ▼
┌──────────────────┐     FAIL      ┌────────────────┐
│  Agent Reviewer   │──────────────▶│ BLOCK PIPELINE  │
│  (Automated)      │    WARN       │                 │
│  Score ≥ 75 PASS │──────────────▶│ Log & proceed   │
│  50-74 WARN      │               │ with notes      │
│  < 50 FAIL       │               │                 │
└──────┬───────────┘               └────────────────┘
       │ PASS
       ▼
┌──────────────────┐     REJECT    ┌────────────────┐
│  Human Reviewer   │──────────────▶│ Re-run agent   │
│  (Telegram)       │    APPROVE    │ with feedback   │
│  Manual approve  │──────────────▶│                 │
│  /approve command │               │ Advance pipeline│
└──────────────────┘               └────────────────┘
```

### Guardrails Catalog

| Guardrail | Scope | Enforcement |
|---|---|---|
| Word Limit (Title ≤100, Desc ≤300) | Agent 1 output | Hard truncation + validation rejection |
| Category Scope | All agents | Only allowed categories pass |
| No Fabrication | Agent 1 | Source URL must resolve, claims must cite |
| Content Safety | All | NSFW/violence/hate speech filter |
| Plagiarism < 30% | Agents 2, 3 | Text similarity check (embeddings or hashing) |
| Brand Voice | Agents 2, 3 | Tone analysis via LLM |
| Hashtag ≤5 | Agent 2 | Count check |
| URL Health | Agents 2, 3 | HTTP HEAD request |
| Source Diversity | Agent 1 | Max 2 per domain |
| Recency (≤7 days) | Agent 1 | Date validation |
| Bias Detection | Agent 3 | Sentiment/political leaning analysis |
| Platform Compliance | Agent 4 | API-specific rule checks |
| Rate Limiting | Agent 4 | Track API call counts |

---

## 9. Scheduling Engine

### Schedule (IST = UTC+5:30)

| Cron (IST) | Cron (UTC) | Action |
|---|---|---|
| 0 9 * * * | 0 3:30 * * * | Agent 1 — Fetch news, Agent Reviewer, post to Telegram for human review |
| 0 10 * * * | 0 4:30 * * * | Agents 2–4 — Create, validate, review, publish (if all approvals given) |

### Implementation

```python
# scheduler/tasks.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from config import CONFIG

scheduler = AsyncIOScheduler(timezone="Asia/Kolkata")

@scheduler.scheduled_job("cron", hour=9, minute=0, timezone="Asia/Kolkata")
async def daily_news_fetch():
    """9 AM IST: Fetch news via Agent 1"""
    await run_pipeline_stage("research")

@scheduler.scheduled_job("cron", hour=10, minute=0, timezone="Asia/Kolkata")
async def daily_publish():
    """10 AM IST: Create, validate, and publish content"""
    await run_pipeline_stage("create_and_publish")
```

### Override Mechanisms
- Telegram `/run all` — manual full pipeline trigger
- Telegram `/news` — manual news fetch only
- Environment variable `AUTO_RUN=false` — disable scheduler entirely

---

## 10. Data Models & Persistence

### NewsArticle (PostgreSQL)
```
id: UUID
title: VARCHAR(500)       # Max 100 words stored
description: TEXT          # Max 300 words stored
source: VARCHAR(200)
url: VARCHAR(2000)
published_time: TIMESTAMP
category: VARCHAR(100)
fetched_at: TIMESTAMP
session_id: UUID           # Pipeline run identifier
```

### SocialContent (PostgreSQL)
```
id: UUID
session_id: UUID
news_ids: UUID[]           # Referencing NewsArticle
platform: ENUM(insta, linkedin, twitter)
content_text: TEXT
image_prompt: TEXT         # For Instagram
hashtags: TEXT[]
word_count: INTEGER
quality_score: FLOAT
validation_status: ENUM(pending, passed, failed, revised)
created_at: TIMESTAMP
```

### ReviewRecord (PostgreSQL)
```
id: UUID
session_id: UUID
agent_name: VARCHAR(100)
reviewer_type: ENUM(auto, human)
score: FLOAT
status: ENUM(pass, warn, fail)
feedback: TEXT
approved_by: VARCHAR(200)  # Telegram user name
approved_at: TIMESTAMP
action_taken: TEXT
```

### PipelineState (PostgreSQL)
```
session_id: UUID (PK)
chat_id: BIGINT            # Telegram chat
current_stage: VARCHAR(100)
status: ENUM(running, completed, failed)
news_category: VARCHAR(500)
published_platforms: TEXT[]
publish_results: JSONB
created_at: TIMESTAMP
updated_at: TIMESTAMP
```

### Redis Usage
| Key Pattern | Purpose | TTL |
|---|---|---|
| `session:{chat_id}:state` | Current pipeline state | 7 days |
| `session:{chat_id}:approval` | Approval flags | 7 days |
| `rate_limit:{agent}:{date}` | Daily LLM token tracking | 24 hours |
| `cache:news:{hash}` | Cached search results | 1 hour |

---

## 11. Evaluation System

The Evaluation Engine automatically scores workflow accuracy and content quality using configurable rubrics, then generates beautiful visual reports accessible via the local UI and Telegram.

### 11.1 Purpose

- Verify the pipeline produces accurate, high-quality output
- Score content against defined rubrics across multiple dimensions
- Track agent performance trends over daily, weekly, and monthly periods
- Provide visual reports and dashboards for human reviewers

### 11.2 Rubric Definitions

```python
# integrations/eval_engine.py

RUBRICS = {
    "content_quality": {
        "name": "Content Quality",
        "metrics": [
            {"name": "Factuality", "weight": 0.30, "max_score": 100},
            {"name": "Originality", "weight": 0.25, "max_score": 100},
            {"name": "Readability", "weight": 0.15, "max_score": 100},
            {"name": "Engagement Potential", "weight": 0.15, "max_score": 100},
            {"name": "Brand Voice Consistency", "weight": 0.15, "max_score": 100},
        ],
        "threshold_pass": 75,
        "threshold_warn": 50,
    },
    "workflow_accuracy": {
        "name": "Workflow Accuracy",
        "metrics": [
            {"name": "Agent Scope Adherence", "weight": 0.30, "max_score": 100},
            {"name": "Guardrail Compliance", "weight": 0.25, "max_score": 100},
            {"name": "Data Flow Integrity", "weight": 0.20, "max_score": 100},
            {"name": "Review Gate Effectiveness", "weight": 0.15, "max_score": 100},
            {"name": "Error Recovery", "weight": 0.10, "max_score": 100},
        ],
        "threshold_pass": 80,
        "threshold_warn": 50,
    },
    "news_research": {
        "name": "News Research Quality",
        "metrics": [
            {"name": "Source Diversity", "weight": 0.25, "max_score": 100},
            {"name": "Recency", "weight": 0.20, "max_score": 100},
            {"name": "Relevance to Categories", "weight": 0.20, "max_score": 100},
            {"name": "Description Accuracy", "weight": 0.20, "max_score": 100},
            {"name": "Title Clarity", "weight": 0.15, "max_score": 100},
        ],
        "threshold_pass": 75,
        "threshold_warn": 50,
    },
    "publishing": {
        "name": "Publishing Quality",
        "metrics": [
            {"name": "Platform Compliance", "weight": 0.30, "max_score": 100},
            {"name": "Content Formatting", "weight": 0.25, "max_score": 100},
            {"name": "Hashtag Relevance", "weight": 0.20, "max_score": 100},
            {"name": "Image-Caption Alignment", "weight": 0.15, "max_score": 100},
            {"name": "Publishing Success Rate", "weight": 0.10, "max_score": 100},
        ],
        "threshold_pass": 70,
        "threshold_warn": 45,
    },
}
```

### 11.3 Evaluation Workflow

```
Pipeline Run Complete
        │
        ▼
┌──────────────────┐
│ Eval Engine Runs  │
│ - Scored against │
│   rubrics         │
│ - Per agent       │
│ - Per pipeline    │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ Results Stored    │
│ PostgreSQL + Redis│
│ (cached reports)  │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ Reports Generated │
│ - Telegram summary│
│ - UI dashboard    │
│ - Scheduled report│
└──────────────────┘
```

### 11.4 Evaluation Triggers

| Trigger | Action |
|---|---|
| End of every pipeline run | Full evaluation of that run |
| Daily (after 10 AM IST publish) | Aggregate daily report |
| Weekly (Sunday 11 PM IST) | Weekly comparison report |
| Monthly (last day 11 PM IST) | Monthly performance report |
| Telegram `/eval status` | Current run status |
| Telegram `/eval report <period>` | Specific period report |

### 11.5 Evaluation Report Format (Telegram)

```
📊 EVALUATION REPORT — Daily: 2026-09-18

🎯 Overall Score: 83/100 ✅ (PASS)

┌──────────────────────────────┬────────┬─────────┐
│ Category                     │ Score  │ Status  │
├──────────────────────────────┼────────┼─────────┤
│ Content Quality              │ 85/100 │ ✅ PASS │
│ Workflow Accuracy            │ 88/100 │ ✅ PASS │
│ News Research Quality        │ 79/100 │ ✅ PASS │
│ Publishing Quality           │ 76/100 │ ✅ PASS │
└──────────────────────────────┴────────┴─────────┘

📈 Trends (vs last 7 days avg):
  Content Quality:   ↑ +3.2
  Workflow Accuracy: ↑ +1.8
  News Research:     ↓ -1.5
  Publishing:        ↑ +2.1

🏆 Top Performing: Workflow Accuracy (88%)
⚠️ Needs Attention: News Research (79%, below weekly avg)

🔍 Agent Breakdown:
  Agent 1 (Researcher): 8/10 articles passed guardrails
  Agent 2 (Creator): 5/5 variants within rubric
  Agent 3 (Validator): 5/5 revisions improved scores
  Agent 4 (Publisher): 3/3 platforms published successfully
  Agent Reviewer: 12/12 evaluations completed
  Agent 5 (Guardian): 0 violations detected

📋 Recommendations:
  - News Research: Consider expanding categories for diversity
  - Content Creator: LinkedIn engagement scores trending up

🔗 View Full Report: http://localhost:8501/eval/2026-09-18
```

### 11.6 Eval Engine Implementation

```python
# integrations/eval_engine.py

class EvalEngine:
    """
    Evaluates pipeline runs against configurable rubrics.
    Uses LLM-based scoring for qualitative metrics.
    Uses deterministic checks for quantitative metrics.
    """
    
    def __init__(self, provider: LLMProvider, rubrics: dict = RUBRICS):
        self.provider = provider
        self.rubrics = rubrics
    
    async def evaluate_run(self, session_id: str) -> EvalResult:
        """Full evaluation of a pipeline run."""
        pipeline_data = await self._load_session(session_id)
        results = {}
        for category, rubric in self.rubrics.items():
            results[category] = await self._score_category(
                pipeline_data, rubric
            )
        return EvalResult(
            session_id=session_id,
            category_scores=results,
            overall_score=self._compute_overall(results),
            recommendations=await self._generate_recommendations(results),
            evaluated_at=datetime.now(),
        )
    
    async def _score_category(self, data, rubric) -> CategoryScore:
        """Score a rubric category — LLM for qualitative, code for quantitative."""
        quantitative_scores = self._compute_quantitative(data, rubric)
        qualitative_prompt = self._build_eval_prompt(data, rubric, quantitative_scores)
        llm_scores = await self.provider.generate_structured(
            qualitative_prompt, rubric_schema
        )
        return CategoryScore(
            quantitative=quantitative_scores,
            qualitative=llm_scores,
            weighted_total=self._weighted_total(quantitative_scores, llm_scores, rubric),
        )
    
    async def generate_report(self, period: str) -> Report:
        """Generate aggregated report for period (daily/weekly/monthly)."""
        data = await self._load_period_data(period)
        return Report(
            period=period,
            aggregates=self._aggregate(data),
            trends=self._compute_trends(data),
            agent_breakdown=self._agent_summary(data),
            charts=self._generate_chart_data(data),
        )
```

### 11.7 Eval Database Models

```python
# models/evaluation.py

class EvalResult(Base):
    __tablename__ = "eval_results"
    
    id: UUID                    # Primary key
    session_id: UUID            # Pipeline run
    eval_type: str              # "run", "daily", "weekly", "monthly"
    period_start: TIMESTAMP
    period_end: TIMESTAMP
    overall_score: FLOAT        # 0-100
    category_scores: JSONB      # {content_quality: 85, ...}
    agent_scores: JSONB         # {agent_1: 82, agent_2: 88, ...}
    recommendations: TEXT[]     # List of suggestions
    trend_vs_previous: JSONB    # {content_quality: +3.2, ...}
    report_data: JSONB          # Full report payload for UI
    created_at: TIMESTAMP

class RubricCheckpoint(Base):
    __tablename__ = "rubric_checkpoints"
    
    id: UUID
    session_id: UUID
    agent_name: VARCHAR(100)
    metric_name: VARCHAR(200)
    score: FLOAT
    weight: FLOAT
    weighted_score: FLOAT       # score * weight
    passed: BOOLEAN
    evidence: TEXT              # Why this score was given
    created_at: TIMESTAMP
```

---

## 12. Local UI Dashboard

A Streamlit-based local web UI that provides real-time and historical visibility into all agent activities.

### 12.1 Overview

- **Technology**: Streamlit (zero-config Python web UI, runs locally)
- **Port**: 8501 (configurable)
- **Access**: `http://localhost:8501`
- **Data Source**: PostgreSQL (primary), Redis (real-time cache)
- **Charts**: Streamlit native charts (Bar, Line, Pie) + Plotly for advanced visualizations

### 12.2 UI Pages

#### Page 1: Dashboard (Home)
```
┌───────────────────────────────────────────────────────┐
│  🏠 DASHBOARD              Last Updated: 10:15 IST  │
├───────────────────────────────────────────────────────┤
│                                                       │
│  📊 Today's Pipeline Runs: 2                          │
│  ✅ Completed: 2 | ⏳ Running: 0 | ❌ Failed: 0       │
│                                                       │
│  📈 Quality Score (7-day avg): 83/100                 │
│  🔒 Guardian Alerts Today: 0                          │
│  ⚡ Tokens Used Today: 432,100 / 500,000             │
│  📝 Content Published Today: 12 posts                 │
│                                                       │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐│
│  │ Agent 1  │ │ Agent 2  │ │ Agent 3  │ │ Agent 4  ││
│  │ ✅ PASS  │ │ ✅ PASS  │ │ ✅ PASS  │ │ ✅ PASS  ││
│  │ Score:87 │ │ Score:82 │ │ Score:91 │ │ Score:88 ││
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘│
│                                                       │
│  ┌─ Run History (Today) ─────────────────────────┐   │
│  │ Run #042 | 09:00 IST | ✅ Complete | Score:83│   │
│  │ Run #041 | Yesterday | ✅ Complete | Score:85 │   │
│  └────────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────┘
```

#### Page 2: Agents
- Per-agent cards with current status
- Individual agent detail view:
  - Recent executions with inputs/outputs
  - Token usage over time
  - Success/failure rate
  - Average processing time
  - Last Guardian check result
  - LLM provider and model in use (Agent 6 info)

#### Page 3: Token Manager (NEW)
- Real-time token usage per agent, per provider, per model
- Provider health status (green/yellow/red)
- Daily token budget progress bars (80%, 95% thresholds)
- Provider switch history with reasons
- Semantic cache hit rate
- Context optimization stats (pruned tokens, cached responses)
- Token cost estimates vs actuals
- Token consumption trend charts (hourly, daily, weekly, monthly)

#### Page 4: News Feed
- Latest news fetched by Agent 1
- Filter by category, date, source
- View article details (title ≤100w, description ≤300w)
- See which content was derived from each article

#### Page 4: Content
- All content created by Agent 2
- Preview each variant (Instagram, LinkedIn, Twitter)
- See quality scores and validation status
- Filter by date, platform, status

#### Page 5: Reviews
- All review decisions (auto + human)
- Who approved/rejected what and why
- Review timeline for each pipeline run
- Edit history

#### Page 6: Guardian Alerts
- Real-time alert feed
- Filter by severity (INFO, WARN, CRITICAL)
- Filter by agent
- Alert details with context
- Compliance score over time chart

#### Page 7: Evaluations
- Daily evaluation summaries (today, yesterday, last 7 days)
- Weekly comparison charts
- Monthly trend reports
- Category breakdown (radar chart)
- Agent scoring breakdown (bar chart)
- Download reports (CSV/PDF)

#### Page 8: Settings
- Toggle feature flags
- Adjust pipeline categories
- Set quality thresholds
- Configure Guardian sensitivity
- Manage API keys (encrypted)
- Reset pipeline state

### 12.2 Date Range Filters

All pages support date range filtering:

| Filter | Options |
|---|---|
| Today | Last 24 hours |
| Yesterday | Prior 24 hours |
| Last 7 Days | Rolling weekly |
| Last 30 Days | Rolling monthly |
| Custom Range | Date picker (start → end) |
| Weekly | ISO week selector |
| Monthly | Month selector |

### 12.3 UI Implementation

```python
# ui/app.py

import streamlit as st

st.set_page_config(page_title="Hermes Social Agent", layout="wide")

# Sidebar navigation
page = st.sidebar.radio("Navigate", [
    "🏠 Dashboard",
    "🤖 Agents",
    "📰 News Feed",
    "📝 Content",
    "🔍 Reviews",
    "🛡️ Guardian",
    "📊 Evaluations",
    "⚙️ Settings",
])

# Page routing
if page == "🏠 Dashboard":
    from ui.pages.dashboard import render
    render()
elif page == "🛡️ Guardian":
    from ui.pages.guardian import render
    render()
elif page == "📊 Evaluations":
    from ui.pages.evaluations import render
    render()
# ... etc.
```

### 12.4 Real-Time Updates
- Dashboard auto-refreshes every 30 seconds
- WebSocket-like updates via Redis pub/sub for Guardian alerts
- Telegram notifications mirror important UI events

### 12.5 Running the Dashboard

```bash
# Start dashboard alongside the main application
python run.py --ui

# Or standalone
streamlit run ui/app.py --server.port 8501
```

---

## 13. Implementation Roadmap

### Phase 1 — Foundation (Week 1–2)
- [ ] Set up project structure and virtual environment
- [ ] Install dependencies (`requirements.txt`)
- [ ] Configure PostgreSQL + Redis via docker-compose
- [ ] Implement `config.py` and environment loading
- [ ] Build `providers/nvidia_nim.py` — verify API connectivity
- [ ] Build `providers/openrouter.py` — verify API connectivity
- [ ] Build `providers/router.py` — dual-provider with Token Manager integration
- [ ] Implement `llm_manager/budget.py` — token budget tracking
- [ ] Implement `llm_manager/counter.py` — token counting with tiktoken + tokenizers
- [ ] Implement database models including token models
- [ ] Test LLM calls with both free-tier models
- [ ] Verify token counting accuracy against actual API responses

### Phase 2 — Agent 1 + Search (Week 2–3)
- [ ] Implement `integrations/web_search.py` (DuckDuckGo + BeautifulSoup)
- [ ] Build `agents/researcher.py` with prompt engineering
- [ ] Integrate Token Manager into Agent 1's LLM calls
- [ ] Implement word count enforcement (Title ≤100, Desc ≤300)
- [ ] Create `guardrails/word_limit.py` and `category_filter.py`
- [ ] Test with real news categories, iterate prompts

### Phase 3 — Review + Telegram (Week 3–4)
- [ ] Implement `agents/reviewer.py` with scoring logic
- [ ] Build Telegram bot (`integrations/telegram_bot.py`) with new commands
  - [ ] `/tokens` — token usage and budgets
  - [ ] `/providers` — provider status
  - [ ] `/switch` — manual provider switch
- [ ] Implement approval workflow commands
- [ ] Create session management via Redis
- [ ] Test full research → review → approval flow

### Phase 4 — Agents 2 & 3 (Week 4–5)
- [ ] Build `agents/creator.py` with multi-platform output
- [ ] Build `agents/validator.py` with fact-checking and refinement
- [ ] Integrate Token Manager into Agents 2 and 3
- [ ] Implement `llm_manager/optimizer.py` — context optimization
- [ ] Implement `llm_manager/cache.py` — semantic caching
- [ ] Implement plagiarism detection (simple n-gram or hash-based)
- [ ] Add content safety guardrails
- [ ] Implement `integrations/image_generator.py`

### Phase 5 — Agent 4 + Publishing (Week 5–6)
- [ ] Build `integrations/social_publisher.py` (API clients for IG, LinkedIn, Twitter)
- [ ] Build `agents/publisher.py`
- [ ] Integrate Token Manager into Agent 4
- [ ] Implement rate limiting and retry logic
- [ ] Add dry-run mode

### Phase 6 — Guardian Agent (Week 6–7)
- [ ] Build `agents/guardian.py` — monitoring framework
- [ ] Implement `models/guardian.py` — data models
- [ ] Build Guardian alert system (Telegram integration)
- [ ] Implement Guardian rules engine (scope, tools, tokens, loops)
- [ ] Build Guardian report generator
- [ ] Wire Guardian into orchestrator (intercept agent calls)
- [ ] Test Guardian with simulated violations

### Phase 7 — LLM Token Manager (Week 7)
- [ ] Build `llm_manager/` full module:
  - [ ] `budget.py` — per-agent, per-provider daily budgets
  - [ ] `counter.py` — tiktoken + tokenizers token counting
  - [ ] `switcher.py` — provider/model auto-switching logic
  - [ ] `optimizer.py` — context pruning, compression, summarization
  - [ ] `cache.py` — semantic caching (SHA-256 hash + Redis)
  - [ ] `predictor.py` — token cost prediction before execution
  - [ ] `reporter.py` — daily/weekly/monthly token reports
- [ ] Implement `models/token.py` — TokenUsage, TokenBudget, ProviderCapacity schemas
- [ ] Build `db/repositories/token_repo.py`
- [ ] Integrate Token Manager with `providers/router.py` (TokenAwareRouter)
- [ ] Wire Token Manager into orchestrator (pre/post LLM call hooks)
- [ ] Implement provider downgrade: 8B → 2B models for non-critical tasks
- [ ] Test token budget enforcement and auto-switching
- [ ] Build `/tokens`, `/tokens budget`, `/tokens report`, `/providers`, `/switch` Telegram commands
- [ ] Verify token counting accuracy across all 4 models

### Phase 8 — Evaluation Engine (Week 7–8)
- [ ] Build `integrations/eval_engine.py` — rubric-based scoring
- [ ] Implement `models/evaluation.py` — eval data models
- [ ] Build `db/repositories/eval_repo.py`
- [ ] Create evaluation triggers (end-of-run, scheduled)
- [ ] Build Telegram eval report format
- [ ] Test eval scoring accuracy

### Phase 9 — Local UI Dashboard (Week 8–9)
- [ ] Install Streamlit, Plotly
- [ ] Build `ui/app.py` — main entry point with navigation
- [ ] Build `ui/pages/dashboard.py` — overview with charts + token summary
- [ ] Build `ui/pages/agents.py` — agent monitoring
- [ ] Build `ui/pages/token_manager.py` — token usage & provider monitoring (NEW)
- [ ] Build `ui/pages/guardian.py` — alert feed
- [ ] Build `ui/pages/evaluations.py` — eval reports
- [ ] Build remaining pages (news, content, reviews, settings)
- [ ] Implement date range filters (daily, weekly, monthly)
- [ ] Wire PostgreSQL data sources
- [ ] Test UI end-to-end locally

### Phase 10 — Orchestrator + Scheduling (Week 9–10)
- [ ] Build `pipeline.py` orchestrator with state machine
- [ ] Implement `scheduler/tasks.py` with APScheduler
- [ ] Wire all agents together including Guardian, Token Manager, and Eval
- [ ] End-to-end testing (manual trigger mode)
- [ ] Error handling, logging, and retry logic

### Phase 11 — Polish & Deploy (Week 10–11)
- [ ] Add structured logging (`utils/logger.py`)
- [ ] Add monitoring (pipeline health checks)
- [ ] Write integration tests
- [ ] Dockerize application (Dockerfile)
- [ ] Deploy and monitor first scheduled run
- [ ] Fine-tune token budgets based on real usage data

---

## 14. Dependencies

```txt
# requirements.txt
# LLM & AI
openai>=1.0.0              # Compatible with NVIDIA NIM & OpenRouter OpenAI API
Pillow>=10.0.0             # Image processing (for Instagram upload)

# Token Management (Agent 6)
tiktoken>=0.7.0            # github.com/openai/tiktoken — Fast BPE tokenization
tokenizers>=0.15.0         # github.com/huggingface/tokenizers — Fast tokenizers
transformers>=4.40.0       # github.com/huggingface/transformers — Model tokenizers

# Agent & Orchestration
apscheduler>=3.10.4        # Cron scheduling

# Telegram
python-telegram-bot>=21.0  # Telegram Bot API v21

# Web & Search
duckduckgo-search>=4.0.0   # Web search
beautifulsoup4>=4.12.0     # HTML parsing
httpx>=0.27.0              # Async HTTP client

# Dashboard UI
streamlit>=1.30.0          # Local web dashboard
plotly>=5.18.0             # Interactive charts
pandas>=2.1.0              # Data analysis for reports

# Evaluation
numpy>=1.26.0              # Scoring calculations

# Semantic Caching
xxhash>=3.5.0              # Fast hashing for cache keys

# Database
psycopg2-binary>=2.9.0     # PostgreSQL
redis>=5.0.0               # Redis client
alembic>=1.13.0            # DB migrations

# Config & Validation
python-dotenv>=1.0.0       # .env loader
pydantic>=2.0.0            # Data validation

# Utilities
textstat>=0.7.3            # Text statistics (word count)
fuzzywuzzy>=0.18.0         # Fuzzy matching (plagiarism detection)
python-dateutil>=2.9.0     # Date parsing
structlog>=24.1.0          # Structured logging
```

---

## 15. Environment Configuration

### Updated `.env` Template

```env
# ============================================
# NVIDIA NIM Configuration
# ============================================
NVIDIA_API_KEY=your_nvidia_api_key
NVIDIA_MODEL=meta/llama-3.1-8b-instruct
NVIDIA_BASE_URL=https://api.nvidia.com/v1

# ============================================
# OpenRouter Configuration (free-tier fallback)
# ============================================
OPENROUTER_API_KEY=your_openrouter_api_key
OPENROUTER_MODEL=google/gemma-2-9b-it
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

# ============================================
# Telegram Configuration
# ============================================
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_ADMIN_CHAT_ID=your_chat_id

# ============================================
# Database (PostgreSQL)
# ============================================
POSTGRES_USER=agent
POSTGRES_PASSWORD=agent_password
POSTGRES_DB=social_agent
POSTGRES_HOST=localhost
POSTGRES_PORT=5433

# ============================================
# Cache (Redis)
# ============================================
REDIS_HOST=localhost
REDIS_PORT=6380

# ============================================
# Pipeline Configuration
# ============================================
PIPELINE_CATEGORIES=AI,Machine Learning,IT Sector,Automation,Cloud Computing,Cybersecurity,Software Engineering,Developer Tools,AI Agents,Generative AI,LLM
PIPELINE_TITLE_MAX_WORDS=100
PIPELINE_DESC_MAX_WORDS=300
PIPELINE_MIN_QUALITY_SCORE=75
PIPELINE_RESEARCH_HOUR=9
PIPELINE_RESEARCH_MINUTE=0
PIPELINE_PUBLISH_HOUR=10
PIPELINE_PUBLISH_MINUTE=0
PIPELINE_TIMEZONE=Asia/Kolkata
PIPELINE_DAILY_LIMIT=5000

# ============================================
# Guardian Configuration
# ============================================
GUARDIAN_ENABLED=true
GUARDIAN_SEVERITY=warn         # info, warn, critical
GUARDIAN_ALERT_IMMEDIATE=true   # Send CRITICAL alerts immediately
GUARDIAN_TOKEN_BUDGET_PER_AGENT=500000  # Max tokens per agent per day

# ============================================
# LLM Token Manager Configuration (Agent 6)
# ============================================
TOKEN_MANAGER_ENABLED=true
TOKEN_SAFETY_MARGIN=1.2         # Switch at 1.2x estimated need
TOKEN_BUDGET_DEFAULT=500000     # Default daily tokens per agent
TOKEN_BUDGET_WARNING=0.80       # Warn at 80%
TOKEN_BUDGET_CRITICAL=0.95      # Hard stop at 95%
TOKEN_CONTEXT_WARNING=0.70      # Optimize context at 70% of window
TOKEN_CACHE_TTL_HOURS=1         # Semantic cache TTL for queries
TOKEN_CACHE_TTL_LONG=24         # Semantic cache TTL for templates
TOKEN_CACHE_ENABLED=true        # Enable semantic caching
TOKEN_CACHING_ENABLED=true      # Enable context caching
TOKEN_PROVIDER_SWITCH_AUTO=true # Auto-switch on budget breach
TOKEN_REPORT_HOUR_MIDNIGHT=0    # Daily report at midnight IST
TOKEN_MIN_MODEL_FALLBACK=2B     # Min model size for fallback (2B params)

# ============================================
# Evaluation Configuration
# ============================================
EVAL_ENABLED=true
EVAL_RUN_AFTER_EACH_PIPELINE=true
EVAL_DAILY_REPORT_HOUR=22       # 10 PM IST
EVAL_WEEKLY_REPORT_DAY=sunday
EVAL_WEEKLY_REPORT_HOUR=23      # 11 PM IST
EVAL_MONTHLY_REPORT_DAY=last
EVAL_MONTHLY_REPORT_HOUR=23     # 11 PM IST

# ============================================
# UI Dashboard Configuration
# ============================================
UI_ENABLED=true
UI_PORT=8501
UI_AUTO_REFRESH_SECONDS=30
UI_HOST=0.0.0.0

# ============================================
# Social Media (set after obtaining API credentials)
# ============================================
INSTAGRAM_ACCESS_TOKEN=
INSTAGRAM_APP_ID=
LINKEDIN_ACCESS_TOKEN=
LINKEDIN_APP_ID=
TWITTER_API_KEY=
TWITTER_API_SECRET=
TWITTER_ACCESS_TOKEN=
TWITTER_ACCESS_SECRET=

# ============================================
# Feature Flags
# ============================================
AUTO_RUN=true
DRY_RUN=false
```

### Additional Accounts Needed
| Platform | What You Need |
|---|---|
| **NVIDIA** | API key from [build.nvidia.com](https://build.nvidia.com) (free tier) |
| **OpenRouter** | API key from [openrouter.ai](https://openrouter.ai) (free tier, no payment required for listed free models) |
| **Telegram** | Bot token from @BotFather, User ID from @userinfobot |
| **Instagram** | Meta Developer account + Facebook App + Instagram Graph API |
| **LinkedIn** | LinkedIn Developer Portal App (r_organization_social, w_member_social scopes) |
| **Twitter/X** | Developer Portal App (Basic/Pro tier for API access) |

---

## 16. Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| NVIDIA NIM free tier rate limits exhausted | Medium | High | Implement token budgeting, cache results, stagger calls, failover to OpenRouter |
| OpenRouter free tier rate limits exhausted | Low | High | Both providers with automatic failover, token usage tracking |
| Telegram bot goes offline | Low | High | Heartbeat monitoring, auto-restart, persistent state in DB |
| Social media API changes | Low | Medium | Abstract API calls behind adapter pattern, monitor deprecations |
| AI generates inaccurate content | Medium | High | Multi-stage review, fact-checking, human approval gate |
| Pipeline fails mid-run | Medium | Medium | State machine checkpoints, resume-from-failure logic |
| Timezone/scheduling errors | Low | Medium | Explicit timezone in all cron configs, UTC internally |
| News sources block scraping | Medium | Medium | Fallback RSS feeds, rotate user agents, use official APIs |
| Copyright concerns with AI-generated content | Medium | Medium | Plagiarism checks, disclaimers, human review mandatory |
| Data loss on scheduling overlap | Low | Medium | Lock-based execution (Redis distributed lock), prevent concurrent runs |
| Guardian false positives blocking pipeline | Medium | Low | Guardian alerts are advisory only; human has final override via Telegram |
| Guardian itself goes rogue | Low | Critical | Guardian is read-only by design; prompts version-controlled; watchdog timer monitors Guardian |
| Eval scores are inaccurate | Medium | Medium | Hybrid scoring (LLM + deterministic); eval rubrics are configurable and auditable |
| UI dashboard stale data | Low | Low | Auto-refresh every 30s; Redis pub/sub for real-time updates |
| Token budget exceeded across both providers | Medium | High | Token Manager tracks per-agent budgets; hard stop at limit; proactive switching at 80% |
| Token Manager switches model too aggressively | Medium | Medium | Hysteresis in switch thresholds (80% warn, 95% switch); minimum model size enforced; all switches logged |
| Semantic cache returns stale content | Low | Medium | TTL-based expiration (1h queries, 24h templates); cache invalidation on content updates |
| Context optimization removes critical information | Medium | High | System prompt always preserved; relevance scoring before pruning; human review catches issues |
| Token counting inaccurate across models | Medium | Medium | Dual tokenizer validation (tiktoken + tokenizers); verify counts against actual API response headers |
| All providers exhausted simultaneously | Low | Critical | Request queue with backpressure; Telegram notification; auto-retry at budget reset (midnight IST) |

---

## Summary

This plan delivers a production-grade multi-agent pipeline with:

- **6 specialized agents** (Researcher, Creator, Validator, Publisher, Guardian, Token Manager)
- **Dual LLM providers** (NVIDIA NIM + OpenRouter free-tier models) with automatic failover and smart switching
- **Agent Reviewer** (automated quality gate) + **Human Review** (Telegram) + **Guardian** (safeguard monitoring) — 3-layer review
- **LLM Token Manager** (Agent 6) — token budget tracking, provider/model switching, context optimization, semantic caching, powered by `tiktoken`, `tokenizers`, `transformers`
- **13+ guardrails** enforcing quality, safety, and bounds
- **Evaluation Engine** with rubric-based scoring for content quality & workflow accuracy
- **Local UI Dashboard** (Streamlit) with 9 pages including Token Manager monitoring
- **Telegram integration** for control, review, Guardian alerts, token alerts, and eval reports
- **Daily automation** at 9 AM (news) and 10 AM (publish) IST
- **PostgreSQL + Redis** for persistence and state management
- **11-week phased implementation** with testable milestones

