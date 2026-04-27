# 🎵 Model Card: TuneFit 2.0

## 1. Model Name

**TuneFit 2.0** — Conversational Agentic Music Recommender

---

## 2. Intended Use

TuneFit 2.0 is a conversational music recommendation system that accepts natural language input and returns ranked song suggestions with full reasoning transparency. It is designed as a portfolio demonstration of applied AI engineering — specifically how to combine an LLM with a deterministic scoring engine in a way that is auditable, testable, and honest about its own limitations. The system is not intended for production use; the catalog is intentionally small (18 songs) to keep every result manually verifiable. The primary audience is anyone evaluating how an agentic AI pipeline can be structured responsibly.

---

## 3. How the System Works

TuneFit 2.0 runs a four-tool agent loop on every user query:

**Tool 1 — extract_preferences:** The user's natural language message is sent to a Groq-hosted LLM (llama-3.3-70b-versatile), which returns a structured JSON object containing seven preference values: favorite genre, favorite mood, target energy, target acousticness, target valence, target danceability, and target tempo. If the LLM response cannot be parsed, the system falls back to sensible defaults rather than crashing.

**Tool 2 — score_and_retrieve:** The structured preferences are passed to the TuneFit 1.0 scoring engine — a fully deterministic function with no LLM involvement. Each of the 18 catalog songs is scored across seven dimensions (genre match, mood match, energy proximity, acousticness proximity, valence proximity, tempo proximity, danceability proximity), then ranked. A diversity penalty deducts points for repeated artists (−1.5) and repeated genre groups (−0.75) to prevent the top 5 from clustering around one style.

**Tool 3 — evaluate_confidence:** The top results are evaluated for quality. Confidence is calculated as `top_score / 9.0`. Conflicting preferences (high energy + high acousticness, which no catalog song can satisfy simultaneously) are detected directly from the extracted preferences and surface a warning with capped confidence. Additional warnings fire when the preferred genre or mood is absent from any top result.

**Tool 4 — format_response:** The ranked results, confidence level, and any warnings are sent back to the LLM, which writes a 3–4 sentence natural language summary. If this call fails, a hardcoded fallback response is returned instead.

Every tool logs its input and output as a timestamped `ReasoningStep`, which is rendered in the Streamlit UI so users can inspect the full decision chain.

---

## 4. Data

The catalog contains 18 songs spanning 15 genres and 12 moods. Each song has seven attributes: genre, mood, energy (0–1), acousticness (0–1), valence (0–1), danceability (0–1), and tempo in BPM. The distribution is uneven — lofi has three songs, pop has two, and every other genre has exactly one. This means the scoring engine cannot compare multiple options within most genres. The catalog skews toward Western popular music styles; genres common in other markets (reggae, afrobeat, bossa nova, K-pop) are not represented.

---

## 5. Strengths

The system works best when a user's preferred genre is well-represented in the catalog (lofi, in particular, has three songs with consistent audio features and returns high-confidence results reliably). The mood soft-matching logic — where "relaxed" counts as a partial match for "chill" at 0.75 points instead of requiring an exact match — makes recommendations feel more natural than strict binary matching would. The reasoning trace gives users visibility into exactly why each song ranked where it did, which is rare in recommendation systems. The LLM is isolated to language tasks only; it cannot alter which songs appear in the ranked output, which makes the recommendations auditable.

---

## 6. Limitations and Bias

**Genre anchoring:** With one song per genre in most cases, the +2.0 genre bonus permanently locks that song into first place regardless of how poorly its audio features match the user's targets. A user asking for high-energy classical music receives a quiet piano piece at #1 because the genre label outweighs five badly-scored audio dimensions.

**Hand-coded mood groups:** The mood groupings (chill/relaxed/focused, happy/euphoric/energetic, sad/melancholic/moody, etc.) were defined by a single developer based on intuition. They reflect one cultural framing of emotional categories and may not generalize across users or backgrounds.

**LLM non-determinism:** The same natural language input can produce different extracted preferences across runs, meaning identical queries may return different rankings. This is inherent to the LLM layer and cannot be eliminated without caching or mocking.

**LLM conflict smoothing:** When preferences are contradictory (e.g., "high energy but very acoustic"), the LLM tends to resolve the contradiction by producing moderate values rather than faithfully passing the contradiction through. TuneFit 2.0 addresses this by detecting the conflict directly in the extracted preferences before scoring, rather than relying on the score to reveal it.

**Catalog ceiling:** When a user's preferred genre is not in the catalog, the maximum achievable score is 7.0 out of 9.0 (the genre bonus can never fire). The system now surfaces a warning when this happens, but the underlying ceiling is a data problem, not a logic problem.

---

## 7. Evaluation and Testing Results

**Unit tests (`tests/test_recommender.py`):** Five pytest tests run against the scoring engine in complete isolation — no LLM calls, no network, no file I/O. They verify exact match scoring (≥ 8.0 / 9.0), that the genre bonus is worth exactly 2.0 points, that a related-mood match scores 0.75 rather than the 1.5 exact-match bonus, that an unknown genre produces results without raising an exception, and that `top_k` returns exactly the requested number of results. All 5 passed.

**Evaluation harness (`tests/test_harness.py`):** Six end-to-end test cases run through the full live pipeline with real LLM calls. Four semantic cases (chill study, high-energy workout, happy pop, late-night jazz) check that the correct genres and moods surface in the top 3 and that confidence meets a minimum threshold. Two adversarial cases check structural behavior: that an unknown genre triggers a warning, and that conflicting preferences (high energy + high acousticness) trigger a warning and capped confidence. All 6 passed.

**What didn't work initially:** The conflicting-preferences adversarial case originally failed because the LLM smoothed out the contradiction before it reached the scoring engine — producing moderate preference values instead of extreme conflicting ones — so the scoring results looked normal and no warning fired. The fix was to detect the conflict directly from the extracted preferences dictionary before inspecting any scores.

---

## 8. AI Collaboration

**Where AI collaboration helped:** When designing the four-tool pipeline, I originally planned to combine confidence evaluation and response formatting into a single step. A suggestion to separate them — keeping `evaluate_confidence` as a standalone, LLM-free tool that runs before the formatting call — turned out to be the right decision. It meant the confidence logic could be unit-tested independently without any LLM calls, and the reasoning trace in the UI could show confidence as a distinct step with its own input and output rather than a side effect of response generation.

**Where AI gave a flawed suggestion:** An early suggestion to use Streamlit's built-in `st.progress()` component for the song score bars worked functionally but gave no control over bar color. Streamlit's default styling produced a color that conflicted with the amber design theme and visually implied a warning state for high-scoring songs — the opposite of the intended effect. The fix required replacing the component entirely with custom HTML and a CSS gradient bar. The suggestion wasn't wrong about what the component does, but it didn't account for the styling constraints of the design.

---

## 9. Personal Reflection

**What this project taught me about AI systems:** LLMs don't fail loudly. In a purely deterministic system, every bug produces a wrong number, a crash, or an empty result — something obviously incorrect. With an LLM in the pipeline, the model can extract the wrong genre, the scoring engine runs correctly, the confidence looks reasonable, and the output is just slightly off in a way that only registers if you already know the expected answer. Quiet failures are harder to catch than loud ones, and they require a different kind of testing — one that probes the interpretation layer, not just the output.

**How building an agentic system changed how I think about reliability:** Splitting the pipeline into four named, logged tools wasn't just a design preference — it was the only practical way to reason about which part of the system was responsible for a bad output. When a result looked wrong, I could open the reasoning trace and see whether the LLM had misunderstood the input (Tool 1), the scoring engine had correctly ranked a poor catalog match (Tool 2), the confidence evaluator had misjudged result quality (Tool 3), or the response generator had described the songs inaccurately (Tool 4). Without that separation, debugging would have required treating the entire system as a single opaque unit. Reliability in agentic systems isn't a property of the model — it's a property of the architecture around it.

**What I would do differently:** I would write the evaluation harness before writing the orchestrator. Defining pass/fail conditions for edge cases forces clarity about what the system is supposed to do that implementation alone doesn't require. I would also instrument the LLM calls to log every raw response alongside every parsed output from the start — the hardest debugging moments came from trying to reconstruct what the model had actually returned versus what the JSON parser had extracted from it.
