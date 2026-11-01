# Optional module: Firebase features

Identify actual SDK versions, Manifest registrars/providers, managed/native entry points, background jobs, callbacks, and data consumers first. Decide core initialization separately from individual features. Disabling one provider does not justify deleting FirebaseApp, all registrars, or shared Google Task types.

## Options and direct techniques

| Feature | Options and checks |
| --- | --- |
| Core/Installations | Preserve initialization, component discovery, and shared dependencies still in use. Disable/strip only after handling all consumers. Establish actual Installations usage rather than fabricating identities for dependent services. |
| Analytics | Preserve, disable collection, or remove calls within explicit scope. Inspect Manifest `firebase_analytics_collection_enabled=false` and runtime `setAnalyticsCollectionEnabled(false)`. For permanently disabled builds, inspect `firebase_analytics_collection_deactivated=true`. Check persisted overrides and re-enabling calls. [Official configuration](https://firebase.google.com/docs/analytics/android/configure-data-collection) |
| Crashlytics | Preserve, disable automatic reporting, or strip after consumers are gone. Check `firebase_crashlytics_collection_enabled=false`, persisted `setCrashlyticsCollectionEnabled`, and manual `sendUnsentReports`. Disabling automatic reporting may retain local reports; handle uploads/native handlers within scope and verify after restart. [Official behavior](https://firebase.google.com/docs/reference/android/com/google/firebase/crashlytics/FirebaseCrashlytics) |
| Messaging/FCM | Preserve, disable registration/push, or replace with the app's notification mechanism. For automatic initialization, inspect `firebase_messaging_auto_init_enabled=false` together with Analytics collection settings. Trace explicit registration, token retrieval, subscriptions, refresh, and retries; one auto-init flag does not cover explicit calls. [Official initialization](https://firebase.google.com/docs/cloud-messaging/android/get-started#prevent_auto_initialization) |
| Remote Config | Preserve; freeze typed local configuration; or adapt an owned configuration provider. `setDefaultsAsync` supplies defaults but does not globally disable fetch, activate, or real-time updates. Inventory actual keys, types, versions, and startup defaults. [API reference](https://firebase.google.com/docs/reference/android/com/google/firebase/remoteconfig/FirebaseRemoteConfig) |
| App Check | Preserve; replace only the selected Play Integrity provider; or return a contract-complete unavailable result. Preserve other Firebase initialization. When the server enforces attestation, report limits or adapt a user-controlled backend; do not fabricate valid attestation tokens. |
| Auth | Preserve; use a local guest/provider; or adapt an owned identity service. Preserve or explicitly migrate save bindings. Distinguish local users from real remote identities; do not silently erase signed-in data or fabricate ID tokens accepted by the original service. |
| Firestore/Realtime Database | Preserve; use an offline cache containing the required data; replace with local persistence or an owned service. Verify first install, missing documents, pending writes, conflicts, timestamps, and reconnection. Readable cache does not prove complete localization. |
| Storage | Preserve; package/cache selected content; or adapt an owned resource source. Follow the [resource workflow](resources-and-downloads.md), checking authentication, paths, and integrity. Disabling the client SDK does not supply missing resources. |

These flags/APIs are search leads. Actual entry points, names, and precedence depend on the shipped SDK. Older/newer FCM token and registration APIs may differ. Use target-version official documentation and actual method bodies rather than requiring the APK to upgrade to the latest SDK.

## Complete async, state, and retry paths

1. Establish whether callers await a Task, PendingResult, native future, coroutine, or static field. Record success, unavailability, failure, and cancellation separately.
2. When disabling networking, reuse original unavailable/failure paths or complete with the same result type. Do not return never-completing Tasks, invalid non-null tokens, default success, or uninitialized objects.
3. Inspect provider registration, request start, and upper-layer Ready independently. Private `sent`/`initialized` fields may only deduplicate calls. Enumerate reads, writes, and waiters before deciding whether a replacement state is required.
4. Preserve initialization continuations, background-work completion, and thread scheduling for unselected modules. Bound explicit retries/timed refresh to avoid fast failure loops after networking is disabled.
5. Before removing registrars, services, or native libraries, inspect all shared consumers and JNI/reflection paths. Use structured Manifest edits rather than deleting every node/package containing `firebase`.

## Verification

Verify cold startup, updates retaining data, selected-service failures/unavailability, offline caches, foreground/background transitions, and restarts. Check whether a seemingly telemetry-only Ready signal also gates game startup or saves.

No reporting logs, a single disabled metadata flag, or the continued presence of Firebase classes cannot independently prove behavior. Distinguish automatic collection, explicit requests, cached data, background uploads, and code stripping. Report observed network scope, SDK versions, and uncovered paths. Keep untested no-GMS/offline environments explicitly unknown.
