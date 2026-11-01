# Optional module: ads, mediation, and rewards

## Choose behavior and reward policy first

| Mode | Actual treatment |
| --- | --- |
| Preserve | Retain ads and their original reward, dismissal, and consent flows; handle only other selected modules. |
| Disable selected formats | Specify banner, interstitial, app-open, native, rewarded video, or other selected formats. Prevent their loading/display/refresh and entry points; preserve other formats as chosen. |
| Disable the whole SDK | Handle explicit initialization, Manifest automatic entry points, managed/native/JNI wrappers, preloading, timers, and background work. Give consumers complete unavailable/failure results. |
| Strip code/resources/libraries | Remove after proving no shared dependencies or dynamic references, then rebuild and verify at runtime. Record disabled entry points separately from complete stripping. |

Choose rewarded ads independently: preserve original ad/reward behavior; report unavailable and follow original normal failure/fallback paths; or implement a local reward alternative explicitly requested by the user. Ordinary ad removal does not automatically authorize extra rewards, free revivals, or economy changes.

If a plan asks to disable the entire SDK while retaining its real rewarded ads, resolve the dependency conflict first: retain required formats/adapters or explicitly choose a local alternative. Do not describe remotely verified capabilities as preserved without evidence.

Implement and test local reward alternatives in the game's settlement layer, preserving counts, amounts, cooldowns, persistence, and idempotency. Do not falsely report impressions, clicks, qualified views, or signed receipts to an ad platform. Real SSV/server rewards require separate adaptation; a local callback is not remote confirmation.

## Locate and modify

1. Trace the application ad manager/factory through the actual SDK, each enabled mediation adapter, and Manifest entry points. Include providers, services, receivers, Activities, native/Unity plugins, and background jobs. Search terms only identify candidates.
2. Inspect startup, between-level transitions, foreground resume, periodic refresh, load-failure retries, cached-ad display, and resource preloading. Hiding a View does not prove loading/networking stopped.
3. Choose the smallest boundary: format factory, app provider, load/show adapter, or complete SDK initialization. Multiple SDKs/adapters may start independently; handle the actual activation graph.
4. Preserve shared foundations such as Google Task, Firebase core, AndroidX/WorkManager, and game services. Prove the absence of consumers before deleting them. Only independent selected-SDK components enter the removal plan.
5. Deliver appropriate load/show unavailable results according to original bridge serialization, threads, and consumer state. End waits and restore input, audio, pause state, and button availability. A bare return or contradictory success/failure events is insufficient.

## Reward and dismissal are different callbacks

Rewards, display failures, dismissal, and impression/revenue reports are distinct events. Dismissal does not directly mean a reward was earned. Google Mobile Ads Unity, for example, exposes separate reward, full-screen-closed, and full-screen-failed interfaces. Verify event names and lifecycles against the target version. [Official rewarded ad workflow](https://developers.google.com/admob/unity/rewarded)

Complete each request with its contractually correct terminal result. If multiple events are required, verify ordering and consumers rather than universally emitting failure followed by dismissal. Check whether failure listeners reload immediately and prevent infinite retries after disabling ads.

Before removing a consent/privacy SDK, establish that it has no other consumers. Do not bypass the flow by automatically granting tracking consent. Personalization, identifier collection, attribution, and ad loading are separate controls; handle the selected scope individually.

## Verification

Cover startup, before/after levels, foreground resume, failure/cancellation, cached ads, no-fill, and rewarded entry points. Record completion counts, callback threads, UI recovery, reward changes, cooldowns, and state after restart.

For loading tests, use the target SDK's test mode/test units. Automated tests must not generate real ad clicks or paid events. Verify disabling through entry points, scheduling/retries, and network observation within the permitted scope. Missing logs do not prove no requests occurred.

Report actual SDK/adapter treatment, preserved formats, reward policy, shared components, and remaining dependencies. Assess full offline capability together with [downloads](resources-and-downloads.md), [Firebase](firebase.md), and the game's business backend.
