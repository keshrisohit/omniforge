# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

OmniForge is an enterprise-grade, agent-first platform where agents build agents. It enables developers and technical business users to create, deploy, and orchestrate AI agents. The platform is in early development with minimal implementation.

**Dual Deployment Model:**
- **Open Source SDK** - Python library for developers (standalone or platform client)
- **Premium Chatbot-Driven Platform** - No-code interface for creating agents through conversation

**Key Features:**
- Open source Python SDK (use standalone or connect to platform)
- Chatbot-driven no-code agent creation (premium)
- Enterprise-ready (multi-tenancy, RBAC, security)
- Reliable orchestration at scale
- Human-in-the-loop (HITL) capabilities
- Allways use Evals for agents

## Development Commands

### Setup
```bash
# Install package in editable mode with dev dependencies
pip install -e ".[dev]"
```

### Testing

**Default: always run fast tests. Only run slow/full tests when explicitly needed.**

```bash
# Fast tests — unit tests only, no integration/docker/eval (~1 min) ← USE THIS BY DEFAULT
make test

# Full test suite — all tests including integration (~4 min)
make test-full

# Full test suite with coverage report
make test-cov

# Run specific test file
pytest tests/test_<module>.py --no-cov

# Run specific test function
pytest tests/test_<module>.py::test_<function> --no-cov
```

**Test categories:**
- **Fast (default):** unit tests in `tests/` excluding `tests/integration/`, no `docker`/`eval` markers
- **Slow (explicit only):** `tests/integration/` — requires running services (Docker, real DBs, OAuth)

### Code Quality
```bash
# Format code (auto-fixes)
black .

# Lint code
ruff check .

# Lint with auto-fix
ruff check . --fix

# Type check
mypy src/
```

## Architecture

The project follows a **strict separation** between frontend and backend:

```
omniforge/
├── frontend/              # ALL frontend code (React/Next.js)
│   ├── app/              # Next.js App Router pages
│   ├── components/       # React components
│   ├── lib/              # Frontend utilities, hooks, API client
│   ├── types/            # TypeScript types
│   ├── __tests__/        # Frontend tests
│   └── coding-guidelines.md
│
├── src/omniforge/        # Backend Python code
│   ├── agents/           # Agent domain
│   ├── orchestration/    # Orchestration layer
│   ├── security/         # RBAC, auth, multi-tenancy
│   └── ...
│
├── tests/                # Backend tests (mirrors src/)
├── specs/                # Product specs and plans
└── coding-guidelines.md  # Backend coding guidelines
```

### Frontend-Backend Separation (CRITICAL)

**ALL frontend code MUST stay in `frontend/` folder:**
- ✅ React/Next.js components, hooks, utilities
- ✅ TypeScript types for frontend
- ✅ Frontend tests
- ✅ Tailwind configs, styles, assets

**Backend and frontend communicate ONLY via APIs:**
- ❌ Never import backend code into frontend
- ❌ Never import frontend code into backend
- ❌ Never share code between frontend and backend
- ✅ Use REST APIs or GraphQL for all communication

### Configuration Notes

**Backend (Python):**
- **Python version**: Requires Python 3.9+
- **Line length**: 100 characters (enforced by black and ruff)
- **Type checking**: mypy configured with `disallow_untyped_defs = true`
- **Test coverage**: pytest runs with coverage by default
- See `coding-guidelines.md` for backend standards

**Frontend (Next.js/React):**
- **Framework**: Next.js 14+ with App Router
- **Language**: TypeScript (strict mode)
- **Styling**: Tailwind CSS + CSS Modules
- **Testing**: Vitest + React Testing Library
- See `frontend/coding-guidelines.md` for frontend standards

## Development Workflow with Sub-Agents

When working on features or changes, use the following sub-agent workflow:

### 1. Specify (product-spec-architect)
Use for creating product specifications that capture user needs and requirements.
- Translate high-level ideas into structured specifications
- Define user journeys and success criteria
- Document what you're building from a user perspective
- Always save the specification in the `specs/` folder

### 2. Plan (technical-plan-architect)
Use for translating product requirements into technical implementation plans.
- Design technical architecture and approach
- Choose appropriate patterns and technologies
- Create comprehensive technical specifications
- Consider multiple architectural variations when needed
- Always save the plan in the `specs/` folder
- Revisit and ensure that you are not over-complicating things.


### 3. Task (task-decomposer)
Use for breaking down specifications into concrete, implementable tasks.


**Task Content:**
- Keep task descriptions concise and actionable (10-30 lines per file)
- Include what needs to be built and key requirements
- Avoid excessive implementation details - trust the executor agent
- Organize tasks in the `specs/tasks/feature-xxx` folder

### 4. Implement (focused-task-executor)
Use for executing specific, well-defined tasks from the decomposed plan.
- Implement all the task following the coding guidelines in coding-guidelines.md
- Work on focused, manageable chunks of code
- Implement one task at a time
- Ensure each task is completed before moving to the next
- Ensure that you do not break any existing functionality

### Workflow Example
```
User Request → Specify (create spec) → Plan (technical design) → Review (validate plan) → Task (decompose) → Implement (execute tasks)
```

This structured approach ensures clear requirements, solid architecture, and maintainable implementation.

**Ask for confirmation after each spec, plan, review, task and implement step to ensure that the sub-agent is following the workflow.**

**Do a git commit of the feature after each feature development.**

**Always ask for confirmation after each spec, plan, review, task and implement step to ensure that the sub-agent is following the workflow.**
**Always ask questions, call out tradeoffs of selected approach and brainstorm first before getting deep into implementation.**

**MUST Do - Run `make test` (fast tests) after every change to validate. Only run `make test-full` when integration behavior is affected. Do a git commit after each feature development.**

**Do not create unwanted documents in the project. Also dont explain everything in the documents.**
