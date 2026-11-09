# Review public content

Publish source, tests, requirements, and portable documentation only. Keep the following local:

- Virtual environments, extracted native packages, caches, generated agent tooling, and crash dumps.
- Raw benchmark output, logs, traces, application settings, and workstation screenshots.
- Credentials, private keys, recovery material, personal email addresses, and absolute home paths.

The `.gitignore` rules are a first barrier; review the exact staged tree before each public push. Ignored files can still be force-added, and content already committed needs a separate review.

Use a GitHub-provided no-reply address for public commit metadata when keeping a personal email private. Include the required DCO sign-off and preserve any separately configured commit signing.

Run a local secret scan against an export of the proposed tree, then inspect names, addresses, paths, embedded URLs, binaries, and image metadata manually. Do not upload private data to a scanning service. Inspect any screenshot visually and use synthetic data before explicitly approving it for publication.

Before pushing, run the applicable tests, strict OpenSpec validation, and `git diff --cached --check`. After pushing, verify repository visibility, remote commit/tree hashes, and an unauthenticated read of public source. A local commit or successful push command alone is not the final publication check.
