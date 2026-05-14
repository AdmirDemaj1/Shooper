# AutoScout Documentation

Central knowledge base for the AutoScout AI project. Architecture decisions, runbooks, retrospectives.

## Directory Structure

```
autoscout-docs/
├── architecture/
│   ├── adr-0001-fastapi-for-backend.md      # Architecture Decision Records
│   ├── adr-0002-react-native-for-mobile.md
│   ├── system-design.md
│   └── data-flow.md
├── runbooks/
│   ├── source-broken.md                     # How to fix a broken source adapter
│   ├── whatsapp-template-rejected.md
│   ├── database-migration.md
│   ├── deploy-hotfix.md
│   └── incident-response.md
├── guides/
│   ├── local-dev-setup.md
│   ├── database-schema.md
│   ├── adding-a-source.md
│   ├── llm-prompt-workflow.md
│   ├── releasing-mobile-app.md
│   └── twilio-integration.md                 # WhatsApp via Twilio (dev approach)
├── retros/
│   ├── sprint-0-retrospective.md            # Post-sprint learnings
│   ├── sprint-1-retrospective.md
│   └── ...
├── compliance/
│   ├── privacy-policy.md
│   ├── terms-of-service.md
│   ├── legal-review-checklist.md
│   └── albania-dpa-compliance.md
├── brand/
│   ├── tone-voice.md
│   ├── logo-guidelines.md
│   └── color-palette.md
└── README.md
```

## Key Documents

### Architecture Decision Records (ADRs)

ADRs document *why* we chose a technology or approach. Format:

```markdown
# ADR-0001: Use FastAPI for Backend

## Status
Accepted

## Context
We need a Python backend that supports async/await natively and integrates well with the ML/LLM side.

## Decision
Use FastAPI with Pydantic for strict typing.

## Consequences
- Pro: Strong typing, auto-generated docs, fast async handling
- Pro: Large Python community, battle-tested libraries
- Con: Smaller ecosystem than Flask/Django for certain features (handled via third-party packages)
```

### Runbooks

Runbooks are step-by-step playbooks for common operational tasks or incidents.

Example: `runbooks/source-broken.md` — triggered when a source's success rate drops below 80%.

### Retros

After every sprint, the team writes a retrospective:
- What went well?
- What could be better?
- What will we change next sprint?

Stored as `retros/sprint-X-retrospective.md`.

## Contributing

1. **New ADR?** Copy the template from `architecture/adr-template.md` and fill it out. Link it from the index.
2. **New runbook?** Keep steps short and numbered. Assume the reader is stressed and in a hurry.
3. **Retro?** Write it within 24h of sprint end while memories are fresh.

## Linking Between Docs

Use relative links:
```markdown
[See the source-broken runbook](../runbooks/source-broken.md)
```

## Who Owns What?

- **Architecture:** Tech Lead
- **Runbooks:** On-call engineers (update as you fix things)
- **Guides:** The engineer who worked on that feature most recently
- **Retros:** PM (facilitates, but all team members contribute)
- **Compliance:** Legal counsel + PM
- **Brand:** Product Designer
