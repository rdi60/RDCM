# Third-party skills

The skills in this directory (`banner-design`, `brand`, `design`, `design-system`,
`slides`, `ui-styling`, `ui-ux-pro-max`) are vendored from the
[ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill)
plugin by Next Level Builder, licensed under MIT. Fonts under
`ui-styling/canvas-fonts` are licensed separately under the SIL Open Font
License (OFL); see the `*-OFL.txt` files alongside them.

MIT License

Copyright (c) 2024 Next Level Builder

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

---

The `impeccable` skill (and its `.claude/agents/impeccable-*.md` sub-agents)
is vendored from [pbakaus/impeccable](https://github.com/pbakaus/impeccable)
by Paul Bakaus, licensed under Apache-2.0. Its `.claude/settings.json`
auto-run hook (which would execute a downloaded engine binary after every
Edit/Write and at session end) was intentionally NOT installed — only the
skill, reference docs, and agents, so the detector/commands (`/impeccable
polish`, `audit`, `critique`, etc.) run only when explicitly invoked. The
skill's own launcher script still downloads a checksum-verified platform
binary from GitHub releases on first explicit invocation; see
https://impeccable.style/docs/hooks to opt into the automatic hook later.

Apache License 2.0 — see https://github.com/pbakaus/impeccable/blob/main/LICENSE
for the full text; copyright Paul Bakaus.

---

The skills `accessibility`, `api-design`, `backend-patterns`,
`database-migrations`, `django-patterns`, `django-security`, `django-tdd`,
`django-verification`, `git-workflow`, `postgres-patterns`,
`python-patterns`, `python-testing`, `security-review`, and `security-scan`
are a curated subset vendored from
[affaan-m/ecc](https://github.com/affaan-m/ecc) ("ECC", by Affaan Mustafa),
licensed under MIT. ECC is a much larger agent-harness framework (314
skills, plus hooks that intercept Bash/Write/Edit/MCP tool calls on every
session, governance/secret-scanning capture, and an edit-gating system) —
only these plain-markdown, RDCM-relevant skills were vendored. The
project's `hooks/hooks.json` and the other ~300 unrelated skills were
deliberately NOT installed.

MIT License

Copyright (c) 2026 Affaan Mustafa

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

---

The `security-audit` skill is vendored from
[cloudflare/security-audit-skill](https://github.com/cloudflare/security-audit-skill),
licensed under MIT. It orchestrates a structured, multi-phase security audit
(reconnaissance, coverage-led hunting, candidate validation, independent
verification, reporting) and ships two zero-dependency Node validator
scripts (`validate-findings.cjs`, `validate-coverage-ledger.cjs`) that only
touch the local filesystem — no hooks, no network calls.

MIT License

Copyright (c) 2025-2026 Cloudflare, Inc.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

---

The `find-skills` skill is vendored from
[vercel-labs/skills](https://github.com/vercel-labs/skills) (the official
Vercel Labs `skills` CLI / skills.sh project), licensed under MIT. It is a
pure-instruction skill with no scripts: it teaches the agent to discover and
recommend other skills via `npx skills find`/`npx skills add`.

MIT License

Copyright (c) 2026 Vercel, Inc.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

---

The skills `animate`, `animate-expo`, `animation-performance`,
`animation-vocabulary`, `apple-design`, `ask-sonner`, `break-ui`,
`emil-design-eng`, `find-animation-opportunities`, `improve-animations`,
`mobile-native`, `pick-ui-library`, `prototype`, `remove-animations`,
`review-animations`, and `write-swift` are vendored from
[emilkowalski/skills](https://github.com/emilkowalski/skills) by Emil
Kowalski, licensed under MIT.

MIT License

Copyright (c) 2026 Emil Kowalski

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
