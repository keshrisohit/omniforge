# Prompt Management Module

**Created**: 2026-01-11
**Last Updated**: 2026-01-11
**Version**: 1.0
**Status**: Draft

## Overview

The Prompt Management Module is a foundational system that enables OmniForge to compose, store, version, validate, test, and cache prompts across multiple layers of the platform. It provides a layered merge architecture where prompts from different organizational levels (system, tenant, feature, agent, user) combine at runtime to produce contextually appropriate instructions for AI agents. This module serves as the backbone for all agent behavior customization, enabling both developers and business users to shape how agents communicate and respond without modifying code.

## Alignment with Product Vision

This specification directly advances OmniForge's core vision:

- **Enterprise-Ready from Day One**: Multi-tenant prompt isolation ensures organizations can customize agent behavior without affecting other tenants, with clear RBAC controls over who can modify prompts at each layer
- **Agents Build Agents**: The chatbot-driven platform can use this module to let users customize agent personalities and behaviors through conversation, dynamically updating prompts without code changes
- **Simplicity over Flexibility**: The layered merge approach provides powerful customization while hiding complexity; users at each level only see prompts relevant to their scope
- **Dual Deployment Model**: SDK users get programmatic access to prompt composition while platform users get a managed experience with versioning and A/B testing built in
- **Reliability over Speed**: Versioning and rollback capabilities ensure prompt changes can be safely deployed and quickly reverted if issues arise

## User Personas

### Primary Users

#### Platform Developer (SDK User)
A software developer using the Python SDK to create custom agents.
- **Context**: Writing Python code, defining agent behaviors, testing locally
- **Goals**: Define prompts programmatically, inject variables at runtime, test different prompt versions locally before deployment
- **Pain Points**: Hard-coded prompts that require code changes to update, no visibility into prompt composition at runtime, difficulty coordinating prompts across team members
- **Module Interaction**: Uses SDK APIs to define prompts, register templates, compose final prompts programmatically

#### Tenant Administrator
An organization administrator managing their tenant's OmniForge deployment.
- **Context**: Web dashboard, configuring organization-wide settings, managing team access
- **Goals**: Customize agent behaviors for their organization, establish brand voice and compliance requirements, control who can modify prompts
- **Pain Points**: No ability to differentiate their agents from defaults, compliance requirements hard to enforce consistently, no audit trail for prompt changes
- **Module Interaction**: Manages tenant-level prompts via dashboard or API, sets organizational defaults, reviews audit logs

#### Agent Developer (No-Code User)
A business user creating agents through the OmniForge chatbot interface.
- **Context**: Web-based chat interface, describing desired agent behavior in natural language
- **Goals**: Create agents with specific personalities and behaviors, customize without technical knowledge, iterate quickly on agent responses
- **Pain Points**: Technical jargon in prompt configuration, unclear how changes affect behavior, no way to test changes before deployment
- **Module Interaction**: Describes customizations in chat, sees immediate preview of how prompts will behave, approves changes through conversation

#### Platform Administrator
A system administrator managing the OmniForge platform itself.
- **Context**: Platform-level dashboard, system configuration, multi-tenant management
- **Goals**: Define system-wide prompt defaults, ensure security and compliance across all tenants, monitor prompt usage and performance
- **Pain Points**: No visibility into how prompts are being used, difficulty enforcing platform-wide policies, no standardization across agents
- **Module Interaction**: Manages system-level prompts, configures global validation rules, monitors prompt performance across tenants

### Secondary Users

#### AI Agent (System Actor)
Agents that consume composed prompts at runtime.
- **Context**: Processing user requests, needing contextually appropriate instructions
- **Goals**: Receive well-formed, relevant prompts that guide appropriate responses
- **Pain Points**: Inconsistent prompt quality, missing context, conflicting instructions
- **Module Interaction**: Requests composed prompts via internal API, receives fully merged and rendered templates

#### Compliance Officer
A role focused on ensuring regulatory and policy compliance.
- **Context**: Reviewing prompt content for compliance, investigating incidents
- **Goals**: Ensure prompts meet regulatory requirements, audit who changed what and when, verify sensitive content handling
- **Pain Points**: No visibility into prompt content, no audit trail, difficulty proving compliance
- **Module Interaction**: Reviews prompt versions via dashboard, exports audit logs, validates prompts against compliance rules

## Problem Statement

Currently, OmniForge agents have prompts defined directly in code or configuration files. This creates several problems from the user's perspective:

1. **No Customization Path**: Tenant administrators cannot customize how agents behave for their organization without involving developers. A financial services company and a retail company get identical agent responses, despite very different needs.

2. **Risky Updates**: Changing a prompt requires a code deployment. If the change causes problems, rolling back requires another deployment. Users experience broken agent behavior while waiting for fixes.

3. **No Experimentation**: Product teams cannot test whether a different prompt improves user outcomes. They must guess or make changes blindly, risking production issues.

4. **Compliance Gaps**: There is no way to enforce that certain language or disclaimers appear in agent responses, and no audit trail showing who approved what prompt language.

5. **Scattered Configuration**: Prompts are defined in different places (code, config files, databases) with no unified way to understand or manage them.

6. **Performance Uncertainty**: Rendering complex prompt templates on every request adds latency, but there is no caching strategy to optimize this.

The Prompt Management Module solves these problems by providing a unified system for defining, composing, versioning, and optimizing prompts across all layers of the platform.

## Core Concepts

### Prompt Layers

Prompts in OmniForge exist at five distinct layers, each with clear ownership and purpose:

```
+------------------+     Merge Direction
|   USER PROMPT    |         |
+------------------+         |
        |                    |
+------------------+         |
|  AGENT PROMPT    |         |
+------------------+         v
        |
+------------------+
| FEATURE PROMPT   |     (Layers merge
+------------------+      top-to-bottom
        |                with defined
+------------------+      merge points)
| TENANT PROMPT    |
+------------------+
        |
+------------------+
| SYSTEM PROMPT    |  <-- Foundation
+------------------+
```

**Layer 1 - System Prompts (Platform-Level)**
- Owned by: Platform Administrators
- Purpose: Establish foundational behavior, safety guidelines, and platform-wide standards
- Example: Safety disclaimers, response format guidelines, fundamental agent identity
- Characteristics: Rarely changes, highest stability, always present

**Layer 2 - Tenant Prompts (Organization-Level)**
- Owned by: Tenant Administrators
- Purpose: Customize agent behavior for an organization's brand, policies, and compliance needs
- Example: Company name, brand voice, industry-specific disclaimers, regulatory requirements
- Characteristics: Changes occasionally, scoped to tenant, overrides system defaults where allowed

**Layer 3 - Feature Prompts (Capability-Level)**
- Owned by: Platform Developers, Feature Teams
- Purpose: Define behavior for specific agent capabilities or skills
- Example: Code review instructions, document summarization style, data analysis approach
- Characteristics: Tied to feature releases, versioned with features, skill-specific

**Layer 4 - Agent Prompts (Instance-Level)**
- Owned by: Agent Creators (Developers or No-Code Users)
- Purpose: Define specific agent personality, expertise, and behavioral nuances
- Example: Agent name, persona, specific expertise areas, conversation style
- Characteristics: Most frequently customized, per-agent configuration

**Layer 5 - User Prompts (Runtime-Level)**
- Owned by: End Users
- Purpose: The actual user input and any user-specific context
- Example: The user's question, their preferences, conversation history
- Characteristics: Dynamic, per-request, untrusted input that must be safely incorporated

### Merge Strategy

Prompts merge using defined **merge points** - explicit markers in templates that specify where content from other layers should be inserted.

```jinja
{# System Prompt Template #}
You are an AI assistant created by OmniForge.

{{ merge_point("safety_guidelines") }}

{{ merge_point("tenant_customization") }}

Your core capabilities include:
{{ merge_point("feature_capabilities") }}

{{ merge_point("agent_persona") }}

The user has asked:
{{ merge_point("user_input") }}
```

**Merge Rules:**
1. Each merge point has a defined **merge behavior**: `append`, `prepend`, `replace`, or `inject`
2. If a layer does not define content for a merge point, it is skipped
3. Lower layers (system) define the structure; higher layers fill in customizations
4. Merge conflicts are resolved by **priority**: higher layers win unless the lower layer marks content as `locked`
5. Empty merge points collapse cleanly (no double newlines, no placeholder text)

### Template Engine (Jinja2)

All prompts use Jinja2 templating for dynamic content:

```jinja
{# Tenant Prompt Example #}
{{ tenant_customization }}
You represent {{ tenant.name }}, a leader in {{ tenant.industry }}.
Our brand voice is {{ tenant.brand_voice | default("professional and helpful") }}.

{% if tenant.compliance_requirements %}
Important: Always include the following disclaimer when discussing {{ tenant.compliance_topic }}:
"{{ tenant.disclaimer_text }}"
{% endif %}
```

**Supported Jinja2 Features:**
- Variables: `{{ variable_name }}`
- Filters: `{{ name | upper }}`, `{{ list | join(", ") }}`
- Conditionals: `{% if condition %}...{% endif %}`
- Loops: `{% for item in list %}...{% endfor %}`
- Template inheritance: `{% extends "base.jinja" %}`
- Custom filters: Platform-defined filters for common operations

**Security Constraints:**
- No file system access from templates
- No code execution beyond Jinja2 expressions
- Sandboxed execution environment
- Injection protection for user-provided variables

## User Journeys

### Journey 1: Platform Admin Sets System Defaults

**Context**: A platform administrator needs to establish the foundational safety guidelines that all agents across all tenants must follow.

1. **Admin accesses system settings** - Opens the platform admin dashboard and navigates to Prompt Management > System Prompts
2. **Admin views current system prompt** - Sees the existing system prompt with syntax highlighting, variable documentation, and merge point annotations
3. **Admin edits safety section** - Modifies the safety guidelines to add a new requirement about not providing medical advice
4. **System validates changes** - The editor validates Jinja2 syntax, checks for required merge points, and runs content validation rules
5. **Admin previews impact** - Clicks "Preview" and selects a sample tenant/agent combination to see how the change affects the final composed prompt
6. **Admin commits change** - Enters a commit message describing the change, system creates a new version
7. **Change takes effect** - New prompts are used for new requests; cached prompts are invalidated

**Key Experience**: The admin should feel confident that their safety guideline will apply universally without breaking existing customizations. The preview shows exactly how the change flows through to actual agent prompts.

### Journey 2: Tenant Admin Customizes Brand Voice

**Context**: A tenant administrator for "Acme Financial Services" wants their agents to use a formal, compliance-conscious tone and always include their regulatory disclaimer.

1. **Admin opens tenant settings** - Logs into OmniForge, navigates to Settings > Agent Behavior
2. **Admin sees customization options** - Dashboard shows available customization points with current values and descriptions of what each controls
3. **Admin sets brand voice** - Selects "Formal" from a dropdown, or enters custom text: "Professional, precise, and compliance-conscious. Avoid casual language."
4. **Admin adds disclaimer** - In the "Compliance" section, enables the financial disclaimer option and enters their specific legal text
5. **Admin previews changes** - Sees a side-by-side comparison of before/after agent responses using sample conversations
6. **Admin activates changes** - Clicks "Apply to All Agents" or selects specific agents
7. **Changes propagate** - All Acme agents now use the new brand voice; existing conversations continue with the old prompt, new conversations use the updated prompt

**Key Experience**: The admin never sees raw Jinja2 syntax. They interact through a friendly UI that exposes safe customization options. They can immediately see how their changes affect agent behavior.

### Journey 3: Developer Defines Agent-Specific Prompt

**Context**: A developer using the SDK is creating a specialized "Code Review Agent" that needs specific instructions about how to analyze and comment on code.

1. **Developer defines agent class** - In Python, creates a new agent extending `BaseAgent`
2. **Developer specifies prompt config** - Uses SDK to define the agent's prompt configuration:
   ```python
   class CodeReviewAgent(BaseAgent):
       prompt_config = PromptConfig(
           agent_prompt="""
           You are an expert code reviewer specializing in {{ languages | join(", ") }}.

           Review code for:
           - Security vulnerabilities
           - Performance issues
           - Code style and best practices
           - Potential bugs

           {% if strict_mode %}
           Flag ALL issues, no matter how minor.
           {% else %}
           Focus on significant issues that impact quality.
           {% endif %}
           """,
           variables={
               "languages": ["Python", "JavaScript", "Go"],
               "strict_mode": False
           }
       )
   ```
3. **Developer tests locally** - Runs the agent locally, SDK composes the full prompt and logs it for inspection
4. **Developer views composed prompt** - Uses `agent.get_composed_prompt()` to see exactly what the LLM will receive
5. **Developer iterates** - Adjusts prompt, tests again, commits when satisfied
6. **Agent deployed** - Agent goes live, prompt stored in database for runtime composition

**Key Experience**: The developer has full control over their agent's personality while the platform handles layering in system, tenant, and feature prompts automatically. They can see the exact composed prompt for debugging.

### Journey 4: Business User Customizes Agent via Chat

**Context**: A business user wants to create a customer support agent for their e-commerce platform. They are using the no-code chat interface.

1. **User starts conversation** - Opens OmniForge chat, says "I want to create a customer support agent"
2. **Platform asks questions** - "What should your agent be called? What's your company name? What tone should it use?"
3. **User describes personality** - "Call it 'Alex', use a friendly but professional tone, my company is 'TechGadgets'"
4. **Platform summarizes** - Shows a summary of the agent configuration including the prompt customizations it will apply
5. **User requests adjustment** - "Actually, make it more casual - like talking to a friend"
6. **Platform updates preview** - Shows how the updated personality affects sample responses
7. **User approves** - "That looks good, create it"
8. **Agent created** - Platform stores the prompt configuration, agent is ready to use
9. **User tests** - Immediately chats with their new agent to verify the personality

**Key Experience**: The user never sees "prompt" or "template" - they describe what they want in natural language. The platform translates their intent into proper prompt configuration and shows them the result, not the implementation.

### Journey 5: A/B Testing Prompt Variations

**Context**: The product team wants to test whether a more empathetic tone in error messages leads to better user satisfaction.

1. **PM creates experiment** - In the dashboard, creates a new A/B test for the "error handling" prompt section
2. **PM defines variants** -
   - Control (A): Current error messages
   - Treatment (B): More empathetic error messages with "I understand this is frustrating..."
3. **PM sets traffic split** - 50% control, 50% treatment
4. **PM defines success metric** - User satisfaction rating after error encounters
5. **Experiment launches** - System randomly assigns users to variants, tracks which prompt each user sees
6. **PM monitors results** - Dashboard shows conversion rates, statistical significance, and sample responses from each variant
7. **Experiment concludes** - After sufficient data, PM sees that Treatment (B) has 12% higher satisfaction
8. **PM promotes winner** - Clicks "Promote to Production", the empathetic version becomes the new default
9. **Audit log updated** - Full record of the experiment, results, and promotion decision

**Key Experience**: The PM can run rigorous experiments without involving engineering. The platform handles traffic splitting, tracking, and statistical analysis. The promotion path is clear and reversible.

### Journey 6: Investigating a Prompt Issue

**Context**: Users are reporting that an agent is giving incorrect information. The support team needs to investigate what prompt the agent was using.

1. **Support receives ticket** - User reports "Agent told me I could return items after 90 days, but our policy is 30 days"
2. **Support accesses conversation** - Pulls up the conversation in the admin console
3. **Support views prompt snapshot** - Clicks "View Prompt Used" to see the exact composed prompt that was active at the time of the response
4. **Support identifies issue** - Sees that the tenant's return policy variable was set incorrectly to "90 days"
5. **Support traces history** - Views the prompt version history to see who changed the return policy value and when
6. **Support fixes issue** - Updates the tenant variable to "30 days"
7. **Support verifies fix** - Tests the agent to confirm it now gives correct information
8. **Root cause documented** - Adds note to the audit log explaining the issue and resolution

**Key Experience**: Support can quickly trace exactly what prompt an agent used for any conversation, see the full version history, and understand who made what changes. No guessing, no "works on my machine" issues.

## Success Criteria

### User Outcomes

- **Customization Without Code**: A tenant admin can customize agent brand voice and see the changes reflected in agent responses within 5 minutes, without writing any code or involving developers
- **Safe Experimentation**: Product teams can run A/B tests on prompt variations and determine winners within 2 weeks with statistical confidence, without risking production stability
- **Fast Rollback**: When a prompt change causes issues, administrators can roll back to the previous version within 30 seconds, and the rollback takes effect immediately for new conversations
- **Clear Traceability**: For any agent response, support can determine exactly what prompt was used and trace its complete version history within 2 minutes
- **Performance Maintained**: Prompt composition adds less than 10ms latency to agent response time (p95), with caching reducing repeat composition to < 1ms

### Business Outcomes

- **Reduced Engineering Load**: Prompt updates that previously required code deployments can now be made by non-engineers, reducing engineering involvement in prompt changes by 80%
- **Faster Iteration**: Time from prompt idea to production deployment reduced from days (code change cycle) to minutes (dashboard change)
- **Compliance Confidence**: Organizations can demonstrate prompt version history and audit trails for regulatory compliance reviews

### Technical Outcomes

- **Template Validation**: 100% of prompt templates are validated before activation, preventing syntax errors from reaching production
- **Cache Efficiency**: Cache hit rate > 90% for prompt composition in steady-state operation
- **Multi-Tenant Isolation**: Zero cross-tenant prompt leakage, verified by automated isolation tests

## Key Experiences

### The "Just Works" Composition Experience

When an agent needs a prompt, the composition should be invisible. The agent asks for a prompt, receives a fully composed, contextually appropriate result. The developer should never need to think about which layers applied or how merging worked - unless they specifically want to debug.

### The "See What You're Getting" Preview Experience

Before any prompt change is saved, users should be able to preview exactly how it affects agent behavior. Not an abstract "your change will be applied" message, but actual sample conversations showing before/after responses. This builds confidence to make changes.

### The "Who Changed What" Audit Experience

Every prompt change should be traceable. When something goes wrong, finding the root cause should take minutes, not hours. The version history should tell a story: who made this change, when, why (commit message), and exactly what changed (diff).

### The "Safely Experiment" A/B Testing Experience

Running an experiment should feel safe. Traffic splitting should be automatic and fair. Rolling back should be instant. The platform should protect users from statistical errors (declaring winners too early, insufficient sample size) without requiring statistics expertise.

### The "Instant Rollback" Recovery Experience

When a prompt change causes problems, reverting should be one click. The previous version should take effect immediately for new conversations. Users should not experience prolonged broken behavior while waiting for a fix.

## Technical Architecture

### Data Model

```
Prompt
├── id: UUID
├── layer: Enum (SYSTEM, TENANT, FEATURE, AGENT, USER)
├── scope_id: String (tenant_id, feature_id, agent_id, or null for system)
├── name: String
├── content: Text (Jinja2 template)
├── merge_points: JSON (list of merge point definitions)
├── variables_schema: JSON (JSON Schema for required variables)
├── metadata: JSON (description, tags, etc.)
├── created_at: DateTime
├── created_by: String (user_id)
└── is_active: Boolean

PromptVersion
├── id: UUID
├── prompt_id: UUID (FK to Prompt)
├── version: Integer
├── content: Text (Jinja2 template at this version)
├── variables_schema: JSON
├── change_message: Text (commit message)
├── changed_by: String (user_id)
├── changed_at: DateTime
└── is_current: Boolean

PromptExperiment
├── id: UUID
├── prompt_id: UUID (FK to Prompt)
├── name: String
├── status: Enum (DRAFT, RUNNING, PAUSED, COMPLETED)
├── variants: JSON (list of variant definitions)
├── traffic_allocation: JSON (variant -> percentage)
├── success_metric: String
├── start_date: DateTime
├── end_date: DateTime
└── results: JSON (statistical results)

PromptCache
├── cache_key: String (hash of composition inputs)
├── composed_prompt: Text
├── layer_versions: JSON (prompt_id -> version used)
├── created_at: DateTime
└── expires_at: DateTime
```

### Merge Point Definition

```json
{
  "merge_points": [
    {
      "name": "safety_guidelines",
      "behavior": "append",
      "required": true,
      "locked": true,
      "description": "Platform safety guidelines that must be included"
    },
    {
      "name": "tenant_customization",
      "behavior": "replace",
      "required": false,
      "locked": false,
      "description": "Tenant-specific customizations"
    },
    {
      "name": "agent_persona",
      "behavior": "inject",
      "required": false,
      "locked": false,
      "description": "Agent-specific personality and behavior"
    }
  ]
}
```

**Merge Behaviors:**
- `append`: Content from higher layer is added after lower layer content
- `prepend`: Content from higher layer is added before lower layer content
- `replace`: Higher layer content completely replaces lower layer content
- `inject`: Content is inserted at the specified position within the template

**Merge Constraints:**
- `locked: true`: Lower layer content cannot be overridden (safety-critical content)
- `required: true`: Merge point must have content from at least one layer

### Composition Algorithm

```
compose_prompt(agent_id, tenant_id, feature_ids, user_input, variables):
    1. Check cache for existing composition
       - If hit, return cached result

    2. Load prompts from each layer:
       - system_prompt = get_system_prompt()
       - tenant_prompt = get_tenant_prompt(tenant_id)
       - feature_prompts = [get_feature_prompt(f) for f in feature_ids]
       - agent_prompt = get_agent_prompt(agent_id)

    3. For each merge point in system_prompt:
       - Collect content from all layers that define it
       - Apply merge behavior (append/prepend/replace/inject)
       - Respect locked constraints
       - Resolve conflicts by layer priority

    4. Render Jinja2 template with:
       - Platform variables
       - Tenant variables
       - Agent variables
       - Runtime variables
       - User input (safely escaped)

    5. Validate composed prompt:
       - Check length limits
       - Verify no malformed output
       - Validate safety rules

    6. Cache result with version metadata

    7. Return composed prompt
```

### Caching Strategy

**Cache Key Generation:**
```
cache_key = hash(
    system_prompt_version,
    tenant_prompt_version,
    feature_prompt_versions[],
    agent_prompt_version,
    variable_hash,  # Hash of non-user variables
    # Note: User input is NOT in cache key (too variable)
)
```

**Cache Invalidation:**
- On prompt update: Invalidate all cache entries containing that prompt version
- On variable change: Invalidate cache entries using those variables
- Time-based expiry: 1 hour default, configurable per prompt
- Manual flush: Admin can force cache clear for debugging

**Cache Layers:**
1. In-memory (per-instance): Hot prompts for immediate access
2. Distributed cache (Redis): Shared across instances
3. Database: Source of truth for reconstruction

### Validation Rules

**Syntax Validation:**
- Jinja2 template parses without errors
- All merge points are properly closed
- Variable references match schema

**Content Validation:**
- Length within configured limits (per layer, per total)
- No prohibited content (configurable blocklist)
- Required sections present (for compliance)
- No injection vulnerabilities in variable substitution

**Semantic Validation:**
- Merge points referenced in content are defined
- Variable types match schema
- Conditional logic is well-formed

**Safety Validation:**
- User-provided content is properly escaped
- No prompt injection patterns detected
- Locked content is preserved

## Edge Cases and Considerations

### Merge Conflicts

**Scenario**: A tenant prompt and feature prompt both try to set the same merge point with `replace` behavior.

**Resolution**: Layer priority determines winner. Higher layers (closer to user) win by default. If this is undesirable, the lower layer can mark the merge point as `locked`.

**User Experience**: The dashboard shows a warning when a conflict exists, indicating which layer's content will be used.

### Missing Layer Content

**Scenario**: A tenant has not configured any tenant-level prompts.

**Resolution**: The merge simply skips that layer. The system prompt provides defaults that work without tenant customization. Merge points with `required: false` can be empty.

**User Experience**: Agents work correctly with just system defaults. Tenant customization is additive, not required.

### Variable Not Defined

**Scenario**: A prompt template references `{{ tenant.support_email }}` but the tenant has not configured this variable.

**Resolution**: Jinja2's `default` filter is encouraged: `{{ tenant.support_email | default("support@example.com") }}`. If no default and variable is missing, validation fails before activation.

**User Experience**: Validation prevents broken prompts from being activated. Clear error message identifies the missing variable.

### Very Long Prompts

**Scenario**: After composing all layers, the prompt exceeds LLM token limits.

**Resolution**: Configurable total length limit per agent/model. Validation warns before the limit is reached. If exceeded, truncation strategy applies (truncate user history first, then agent details, never system safety).

**User Experience**: Warning appears during prompt editing if projected length approaches limits. Clear guidance on what will be truncated if limits are exceeded.

### Concurrent Edits

**Scenario**: Two admins edit the same prompt simultaneously.

**Resolution**: Optimistic locking with version numbers. Second save sees a conflict, can view the diff, and choose to merge or overwrite.

**User Experience**: Clear conflict resolution UI showing both versions and differences.

### Experiment in Progress

**Scenario**: An admin tries to edit a prompt that has an active A/B test.

**Resolution**: Changes create a new variant or modify a draft version, not the live experiment. Admin is warned that an experiment is running and given options.

**User Experience**: Dashboard clearly shows experiment status. Changes are staged, not immediately applied to running experiments.

### Cross-Tenant Leakage Prevention

**Scenario**: A bug or misconfiguration could expose one tenant's prompt content to another.

**Resolution**:
- Tenant ID is mandatory context for all prompt operations
- Database queries always filter by tenant_id
- Cache keys include tenant_id
- Automated tests verify isolation

**User Experience**: Tenants never see evidence of other tenants. Isolation is invisible but absolute.

### Rollback While Experiment Running

**Scenario**: An admin needs to rollback a prompt but an A/B test is active.

**Resolution**: Rolling back pauses the experiment and reverts all variants to the selected historical version. Experiment can be resumed with new variants.

**User Experience**: Clear warning about experiment impact. Option to pause experiment, rollback, and resume or cancel experiment.

## Security Considerations

### Access Control (RBAC)

| Role | System Prompts | Tenant Prompts | Feature Prompts | Agent Prompts |
|------|---------------|----------------|-----------------|---------------|
| Platform Admin | Full Access | Read Only | Read Only | Read Only |
| Tenant Admin | Read Only | Full Access | Read Only | Full Access (own tenant) |
| Developer | Read Only | Read Only | Full Access | Full Access (own agents) |
| Operator | Read Only | Read Only | Read Only | Read Only |
| Viewer | Read Only | Read Only | Read Only | Read Only |

### Audit Logging

All prompt operations are logged:
- Create, update, delete operations
- Version changes and rollbacks
- A/B experiment lifecycle events
- Cache invalidations
- Composition requests (optional, can be sampled)

Log entries include:
- Timestamp
- User ID
- Tenant ID
- Operation type
- Before/after states (for changes)
- Source IP and user agent

### Prompt Injection Prevention

- User input variables are always sanitized
- Jinja2 sandbox environment prevents code execution
- Template validation rejects suspicious patterns
- Runtime detection of injection attempts
- Rate limiting on prompt composition

### Sensitive Content

- Prompts can be marked as "sensitive" requiring additional access controls
- Sensitive variables (API keys, credentials) are never stored in prompts
- Audit logs redact sensitive content
- Encrypted at rest, decrypted only for composition

## API Design

### SDK Interface

```python
from omniforge.prompts import PromptManager, PromptConfig, PromptLayer

# Configure prompt for an agent
class MyAgent(BaseAgent):
    prompt_config = PromptConfig(
        agent_prompt="You are {{ agent_name }}, an expert in {{ domain }}.",
        variables={
            "agent_name": "Alex",
            "domain": "customer support"
        },
        merge_behavior={
            "agent_persona": "replace"
        }
    )

# Programmatic prompt management
manager = PromptManager(tenant_id="acme-corp")

# Create a new prompt
prompt = manager.create_prompt(
    layer=PromptLayer.TENANT,
    name="brand_voice",
    content="Respond in a {{ tone }} tone.",
    variables_schema={"tone": {"type": "string", "enum": ["formal", "casual"]}}
)

# Update with versioning
manager.update_prompt(
    prompt_id=prompt.id,
    content="Respond in a {{ tone }} tone. Be concise.",
    change_message="Added conciseness instruction"
)

# Compose prompt for an agent
composed = manager.compose_prompt(
    agent_id="agent-123",
    variables={"user_query": "How do I return an item?"}
)

# Access version history
history = manager.get_prompt_history(prompt_id=prompt.id)

# Rollback
manager.rollback_prompt(prompt_id=prompt.id, to_version=2)
```

### REST API Endpoints

```
# Prompt CRUD
GET    /api/v1/prompts                     # List prompts (filtered by layer, tenant)
POST   /api/v1/prompts                     # Create prompt
GET    /api/v1/prompts/{id}                # Get prompt
PUT    /api/v1/prompts/{id}                # Update prompt
DELETE /api/v1/prompts/{id}                # Delete prompt (soft delete)

# Versioning
GET    /api/v1/prompts/{id}/versions       # List versions
GET    /api/v1/prompts/{id}/versions/{v}   # Get specific version
POST   /api/v1/prompts/{id}/rollback       # Rollback to version

# Composition
POST   /api/v1/prompts/compose             # Compose prompt for agent

# Validation
POST   /api/v1/prompts/validate            # Validate prompt template

# A/B Testing
POST   /api/v1/prompts/{id}/experiments    # Create experiment
GET    /api/v1/prompts/{id}/experiments    # List experiments
PUT    /api/v1/experiments/{id}            # Update experiment
POST   /api/v1/experiments/{id}/start      # Start experiment
POST   /api/v1/experiments/{id}/stop       # Stop experiment
POST   /api/v1/experiments/{id}/promote    # Promote winning variant

# Cache Management
DELETE /api/v1/prompts/cache               # Clear cache (admin only)
GET    /api/v1/prompts/cache/stats         # Cache statistics
```

## Open Questions

### Template Inheritance vs. Composition

Should prompts use Jinja2's template inheritance (`{% extends %}`) or our merge point system? Or both?

**Considerations:**
- Template inheritance is familiar to developers
- Merge points give more control to non-technical users
- Could support both with clear guidance on when to use each

### Variable Namespacing

How do we prevent variable name collisions across layers?

**Options:**
1. Prefixed namespaces: `system.safety_level`, `tenant.brand_name`
2. Separate variable contexts per layer
3. Single flat namespace with collision warnings

### Prompt Testing Environment

How do users test prompt changes without affecting production?

**Options:**
1. Staging environment per tenant
2. "Draft" mode that only affects test conversations
3. Preview-only mode with no persistence

### Historical Prompt Lookup Performance

For audit and debugging, we need to look up exact prompts used for past conversations. How do we handle this efficiently?

**Options:**
1. Store composed prompt with each conversation
2. Store version references and reconstruct
3. Snapshot at regular intervals

### Metrics for A/B Testing

What metrics should we track for A/B tests, and how do we attribute outcomes to prompts?

**Considerations:**
- User satisfaction ratings
- Task completion rates
- Follow-up question frequency
- Time to resolution
- Sentiment analysis of user responses

## Out of Scope (For Now)

- **Visual Prompt Builder**: Drag-and-drop prompt composition interface
- **AI-Assisted Prompt Writing**: LLM suggestions for improving prompts
- **Cross-Tenant Prompt Sharing**: Marketplace for prompt templates
- **Prompt Analytics**: Deep analysis of prompt performance (beyond A/B testing)
- **Dynamic Prompt Selection**: Automatically choosing prompts based on context
- **Multi-Language Prompts**: Internationalization of prompt content
- **Prompt Chaining**: Complex multi-step prompt workflows
- **External Template Sources**: Loading prompts from external systems

## Integration Points

### Agent Module

- Agents request composed prompts via `PromptManager.compose_prompt()`
- Agent definitions include prompt configuration
- Agent creation validates prompt references

### Security Module

- RBAC controls access to prompt operations
- Tenant context determines prompt scope
- Audit logging integrates with security logging

### Orchestration Module

- Multi-agent workflows may need coordinated prompts
- Feature prompts may be dynamically selected based on task

### Chat Service

- Chat service passes user input to prompt composition
- Conversation history may be included in prompt context

## Evolution Notes

### 2026-01-11 (Initial Draft)

- Created specification based on requirements for layered prompt management
- Key design decisions:
  - Five-layer architecture (system, tenant, feature, agent, user) provides clear separation of concerns
  - Merge points over template inheritance for non-technical user accessibility
  - Jinja2 chosen for industry standard templating with good security sandboxing
  - Database-only storage for dynamic updates and multi-tenant isolation
  - A/B testing as first-class feature to enable experimentation culture
- Identified key open questions around template inheritance, variable namespacing, and testing environments
- Security model aligned with existing RBAC permissions in platform
- Next steps: Technical planning phase to define implementation architecture

---

## References

- [OmniForge Product Vision](./product-vision.md)
- [Base Agent Interface Specification](./base-agent-interface-spec.md)
- [Jinja2 Documentation](https://jinja.palletsprojects.com/)
- [OmniForge RBAC Implementation](../src/omniforge/security/rbac.py)
- [OmniForge Tenant Context](../src/omniforge/security/tenant.py)
