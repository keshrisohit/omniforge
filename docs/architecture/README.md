# OmniForge Architecture Documentation

This directory contains comprehensive architecture documentation for the OmniForge platform.

## Documentation Index

### 🎯 [System Overview](./system-overview.md)
**Start here for a high-level understanding**

A simplified view of the OmniForge architecture covering:
- 5-layer architecture (Presentation → Application → Platform Services → Infrastructure → External)
- Simplified component diagram
- Data flow examples
- Technology decisions
- Deployment models
- Recent milestones and roadmap

**Best for**: Product managers, new developers, stakeholders

---

### 🔧 [Component Diagram](./component-diagram.md)
**Detailed technical architecture**

Comprehensive component-level architecture including:
- All 20+ backend modules with relationships
- API gateway and middleware stack
- Domain-driven design layers
- Infrastructure services
- External integrations
- Architecture patterns used

**Best for**: Senior developers, architects, technical leads

---

### 🛠️ [Skill Creation Flow](./skill-creation-flow.md)
**Deep dive into the skill creation system**

Detailed documentation of the FSM-based skill creation system:
- 11-state finite state machine diagram
- Component interaction flows
- Sequence diagrams for complete creation flow
- Pattern detection logic
- Path normalization examples
- LLM prompt structures
- Performance metrics

**Best for**: Developers working on skills, AI/LLM integration developers

---

## Quick Reference

### System Statistics (as of Feb 2026)

| Metric | Value |
|--------|-------|
| Total Backend LOC | ~25,000 |
| Frontend LOC | ~100 (Pre-Alpha) |
| Backend Modules | 20+ |
| Test Files | 219 |
| Pre-built Skills | 40+ |
| API Routes | 9 |

### Maturity Levels

- 🟢 **Production**: Core infrastructure, agents, orchestration, storage, security, LLM layer
- 🟡 **MVP**: Skill creation system, builder domain (Feb 2026)
- 🔴 **Pre-Alpha**: Frontend (scaffolding only)

### Technology Stack

**Backend**
- Python 3.9+
- FastAPI (web framework)
- SQLAlchemy (ORM, async/sync)
- LiteLLM (multi-provider LLM)
- pytest (testing)

**Frontend** (Planned)
- Next.js 14+
- TypeScript
- Tailwind CSS

**External**
- OpenAI, Anthropic (LLM providers)
- PostgreSQL / SQLite (database)
- OAuth 2.0 (authentication)

### Architecture Patterns

1. **Repository Pattern** - Data access abstraction
2. **Factory Pattern** - Application and service creation
3. **Observer Pattern** - Event streaming and monitoring
4. **Strategy Pattern** - Pluggable LLM providers and tools
5. **FSM Pattern** - Skill creation workflow
6. **Middleware Pattern** - Request processing pipeline
7. **Registry Pattern** - Tool and agent discovery
8. **Dependency Injection** - Loose coupling

### Key Components by Layer

#### Application Layer
- **Agents**: Master agent orchestration with A2A protocol
- **Skills**: 40+ skills + FSM-based creation system (4,600 LOC)
- **Chat**: LLM-powered chat with streaming
- **Builder**: Automated skill and repository creation

#### Infrastructure Layer
- **LLM Layer**: Multi-provider integration via LiteLLM
- **Storage**: SQLAlchemy with repository pattern
- **Security**: RBAC, multi-tenancy, OAuth
- **Observability**: Structured logging and metrics

#### Platform Services
- **Orchestration**: Discovery, routing, execution scheduling
- **Tools**: Registry and executor
- **Prompts**: Template management

### Recent Developments

**February 2026**
- ✅ Skill creation system MVP (4,600 LOC)
- ✅ Path normalization for portable skills
- ✅ Anthropic specification compliance
- ✅ 11-state FSM for conversational creation
- ✅ 4 skill pattern detection
- ✅ LLM-powered requirements extraction
- ✅ 203 passing skill creation tests

**January 2026**
- ✅ Massive 501-file commit (114K LOC)
- ✅ 20+ new skills added
- ✅ Conversation routing improvements
- ✅ Enhanced LLM reliability

### Known Gaps & Roadmap

**P0 Gaps** (Critical)
- ⚠️ Tool permissions: `determine_required_tools()` stub
- ⚠️ Reference generation: Missing references/ directory creation
- ⚠️ Asset generation: Missing assets/ directory creation

**P1 Gaps** (Important)
- Frontend implementation (currently pre-alpha)
- Interactive skill editing in creation flow
- Enhanced error recovery in FSM

**Future Enhancements**
- Advanced skill composition
- Multi-skill orchestration
- Enhanced governance and compliance
- Performance optimization

## Navigation Guide

### By Role

**Product Manager / Stakeholder**
1. Start: [System Overview](./system-overview.md)
2. Understand deployment: See "Deployment Model" section
3. Review maturity: Check "Maturity Levels"

**New Developer**
1. Start: [System Overview](./system-overview.md)
2. Deep dive: [Component Diagram](./component-diagram.md)
3. Understand data flow: See sequence diagrams

**Senior Developer / Architect**
1. Start: [Component Diagram](./component-diagram.md)
2. Review patterns: See "Architecture Patterns"
3. Analyze specifics: [Skill Creation Flow](./skill-creation-flow.md)

**AI/LLM Developer**
1. Start: [Skill Creation Flow](./skill-creation-flow.md)
2. Review prompts: See "LLM Prompts Structure"
3. Understand integration: [Component Diagram](./component-diagram.md) → LLM Layer

**Skills Developer**
1. Start: [Skill Creation Flow](./skill-creation-flow.md)
2. Understand patterns: See "Skill Patterns and Detection Logic"
3. Review validation: See "Validation Rules"

### By Task

**Understanding the overall system**
→ [System Overview](./system-overview.md)

**Planning a new feature**
→ [Component Diagram](./component-diagram.md) → Find relevant modules

**Working on skill creation**
→ [Skill Creation Flow](./skill-creation-flow.md)

**Troubleshooting integration issues**
→ [Component Diagram](./component-diagram.md) → Check component relationships

**Optimizing LLM usage**
→ [Skill Creation Flow](./skill-creation-flow.md) → See "Performance Metrics"

**Understanding security model**
→ [Component Diagram](./component-diagram.md) → Security & Enterprise section

## Additional Resources

### Code Guidelines
- Backend: `/coding-guidelines.md`
- Frontend: `/frontend/coding-guidelines.md`
- Project: `/CLAUDE.md`

### Specifications
- Product specs: `/specs/`
- Technical plans: `/specs/`
- Tasks: `/specs/tasks/`

### Testing
- Test suite: `/tests/` (219 files)
- Test commands: See `/CLAUDE.md`

### API Documentation
- OpenAPI: Available at `/docs` when running the server
- Route modules: `/src/omniforge/api/routes/`

## Contributing to Architecture Docs

When updating architecture documentation:

1. **Keep diagrams in sync**: Update all relevant diagrams when architecture changes
2. **Use consistent notation**: Follow Mermaid diagram conventions
3. **Update statistics**: Keep LOC counts and metrics current
4. **Document decisions**: Explain architectural choices and trade-offs
5. **Maintain navigation**: Update this README when adding new docs
6. **Version awareness**: Note the date of architectural snapshots

## Feedback and Questions

For questions about the architecture:
1. Check these docs first
2. Review the code in relevant modules
3. Check `/CLAUDE.md` for project guidelines
4. Consult with the development team

---

**Last Updated**: February 4, 2026
**Architecture Version**: 0.1.0 (MVP)
**Documentation Status**: Complete for current implementation
