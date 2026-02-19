# TASK-312: White-Label Infrastructure

**Phase**: 3B (B2B2C Enterprise)
**Estimated Effort**: 12 hours
**Dependencies**: TASK-311 (Multi-Tenant Isolation)
**Priority**: P2

## Objective

Create white-labeling infrastructure allowing Tier 2 customers to brand the agent builder for their end customers.

## Requirements

- Create `b2b2c_orgs` table for organization configuration
- Implement branding model (logo, colors, fonts, custom domain)
- Create theme API for frontend customization
- Support custom domain routing (CNAME verification)
- Add organization-level feature flags
- Create white-label preview functionality

## Implementation Notes

- Reference technical plan Section 11.3 for B2B2C schema
- Branding stored as JSON in b2b2c_orgs.branding
- Custom domains require DNS CNAME verification
- Theme API returns CSS variables for frontend
- Preview mode shows branding without deploying

## Acceptance Criteria

- [ ] b2b2c_orgs table stores branding configuration
- [ ] Theme API returns customized CSS variables
- [ ] Custom domain routing works with CNAME verification
- [ ] Organization logo appears in all white-labeled pages
- [ ] Color scheme applies consistently across UI
- [ ] Feature flags enable/disable capabilities per org
- [ ] Preview mode shows changes before deployment
- [ ] API documentation for white-label configuration

## Files to Create/Modify

- `src/omniforge/b2b2c/__init__.py` - B2B2C package
- `src/omniforge/b2b2c/models.py` - B2B2COrg, Branding models
- `src/omniforge/b2b2c/repository.py` - B2B2C repository
- `src/omniforge/b2b2c/theming.py` - Theme generation
- `src/omniforge/b2b2c/domains.py` - Custom domain verification
- `src/omniforge/api/routes/b2b2c.py` - White-label API endpoints
- `tests/b2b2c/test_theming.py` - Theme generation tests
- `tests/b2b2c/test_domains.py` - Domain verification tests
