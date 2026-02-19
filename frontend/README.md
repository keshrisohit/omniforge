# OmniForge Frontend

This directory contains **ALL** frontend-related code for the OmniForge platform.

## Technology Stack

- **Framework**: Next.js 14+ (App Router)
- **Language**: TypeScript (strict mode)
- **Styling**: Tailwind CSS + CSS Modules
- **State Management**: React Context + TanStack Query
- **Forms**: React Hook Form + Zod
- **Testing**: Vitest + React Testing Library

## Getting Started

```bash
# Install dependencies
cd frontend
npm install

# Run development server
npm run dev

# Run tests
npm test

# Build for production
npm run build

# Run linter
npm run lint
```

## Critical Rule: Frontend Isolation

⚠️ **ALL frontend code MUST stay within this `frontend/` directory.**

### What belongs here:
- ✅ React/Next.js components
- ✅ Styles (CSS, Tailwind configs)
- ✅ Frontend utilities and hooks
- ✅ Frontend tests
- ✅ Public assets (images, fonts, icons)
- ✅ Frontend configuration files
- ✅ Frontend dependencies (package.json)

### What does NOT belong here:
- ❌ Backend API code (use `src/omniforge/` for that)
- ❌ Python code
- ❌ Database models
- ❌ Backend utilities

## Communication with Backend

Frontend communicates with the backend **ONLY** through REST APIs or GraphQL.

- Never import backend code into frontend
- Never share code between frontend and backend
- Use API client (`lib/api/client.ts`) for all backend communication

## Documentation

See [Frontend Coding Guidelines](./coding-guidelines.md) for detailed coding standards and best practices.

## Project Structure

```
frontend/
├── app/                    # Next.js App Router pages
├── components/             # Reusable React components
├── lib/                    # Utilities, hooks, API client
├── types/                  # TypeScript definitions
├── styles/                 # Global styles
├── public/                 # Static assets
├── __tests__/              # Test files
└── coding-guidelines.md    # Coding standards
```

## Key Principles

1. **Simplicity over flexibility** - Clean, understandable components
2. **Reliability over speed** - Correct, accessible UIs first
3. **Enterprise-ready** - Security and scalability from day one
4. **API-first** - Backend communication via well-defined APIs only
5. **Test everything** - All components and hooks must have tests
