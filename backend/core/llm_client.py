import logging
import re
import unicodedata
from typing import Optional

from backend.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()



# ── Ollama reachability probe ─────────────────────────────────────────────────

def probe_ollama(timeout: float = 3.0) -> bool:
    """
    Returns True if Ollama is reachable at the configured base URL.
    Hits /api/tags — a lightweight, always-available endpoint.
    """
    import urllib.request
    import urllib.error
    try:
        url = settings.ollama_base_url.rstrip("/") + "/api/tags"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout):
            return True
    except Exception:
        return False


def get_provider_status() -> dict:
    """
    Returns a dict describing the active provider and its reachability.
    Used by GET /api/v1/provider-status.
    """
    provider = settings.llm_provider.lower()
    if provider == "local":
        online = probe_ollama()
        return {
            "provider": "local",
            "model": settings.llm_model,
            "status": "online" if online else "offline",
            "fallback": None,
        }
    elif provider == "openai":
        return {"provider": "openai", "model": settings.llm_model, "status": "configured", "fallback": None}
    elif provider == "google":
        return {"provider": "google", "model": settings.llm_model, "status": "configured", "fallback": None}
    elif provider == "anthropic":
        return {"provider": "anthropic", "model": settings.llm_model, "status": "configured", "fallback": None}
    return {"provider": provider, "model": settings.llm_model, "status": "unknown", "fallback": None}


def _build_gemini_llm(model: str = "gemini/gemini-3.5-flash", api_key: str = ""):
    """Build a Gemini LLM via LiteLLM. Key is passed as a constructor arg, never written to os.environ."""
    from pandasai_litellm.litellm import LiteLLM  # type: ignore
    key = api_key or settings.google_api_key
    kwargs: dict = {"model": model, "timeout": settings.llm_timeout_seconds}
    if key:
        # Pass key as a scoped kwarg rather than mutating os.environ
        kwargs["api_key"] = key
    return LiteLLM(**kwargs)


def build_llm(force_fallback: bool = False):
    """
    Build and return the configured LLM.

    PRIVACY NOTE (Option A decision):
    - When LLM_PROVIDER=local, PandasAI sends up to 10 sample rows to Ollama.
      Since Ollama runs on the same server, data never leaves the host.
    - When LLM_PROVIDER=openai/anthropic/google, sample rows ARE sent to the
      external API. This requires explicit operator consent via config.

    FALLBACK:
    - If LLM_PROVIDER=local and Ollama is unreachable, this function tries each
      server-configured key in order: Google → OpenAI → Anthropic (whichever
      has a non-empty key in .env). Raises only if none are configured.
    """
    provider = settings.llm_provider.lower()

    if provider == "local" or force_fallback is False and provider == "local":
        # Check reachability first; fall back to any configured server key
        if not probe_ollama():
            # Build ordered list of available (provider, key) pairs from .env
            fallback_candidates = [
                ("google",    settings.google_api_key,    "gemini/gemini-2.0-flash"),
                ("openai",    settings.openai_api_key,    "gpt-4o-mini"),
                ("anthropic", settings.anthropic_api_key, "anthropic/claude-3-haiku-20240307"),
            ]
            for fb_name, fb_key, fb_model in fallback_candidates:
                if fb_key:
                    logger.warning(
                        "Ollama unreachable — falling back to %s (%s).", fb_name, fb_model
                    )
                    try:
                        from pandasai_litellm.litellm import LiteLLM  # type: ignore
                        return LiteLLM(
                            model=fb_model,
                            api_key=fb_key,
                            timeout=settings.llm_timeout_seconds,
                        )
                    except ImportError:
                        pass  # try next candidate
            raise RuntimeError(
                "Ollama is not reachable at %s and no fallback API key (Google/OpenAI/Anthropic) "
                "is configured in .env. Start Ollama or add a fallback key." % settings.ollama_base_url
            )
        try:
            from pandasai_litellm.litellm import LiteLLM  # type: ignore
            llm = LiteLLM(
                model=settings.llm_model,
                api_base=settings.ollama_base_url,
                timeout=settings.llm_timeout_seconds,
            )
            logger.info("LLM: Ollama/%s at %s", settings.llm_model, settings.ollama_base_url)
            return llm
        except ImportError:
            raise RuntimeError(
                "pandasai-litellm is not installed. Run: pip install pandasai-litellm"
            )

    elif provider == "openai":
        if not settings.openai_api_key:
            raise RuntimeError("LLM_PROVIDER=openai but OPENAI_API_KEY is not set.")
        try:
            from pandasai_openai import OpenAI  # type: ignore
            llm = OpenAI(api_token=settings.openai_api_key, timeout=settings.llm_timeout_seconds)
            logger.warning(
                "LLM_PROVIDER=openai: PandasAI will send sample rows to OpenAI. "
                "Operator consent required."
            )
            return llm
        except ImportError:
            raise RuntimeError("pandasai-openai is not installed. Run: pip install pandasai-openai")

    elif provider == "anthropic":
        if not settings.anthropic_api_key:
            raise RuntimeError("LLM_PROVIDER=anthropic but ANTHROPIC_API_KEY is not set.")
        try:
            from pandasai_litellm.litellm import LiteLLM  # type: ignore
            llm = LiteLLM(
                model="anthropic/claude-3-haiku-20240307",
                api_key=settings.anthropic_api_key,  # scoped, never writes to os.environ
                timeout=settings.llm_timeout_seconds,
            )
            return llm
        except ImportError:
            raise RuntimeError("pandasai-litellm is not installed. Run: pip install pandasai-litellm")

    elif provider == "google":
        return _build_gemini_llm()

    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {provider!r}. Use: local | openai | anthropic | google")




def configure_pandasai(llm=None, llm_config: dict | None = None) -> None:
    """Configure PandasAI globally. Called per-task with optional per-request override."""
    import pandasai as pai  # lazy — not available on Python 3.14 dev hosts

    if llm is None:
        if llm_config:
            provider = llm_config.get("provider", "").lower()
            model    = llm_config.get("model", "")
            api_key  = llm_config.get("api_key", "")
        else:
            provider = settings.llm_provider.lower()
            model    = settings.llm_model
            api_key  = ""

        if provider in ("openai",) and api_key:
            try:
                from pandasai_openai import OpenAI  # type: ignore
                llm = OpenAI(api_token=api_key, timeout=settings.llm_timeout_seconds)
                logger.info("LLM: OpenAI/%s (per-request key)", model)
            except ImportError:
                raise RuntimeError("pandasai-openai not installed. Run: pip install pandasai-openai")

        elif provider in ("anthropic",) and api_key:
            try:
                from pandasai_litellm.litellm import LiteLLM  # type: ignore
                # Pass key as a scoped constructor arg, not via os.environ
                actual_model = model or "anthropic/claude-3-haiku-20240307"
                if not actual_model.startswith("anthropic/"):
                    actual_model = "anthropic/" + actual_model
                    
                llm = LiteLLM(
                    model=actual_model,
                    api_key=api_key,
                    timeout=settings.llm_timeout_seconds,
                )
                logger.info("LLM: Anthropic/%s (per-request key)", actual_model)
            except ImportError:
                raise RuntimeError("pandasai-litellm not installed. Run: pip install pandasai-litellm")

        elif provider in ("google",) and api_key:
            try:
                from pandasai_litellm.litellm import LiteLLM  # type: ignore
                # Pass key as a scoped constructor arg, not via os.environ
                llm = LiteLLM(
                    model=model or "gemini/gemini-3.5-flash",
                    api_key=api_key,
                    timeout=settings.llm_timeout_seconds,
                )
                logger.info("LLM: Google/%s (per-request key)", model)
            except ImportError:
                raise RuntimeError("pandasai-litellm not installed. Run: pip install pandasai-litellm")

        elif provider in ("local",):
            # Local Ollama — probe first, fall back to any configured server key if down
            if not probe_ollama():
                fallback_candidates = [
                    ("google",    settings.google_api_key,    "gemini/gemini-2.0-flash"),
                    ("openai",    settings.openai_api_key,    "gpt-4o-mini"),
                    ("anthropic", settings.anthropic_api_key, "anthropic/claude-3-haiku-20240307"),
                ]
                for fb_name, fb_key, fb_model in fallback_candidates:
                    if fb_key:
                        logger.warning(
                            "Ollama unreachable — falling back to %s (%s) for this request.",
                            fb_name, fb_model
                        )
                        try:
                            from pandasai_litellm.litellm import LiteLLM  # type: ignore
                            llm = LiteLLM(
                                model=fb_model,
                                api_key=fb_key,
                                timeout=settings.llm_timeout_seconds,
                            )
                            break
                        except ImportError:
                            pass
                if llm is None:
                    raise RuntimeError(
                        "Ollama is not reachable and no fallback API key is configured in .env."
                    )
            else:
                # drop_params=True suppresses LiteLLM's capability-probe (api/show) calls
                try:
                    from pandasai_litellm.litellm import LiteLLM  # type: ignore
                    ollama_model = model or settings.llm_model
                    llm = LiteLLM(
                        model=ollama_model,
                        api_base=settings.ollama_base_url,
                        timeout=settings.llm_timeout_seconds,
                        drop_params=True,
                        extra_body={
                            "options": {
                                "num_ctx": 4096,
                            },
                            "keep_alive": "1h",
                        },
                    )
                    logger.info("LLM: Ollama/%s (per-request)", ollama_model)
                except ImportError:
                    raise RuntimeError("pandasai-litellm not installed. Run: pip install pandasai-litellm")

    pai.config.set({
        "llm": llm,
        "save_logs": True,
        "verbose": False,
        "max_retries": 2,
    })
    logger.info("PandasAI configured.")



# ── Comparison keywords: trigger multi-series hint (Issue 2) ─────────────────

def _strip_accents(s: str) -> str:
    """Remove Unicode diacritics (used for accent-insensitive keyword matching)."""
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')


_COMPARISON_KW = [
    "compare", "comparer", "versus", "vs", "comparaison",
    "par rapport", "between", "entre",
]

# Regex that matches year-range patterns like "2004-2005", "2004–2005", "between 2004 and 2010"
_YEAR_RANGE_RE = re.compile(
    r"(\b\d{4}\s*[-–]\s*\d{4}\b|between\s+\d{4}\s+and\s+\d{4}|de\s+\d{4}\s+[àa]\s+\d{4})",
    re.IGNORECASE,
)


def _is_comparison_prompt(user_prompt: str) -> bool:
    """Return True when the prompt is asking to compare values across groups/periods."""
    text_norm = _strip_accents(user_prompt.lower())
    for kw in _COMPARISON_KW:
        kw_norm = _strip_accents(kw.lower())
        if re.search(rf"\b{re.escape(kw_norm)}\b", text_norm):
            return True
    return bool(_YEAR_RANGE_RE.search(user_prompt))


def build_aggregation_prompt(
    user_prompt: str,
    chart_type: Optional[str],
    columns_info: str,
    provider: str = "",
) -> str:
    """
    Engineer the prompt sent to PandasAI so it returns a DataFrame
    (aggregated data) rather than a matplotlib chart image.

    Chart-type-specific hints steer the LLM toward the exact shape _histogram /
    build_chart_spec downstream expects:
      - histogram  → raw single numeric column (do NOT bin — we bin ourselves)
      - pie/bar/line → (label_col, value_col) with 2 columns, named clearly
      - scatter    → (x_col, y_col) both numeric

    provider: when "local", adds a strict output format block (Issue 1).
    """
    if chart_type == "histogram":
        chart_hint = (
            " The visualization type will be: histogram. "
            "Return a single numeric column containing the RAW individual values — "
            "do NOT pre-aggregate, bin, or group them. We will compute the bins ourselves."
        )
    elif chart_type in ("bar", "line", "pie"):
        chart_hint = (
            f" The visualization type will be: {chart_type}. "
            "Return exactly 2 columns: the first should be the category/label column, "
            "the second the numeric value column. Name the columns clearly."
        )
    elif chart_type == "area":
        chart_hint = (
            " The visualization type will be: area (filled line chart). "
            "Return exactly 2 columns: the first should be the time/category axis column, "
            "the second the numeric value column. Same shape as a line chart."
        )
    elif chart_type == "scatter":
        chart_hint = (
            " The visualization type will be: scatter. "
            "Return exactly 2 numeric columns for the x and y axes."
        )
    elif chart_type == "radar":
        chart_hint = (
            " The visualization type will be: radar. "
            "Return a DataFrame with one categorical column (the spoke labels/dimensions) "
            "and one or more numeric columns (one per series). Each row is one spoke."
        )
    elif chart_type == "heatmap":
        chart_hint = (
            " The visualization type will be: heatmap. "
            "Return a DataFrame with exactly 3 columns: row label (categorical), "
            "column label (categorical), and a numeric value. "
            "This is a long-format (tidy) table — one row per cell in the heatmap."
        )
    elif chart_type == "text":
        chart_hint = ""
    else:
        chart_hint = f" The visualization type will be: {chart_type}." if chart_type else ""

    # Issue 2: if this is a comparison prompt, steer the LLM to return one DataFrame
    # with one column per series rather than multiple separate DataFrames.
    comparison_hint = ""
    if chart_type not in ("text", None) and _is_comparison_prompt(user_prompt):
        comparison_hint = (
            " COMPARISON REQUEST: Return a SINGLE DataFrame where each group/period/category "
            "is a separate column (one row per time-point or label). "
            "Do NOT return separate DataFrames — only ONE combined DataFrame."
        )

    assistant_persona = (
        "You are an intelligent data analysis assistant.\n"
        "For every uploaded dataset:\n"
        "- Automatically inspect the dataset before answering.\n"
        "- Detect all columns, data types, units, and relationships.\n"
        "- Infer the meaning of each column from its name and values.\n"
        "- Never assume fixed column names or a predefined schema.\n"
        "- Never invent columns.\n"
        "- Adapt to any dataset regardless of language (French, English, Spanish, etc.).\n"
        "- Automatically identify dates, categories, numeric values, currencies, locations, percentages, IDs and text fields.\n"
        "- Choose the most appropriate visualization for the user's request.\n"
        "- If the user asks for metrics over time, automatically detect the date column and the metric column.\n"
        "- If multiple columns could match, choose the most likely one based on context.\n"
        "- Only ask for clarification when there is genuine ambiguity.\n"
        "- Never ask for clarification when a single obvious match exists.\n"
        "- Generate charts, KPIs, summaries and insights automatically.\n"
        "- Make the experience feel like ChatGPT Advanced Data Analysis or Power BI Copilot.\n\n"
    )

    if chart_type == "text" or chart_type is None:
        instruction = (
            f"[INSTRUCTION] Answer the following request directly with a clear, helpful text/markdown response.\n"
            f"Do NOT return a DataFrame unless necessary, just the final text answer.\n"
            f"Do NOT generate any plots or charts.\n"
            f"CRITICAL: You MUST end your code by declaring a variable named `result` containing a dictionary with your text answer. Example: `result = {{'type': 'string', 'value': 'Your final answer here'}}`\n"
        )
    else:
        instruction = (
            f"[INSTRUCTION] Return ONLY a pandas DataFrame with the aggregated data "
            f"needed to answer the following request.{chart_hint}{comparison_hint} "
            f"Do NOT generate any plots, charts, or images. "
            f"Do NOT import or use matplotlib, seaborn, plotly, or any plotting library. "
            f"Return just the aggregated data as a DataFrame with meaningful column names.\n"
            f"CRITICAL: You MUST end your code by declaring a variable named `result` containing a dictionary with the DataFrame. Example: `result = {{'type': 'dataframe', 'value': final_df}}`\n"
        )

    # Issue 1: strict output format for small local models (Ollama/LiteLLM local).
    # Cloud models handle the above instructions well; small models need explicit examples
    # and hard prohibitions to avoid returning strings, markdown, or plot calls.
    local_strict_block = ""
    if provider == "local":
        local_strict_block = (
            "\n[STRICT OUTPUT FORMAT — LOCAL MODEL]\n"
            "You MUST write Python code that ends with exactly this pattern:\n"
            "  result = {'type': 'dataframe', 'value': pd.DataFrame({'Category': [...], 'Value': [...]}) }\n"
            "Replace 'Category' and 'Value' with the actual column names from the dataset.\n"
            "ABSOLUTE PROHIBITIONS (your output will be rejected if you do any of these):\n"
            "  - Do NOT wrap code in markdown (no ```python blocks)\n"
            "  - Do NOT use print(), display(), or show()\n"
            "  - Do NOT import or call matplotlib, seaborn, plotly, or any plotting library\n"
            "  - Do NOT return a string — always return a DataFrame in result['value']\n"
            "  - Do NOT return a Python dict — result['value'] must be a pd.DataFrame object\n"
            "  - Do NOT explain your code or add comments\n"
        )

    return (
        f"{assistant_persona}"
        f"{instruction}"
        f"{local_strict_block}"
        f"[Available columns] {columns_info}\n"
        f"[User request] {user_prompt}"
    )


def generate_explanation(
    user_prompt: str,
    chart_type: str,
    result_summary: str,
    llm_config: dict | None = None,
) -> Optional[str]:
    """
    Generate a 1-2 sentence plain-language explanation of a chart result.

    This is an OPT-IN call (controlled by the X-Explain: true header).
    It runs AFTER the chart is already built, so a failure here never
    blocks the chart response.

    Uses the same LLM backend as PandasAI (LiteLLM or OpenAI wrapper),
    called directly via .chat() instead of through PandasAI.
    """
    try:
        prompt = (
            "Tu es un assistant d'analyse de données. "
            "En 1-2 phrases courtes en français, explique ce que montre ce graphique :\n"
            f"- Question de l'utilisateur : {user_prompt}\n"
            f"- Type de graphique : {chart_type}\n"
            f"- Résumé des données : {result_summary}\n"
            "Sois précis et factuel. Ne répète pas la question."
        )
        # Re-use the configured LLM (already set by configure_pandasai)
        import pandasai as pai
        llm = pai.config.get("llm")
        if llm is None:
            return None

        # LiteLLM and OpenAI wrappers both expose .chat()
        response = llm.chat(prompt)
        if isinstance(response, str):
            return response.strip()[:500]
        # Some wrappers return objects with .content or similar
        text = getattr(response, "content", None) or str(response)
        return text.strip()[:500]
    except Exception as exc:
        logger.warning("Explanation generation failed (non-blocking): %s", exc)
        return None


def classify_data_intent(user_prompt: str, column_names: list[str]) -> Optional[bool]:
    """
    Ask the configured LLM whether a user prompt is a data-analysis request.

    Returns:
      True  — LLM is confident this is a data question
      False — LLM says this is NOT a data question (off-topic, greeting, etc.)
      None  — LLM unavailable or failed → caller should fall back to keyword matching

    This is intentionally cheap: max_tokens=5, temperature=0, single short prompt.
    It uses the same LLM that PandasAI is already configured with.
    """
    try:
        import pandasai as pai
        llm = pai.config.get("llm")
        if llm is None:
            return None

        cols_preview = ", ".join(column_names[:10])
        classification_prompt = (
            "You are a routing assistant. Decide if the user's message is a data-analysis "
            "request that could be answered using a dataset with these columns: "
            f"[{cols_preview}].\n"
            "Answer with ONLY the single word YES or NO. No explanation, no punctuation.\n"
            f"User message: {user_prompt}"
        )

        response = llm.chat(classification_prompt)
        if isinstance(response, str):
            answer = response.strip().upper()
        else:
            answer = (getattr(response, "content", None) or str(response)).strip().upper()

        if answer.startswith("YES"):
            return True
        if answer.startswith("NO"):
            return False
        # Unexpected output — fall back
        logger.warning("classify_data_intent got unexpected LLM response: %r", answer)
        return None
    except Exception as exc:
        logger.warning("classify_data_intent failed (will fall back to keywords): %s", exc)
        return None
