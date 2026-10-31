# Diagnose and restore protected Unity/IL2CPP initialization

Use this guide only when protected initialization has been established. Ordinary Unity targets should not automatically enter dynamic decryption or kernel capture workflows.

## Verify Java and native layers separately

Java startup may decrypt static Strings, initialize reflected Methods, and load helper DEX files. A null method after making a VM inert does not prove Unity itself is missing. Compare fields, class loaders, and call chains in an unmodified runtime first.

Record field signatures, exact string values, each Method's declaring class and parameter types, and helper DEX hashes. After compilation, verify actual DEX static values rather than only generated smali text. Restoring the main Activity does not restore other virtualized broadcast, service, Bluetooth, or sharing methods; list uncovered entry points individually.

Inventory the native layer:

- `DT_NEEDED`, `DT_INIT`, `INIT_ARRAY`, and constructor call order.
- Dynamic symbols, PLT/GOT, RELA/RELR/packed relocations, and ELF load segments.
- Rewritten code, encrypted `.data`, metadata usage tokens, TLS, static registries, and default values.

Resolved exports in an unmodified runtime can help identify missing imports, but restore portable symbols and relocations rather than writing process-specific absolute addresses into ELF. Check same-address exports, IFUNC, and aliases against their actual contracts. Equal addresses do not prove interchangeable symbols.

Direct restoration procedure:

1. Preserve original dynamic tables, symbol tables, relocations, code, and file positions for target GOT/data slots. Record mappings and slot values from the unmodified runtime.
2. Attribute resolved addresses to actual modules/exports. Use call sites to distinguish functions, data, aliases, and IFUNC; retain ambiguous entries as unknown.
3. Generate required dynamic strings, symbols, and ABI-appropriate symbolic relocations. Repair dynamic-table references and necessary file/load-segment layout. Handle Android packed relocations, RELR, TLS, and relative relocations separately; do not replace them all with function PLT entries.
4. Restore decrypted code and static data from the correct stage. Preserve loader-managed relocation semantics rather than freezing current absolute addresses into initial values.
5. Remove protection dependencies/initializers only after proving they no longer perform required work. Independently check dependencies, symbol identities, relocation ranges, load-segment congruence, and target page alignment, then compare startup without an attached observer.

## Distinguish initial values from runtime state

Late memory snapshots can reveal code, exports, and resolved imports. Late `.data` may contain heap addresses, object pointers, locks, allocator state, and thread indexes. Copying it wholesale produces a file valid only in its source process.

If protection `DT_INIT` decrypts data before normal constructors run, **after DT_INIT returns and before INIT_ARRAY starts** is a useful candidate capture boundary. Prove it from actual control flow: protection may invoke constructors itself or defer initialization, making the boundary name insufficient.

For each candidate, record source hash, module/load base, captured RVA/size, stopped PC, actual initialization function, thread, stop state, capture method, tracing attachment, and code modifications. Verify mapping/ELF identity and handle relocation slots throughout the captured range.

Restoration output must establish:

1. Non-relocated data came from the correct stage, and relocated locations use portable ELF mechanisms.
2. No process-specific pointers remain. Mark uncertain fields individually; do not fill gaps with guessed values and declare completion.
3. Independently recoverable tokens, constant tables, and initialization templates agree with captures.
4. Data restoration did not accidentally alter code/import repairs. Track feature patches separately and verify their input bytes.

Source defaults, values reset to zero after startup, and plausible physical parameters do not necessarily equal initial values in the compiled target. Semantic reconstruction produces candidates that require validation against actual initial values or equivalent behavior.

## Escalate capture methods according to evidence

Start with ordinary tools that answer the specific gap. If a debugger or injection makes the original fail at startup, record the difference and change approach instead of repeating the same attachment. Retain an original-package control without attached tools.

If ordinary Frida/LLDB observation cannot reach the required stage, an alternative in a task-owned AOSP ARM64 environment with suitable permissions is external perf hardware execution events plus BPF-generated SIGSTOP, followed by external reads of `/proc/PID/mem`. This can avoid injected app modules and ptrace attachment, but its actual effects still need recording. See [tools-and-environment.md](tools-and-environment.md) for NDK, debugger, device permission, and kernel prerequisites.

This is an **environment-specific fallback** requiring verified kernel capability, access permissions, register layout, linker build, and actual disassembly. The skill does not ship a universal capture program. Do not automatically root the user's device or change its security settings.

### Repeated ARM64 perf+BPF breakpoint hits

ARM64 execution breakpoints in Linux/Android kernels may depend on `is_default_overflow_handler` to single-step over the original instruction automatically. If installing a BPF handler changes that condition, returning 0 or 1 for a non-target event may not restore stepping and can repeatedly trigger the same PC. Check the current kernel implementation and hit counts before adopting a workaround.

Primary reference: [Linux v6.1 arm64 hw_breakpoint.c](https://github.com/torvalds/linux/blob/v6.1/arch/arm64/kernel/hw_breakpoint.c). Inspect `breakpoint_handler`, `is_default_overflow_handler`, and `user_enable_single_step`; recheck other kernels independently.

Where instruction and event conditions permit, use an external two-PC gate:

1. Stop this process at the PC after initialization returns and save registers.
2. If it is not yet the target module, disable events while all threads are stopped, move the breakpoint to the next actual instruction, re-enable events, and resume.
3. Stop again before that next instruction executes, restore the original check PC, then resume.
4. Capture only at the original check PC after verifying target module identity, initialization address, and data stage.

Select verified ordinary instructions. The next PC must not cross the capture boundary or invoke the next stage. Do not mechanically use `PC+4` for branches, compressed instruction sets, or unanalyzed instructions. Keep parent/child events, new threads, and current gate addresses consistent.

Prefer target-thread events with inheritance/new-thread handling. Even when BPF filters other PIDs, CPU-wide events can repeatedly trap unrelated processes sharing the linker address. TGID filtering alone does not eliminate this impact.

Relocate initialization calls, return points, and successor instructions for each linker build; compute runtime addresses from actual load bases. Library-specific initialization wrappers may offer other post-call locations, but event timing, module identity, and constructor boundaries still require proof.

## Completion criteria

Before building, audit restored imports, dependencies, initializers, load segments, alignment, relocations, and static data. Retain SHA-256 inventories and label outputs with unrestored data as diagnostic builds.

Native restoration, feature patches, signing, and actual runtime evidence must correspond to the same artifact before delivery. Startup without GMS/network, specific level behavior, and save/restart verification are required evidence for those capabilities. Keep untested callbacks and chapters explicitly unknown.
