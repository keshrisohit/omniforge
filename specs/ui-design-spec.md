# OmniForge UI/UX Design Specification

**Created**: 2026-01-25
**Last Updated**: 2026-01-25
**Version**: 1.0
**Status**: Draft

---

## Overview

This specification defines the comprehensive UI/UX design system for the OmniForge premium platform. The design philosophy follows a modern minimal aesthetic inspired by Linear, Notion, and Vercel - prioritizing clarity, whitespace, and purposeful interactions. The platform enables non-technical users to create automation agents through natural conversation while providing technical administrators with powerful management and monitoring capabilities.

---

## Alignment with Product Vision

| Vision Principle | How UI/UX Delivers |
|------------------|-------------------|
| **Agents Build Agents** | Chat-first interface makes agent creation conversational and intuitive |
| **Simplicity Over Flexibility** | Clean, focused UI with progressive disclosure - advanced options hidden until needed |
| **No-Code Interface** | Visual representations of agents, skills, and workflows - no code visible to users |
| **Enterprise-Ready** | Team management, RBAC controls, and audit logs seamlessly integrated |
| **Reliability** | Clear status indicators, execution history, and error states build trust |

---

## Design System Foundation

### Design Tokens

#### Colors

**Light Mode**

| Token | Value | Usage |
|-------|-------|-------|
| `--bg-primary` | `#FFFFFF` | Main background |
| `--bg-secondary` | `#FAFAFA` | Secondary surfaces, sidebars |
| `--bg-tertiary` | `#F5F5F5` | Cards, inputs, hover states |
| `--border-subtle` | `#E5E5E5` | Subtle dividers |
| `--border-default` | `#D4D4D4` | Default borders |
| `--text-primary` | `#171717` | Primary text |
| `--text-secondary` | `#525252` | Secondary text |
| `--text-muted` | `#A3A3A3` | Muted text, placeholders |
| `--accent-primary` | `#2563EB` | Primary actions, links |
| `--accent-hover` | `#1D4ED8` | Primary hover state |
| `--success` | `#16A34A` | Success states |
| `--warning` | `#D97706` | Warning states |
| `--error` | `#DC2626` | Error states |
| `--info` | `#0EA5E9` | Info states |

**Dark Mode**

| Token | Value | Usage |
|-------|-------|-------|
| `--bg-primary` | `#0A0A0A` | Main background |
| `--bg-secondary` | `#141414` | Secondary surfaces, sidebars |
| `--bg-tertiary` | `#1F1F1F` | Cards, inputs, hover states |
| `--border-subtle` | `#262626` | Subtle dividers |
| `--border-default` | `#404040` | Default borders |
| `--text-primary` | `#FAFAFA` | Primary text |
| `--text-secondary` | `#A3A3A3` | Secondary text |
| `--text-muted` | `#525252` | Muted text, placeholders |
| `--accent-primary` | `#3B82F6` | Primary actions, links |
| `--accent-hover` | `#60A5FA` | Primary hover state |

#### Typography

| Token | Font | Weight | Size | Line Height |
|-------|------|--------|------|-------------|
| `--heading-xl` | Inter/Geist | 600 | 32px | 40px |
| `--heading-lg` | Inter/Geist | 600 | 24px | 32px |
| `--heading-md` | Inter/Geist | 600 | 20px | 28px |
| `--heading-sm` | Inter/Geist | 600 | 16px | 24px |
| `--body-lg` | Inter/Geist | 400 | 16px | 24px |
| `--body-md` | Inter/Geist | 400 | 14px | 20px |
| `--body-sm` | Inter/Geist | 400 | 13px | 18px |
| `--body-xs` | Inter/Geist | 400 | 12px | 16px |
| `--mono` | Geist Mono | 400 | 13px | 20px |

#### Spacing Scale

| Token | Value |
|-------|-------|
| `--space-0` | 0px |
| `--space-1` | 4px |
| `--space-2` | 8px |
| `--space-3` | 12px |
| `--space-4` | 16px |
| `--space-5` | 20px |
| `--space-6` | 24px |
| `--space-8` | 32px |
| `--space-10` | 40px |
| `--space-12` | 48px |
| `--space-16` | 64px |

#### Border Radius

| Token | Value |
|-------|-------|
| `--radius-sm` | 4px |
| `--radius-md` | 6px |
| `--radius-lg` | 8px |
| `--radius-xl` | 12px |
| `--radius-2xl` | 16px |
| `--radius-full` | 9999px |

#### Shadows

| Token | Value |
|-------|-------|
| `--shadow-sm` | `0 1px 2px rgba(0,0,0,0.05)` |
| `--shadow-md` | `0 4px 6px -1px rgba(0,0,0,0.07), 0 2px 4px -1px rgba(0,0,0,0.04)` |
| `--shadow-lg` | `0 10px 15px -3px rgba(0,0,0,0.08), 0 4px 6px -2px rgba(0,0,0,0.04)` |
| `--shadow-xl` | `0 20px 25px -5px rgba(0,0,0,0.08), 0 10px 10px -5px rgba(0,0,0,0.03)` |

#### Animation & Transitions

| Token | Value | Usage |
|-------|-------|-------|
| `--duration-fast` | 100ms | Micro-interactions |
| `--duration-normal` | 200ms | Standard transitions |
| `--duration-slow` | 300ms | Complex animations |
| `--ease-default` | `cubic-bezier(0.4, 0, 0.2, 1)` | Default easing |
| `--ease-in` | `cubic-bezier(0.4, 0, 1, 1)` | Entering elements |
| `--ease-out` | `cubic-bezier(0, 0, 0.2, 1)` | Exiting elements |

---

## Navigation Structure

### Global Navigation

```
+------------------------------------------+
| [Logo] OmniForge                    [?] [User] |
+------------------------------------------+
|         |                                 |
| [Home]  |                                 |
| [Chat]  |        MAIN CONTENT             |
| [Agents]|                                 |
| [Skills]|                                 |
| [Integ..]|                                |
| [Analyt..]|                               |
|         |                                 |
+---------+                                 |
| [Settings]                                |
+------------------------------------------+
```

**Left Sidebar (Collapsed by Default)**
- Width: 64px collapsed, 240px expanded
- Hover or click to expand
- Persistent across all pages
- Contains primary navigation icons

**Top Bar**
- Height: 56px
- Contains: Logo, breadcrumbs, search (Cmd+K), help, notifications, user menu

**Main Content Area**
- Max-width: 1440px (centered)
- Padding: 32px horizontal, 24px vertical

### Navigation Items

| Icon | Label | Route | Description |
|------|-------|-------|-------------|
| Home | Dashboard | `/` | Overview and quick actions |
| MessageSquare | Agent Builder | `/chat` | Conversational agent creation |
| Bot | My Agents | `/agents` | Agent list and management |
| Blocks | Skill Library | `/skills` | Browse and search skills |
| Plug | Integrations | `/integrations` | Connected services |
| BarChart3 | Analytics | `/analytics` | Usage and performance metrics |
| Settings | Settings | `/settings` | Account and team settings |

---

## Page Specifications

### 1. Authentication

#### 1.1 Login Page

**Purpose**: Authenticate users with emphasis on SSO for enterprise customers.

**Layout**
```
+--------------------------------------------------+
|                                                  |
|              [OmniForge Logo]                    |
|                                                  |
|        Welcome back to OmniForge                 |
|     Create, deploy, and manage AI agents         |
|                                                  |
|  +------------------------------------------+    |
|  |  [G] Continue with Google                |    |
|  +------------------------------------------+    |
|  |  [MS] Continue with Microsoft            |    |
|  +------------------------------------------+    |
|  |  [SAML] Continue with SSO                |    |
|  +------------------------------------------+    |
|                                                  |
|                    ---- or ----                  |
|                                                  |
|  Email                                           |
|  +------------------------------------------+    |
|  |  name@company.com                        |    |
|  +------------------------------------------+    |
|                                                  |
|  Password                                        |
|  +------------------------------------------+    |
|  |  ********                           [Eye]|    |
|  +------------------------------------------+    |
|                                                  |
|  [        Sign In        ]    Forgot password?  |
|                                                  |
|  Don't have an account? Sign up                  |
|                                                  |
+--------------------------------------------------+
```

**Key Components**
- **Logo**: Centered, 48px height
- **Headline**: `--heading-lg`, centered
- **Subheadline**: `--body-md`, `--text-secondary`
- **SSO Buttons**: Full-width, stacked, 48px height, `--border-default`
- **Divider**: Horizontal line with "or" text centered
- **Form Inputs**: Full-width, 44px height, focus ring `--accent-primary`
- **Primary Button**: Full-width, 44px height, `--accent-primary` background
- **Links**: `--accent-primary`, underline on hover

**States**
- **Loading**: Button shows spinner, inputs disabled
- **Error**: Red border on invalid field, error message below in `--error`
- **SSO Redirect**: Loading overlay with progress indicator

**Mobile Considerations**
- Stack all elements vertically
- Full-width container with 16px horizontal padding
- Touch-friendly button heights (48px minimum)

#### 1.2 Signup Flow

**Purpose**: Onboard new users with minimal friction.

**Flow Steps**
1. **Email Entry**: Single input, check if domain requires SSO
2. **SSO Redirect** (if enterprise domain): Redirect to identity provider
3. **Password Creation** (if non-SSO): Password + confirmation
4. **Profile Setup**: Name, optional avatar, job role (dropdown)
5. **Team Setup**: Create team or join existing (via invite code)
6. **Welcome**: Quick tour option, link to create first agent

**Key Components**
- **Progress Indicator**: Dots or steps at top (e.g., "Step 2 of 4")
- **Back Button**: Top-left, allows returning to previous step
- **Form Fields**: Same styling as login
- **Skip Option**: For optional steps (e.g., avatar upload)

---

### 2. Main Dashboard

**Purpose**: Provide overview of agent status, recent activity, and quick actions.

**Layout**
```
+--------------------------------------------------+
| Dashboard                           [+ New Agent]|
+--------------------------------------------------+
|                                                  |
| Good morning, Maya                               |
|                                                  |
| +----------------+  +----------------+  +--------+
| | Active Agents  |  | Executions     |  | Success|
| |       12       |  | 1,247 (7d)     |  |  96.2% |
| +----------------+  +----------------+  +--------+
|                                                  |
| RECENT ACTIVITY                         View All |
| +----------------------------------------------+ |
| | [Bot] Weekly Reporter ran successfully       | |
| | 2 minutes ago                                | |
| +----------------------------------------------+ |
| | [Bot] Meeting Briefing triggered             | |
| | 15 minutes ago                               | |
| +----------------------------------------------+ |
| | [Warning] Slack Integration expiring soon    | |
| | 1 hour ago                                   | |
| +----------------------------------------------+ |
|                                                  |
| MY AGENTS                               View All |
| +---------------------+  +---------------------+ |
| | Weekly Reporter     |  | Meeting Briefing   | |
| | Active - Mon 8:30am |  | Active - On event  | |
| | Last: 2 min ago OK  |  | Last: 15 min ago OK| |
| | [Run Now] [Edit]    |  | [Run Now] [Edit]   | |
| +---------------------+  +---------------------+ |
|                                                  |
| QUICK ACTIONS                                    |
| +---------------------+  +---------------------+ |
| | [+] Create Agent    |  | [Plug] Connect App | |
| | Build with AI chat  |  | Add integration    | |
| +---------------------+  +---------------------+ |
|                                                  |
+--------------------------------------------------+
```

**Key Components**

**Metric Cards**
- Height: 100px
- Background: `--bg-tertiary`
- Border: `--border-subtle`
- Radius: `--radius-lg`
- Metric value: `--heading-xl`
- Label: `--body-sm`, `--text-secondary`
- Trend indicator: Arrow + percentage, colored by direction

**Activity Feed**
- List of recent events with icon, description, timestamp
- Icon colors: Success (green), Warning (yellow), Error (red), Info (blue)
- Timestamp: Relative (e.g., "2 minutes ago")
- Clickable rows navigate to relevant detail page
- Max 5 items, "View All" link

**Agent Cards**
- Width: Responsive grid (2-4 columns)
- Height: Auto, min 140px
- Shows: Name, status badge, trigger type, last run, quick actions
- Status badge: Active (green), Paused (gray), Error (red)
- Hover: Subtle shadow increase, action buttons appear

**Quick Actions**
- Large clickable cards with icon and description
- Primary actions: Create Agent, Connect Integration

**States**
- **Empty State**: Illustration + "Create your first agent" CTA
- **Loading**: Skeleton loaders for all cards
- **Error**: Error banner at top with retry option

**Mobile Considerations**
- Single column layout
- Metric cards scroll horizontally
- Agent cards stack vertically
- Quick actions as floating action button (FAB)

---

### 3. Conversational Agent Builder (CORE FEATURE)

**Purpose**: Enable users to create agents through natural language conversation.

#### 3.1 Chat Interface (Primary View)

**Layout**
```
+--------------------------------------------------+
| Agent Builder                    [Skill Library] |
+--------------------------------------------------+
|                                                  |
|                                                  |
|        [Bot Avatar]                              |
|        Hi Maya! I'm here to help you             |
|        create automation agents.                 |
|                                                  |
|        What would you like to automate           |
|        today? You can describe it in             |
|        plain English.                            |
|                                                  |
|        Examples:                                 |
|        - Generate weekly reports from Notion     |
|        - Alert me when deadlines approach        |
|        - Match invoices with purchase orders     |
|                                                  |
|                                                  |
|                                                  |
|                                                  |
|                                                  |
+--------------------------------------------------+
|  +--------------------------------------------+  |
|  | Describe what you want to automate...   [->] |
|  +--------------------------------------------+  |
+--------------------------------------------------+
```

**Message Types**

**User Message**
```
+--------------------------------------------------+
|                                   [User Avatar]  |
|        Generate weekly reports from my Notion    |
|        databases and post to Slack every Monday  |
+--------------------------------------------------+
```
- Aligned right
- Background: `--accent-primary` with white text
- Radius: `--radius-lg` (top-left, bottom-left, bottom-right)
- Max-width: 70%

**Bot Message**
```
+--------------------------------------------------+
| [Bot Avatar]                                     |
| I can help you create that! Let me understand    |
| your workflow better.                            |
|                                                  |
| Which Notion databases should I include?         |
|                                                  |
| +-------------------+  +-------------------+     |
| | Client Projects   |  | Internal Tasks    |     |
| +-------------------+  +-------------------+     |
| +-------------------+                           |
| | Team Initiatives  |                           |
| +-------------------+                           |
|                                                  |
| [Select databases]                              |
+--------------------------------------------------+
```
- Aligned left
- Background: `--bg-tertiary`
- Radius: `--radius-lg` (top-right, bottom-left, bottom-right)
- Max-width: 70%
- Can contain: Text, quick reply buttons, selectable options, cards

**Interactive Elements in Messages**

**Quick Reply Buttons**
- Horizontal scrollable row
- Pill-shaped buttons
- Border: `--border-default`
- Hover: `--bg-tertiary`
- Click: Sends as user message

**Selection Cards**
- Multi-select checkboxes
- Show integration icon + name
- Selected state: Border `--accent-primary`, checkmark

**Agent Preview Card**
```
+----------------------------------------------+
|  AGENT PREVIEW                               |
|                                              |
|  Weekly Reporter                             |
|  Generates weekly reports from Notion and    |
|  posts to Slack                              |
|                                              |
|  SKILLS:                                     |
|  1. Notion Weekly Summary (public)           |
|  2. Slack Poster (custom)                    |
|                                              |
|  TRIGGER: Every Monday at 8:30 AM            |
|                                              |
|  [Edit Details]  [Test Agent]  [Create]      |
+----------------------------------------------+
```
- Full-width within message
- Shows agent summary before creation
- Action buttons for editing, testing, creating

**Input Area**
- Height: 56px minimum, auto-expand to 200px max
- Background: `--bg-tertiary`
- Border: `--border-default`
- Focus: Border `--accent-primary`
- Placeholder: "Describe what you want to automate..."
- Send button: Icon only, `--accent-primary`
- Supports: Text input, file upload (drag & drop)

**Typing Indicator**
- Three animated dots
- Appears when bot is processing
- "OmniForge is thinking..."

#### 3.2 Integration Connection Flow

**Triggered When**: User mentions an integration they haven't connected.

**Flow**
```
Bot: "I see you want to connect to Notion. Let me help
      you set that up.

      [Connect Notion]"

User clicks [Connect Notion]

+--------------------------------------------------+
|  CONNECT NOTION                           [X]    |
+--------------------------------------------------+
|                                                  |
|  [Notion Logo]                                   |
|                                                  |
|  OmniForge needs access to your Notion           |
|  workspace to create automations.                |
|                                                  |
|  We'll request access to:                        |
|  [Check] Read your databases                     |
|  [Check] Read page content                       |
|  [Check] Create and update pages                 |
|                                                  |
|  +--------------------------------------------+  |
|  |  [Notion] Connect with Notion              |  |
|  +--------------------------------------------+  |
|                                                  |
|  Your data is encrypted and secure.             |
|  [Learn about our security]                      |
|                                                  |
+--------------------------------------------------+
```

**OAuth Flow**
1. Modal explains permissions
2. User clicks "Connect with [Service]"
3. Opens OAuth popup/redirect
4. On success: Modal closes, chat continues
5. On failure: Error message with retry option

**Post-Connection**
```
Bot: "Notion connected! I can see these databases:

      - Client Projects (32 pages)
      - Internal Tasks (156 pages)
      - Team Initiatives (12 pages)

      Which ones should I include in your weekly report?"
```

#### 3.3 Agent Testing Interface

**Triggered When**: User wants to test before creating agent.

**Layout**
```
+--------------------------------------------------+
| TEST: Weekly Reporter                     [X]    |
+--------------------------------------------------+
|                                                  |
|  Running test with your actual data...           |
|                                                  |
|  STEP 1: Fetching Notion data            [Done]  |
|  STEP 2: Generating report               [Done]  |
|  STEP 3: Preparing Slack message      [Running]  |
|                                                  |
+--------------------------------------------------+
|  TEST OUTPUT                                     |
|                                                  |
|  # Weekly Report - Jan 25, 2026                  |
|                                                  |
|  ## Client Projects                              |
|  - Project Alpha: On Track (3 updates)           |
|  - Project Beta: At Risk (blocker identified)    |
|                                                  |
|  ## Internal Tasks                               |
|  - 12 tasks completed                            |
|  - 5 tasks in progress                           |
|                                                  |
+--------------------------------------------------+
|  [Cancel Test]  [Edit Agent]  [Looks Good!]      |
+--------------------------------------------------+
```

**Key Elements**
- Step-by-step progress with status icons
- Live output preview (scrollable)
- Syntax highlighting for reports
- Action buttons: Cancel, Edit, Confirm

#### 3.4 Skill Library Browser (Sidebar)

**Triggered When**: User clicks "Skill Library" or bot suggests public skills.

**Layout**
```
+--------------------------------------------------+
|                    |  SKILL LIBRARY              |
|                    +-----------------------------+
|                    |  [Search skills...]         |
|   MAIN CHAT        |                             |
|   AREA             |  CATEGORIES                 |
|                    |  [All] [Notion] [Slack]     |
|                    |  [Reports] [Notifications]  |
|                    |                             |
|                    |  POPULAR SKILLS             |
|                    |  +-------------------------+|
|                    |  | Notion Weekly Summary   ||
|                    |  | by @derek - 247 users   ||
|                    |  | [Use This]              ||
|                    |  +-------------------------+|
|                    |  +-------------------------+|
|                    |  | Slack Alert Sender      ||
|                    |  | by @omniforge - 1.2k    ||
|                    |  | [Use This]              ||
|                    |  +-------------------------+|
|                    |                             |
+--------------------------------------------------+
```

**Skill Card**
- Name, author, usage count
- Integration icons
- Brief description (truncated)
- "Use This" button
- Click card for full details

**States**
- **Empty State**: When building first agent, show curated suggestions
- **Loading State**: Skeleton cards
- **Error State**: Retry button

---

### 4. Agent Management

#### 4.1 Agent List

**Purpose**: View and manage all created agents.

**Layout**
```
+--------------------------------------------------+
| My Agents                            [+ New Agent]|
+--------------------------------------------------+
|                                                  |
| [Search agents...]  [Status: All v] [Sort: Recent v] |
|                                                  |
| [Grid View] [List View]                          |
|                                                  |
+--------------------------------------------------+

GRID VIEW:
+---------------------+  +---------------------+
|  Weekly Reporter    |  |  Meeting Briefing   |
|  [Active]           |  |  [Active]           |
|                     |  |                     |
|  Generates weekly   |  |  Creates briefing   |
|  reports from...    |  |  docs before...     |
|                     |  |                     |
|  [Notion] [Slack]   |  |  [Notion] [Calendar]|
|                     |  |                     |
|  Last run: 2m ago   |  |  Last run: 15m ago  |
|  [OK] 96% success   |  |  [OK] 100% success  |
|                     |  |                     |
|  [Run] [Pause] ...  |  |  [Run] [Pause] ...  |
+---------------------+  +---------------------+

LIST VIEW:
+--------------------------------------------------+
| [Check] | Name           | Status | Last Run | Actions |
+--------------------------------------------------+
| [ ]     | Weekly Reporter | Active | 2m ago   | [...] |
| [ ]     | Meeting Briefing| Active | 15m ago  | [...] |
| [ ]     | Invoice Matcher | Paused | 2d ago   | [...] |
+--------------------------------------------------+
```

**Key Components**

**View Toggle**
- Icon buttons for grid/list
- Persists preference

**Filters & Sort**
- Status: All, Active, Paused, Error
- Sort: Recent activity, Name A-Z, Created date
- Search: Fuzzy match on name and description

**Agent Card (Grid)**
- Width: 320px (flexible grid)
- Height: Auto
- Contents: Name, status badge, description (2 lines), integration icons, last run, success rate, actions
- Hover: Elevate shadow, show all action buttons

**Agent Row (List)**
- Checkbox for bulk actions
- Name (clickable to detail)
- Status badge
- Last run (relative time)
- Action menu (...)

**Bulk Actions**
- When items selected, show action bar
- Actions: Pause Selected, Delete Selected, Export

**States**
- **Empty**: Illustration + "Create your first agent" CTA
- **Loading**: Skeleton cards/rows
- **Error**: Banner with retry

#### 4.2 Agent Detail Page

**Purpose**: View agent details, execution history, and settings.

**Layout**
```
+--------------------------------------------------+
| [<] My Agents                                    |
+--------------------------------------------------+
| Weekly Reporter                        [Actions v]|
| Generates weekly reports from Notion and posts   |
| to Slack                                         |
|                                                  |
| [Active]  [Notion] [Slack]  Created Jan 15, 2026 |
|                                                  |
+--------------------------------------------------+
| [Overview] [Executions] [Settings]               |
+--------------------------------------------------+

OVERVIEW TAB:
+--------------------------------------------------+
|                                                  |
| QUICK STATS                                      |
| +----------+  +----------+  +----------+         |
| | 127      |  | 96.2%    |  | 3.2s     |         |
| | Runs     |  | Success  |  | Avg Time |         |
| +----------+  +----------+  +----------+         |
|                                                  |
| TRIGGER                                          |
| Schedule: Every Monday at 8:30 AM (UTC-8)        |
| Next run: Jan 27, 2026 at 8:30 AM                |
|                                                  |
| SKILLS                                           |
| +--------------------------------------------+   |
| | 1. Notion Weekly Summary (public)          |   |
| |    Fetches data from: Client Projects,     |   |
| |    Internal Tasks                          |   |
| +--------------------------------------------+   |
| | 2. Slack Poster (custom)                   |   |
| |    Posts to: #team-updates                 |   |
| +--------------------------------------------+   |
|                                                  |
| [Run Now]  [Edit Agent]  [Pause]                 |
|                                                  |
+--------------------------------------------------+
```

**Tab: Executions**
```
+--------------------------------------------------+
| EXECUTION HISTORY                    [Filter v]  |
+--------------------------------------------------+
| [OK] Jan 20, 8:30 AM    3.1s   [View Log]        |
| [OK] Jan 13, 8:30 AM    3.4s   [View Log]        |
| [!!] Jan 6, 8:30 AM     --     [View Log]        |
|      Error: Notion API rate limit                 |
| [OK] Dec 30, 8:30 AM    2.9s   [View Log]        |
+--------------------------------------------------+
```

**Tab: Settings**
```
+--------------------------------------------------+
| AGENT SETTINGS                                   |
+--------------------------------------------------+
|                                                  |
| Name                                             |
| +--------------------------------------------+   |
| | Weekly Reporter                            |   |
| +--------------------------------------------+   |
|                                                  |
| Description                                      |
| +--------------------------------------------+   |
| | Generates weekly reports from Notion and   |   |
| | posts to Slack                             |   |
| +--------------------------------------------+   |
|                                                  |
| Trigger                                          |
| ( ) On-demand only                               |
| (x) Scheduled                                    |
|     [Every Monday] at [8:30 AM] [UTC-8]          |
| ( ) Event-triggered                              |
|                                                  |
| DANGER ZONE                                      |
| [Delete Agent]                                   |
|                                                  |
+--------------------------------------------------+
```

#### 4.3 Execution Log Viewer

**Purpose**: View detailed execution logs for debugging.

**Layout (Modal or Side Panel)**
```
+--------------------------------------------------+
| EXECUTION LOG                              [X]   |
| Jan 20, 2026 at 8:30:15 AM                       |
+--------------------------------------------------+
| Duration: 3.1s    Status: [Success]              |
+--------------------------------------------------+
|                                                  |
| [8:30:15] Starting agent: Weekly Reporter        |
| [8:30:15] Running skill: Notion Weekly Summary   |
| [8:30:16] Fetched 32 pages from Client Projects  |
| [8:30:17] Fetched 156 pages from Internal Tasks  |
| [8:30:18] Generated report (2.3kb)               |
| [8:30:18] Running skill: Slack Poster            |
| [8:30:19] Posted to #team-updates                |
| [8:30:19] Agent completed successfully           |
|                                                  |
+--------------------------------------------------+
| OUTPUT                                           |
| +--------------------------------------------+   |
| | # Weekly Report - Jan 20, 2026             |   |
| | ...                                        |   |
| +--------------------------------------------+   |
|                                                  |
| [Copy Log]  [Download]                           |
+--------------------------------------------------+
```

**Key Features**
- Timestamps with millisecond precision
- Color-coded by log level (info, warn, error)
- Expandable sections for skill outputs
- Copy/download functionality
- Syntax highlighting for output

---

### 5. Skill Library

**Purpose**: Browse, search, and discover public skills.

**Layout**
```
+--------------------------------------------------+
| Skill Library                                    |
+--------------------------------------------------+
|                                                  |
| [Search skills by name, integration, or tag...]  |
|                                                  |
| CATEGORIES                                       |
| [All] [Notion] [Slack] [Linear] [GitHub]        |
| [Reports] [Notifications] [Sync] [Data]          |
|                                                  |
+--------------------------------------------------+
| FEATURED                                         |
| +-------------------+  +-------------------+     |
| | Notion Weekly     |  | Slack Alert       |     |
| | Summary           |  | Sender            |     |
| | by @omniforge     |  | by @omniforge     |     |
| | 1.2k users        |  | 890 users         |     |
| +-------------------+  +-------------------+     |
|                                                  |
| ALL SKILLS (247)                     [Sort: Popular v]|
| +-------------------+  +-------------------+     |
| | PO Parser         |  | Invoice Extractor |     |
| | by @derek         |  | by @maya          |     |
| | 540 users         |  | 320 users         |     |
| +-------------------+  +-------------------+     |
+--------------------------------------------------+
```

**Skill Card**
- Icon (based on primary integration)
- Name
- Author (with verification badge if official)
- Usage count
- Integration tags
- Click: Opens skill detail

**Skill Detail Modal**
```
+--------------------------------------------------+
| SKILL DETAIL                               [X]   |
+--------------------------------------------------+
|                                                  |
| [Notion Icon]                                    |
| Notion Weekly Summary                            |
| by @omniforge [Verified]                         |
|                                                  |
| Generate formatted weekly summaries from Notion  |
| databases. Includes grouping, sorting, and       |
| customizable output formats.                     |
|                                                  |
| INTEGRATIONS: [Notion]                           |
| TAGS: #reports #weekly #summary                  |
|                                                  |
| USAGE: 1,247 agents                              |
| UPDATED: Jan 10, 2026                            |
|                                                  |
| WHAT IT DOES                                     |
| - Queries specified Notion databases             |
| - Groups results by property                     |
| - Sorts by priority                              |
| - Outputs formatted Markdown                     |
|                                                  |
| REQUIREMENTS                                     |
| - Notion integration connected                   |
| - At least one database selected                 |
|                                                  |
| [Use in Agent]                                   |
|                                                  |
+--------------------------------------------------+
```

---

### 6. Integrations

**Purpose**: Manage connected services and add new integrations.

**Layout**
```
+--------------------------------------------------+
| Integrations                                     |
+--------------------------------------------------+
|                                                  |
| CONNECTED (3)                                    |
| +--------------------------------------------+   |
| | [Notion]  Notion                           |   |
| | Connected as maya@acme.com                 |   |
| | 3 agents using   |   [Manage] [Disconnect] |   |
| +--------------------------------------------+   |
| | [Slack]   Slack                            |   |
| | Connected to ACME Workspace                |   |
| | 2 agents using   |   [Manage] [Disconnect] |   |
| +--------------------------------------------+   |
| | [Calendar] Google Calendar                 |   |
| | Connected as maya@acme.com                 |   |
| | 1 agent using    |   [Manage] [Disconnect] |   |
| +--------------------------------------------+   |
|                                                  |
| AVAILABLE                                        |
| +----------+  +----------+  +----------+         |
| | [Linear] |  | [GitHub] |  | [Jira]   |         |
| | Linear   |  | GitHub   |  | Jira     |         |
| | [Connect]|  | [Connect]|  | [Connect]|         |
| +----------+  +----------+  +----------+         |
| +----------+  +----------+  +----------+         |
| | [Sheets] |  | [Drive]  |  | [More..] |         |
| | Sheets   |  | Drive    |  | Request  |         |
| | [Connect]|  | [Connect]|  | [Request]|         |
| +----------+  +----------+  +----------+         |
|                                                  |
+--------------------------------------------------+
```

**Connected Integration Row**
- Integration icon and name
- Connection details (email/workspace)
- Usage count (how many agents use it)
- Actions: Manage (permissions), Disconnect

**Available Integration Card**
- Integration icon and name
- "Connect" button
- Click: Opens connection flow modal

**Disconnect Confirmation**
```
+--------------------------------------------------+
| DISCONNECT NOTION?                         [X]   |
+--------------------------------------------------+
|                                                  |
| This will affect 3 agents that use Notion:       |
|                                                  |
| - Weekly Reporter                                |
| - Meeting Briefing                               |
| - Project Tracker                                |
|                                                  |
| These agents will fail until Notion is           |
| reconnected.                                     |
|                                                  |
| [Cancel]  [Disconnect Anyway]                    |
|                                                  |
+--------------------------------------------------+
```

---

### 7. Settings

**Purpose**: Manage account, team, and platform settings.

**Layout**
```
+--------------------------------------------------+
| Settings                                         |
+--------------------------------------------------+
| [Profile] [Team] [Billing] [Security]            |
+--------------------------------------------------+
```

#### 7.1 Profile Settings

```
+--------------------------------------------------+
| PROFILE                                          |
+--------------------------------------------------+
|                                                  |
|        [Avatar]                                  |
|        [Change Photo]                            |
|                                                  |
| Name                                             |
| +--------------------------------------------+   |
| | Maya Johnson                               |   |
| +--------------------------------------------+   |
|                                                  |
| Email                                            |
| +--------------------------------------------+   |
| | maya@acme.com                    [Verified]|   |
| +--------------------------------------------+   |
|                                                  |
| Role                                             |
| +--------------------------------------------+   |
| | Product Manager                        [v] |   |
| +--------------------------------------------+   |
|                                                  |
| PREFERENCES                                      |
|                                                  |
| Theme                                            |
| [Light] [Dark] [System]                          |
|                                                  |
| Timezone                                         |
| +--------------------------------------------+   |
| | America/Los_Angeles (UTC-8)            [v] |   |
| +--------------------------------------------+   |
|                                                  |
| Email Notifications                              |
| [x] Agent failures                               |
| [x] Weekly summary                               |
| [ ] Marketing updates                            |
|                                                  |
| [Save Changes]                                   |
|                                                  |
+--------------------------------------------------+
```

#### 7.2 Team Management

```
+--------------------------------------------------+
| TEAM: ACME Corp                                  |
+--------------------------------------------------+
|                                                  |
| MEMBERS (5)                        [Invite +]    |
| +--------------------------------------------+   |
| | [Avatar] Maya Johnson                      |   |
| | maya@acme.com        Owner     [...]       |   |
| +--------------------------------------------+   |
| | [Avatar] Derek Chen                        |   |
| | derek@acme.com       Admin     [...]       |   |
| +--------------------------------------------+   |
| | [Avatar] Sarah Kim                         |   |
| | sarah@acme.com       Member    [...]       |   |
| +--------------------------------------------+   |
|                                                  |
| PENDING INVITES (1)                              |
| +--------------------------------------------+   |
| | alex@acme.com        Sent Jan 20  [Resend] |   |
| +--------------------------------------------+   |
|                                                  |
| TEAM SETTINGS                                    |
|                                                  |
| Team Name                                        |
| +--------------------------------------------+   |
| | ACME Corp                                  |   |
| +--------------------------------------------+   |
|                                                  |
| Default Agent Visibility                         |
| (x) Private to creator                           |
| ( ) Visible to team                              |
|                                                  |
+--------------------------------------------------+
```

**Role Actions (... menu)**
- Change role (Admin/Member)
- Remove from team
- Transfer ownership (for Owner)

**Invite Modal**
```
+--------------------------------------------------+
| INVITE TEAM MEMBER                         [X]   |
+--------------------------------------------------+
|                                                  |
| Email address                                    |
| +--------------------------------------------+   |
| | email@company.com                          |   |
| +--------------------------------------------+   |
|                                                  |
| Role                                             |
| (x) Member - Can create and manage their agents  |
| ( ) Admin - Can manage team and all agents       |
|                                                  |
| [Cancel]  [Send Invite]                          |
|                                                  |
+--------------------------------------------------+
```

#### 7.3 Billing (Premium)

```
+--------------------------------------------------+
| BILLING                                          |
+--------------------------------------------------+
|                                                  |
| CURRENT PLAN                                     |
| +--------------------------------------------+   |
| | Team Plan                       $49/month  |   |
| | 5 team members, unlimited agents           |   |
| | Next billing: Feb 1, 2026                  |   |
| |                                            |   |
| | [Change Plan]  [Cancel Subscription]       |   |
| +--------------------------------------------+   |
|                                                  |
| USAGE THIS MONTH                                 |
| +----------+  +----------+  +----------+         |
| | 1,247    |  | 5/5      |  | 2.1 GB   |         |
| | Runs     |  | Members  |  | Storage  |         |
| +----------+  +----------+  +----------+         |
|                                                  |
| PAYMENT METHOD                                   |
| +--------------------------------------------+   |
| | Visa ending in 4242           [Edit]       |   |
| +--------------------------------------------+   |
|                                                  |
| BILLING HISTORY                                  |
| +--------------------------------------------+   |
| | Jan 1, 2026    $49.00    [Download]        |   |
| | Dec 1, 2025    $49.00    [Download]        |   |
| +--------------------------------------------+   |
|                                                  |
+--------------------------------------------------+
```

#### 7.4 Security Settings

```
+--------------------------------------------------+
| SECURITY                                         |
+--------------------------------------------------+
|                                                  |
| TWO-FACTOR AUTHENTICATION                        |
| +--------------------------------------------+   |
| | [Shield] 2FA is enabled                    |   |
| |          via Authenticator App             |   |
| |                          [Manage]          |   |
| +--------------------------------------------+   |
|                                                  |
| SSO CONFIGURATION (Admin only)                   |
| +--------------------------------------------+   |
| | [Key] SAML SSO                             |   |
| |       Not configured                       |   |
| |                          [Configure]       |   |
| +--------------------------------------------+   |
|                                                  |
| ACTIVE SESSIONS                                  |
| +--------------------------------------------+   |
| | Chrome on macOS                            |   |
| | San Francisco, CA - Current session        |   |
| +--------------------------------------------+   |
| | Safari on iPhone                           |   |
| | San Francisco, CA - 2 days ago   [Revoke]  |   |
| +--------------------------------------------+   |
|                                                  |
| [Sign Out All Other Sessions]                    |
|                                                  |
| AUDIT LOG                           [View All]   |
| +--------------------------------------------+   |
| | Maya created agent "Weekly Reporter"       |   |
| | Jan 20, 2026 at 2:30 PM                    |   |
| +--------------------------------------------+   |
| | Derek connected Slack integration          |   |
| | Jan 19, 2026 at 11:15 AM                   |   |
| +--------------------------------------------+   |
|                                                  |
+--------------------------------------------------+
```

---

### 8. Analytics

**Purpose**: Monitor agent performance, usage statistics, and costs.

**Layout**
```
+--------------------------------------------------+
| Analytics                                        |
+--------------------------------------------------+
| [7 Days v]  Jan 18 - Jan 25, 2026               |
+--------------------------------------------------+
|                                                  |
| OVERVIEW                                         |
| +----------+  +----------+  +----------+  +-----+|
| | 1,247    |  | 96.2%    |  | 3.2s     |  | $12 ||
| | Total    |  | Success  |  | Avg Time |  | Cost||
| | Runs     |  | Rate     |  |          |  |     ||
| | +15%     |  | +2.1%    |  | -0.3s    |  | +8% ||
| +----------+  +----------+  +----------+  +-----+|
|                                                  |
| EXECUTIONS OVER TIME                             |
| +--------------------------------------------+   |
| |    ___                                     |   |
| |   /   \      ___                           |   |
| |  /     \    /   \                          |   |
| | /       \__/     \___                      |   |
| |                       \___                 |   |
| +--------------------------------------------+   |
| Jan 18  19  20  21  22  23  24  25              |
|                                                  |
| TOP AGENTS BY USAGE                              |
| +--------------------------------------------+   |
| | 1. Weekly Reporter        312 runs   25%   |   |
| | 2. Meeting Briefing       289 runs   23%   |   |
| | 3. Invoice Matcher        201 runs   16%   |   |
| | 4. Project Tracker        156 runs   13%   |   |
| | 5. Slack Notifier         142 runs   11%   |   |
| +--------------------------------------------+   |
|                                                  |
| ERROR BREAKDOWN                                  |
| +--------------------------------------------+   |
| | Notion API timeout         23 (48%)        |   |
| | Slack rate limit           15 (31%)        |   |
| | Invalid data format        10 (21%)        |   |
| +--------------------------------------------+   |
|                                                  |
+--------------------------------------------------+
```

**Key Components**

**Date Range Selector**
- Preset options: 7d, 30d, 90d, Custom
- Date picker for custom range

**Metric Cards**
- Value with trend indicator
- Trend: Percentage change vs previous period
- Color: Green (positive), Red (negative), Gray (neutral)

**Line Chart**
- Executions over time
- Hover: Tooltip with exact values
- Click: Drill down to that day's executions

**Top Agents Table**
- Sortable columns
- Click row: Navigate to agent detail
- Progress bar for visual comparison

**Error Breakdown**
- Pie chart or horizontal bar
- Click: Filter execution list by error type

---

## Common Patterns

### Modals

**Standard Modal**
```
+--------------------------------------------------+
| MODAL TITLE                                [X]   |
+--------------------------------------------------+
|                                                  |
|  Modal content here...                           |
|                                                  |
|                                                  |
+--------------------------------------------------+
|                    [Cancel]  [Primary Action]    |
+--------------------------------------------------+
```

**Specifications**
- Max-width: 560px (small), 720px (medium), 960px (large)
- Border-radius: `--radius-xl`
- Shadow: `--shadow-xl`
- Backdrop: Semi-transparent black (50% opacity)
- Close: X button or Escape key
- Animation: Fade in + scale up from 95%

### Toasts / Notifications

**Toast Types**
- **Success**: Green left border, checkmark icon
- **Error**: Red left border, X icon
- **Warning**: Yellow left border, warning icon
- **Info**: Blue left border, info icon

**Position**: Bottom-right, stacked vertically
**Duration**: 5 seconds (auto-dismiss), or persistent with close button
**Animation**: Slide in from right

### Forms

**Input Field**
```
Label (optional required indicator *)
+--------------------------------------------+
|  Placeholder text                          |
+--------------------------------------------+
Helper text or error message
```

**Specifications**
- Height: 44px
- Padding: 12px horizontal
- Border: `--border-default`
- Focus: 2px ring `--accent-primary`
- Error: Border `--error`, message below in `--error`
- Disabled: Background `--bg-tertiary`, cursor not-allowed

**Select/Dropdown**
- Same styling as input
- Chevron icon on right
- Dropdown: Shadow `--shadow-lg`, max-height 300px with scroll

**Checkbox/Radio**
- 18px size
- Checked: `--accent-primary` fill
- Focus: Ring around control
- Label: Clickable, aligned to control

### Buttons

| Variant | Background | Text | Border | Usage |
|---------|------------|------|--------|-------|
| Primary | `--accent-primary` | White | None | Main actions |
| Secondary | Transparent | `--text-primary` | `--border-default` | Secondary actions |
| Ghost | Transparent | `--text-secondary` | None | Tertiary actions |
| Danger | `--error` | White | None | Destructive actions |

**States**
- Hover: Darken background 10%
- Active: Darken background 20%
- Disabled: 50% opacity, cursor not-allowed
- Loading: Spinner replaces text

**Sizes**
- Small: 32px height, 12px padding
- Medium: 40px height, 16px padding (default)
- Large: 48px height, 20px padding

### Tables

**Specifications**
- Header: `--bg-tertiary`, `--body-sm` bold
- Row: Alternating subtle background, hover highlight
- Borders: Horizontal only, `--border-subtle`
- Pagination: Below table, show range and controls
- Empty: Illustration + message centered

### Empty States

**Structure**
```
+--------------------------------------------------+
|                                                  |
|              [Illustration]                      |
|                                                  |
|           No agents yet                          |
|    Create your first agent to get started        |
|                                                  |
|           [Create Agent]                         |
|                                                  |
+--------------------------------------------------+
```

**Specifications**
- Illustration: Simple, on-brand, 200px max height
- Headline: `--heading-md`
- Description: `--body-md`, `--text-secondary`
- CTA: Primary button

### Loading States

**Skeleton Loaders**
- Match component dimensions
- Animated gradient shimmer
- Background: `--bg-tertiary`

**Spinners**
- Centered in loading area
- Size: 24px (inline), 48px (page-level)
- Color: `--accent-primary`

**Progress Bars**
- For determinate progress
- Height: 4px
- Background: `--bg-tertiary`
- Fill: `--accent-primary`

---

## Responsive Breakpoints

| Breakpoint | Width | Layout Changes |
|------------|-------|----------------|
| Mobile | < 640px | Single column, bottom nav, full-width cards |
| Tablet | 640px - 1024px | Two columns, collapsed sidebar |
| Desktop | 1024px - 1440px | Full sidebar, three+ columns |
| Wide | > 1440px | Max-width container, centered |

### Mobile-Specific Adaptations

**Navigation**
- Bottom tab bar (5 items max)
- Hamburger menu for secondary items
- Full-screen modals

**Chat Interface**
- Full-screen, no sidebars
- Keyboard-aware input positioning
- Touch-friendly message actions

**Agent Cards**
- Full-width, stacked vertically
- Swipe actions (edit, delete)

**Tables**
- Card view on mobile
- Horizontal scroll with sticky first column

---

## Accessibility Requirements

### WCAG 2.1 AA Compliance

**Color Contrast**
- Normal text: 4.5:1 minimum
- Large text (18px+): 3:1 minimum
- Interactive elements: 3:1 minimum

**Keyboard Navigation**
- All interactive elements focusable
- Visible focus indicators
- Logical tab order
- Escape to close modals/dropdowns

**Screen Readers**
- Semantic HTML elements
- ARIA labels for icons and controls
- Live regions for dynamic content
- Skip links for navigation

**Motion**
- Respect prefers-reduced-motion
- No content that flashes > 3 times/second

---

## Micro-interactions

### Button Press
- Scale down 2% on press
- Scale up on release
- Duration: 100ms

### Card Hover
- Elevate shadow
- Subtle scale up (1.01)
- Duration: 200ms

### Toggle/Switch
- Smooth slide animation
- Color transition
- Duration: 200ms

### Page Transitions
- Fade in from below (20px)
- Duration: 300ms
- Stagger for lists (50ms delay between items)

### Chat Messages
- Slide in from bottom
- Typing indicator bounce
- Duration: 200ms

### Success Feedback
- Checkmark animation (draw stroke)
- Subtle confetti for major achievements
- Duration: 500ms

---

## Component Library Summary

### Layout Components
- `AppShell` - Main layout with sidebar and header
- `Sidebar` - Collapsible navigation sidebar
- `Header` - Top bar with search and user menu
- `PageHeader` - Page title with actions
- `Section` - Content section with title
- `Card` - Flexible content container
- `Grid` - Responsive grid layout
- `Stack` - Vertical/horizontal stack

### Navigation Components
- `NavItem` - Sidebar navigation item
- `Breadcrumbs` - Page hierarchy
- `Tabs` - Tab navigation
- `Pagination` - Page controls

### Form Components
- `Input` - Text input
- `TextArea` - Multi-line input
- `Select` - Dropdown select
- `Checkbox` - Checkbox control
- `Radio` - Radio button group
- `Switch` - Toggle switch
- `DatePicker` - Date selection
- `TimePicker` - Time selection
- `FileUpload` - File input

### Data Display Components
- `Table` - Data table with sorting/filtering
- `DataGrid` - Advanced data grid
- `List` - Simple list
- `Badge` - Status badge
- `Tag` - Removable tag
- `Avatar` - User avatar
- `Tooltip` - Hover tooltip
- `Stat` - Metric display

### Feedback Components
- `Toast` - Notification toast
- `Alert` - Inline alert
- `Modal` - Dialog modal
- `Drawer` - Side panel
- `Progress` - Progress bar
- `Spinner` - Loading spinner
- `Skeleton` - Loading skeleton

### Chat Components
- `ChatContainer` - Chat wrapper
- `MessageBubble` - User/bot message
- `QuickReplies` - Quick reply buttons
- `TypingIndicator` - Bot typing animation
- `ChatInput` - Message input
- `AgentPreviewCard` - Agent preview in chat
- `IntegrationSelector` - Integration picker

### Agent Components
- `AgentCard` - Agent grid card
- `AgentRow` - Agent list row
- `SkillCard` - Skill display card
- `ExecutionLog` - Log viewer
- `StatusBadge` - Agent status indicator
- `TriggerIndicator` - Trigger type display

---

## Open Questions

1. **White-label Customization**: How much branding customization should B2B2C customers have access to? Does this affect component theming?

2. **Real-time Collaboration**: Should multiple team members be able to collaborate on agent creation simultaneously? What does that UI look like?

3. **Agent Templates**: Should we offer pre-built agent templates as starting points? Where do they appear in the flow?

4. **Mobile App**: Is a native mobile app planned? Would it be full-featured or monitoring-only?

5. **Notification Center**: Should there be a centralized notification center, or are toasts sufficient?

6. **Onboarding Tour**: What's the ideal onboarding experience for new users? Interactive tour vs. video vs. sample data?

---

## Evolution Notes

### 2026-01-25 (v1.0)
- Initial comprehensive UI/UX specification created
- Defined design tokens, navigation structure, and all major page layouts
- Established component library foundation
- Documented responsive breakpoints and accessibility requirements

---

## Appendix A: Icon Reference

| Icon | Usage |
|------|-------|
| Home | Dashboard |
| MessageSquare | Agent Builder |
| Bot | Agents |
| Blocks | Skills |
| Plug | Integrations |
| BarChart3 | Analytics |
| Settings | Settings |
| Search | Global search |
| Bell | Notifications |
| User | User menu |
| Plus | Create new |
| Play | Run agent |
| Pause | Pause agent |
| Edit | Edit |
| Trash | Delete |
| Check | Success |
| X | Error/Close |
| AlertTriangle | Warning |
| Info | Information |
| ChevronRight | Expand/Navigate |
| MoreHorizontal | Actions menu |

**Icon Library**: Lucide React (consistent with Linear/Notion aesthetic)

---

## Appendix B: Motion Specifications

### Easing Functions
```css
--ease-default: cubic-bezier(0.4, 0, 0.2, 1);
--ease-in: cubic-bezier(0.4, 0, 1, 1);
--ease-out: cubic-bezier(0, 0, 0.2, 1);
--ease-bounce: cubic-bezier(0.34, 1.56, 0.64, 1);
```

### Animation Keyframes

**Fade In Up**
```css
@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
```

**Skeleton Shimmer**
```css
@keyframes shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}
```

**Typing Dots**
```css
@keyframes typingDots {
  0%, 20% { opacity: 0.3; transform: translateY(0); }
  50% { opacity: 1; transform: translateY(-3px); }
  100% { opacity: 0.3; transform: translateY(0); }
}
```
