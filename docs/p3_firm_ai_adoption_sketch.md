# P3 sketch: firm-level AI-tool adoption from posting text (not run)

Status: design sketch only. No data pulled. It follows `docs/did_design.md` (Design B, firm-level adoption).

## Measure
- **Source.** `revelio.postings_cosmos_raw.description` (plus `title_raw` / `jobtitle_translated`), joined to
  `postings_cosmos` on the posting id, for the P2 firm list (`data/firms/firm_list.parquet`). Use US only to start. Chinese
  descriptions would need a separate dictionary (通义/文心/Kimi/DeepSeek/豆包/Copilot, "大模型", "AIGC").
- **Unit.** firm x quarter. Numerator: postings whose description mentions AI coding / LLM tools *as tools the worker uses*.
  Denominator: all postings of the firm (or only its software postings, SOC 15-125x).
- **Dictionary, three tiers, reported separately:**
  1. Named assistants: GitHub Copilot, Cursor, Claude Code, Codex, Windsurf, Tabnine, CodeWhisperer / Amazon Q, Gemini Code Assist,
     ChatGPT, Claude, "AI pair programm*".
  2. Generic usage phrases: "AI-assisted development", "AI coding tools", "LLM-based tools", "prompt engineering",
     "leverage AI tools", "AI-first".
  3. Building AI (kept separate, because it measures AI *products*, not AI *use*): "LLM", "RAG", "fine-tun*", "generative AI", "agents".
- **Server-side.** Use `description ~* '(copilot|cursor ai|claude|chatgpt|...)'` with one month per query, as in 06-12. Word
  boundaries are needed because "Cursor" and "Claude" are also common words and names. Validate by hand on 200 random hits per
  tier (precision) and 200 non-hits from software postings (recall). Report both.

## Use in the design
- **Adopter definition.** A firm adopts in the first quarter where its tier-1+2 share exceeds a threshold, e.g. 2% of its
  software postings, and stays above it for two quarters. Alternatively use a continuous share, pre-registered.
- **Estimation.** Staggered event study of early vs experienced software postings within firm, using Callaway-Sant'Anna or
  Sun-Abraham with not-yet-adopters as controls. Cross it with occupation exposure for a firm-level triple difference.
- **Threats.**
  - Mentioning a tool in a posting reflects both actual adoption and employer branding.
  - Adoption is endogenous to hiring plans: firms that cut junior hiring may also advertise AI tooling.
  - Text length and template changes vary by source, so restrict to LinkedIn-only or company-site postings and control
    for description length.
- **Size.** The description scan is the expensive part: raw text is many GB per month server-side. The output is only
  firm x quarter x tier counts, so it stays well under 100 MB locally.
