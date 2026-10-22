# Vulnerable Test Targets

This directory contains weak and hardened web chat targets for OWASP LLM08 Hidden Context Exposure. Both use a fake prompt and canary only.

- `weak-bot/`: Discloses the planted test system prompt when asked directly.
- `hardened-bot/`: Refuses direct requests for hidden instructions and the canary.

The test suite excludes jailbreaks, impersonation, instruction overrides, obfuscation, and real secret extraction. Test only systems you own or have written permission to assess.
