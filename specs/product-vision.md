# OmniForge Product Vision

**Last Updated:** 2026-01-03

## Product Vision

OmniForge is an enterprise-grade platform where agents build agents. It enables developers and technical business users to create, deploy, and orchestrate AI agents without writing code. The platform solves the gap between simple chatbot builders and complex AI frameworks by providing accessible agent creation with built-in enterprise governance, multi-tenancy, and reliable orchestration at scale.
Think in a way that this agent will help create agent on a platofrm.

**Dual Deployment Model:**

**SDK (Open Source Core):**
The Python SDK serves two purposes:
- **Standalone Tool** - Use OmniForge as an open source library in your applications without any platform dependency
- **Platform Client** - Interact with the hosted OmniForge platform programmatically via API

**Chatbot-Driven Platform (Premium):*÷
- **No-Code Interface** - Conversational chatbot UI for creating and orchestrating agents without writing code
- **Web-based Management** - Dashboard for monitoring, deploying, and managing agents
- **Enterprise Features** - Built-in multi-tenancy, RBAC, SSO, and governance
- **Library** - Anyone can imprt this library and write their own agent

## Guiding Principles

- **Simplicity over flexibility** - Fewer options done well beats endless configuration
- **Enterprise-ready from day one** - Security, RBAC, and multi-tenancy are foundational, not add-ons
- **Agents build agents** - Minimize human coding; the platform itself is agent-first
- **Reliability over speed** - Dependable orchestration matters more than raw performance
- **Data Security** - Custome data are stored separately and not mixed with platform data
- **Cost** - Consider cost to run the platform, and come up with best solution.
- **Scalability** - The platform should be able to scale to handle large number of agents and users.
- **Open Source** - The platform should be open source. All the integration with langchain should be supported.Figure out interfaces from github and langchain doc. Anyone on langchian should be easily able to switch to this or use it.
- **Multi-tenancy** - The plrm should be able to handle multiple tenants.
- **Multi-model** - The platform should be able to handle multiple models.
- **Multi-language** - The platform should be able to handle multiple languages.
- **Multi-modal** - The platform should be able to handle multiple modalities.


## Success Criteria

1. **SDK Users:** A developer can create and deploy an agent using the SDK in under 5 minutes with just Python
2. **Platform Users:** A business user can create a working agent through the chatbot interface without writing code
3. **Both:** Teams can orchestrate complex multi-agent workflows reliably at scale
4. **SDK Flexibility:** Developers can use OmniForge standalone or connect to the platform seamlessly

## Business Model: Open Source Freemium

**Open Source (Free Forever):**
- Complete Python SDK (Apache 2.0 or MIT license)
- Core agent orchestration and workflow capabilities
- Use as standalone library or self-host
- Community-driven development and plugins
- API client for platform interaction
- This should work with all the major LLM providers.

**Premium Chatbot-Driven Platform:**
- **Conversational Interface** - Create agents through natural language chat
- **No-Code Agent Builder** - Visual tools and chatbot-guided workflows
- **Enterprise Authentication** - SSO, SAML, advanced RBAC
- **Managed Cloud Hosting** - No infrastructure management
- **Advanced Features** - Multi-tenancy, monitoring, analytics, SLAs
- **Priority Support** - Direct support and custom integrations

**Philosophy:** Developers get full power through the open source SDK. Non-technical users and enterprises get productivity and governance through the chatbot-driven premium platform. Both approaches use the same core technology.

## Out of Scope

- **Not an ML training platform** - OmniForge uses models, it does not train them
- **Not a chatbot builder** - Agents perform complex tasks, not just Q&A
- **Not for AI/ML experts only** - Requires no deep AI/ML expertise to use
