---
description: Frontend development standards, best practices, and conventions for the Next.js (React, TypeScript) application including App Router structure, component patterns, data fetching, state management, and testing practices
globs: ["frontend/src/**/*.{ts,tsx}", "frontend/app/**/*.{ts,tsx}", "frontend/tsconfig.json", "frontend/next.config.*", "frontend/package.json"]
alwaysApply: true
---

# Frontend Project Configuration and Best Practices

## Table of Contents

- [Overview](#overview)
- [Technology Stack](#technology-stack)
  - [Core Technologies](#core-technologies)
  - [UI Framework](#ui-framework)
  - [State Management & Data Flow](#state-management--data-flow)
  - [Testing Framework](#testing-framework)
  - [Development Tools](#development-tools)
- [Project Structure](#project-structure)
- [Coding Standards](#coding-standards)
  - [Naming Conventions](#naming-conventions)
  - [Component Conventions](#component-conventions)
  - [Data Fetching](#data-fetching)
  - [State Management](#state-management)
  - [Service Layer Architecture](#service-layer-architecture)
- [UI/UX Standards](#uiux-standards)
  - [Styling](#styling)
  - [Form Handling](#form-handling)
  - [Navigation Patterns](#navigation-patterns)
  - [Accessibility](#accessibility)
- [Testing Standards](#testing-standards)
- [Configuration Standards](#configuration-standards)
- [Performance Best Practices](#performance-best-practices)
- [Development Workflow](#development-workflow)

---

## Overview

This document outlines the best practices, conventions, and standards for the frontend application: a Next.js app (React, TypeScript) using the App Router, communicating with the FastAPI backend. These practices ensure code consistency, maintainability, and optimal development experience.

## Technology Stack

### Core Technologies
- **Next.js 15+ (App Router)**: React framework with server components, routing, and build tooling
- **React 19**: Functional components and hooks
- **TypeScript 5+**: Strict type safety throughout

### UI Framework
`[DECISION PENDING]` — component/styling library not yet chosen. Recommended default: **Tailwind CSS**, optionally with **shadcn/ui** components. Update this section once decided.

### State Management & Data Flow
- **Server Components** for data fetching by default
- **React hooks** (`useState`, `useReducer`) for local client state
- Server state library (e.g., TanStack Query) `[DECISION PENDING — add only if client-side polling/mutation caching is needed]`

### Testing Framework
- **Vitest** + **React Testing Library**: Unit and component tests
- **Playwright**: End-to-end testing

### Development Tools
- **ESLint** with `eslint-config-next`
- **Prettier**: Formatting
- **TypeScript**: Static type checking (strict mode)

## Project Structure

```
frontend/
├── app/                      # App Router: routes, layouts, pages
│   ├── layout.tsx            # Root layout
│   ├── page.tsx              # Home page
│   ├── (feature)/            # Route groups per feature
│   │   ├── page.tsx
│   │   ├── loading.tsx       # Streaming/loading UI
│   │   └── error.tsx         # Error boundary
│   └── api/                  # Route handlers (only if a BFF layer is needed)
├── components/               # Shared, reusable UI components
│   └── ui/                   # Design-system primitives
├── features/                 # Feature-specific components and hooks
├── lib/                      # Utilities, API client, shared helpers
│   └── api/                  # Typed backend API client (services)
├── hooks/                    # Shared custom hooks
├── types/                    # Shared TypeScript types
├── public/                   # Static assets
├── tests/                    # Test setup and e2e specs
├── next.config.ts            # Next.js configuration
├── tsconfig.json             # TypeScript configuration
└── package.json              # Dependencies and scripts
```

## Coding Standards

### Naming Conventions

- **Components**: PascalCase (e.g., `ItemCard`, `ChatPanel`)
- **Variables/functions**: camelCase (e.g., `itemId`, `handleSubmit`, `fetchItems`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `API_BASE_URL`)
- **Types/Interfaces**: PascalCase (e.g., `ItemData`, `ChatMessageProps`)
- **Files**: kebab-case for route files per Next.js conventions (`page.tsx`, `layout.tsx`); PascalCase for component files (`ItemCard.tsx`); camelCase for utilities (`apiClient.ts`)
- **Hooks**: camelCase with `use` prefix (e.g., `useItemData`)
- **English only**: All names, comments, and messages must be in English

```tsx
// Good: typed, English, functional component
type ItemCardProps = {
    item: Item;
    onSelect: (item: Item) => void;
};

export function ItemCard({ item, onSelect }: ItemCardProps) {
    return (
        <button type="button" onClick={() => onSelect(item)}>
            {item.name}
        </button>
    );
}
```

### Component Conventions

- **Server Components by default**; add `"use client"` only when the component needs interactivity, browser APIs, or hooks
- Always functional components with hooks; no class components
- Define TypeScript types for all props; use destructuring and default values where appropriate
- Keep components small and focused; extract reusable logic into custom hooks
- Colocate feature-specific components under `features/<feature>/`

### Data Fetching

- **Fetch on the server** whenever possible: async Server Components calling the typed API client
- Use `loading.tsx`/`Suspense` for streaming states and `error.tsx` for error boundaries
- For mutations, prefer **Server Actions** or route handlers; revalidate with `revalidatePath`/`revalidateTag`
- Client-side fetching only for real-time or highly interactive views

```tsx
// app/items/page.tsx — Server Component
import { getItems } from "@/lib/api/items";

export default async function ItemsPage() {
    const items = await getItems();
    return <ItemList items={items} />;
}
```

### State Management

- **useState/useReducer** for component-local state in Client Components
- Lift state only as far as needed; avoid global stores until a concrete need arises
- URL state (search params) for shareable/filterable views
- Always handle loading and error states for async client operations with user-friendly English messages

### Service Layer Architecture

- Centralize backend calls in `lib/api/`, one module per resource
- Use the native `fetch` API with a small typed wrapper; type all request/response payloads to mirror the backend Pydantic schemas
- Read the backend base URL from environment variables (`NEXT_PUBLIC_API_URL` for client-side calls, server-only variable for server-side calls)

```typescript
// lib/api/items.ts
import { apiFetch } from "./client";
import type { Item } from "@/types/item";

export async function getItems(): Promise<Item[]> {
    return apiFetch<Item[]>("/api/v1/items");
}

export async function createItem(payload: ItemCreateRequest): Promise<Item> {
    return apiFetch<Item>("/api/v1/items", { method: "POST", body: JSON.stringify(payload) });
}
```

## UI/UX Standards

### Styling

`[DECISION PENDING — styling library]`. Regardless of the choice:
- Keep styling colocated with components
- Use design tokens/CSS variables for colors and spacing
- Mobile-first responsive design

### Form Handling

- Use **controlled components** or Server Actions with `useActionState` for forms
- Validate on the client for UX, but treat backend validation as authoritative
- Disable submit buttons during submission; show pending state
- Clear or reset form state after successful submission

### Navigation Patterns

- Use `next/link` for navigation and `useRouter` (from `next/navigation`) for programmatic navigation
- Use layouts for shared chrome (nav, breadcrumbs)
- Prefer route-based UI state (dynamic segments, search params) over ad-hoc client state

### Accessibility

- Semantic HTML elements; `aria-label` for icon-only interactive elements
- Keyboard navigation support for all interactive flows
- Alternative text for images (`next/image` requires `alt`)

## Testing Standards

- **Unit/component tests** with Vitest + React Testing Library: test behavior, not implementation details; query by role/label, not test IDs, where possible
- **E2E tests** with Playwright: cover complete user workflows per feature; test both success and error scenarios
- Mock the backend API in unit tests (e.g., MSW); E2E tests may run against a local backend with a seeded database
- Descriptive English test names explaining the expected behavior
- TDD: write a failing test before implementing new behavior

```typescript
// Example component test
import { render, screen } from "@testing-library/react";

it("renders the item name", () => {
    render(<ItemCard item={{ id: 1, name: "Example" }} onSelect={vi.fn()} />);
    expect(screen.getByText("Example")).toBeInTheDocument();
});
```

## Configuration Standards

### TypeScript Configuration
- **strict mode** enabled
- Path alias `@/*` for cleaner imports
- No `any`; prefer `unknown` and narrowing

### ESLint Configuration
- Extend `next/core-web-vitals` and TypeScript rules
- Lint must pass before commits

### Environment Configuration
- `NEXT_PUBLIC_*` variables only for values safe to expose to the browser
- Server-only secrets stay in non-prefixed variables
- Separate `.env.local` per environment; never commit env files

## Performance Best Practices

- Prefer Server Components to minimize client JavaScript
- `next/image` for images and `next/font` for fonts
- Route-level code splitting is automatic; use `dynamic()` for heavy client-only components
- Memoize expensive client computations (`useMemo`, `useCallback`) only when profiling justifies it
- Cache and revalidate server fetches deliberately (`fetch` cache options, `revalidateTag`)
- Monitor Core Web Vitals

## Development Workflow

- **Branch Naming**: Follow `docs/base-standards.md` section 8 (`<type>/session-<N>-<slug>`); use the `new-branch` skill when creating branches. Append `-frontend` to the slug for parallel frontend work (e.g. `feature/session-2-chat-ui-frontend`)
- **Feature Branches**: Develop features in separate branches, adding descriptive suffix "-frontend" to allow working in parallel
- **Descriptive Commits**: Write descriptive commit messages in English
- **Code Review**: Code review before merging
- **Small Branches**: Keep branches small and focused

### Development Scripts
```bash
npm run dev          # Development server
npm run build        # Production build
npm run start        # Serve production build
npm run lint         # ESLint
npm run test         # Unit/component tests (Vitest)
npm run test:e2e     # Playwright E2E tests
```

### Code Quality
- ESLint and TypeScript compilation pass without errors
- All tests passing before merging
- Performance monitoring with Core Web Vitals

This document serves as the foundation for maintaining code quality and consistency across the frontend application. All team members should follow these practices to ensure a maintainable and scalable codebase.
