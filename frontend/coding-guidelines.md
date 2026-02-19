# Frontend Coding Guidelines

**Last Updated:** 2026-01-03

These guidelines ensure quality, consistency, and maintainability for all frontend code in the OmniForge platform.

## Core Principles

All frontend code must align with the [Product Vision](../specs/product-vision.md):

- **Simplicity over flexibility** - Clean, understandable React components over clever abstractions
- **Reliability over speed** - Correct, accessible UIs matter more than premature optimization
- **Enterprise-ready** - Security, accessibility, and scalability from day one

## Critical: Frontend Code Isolation

**ALL frontend-related code MUST stay within the `frontend/` folder.**

This includes:
- ✅ React/Next.js components
- ✅ Styles (CSS, Tailwind, CSS Modules)
- ✅ Frontend utilities and hooks
- ✅ Frontend tests
- ✅ Public assets (images, fonts, icons)
- ✅ Frontend configuration (tsconfig, next.config, etc.)
- ✅ Frontend dependencies (package.json)

**Never:**
- ❌ Place React components in backend folders
- ❌ Mix frontend and backend dependencies
- ❌ Share code between frontend and backend (use APIs)
- ❌ Put frontend assets outside `frontend/`

## Technology Stack

- **Framework**: Next.js 14+ (App Router)
- **Language**: TypeScript (strict mode)
- **Styling**: Tailwind CSS + CSS Modules for component-specific styles
- **State Management**: React Context + Hooks (Zustand for complex global state)
- **Forms**: React Hook Form + Zod validation
- **Testing**: Vitest + React Testing Library
- **API Client**: TanStack Query (React Query)

## Project Structure

```
frontend/
├── app/                    # Next.js App Router
│   ├── (auth)/            # Route groups
│   │   ├── login/
│   │   └── signup/
│   ├── agents/            # Agent management pages
│   ├── dashboard/         # Dashboard pages
│   ├── layout.tsx         # Root layout
│   └── page.tsx           # Home page
│
├── components/            # Reusable components
│   ├── ui/               # Base UI components (buttons, inputs)
│   ├── agents/           # Agent-specific components
│   ├── forms/            # Form components
│   └── layouts/          # Layout components
│
├── lib/                   # Utilities and configuration
│   ├── api/              # API client and endpoints
│   ├── hooks/            # Custom React hooks
│   ├── utils/            # Helper functions
│   ├── validators/       # Zod schemas
│   └── constants.ts      # App constants
│
├── types/                 # TypeScript type definitions
│   ├── agent.ts
│   ├── user.ts
│   └── api.ts
│
├── styles/               # Global styles
│   └── globals.css
│
├── public/               # Static assets
│   ├── images/
│   └── icons/
│
├── __tests__/            # Test files
│   ├── components/
│   ├── hooks/
│   └── utils/
│
├── .eslintrc.json        # ESLint config
├── .prettierrc           # Prettier config
├── tsconfig.json         # TypeScript config
├── next.config.js        # Next.js config
├── tailwind.config.ts    # Tailwind config
└── package.json          # Dependencies
```

## TypeScript Guidelines

**Strict mode is required** - no implicit any, proper typing everywhere.

### Component Props

Always define explicit prop types:

```typescript
// ✅ Good - Explicit props interface
interface AgentCardProps {
  agent: Agent;
  onEdit: (agentId: string) => void;
  onDelete: (agentId: string) => void;
  isLoading?: boolean;
}

export function AgentCard({ agent, onEdit, onDelete, isLoading = false }: AgentCardProps) {
  // Component implementation
}


// ❌ Bad - No prop types
export function AgentCard({ agent, onEdit, onDelete, isLoading }) {
  // TypeScript can't help you here
}
```

### Type Imports

Use type-only imports when possible:

```typescript
// ✅ Good - Type-only import
import type { Agent, AgentStatus } from '@/types/agent';
import { createAgent } from '@/lib/api/agents';

// ❌ Bad - Runtime import for types
import { Agent, AgentStatus } from '@/types/agent';
```

### Avoid Any

Never use `any` - use proper types or `unknown`:

```typescript
// ✅ Good - Proper typing
interface ApiResponse<T> {
  data: T;
  status: number;
  message: string;
}

async function fetchAgent(id: string): Promise<ApiResponse<Agent>> {
  const response = await fetch(`/api/agents/${id}`);
  return response.json();
}


// ❌ Bad - Using any
async function fetchAgent(id: string): Promise<any> {
  const response = await fetch(`/api/agents/${id}`);
  return response.json();
}
```

## Component Design

### Component Types

**Server Components by default** (Next.js App Router):

```typescript
// ✅ Good - Server Component (default)
import { getAgent } from '@/lib/api/agents';

interface AgentPageProps {
  params: { id: string };
}

export default async function AgentPage({ params }: AgentPageProps) {
  const agent = await getAgent(params.id);

  return (
    <div>
      <h1>{agent.name}</h1>
      <AgentDetails agent={agent} />
    </div>
  );
}


// Client Component only when needed
'use client';

import { useState } from 'react';

export function AgentEditor({ agent }: { agent: Agent }) {
  const [isEditing, setIsEditing] = useState(false);
  // Interactive component needs client-side state
}
```

**When to use Client Components (`'use client'`):**
- Interactive elements (buttons, forms, modals)
- React hooks (useState, useEffect, useContext)
- Browser APIs (localStorage, window, navigator)
- Event listeners (onClick, onChange, onSubmit)

### Single Responsibility

One component, one purpose:

```typescript
// ✅ Good - Focused components
export function AgentList({ agents }: { agents: Agent[] }) {
  return (
    <ul>
      {agents.map(agent => (
        <AgentListItem key={agent.id} agent={agent} />
      ))}
    </ul>
  );
}

export function AgentListItem({ agent }: { agent: Agent }) {
  return (
    <li>
      <AgentCard agent={agent} />
    </li>
  );
}

export function AgentCard({ agent }: { agent: Agent }) {
  return (
    <div className="card">
      <AgentStatus status={agent.status} />
      <AgentName name={agent.name} />
      <AgentActions agentId={agent.id} />
    </div>
  );
}


// ❌ Bad - God component doing everything
export function AgentManagement() {
  // 500 lines of mixed concerns:
  // - Fetching data
  // - Rendering list
  // - Handling forms
  // - Managing modals
  // - Business logic
  // - Styling
}
```

### Component Naming

Use clear, descriptive names:

```typescript
// ✅ Good - Clear purpose
function AgentCreateButton() { }
function AgentDeleteConfirmDialog() { }
function AgentStatusBadge() { }

// ❌ Bad - Vague names
function Button() { }
function Dialog() { }
function Badge() { }
```

### Props Destructuring

Destructure props in function signature:

```typescript
// ✅ Good - Destructured props
export function AgentCard({ agent, onEdit, isLoading = false }: AgentCardProps) {
  return <div>{agent.name}</div>;
}

// ❌ Bad - Props object
export function AgentCard(props: AgentCardProps) {
  return <div>{props.agent.name}</div>;
}
```

## State Management

### Local State

Use `useState` for component-local state:

```typescript
'use client';

export function AgentForm() {
  const [name, setName] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  return (
    <form>
      <input value={name} onChange={(e) => setName(e.target.value)} />
    </form>
  );
}
```

### Server State

Use TanStack Query for server data:

```typescript
'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

export function AgentList() {
  // Fetching
  const { data: agents, isLoading, error } = useQuery({
    queryKey: ['agents'],
    queryFn: fetchAgents,
  });

  const queryClient = useQueryClient();

  // Mutations
  const deleteAgent = useMutation({
    mutationFn: (id: string) => deleteAgentById(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agents'] });
    },
  });

  if (isLoading) return <AgentListSkeleton />;
  if (error) return <ErrorMessage error={error} />;

  return (
    <div>
      {agents?.map(agent => (
        <AgentCard
          key={agent.id}
          agent={agent}
          onDelete={() => deleteAgent.mutate(agent.id)}
        />
      ))}
    </div>
  );
}
```

### Global State

Use Context for simple global state:

```typescript
// lib/contexts/auth-context.tsx
'use client';

import { createContext, useContext, useState } from 'react';

interface AuthContextValue {
  user: User | null;
  login: (credentials: Credentials) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);

  const login = async (credentials: Credentials) => {
    const user = await loginApi(credentials);
    setUser(user);
  };

  const logout = () => setUser(null);

  return (
    <AuthContext.Provider value={{ user, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
}
```

Use Zustand for complex global state:

```typescript
// lib/store/agent-store.ts
import { create } from 'zustand';

interface AgentStore {
  selectedAgentId: string | null;
  setSelectedAgent: (id: string | null) => void;
  filters: AgentFilters;
  setFilters: (filters: AgentFilters) => void;
}

export const useAgentStore = create<AgentStore>((set) => ({
  selectedAgentId: null,
  setSelectedAgent: (id) => set({ selectedAgentId: id }),
  filters: {},
  setFilters: (filters) => set({ filters }),
}));
```

## Custom Hooks

Extract reusable logic into custom hooks:

```typescript
// ✅ Good - Custom hook for reusable logic
function useAgentActions(agentId: string) {
  const queryClient = useQueryClient();

  const deploy = useMutation({
    mutationFn: () => deployAgent(agentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agents', agentId] });
    },
  });

  const pause = useMutation({
    mutationFn: () => pauseAgent(agentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agents', agentId] });
    },
  });

  return { deploy, pause };
}

// Usage
export function AgentActionButtons({ agentId }: { agentId: string }) {
  const { deploy, pause } = useAgentActions(agentId);

  return (
    <>
      <button onClick={() => deploy.mutate()}>Deploy</button>
      <button onClick={() => pause.mutate()}>Pause</button>
    </>
  );
}
```

**Custom hook guidelines:**
- Name with `use` prefix
- Extract reusable logic, not one-off code
- Keep hooks focused and single-purpose
- Document parameters and return values

## Forms and Validation

Use React Hook Form + Zod:

```typescript
// lib/validators/agent.ts
import { z } from 'zod';

export const createAgentSchema = z.object({
  name: z.string().min(1, 'Name is required').max(255),
  capabilities: z.array(z.string()).min(1, 'At least one capability required'),
  environment: z.enum(['development', 'staging', 'production']),
});

export type CreateAgentInput = z.infer<typeof createAgentSchema>;


// components/forms/create-agent-form.tsx
'use client';

import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';

export function CreateAgentForm({ onSuccess }: { onSuccess: () => void }) {
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<CreateAgentInput>({
    resolver: zodResolver(createAgentSchema),
  });

  const onSubmit = async (data: CreateAgentInput) => {
    await createAgent(data);
    onSuccess();
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <div>
        <label htmlFor="name">Agent Name</label>
        <input {...register('name')} id="name" />
        {errors.name && <p className="error">{errors.name.message}</p>}
      </div>

      <div>
        <label htmlFor="environment">Environment</label>
        <select {...register('environment')} id="environment">
          <option value="development">Development</option>
          <option value="staging">Staging</option>
          <option value="production">Production</option>
        </select>
        {errors.environment && <p className="error">{errors.environment.message}</p>}
      </div>

      <button type="submit" disabled={isSubmitting}>
        {isSubmitting ? 'Creating...' : 'Create Agent'}
      </button>
    </form>
  );
}
```

## Styling

### Tailwind CSS

Use Tailwind for utility-first styling:

```typescript
// ✅ Good - Tailwind utilities
export function AgentCard({ agent }: { agent: Agent }) {
  return (
    <div className="rounded-lg border border-gray-200 p-6 shadow-sm hover:shadow-md transition-shadow">
      <h3 className="text-lg font-semibold text-gray-900">{agent.name}</h3>
      <p className="mt-2 text-sm text-gray-600">{agent.description}</p>
      <div className="mt-4 flex gap-2">
        <button className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
          Deploy
        </button>
      </div>
    </div>
  );
}
```

### CSS Modules for Complex Components

Use CSS Modules when Tailwind becomes unwieldy:

```typescript
// components/agents/agent-card.module.css
.card {
  border-radius: 0.5rem;
  border: 1px solid var(--gray-200);
  padding: 1.5rem;
  transition: box-shadow 0.2s;
}

.card:hover {
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}

.cardTitle {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--gray-900);
}


// components/agents/agent-card.tsx
import styles from './agent-card.module.css';

export function AgentCard({ agent }: { agent: Agent }) {
  return (
    <div className={styles.card}>
      <h3 className={styles.cardTitle}>{agent.name}</h3>
    </div>
  );
}
```

### Conditional Classes

Use `clsx` or `cn` utility for conditional classes:

```typescript
// lib/utils/cn.ts
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}


// Usage
import { cn } from '@/lib/utils/cn';

export function Button({ variant, className, ...props }: ButtonProps) {
  return (
    <button
      className={cn(
        'px-4 py-2 rounded font-medium',
        variant === 'primary' && 'bg-blue-600 text-white hover:bg-blue-700',
        variant === 'secondary' && 'bg-gray-200 text-gray-900 hover:bg-gray-300',
        className
      )}
      {...props}
    />
  );
}
```

## API Communication

### API Client Setup

```typescript
// lib/api/client.ts
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

export async function apiClient<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  });

  if (!response.ok) {
    throw new ApiError(response.status, `API error: ${response.statusText}`);
  }

  return response.json();
}
```

### API Functions

```typescript
// lib/api/agents.ts
import type { Agent, CreateAgentInput } from '@/types/agent';
import { apiClient } from './client';

export async function fetchAgents(): Promise<Agent[]> {
  return apiClient<Agent[]>('/agents');
}

export async function getAgent(id: string): Promise<Agent> {
  return apiClient<Agent>(`/agents/${id}`);
}

export async function createAgent(data: CreateAgentInput): Promise<Agent> {
  return apiClient<Agent>('/agents', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function deleteAgent(id: string): Promise<void> {
  return apiClient<void>(`/agents/${id}`, {
    method: 'DELETE',
  });
}
```

## Testing

**All components and hooks must have tests.**

### Component Testing

```typescript
// __tests__/components/agent-card.test.tsx
import { render, screen } from '@testing-library/react';
import { AgentCard } from '@/components/agents/agent-card';
import { describe, it, expect, vi } from 'vitest';

describe('AgentCard', () => {
  const mockAgent = {
    id: '1',
    name: 'Test Agent',
    status: 'active',
    createdAt: new Date(),
  };

  it('renders agent name', () => {
    render(<AgentCard agent={mockAgent} onEdit={vi.fn()} onDelete={vi.fn()} />);

    expect(screen.getByText('Test Agent')).toBeInTheDocument();
  });

  it('calls onEdit when edit button clicked', async () => {
    const onEdit = vi.fn();
    const { user } = render(
      <AgentCard agent={mockAgent} onEdit={onEdit} onDelete={vi.fn()} />
    );

    await user.click(screen.getByRole('button', { name: /edit/i }));

    expect(onEdit).toHaveBeenCalledWith('1');
  });

  it('displays active status badge', () => {
    render(<AgentCard agent={mockAgent} onEdit={vi.fn()} onDelete={vi.fn()} />);

    const badge = screen.getByText(/active/i);
    expect(badge).toHaveClass('bg-green-100');
  });
});
```

### Hook Testing

```typescript
// __tests__/hooks/use-agent-actions.test.ts
import { renderHook, waitFor } from '@testing-library/react';
import { useAgentActions } from '@/lib/hooks/use-agent-actions';
import { describe, it, expect, vi } from 'vitest';

describe('useAgentActions', () => {
  it('deploys agent successfully', async () => {
    const { result } = renderHook(() => useAgentActions('agent-1'));

    result.current.deploy.mutate();

    await waitFor(() => {
      expect(result.current.deploy.isSuccess).toBe(true);
    });
  });
});
```

## Accessibility

**Accessibility is required, not optional.**

### Semantic HTML

```typescript
// ✅ Good - Semantic HTML
export function AgentList({ agents }: { agents: Agent[] }) {
  return (
    <section aria-labelledby="agents-heading">
      <h2 id="agents-heading">Your Agents</h2>
      <ul>
        {agents.map(agent => (
          <li key={agent.id}>
            <article>
              <h3>{agent.name}</h3>
            </article>
          </li>
        ))}
      </ul>
    </section>
  );
}

// ❌ Bad - Divs everywhere
export function AgentList({ agents }: { agents: Agent[] }) {
  return (
    <div>
      <div>Your Agents</div>
      <div>
        {agents.map(agent => (
          <div key={agent.id}>
            <div>{agent.name}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
```

### ARIA Labels

```typescript
// ✅ Good - Proper labels
<button
  onClick={handleDelete}
  aria-label={`Delete agent ${agent.name}`}
>
  <TrashIcon />
</button>

<input
  type="search"
  placeholder="Search agents..."
  aria-label="Search agents"
/>

// ❌ Bad - No labels for icon buttons
<button onClick={handleDelete}>
  <TrashIcon />
</button>
```

### Keyboard Navigation

```typescript
'use client';

export function Modal({ isOpen, onClose, children }: ModalProps) {
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };

    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
      return () => document.removeEventListener('keydown', handleEscape);
    }
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-50"
    >
      {children}
    </div>
  );
}
```

## Performance

### Code Splitting

```typescript
// Dynamic imports for heavy components
import dynamic from 'next/dynamic';

const AgentEditor = dynamic(() => import('@/components/agents/agent-editor'), {
  loading: () => <AgentEditorSkeleton />,
  ssr: false, // Client-side only if needed
});
```

### Memoization

```typescript
import { memo, useMemo, useCallback } from 'react';

// Memoize expensive components
export const AgentCard = memo(function AgentCard({ agent, onEdit }: AgentCardProps) {
  return <div>{agent.name}</div>;
});

// Memoize expensive calculations
export function AgentDashboard({ agents }: { agents: Agent[] }) {
  const stats = useMemo(() => {
    return {
      total: agents.length,
      active: agents.filter(a => a.status === 'active').length,
      paused: agents.filter(a => a.status === 'paused').length,
    };
  }, [agents]);

  return <div>{stats.total} agents</div>;
}

// Memoize callbacks passed to children
export function AgentList({ agents }: { agents: Agent[] }) {
  const handleEdit = useCallback((id: string) => {
    console.log('Editing', id);
  }, []);

  return (
    <div>
      {agents.map(agent => (
        <AgentCard key={agent.id} agent={agent} onEdit={handleEdit} />
      ))}
    </div>
  );
}
```

## Error Handling

### Error Boundaries

```typescript
// components/error-boundary.tsx
'use client';

import { Component, type ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback || (
        <div className="error-boundary">
          <h2>Something went wrong</h2>
          <p>{this.state.error?.message}</p>
        </div>
      );
    }

    return this.props.children;
  }
}
```

### Loading and Error States

```typescript
'use client';

export function AgentList() {
  const { data: agents, isLoading, error } = useQuery({
    queryKey: ['agents'],
    queryFn: fetchAgents,
  });

  if (isLoading) {
    return <AgentListSkeleton />;
  }

  if (error) {
    return (
      <div className="error-message" role="alert">
        <h3>Failed to load agents</h3>
        <p>{error.message}</p>
        <button onClick={() => window.location.reload()}>Retry</button>
      </div>
    );
  }

  if (!agents || agents.length === 0) {
    return <EmptyState message="No agents found" />;
  }

  return (
    <ul>
      {agents.map(agent => (
        <AgentListItem key={agent.id} agent={agent} />
      ))}
    </ul>
  );
}
```

## Code Review Checklist

Before submitting frontend code for review:

**Code Quality:**
- [ ] TypeScript strict mode enabled, no `any` types
- [ ] All components and hooks have proper TypeScript types
- [ ] ESLint passes with no warnings
- [ ] Prettier formatting applied
- [ ] No console.log statements in production code

**Component Design:**
- [ ] Components follow single responsibility principle
- [ ] Server Components used by default, Client Components only when needed
- [ ] Props properly typed with interfaces
- [ ] Components are small and focused (< 200 lines)

**State Management:**
- [ ] Local state for UI, TanStack Query for server state
- [ ] No prop drilling (use Context or Zustand for deep state)
- [ ] Forms use React Hook Form + Zod validation

**Styling:**
- [ ] Tailwind CSS used for styling
- [ ] No inline styles (except dynamic values)
- [ ] Responsive design implemented (mobile-first)
- [ ] Dark mode support if applicable

**Accessibility:**
- [ ] Semantic HTML elements used
- [ ] ARIA labels on interactive elements
- [ ] Keyboard navigation works
- [ ] Color contrast meets WCAG AA standards
- [ ] Focus states visible

**Performance:**
- [ ] Heavy components are code-split
- [ ] Images optimized and use Next.js Image component
- [ ] No unnecessary re-renders (use memo/useMemo/useCallback)
- [ ] API calls are cached and deduplicated

**Testing:**
- [ ] All components have tests
- [ ] Custom hooks have tests
- [ ] Critical user flows are tested
- [ ] Accessibility tested with screen reader

**Security:**
- [ ] No sensitive data in client-side code
- [ ] API calls use proper authentication
- [ ] User input is validated and sanitized
- [ ] XSS protection in place

**Frontend Isolation:**
- [ ] All frontend code is in `frontend/` folder
- [ ] No backend code imported into frontend
- [ ] Communication with backend is via APIs only

## Resources

- [Next.js Documentation](https://nextjs.org/docs)
- [React Documentation](https://react.dev)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)
- [Tailwind CSS](https://tailwindcss.com/docs)
- [TanStack Query](https://tanstack.com/query/latest)
- [React Hook Form](https://react-hook-form.com/)
- [Zod](https://zod.dev/)
- [Product Vision](../specs/product-vision.md)
