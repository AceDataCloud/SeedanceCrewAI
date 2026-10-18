# Seedance by Ace Data Cloud for CrewAI

Independent native **Seedance** video tools for CrewAI. Provided by **Ace Data Cloud**, not an official Seedance or CrewAI product. This is a standalone service package; no all-services bundle or generic provider setup is required.

[简体中文](readme/README_zh_Hans.md) · [Current models and prices](https://platform.acedata.cloud/models?utm_source=github&utm_medium=referral&utm_campaign=evergreen&utm_content=seedancecrewai_readme_pricing)

## 1. Install the stable release

The Ace-maintained **Seedance** native CrewAI tools are merged on main and released as **0.1.0**. This is a standalone service package. It is **not an official CrewAI/AMP catalog listing**, and no PyPI publication is claimed yet. Install the public wheel with its exact SHA256:

```bash
uv add 'crewai-seedance @ https://github.com/AceDataCloud/SeedanceCrewAI/releases/download/v0.1.0/crewai_seedance-0.1.0-py3-none-any.whl#sha256=3b0f4decb7b5e85775e5461c8d433c0976f6316cbc4e4d2e202fd1d14f8ee1da'
```

Or install the exact merged source:

```bash
uv add 'crewai-seedance @ git+https://github.com/AceDataCloud/SeedanceCrewAI.git@8c5ed37d28f2110987d478ed5010df39907b929e'
```

[Stable release](https://github.com/AceDataCloud/SeedanceCrewAI/releases/tag/v0.1.0) · [Merged source](https://github.com/AceDataCloud/SeedanceCrewAI/commit/8c5ed37d28f2110987d478ed5010df39907b929e). Tags and pages are informational; the immutable source SHA or wheel SHA256 binds the artifact. Historical previews remain unchanged and are not the recommended version. When an existing authorized PyPI publisher can publish after the shared new-project quota resets, the normal `uv add crewai-seedance` command will become available; do not assume publication before registry readback.

CrewAI requires Python3.10–3.13. Complete Linux installation, tests and clean-wheel checks passed. Intel macOS may lack the mandatory lancedb wheel; use a supported Linux environment instead of skipping dependencies for production.

## 2. Register / sign in and get your own API Token

1. Open [Ace Data Cloud → Applications](https://platform.acedata.cloud/console/applications?utm_source=github&utm_medium=referral&utm_campaign=evergreen&utm_content=seedancecrewai_readme_api_key); register and sign in. If needed, choose **Initialize General Application**.
2. Open **General application**, check **Seedance** service access, current model price and balance. A service-specific application can only use its entitled service.
3. Copy the selected API Key using icon **1**, or **Manage Keys** **2** → **Create** for a separate `Seedance CrewAI` key.

![Copy Key or open Manage Keys; authentic screenshot with credentials redacted](assets/tutorial/get-api-key-en.png)

4. Configure expiration and usage limits only as needed. If **Allowed APIs** is enabled, include both `/seedance/videos` and `/seedance/tasks`.

![Create a separate credential; historical example name](assets/tutorial/create-api-key-en.png)

Historical authentic Ace screenshots reused unchanged from SunoDify commit `8d3d03570e73324220f111f7fe343da0792a8071`, retrieved 2026-10-18. The second image's old name `Dify tutorial` is an example only: use `Seedance CrewAI`. No visible real credential is included; [image sources](assets/tutorial/source.json).

Set the raw consumer Token in environment variable `ACEDATACLOUD_API_KEY` through secure terminal input or a secret manager. It is not a `platform-...` management Token and must not include `Bearer `, spaces or quotation marks. Never place it in prompts, screenshots, committed `.env` or workflow exports. `api_key=...` may be supplied from secure credential storage and is excluded from serialization.

## 3. Add the named native tools

```python
from crewai import Agent
from seedance_crewai import SeedanceGenerateVideoTool, SeedanceRetrieveTaskTool

agent = Agent(
    role="Seedance producer",
    goal="Create the approved media, then retrieve the original task result",
    backstory="Use Seedance through Ace Data Cloud within the user's approved budget.",
    llm=your_configured_llm,
    tools=[SeedanceGenerateVideoTool(), SeedanceRetrieveTaskTool()],
    allow_delegation=False,
    max_retry_limit=0,
)
```

The two discoverable tool names are **Seedance by Ace Data Cloud - Generate Video** and **Seedance by Ace Data Cloud - Retrieve Task**. The Token goes in the environment, not a custom MCP header or agent prompt. Adding tools does not execute them. The caller approves paid requests; generation defaults to one use per instance to reduce duplicate submissions, which is not a funds cap or a permission system.

## 4. Service-specific input and first use

Structured `content`: text, image URL (+ first/last/reference role), audio URL (+ reference_audio), video URL (+ reference_video). Lowercase `resolution` (`480p/720p/1080p/4k`), `ratio`, optional duration -1..30, frames, seed, camerafixed, watermark, generate_audio and return_last_frame. Availability and valid combinations depend on the selected public model. This package does not expose web search, callbacks, expiry, priority or provider admin fields.

Check [the current model catalog and price](https://platform.acedata.cloud/models?utm_source=github&utm_medium=referral&utm_campaign=evergreen&utm_content=seedancecrewai_readme_first_use) before calling; model IDs are passed unchanged and no substitute model is added. The following values are examples from the pinned current API contract, not permanent defaults. **Executing generation is billable**; this guide does not run it.

```python
import json
from seedance_crewai import SeedanceGenerateVideoTool, SeedanceRetrieveTaskTool

parameters = {
    "model": "doubao-seedance-2-0-mini-260615",
    "content": [
        {
            "type": "text",
            "text": "A calm sunrise over a mountain lake"
        }
    ],
    "resolution": "480p",
    "ratio": "16:9",
    "generate_audio": False
}
# BILLABLE when executed; approve the current model and budget first.
submitted = SeedanceGenerateVideoTool().run(**parameters)
submitted = json.loads(submitted)  # A ToolFailure must be handled before this step.
task_id = submitted["task_id"]
result = SeedanceRetrieveTaskTool().run(task_id=task_id, wait_seconds=240)
print(result)
```

The request submits once with `async=true`. accepted/pending is **not** a terminal result, even when an envelope has success=true. Preserve the original task ID; pending, timeouts or unknown submission outcomes do not authorize another generation. Bounded wait only queries that same ID, and can include an in-flight request timeout. Continue using Retrieve Task until terminal status. A true completed response requires the stored finished_at, service success and a valid target media URL. Nested failed states are treated as failure; a missing terminal media link is not fake success.

For a task you already own, run only this read-only example:

```bash
uv run python examples/query_existing.py YOUR_EXISTING_TASK_ID
```

The query is `POST /seedance/tasks` with `action=retrieve,id=...`. A completed result returns `status=succeeded`, `success=true`, `task_id`, filtered `media_urls` and original `cost` in Credits when present. No raw original prompt, request, account/application identity, internal diagnostics or unfiltered body is returned. `cost` is not a new bill or USD amount. URL presence does not verify ongoing media playback.

## 5. Inspect execution and output

![Official historical CrewAI execution trace; not this service or Ace runtime evidence](assets/tutorial/official-crewai-tracing.png)

Official [CrewAI tracing reference](https://docs.crewai.com/en/observability/tracing), historical date marker 10/1/2025, capture version unspecified; retrieved 2026-10-18. Left: task and tool timeline; right: expanded Response output, not input. **Not this package running, not an Ace task and not a promised new GUI.** Trace account/auth/consent is optional and not enabled by this package. For your actual run inspect the named tool and its returned terminal fields; never expose Token or private media URLs in screenshots.

## Troubleshooting, privacy and cost

| Result | Action |
|---|---|
| 401 / 403 | Check full raw consumer Token, expiration, service entitlement, Allowed APIs and balance. A 403 is not always moderation. |
| 400 / schema rejection | Follow this service's fields, casing and model capability; unknown cross-service fields are rejected before network. |
| pending / no media yet | Query the same original task ID; never regenerate to poll. |
| 429 | Reduce concurrency and wait. One HTTP attempt per operation; your configured LLM/agent may retry separately. |
| Timeout / 5xx | Submission outcome can be unknown. Inspect request history before creating another task. |
| ToolFailure | Failed task or invalid terminal media; structured non-retryable result. Preserve task/trace ID for support, never Key. |
| Result URL cannot open | Check terminal success and your network; link existence alone is not playback evidence. |

The code is free; media generation and the LLM you configure have their current prices. No payment handler, fallback or automatic paid HTTP retry is added. Original Credits cost follows the API's current package/account rate and discounts; this package does not hard-code USD conversion. No install/CI count is presented as users or revenue.

Provided prompts/references and the consumer Token are sent to `api.acedata.cloud` over HTTPS. The package adds no telemetry or tracing; CrewAI/your LLM may have separate settings. [Privacy](PRIVACY.md). [Source](https://github.com/AceDataCloud/SeedanceCrewAI) · [Issues](https://github.com/AceDataCloud/SeedanceCrewAI/issues) · dev@acedata.cloud

Development: `uv sync --group dev`, `uv run pytest`, `uv run ruff check .`, `uv build`. Paid HTTP is mocked in tests; native Agent/Task/Crew cycles use a deterministic local model fixture. See `tests/contract-source.json` for immutable service contract provenance and `tests/live-readonly-evidence.json` when an old-task check is available. No new paid request runs in CI.
