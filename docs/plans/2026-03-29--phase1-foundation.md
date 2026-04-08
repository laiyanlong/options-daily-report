# Phase 1: Foundation — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Set up Expo project with 5-tab navigation, dark/light theme, GitHub API integration, SQLite cache, and Zustand stores.

**Architecture:** Expo SDK 54 + Expo Router for file-based tab navigation. Zustand for state. expo-sqlite for local cache. GitHub API for report data.

**Tech Stack:** Expo, React Native, TypeScript, Expo Router, Zustand, expo-sqlite, expo-secure-store

---

### Task 1: Create Expo Project

**Files:**
- Create: `dappgo-options-app/` (new repo at ~/git/)

**Step 1:** Create Expo project
```bash
cd ~/git
npx create-expo-app@latest dappgo-options-app --template tabs
cd dappgo-options-app
```

**Step 2:** Install dependencies
```bash
npx expo install expo-sqlite expo-secure-store zustand react-native-svg victory-native @react-native-async-storage/async-storage
npx expo install expo-font expo-splash-screen
```

**Step 3:** Verify it runs
```bash
npx expo start
```

**Step 4:** Commit
```bash
git init && git add -A && git commit -m "feat: initial Expo project setup"
```

---

### Task 2: Set Up Tab Navigation (5 tabs)

**Files:**
- Modify: `app/(tabs)/_layout.tsx`
- Create: `app/(tabs)/index.tsx` (Dashboard)
- Create: `app/(tabs)/reports.tsx`
- Create: `app/(tabs)/backtest.tsx`
- Create: `app/(tabs)/matrix.tsx`
- Create: `app/(tabs)/settings.tsx`

---

### Task 3: Theme System (Dark/Light)

**Files:**
- Create: `src/theme/colors.ts`
- Create: `src/theme/typography.ts`
- Create: `src/theme/spacing.ts`
- Create: `src/theme/ThemeProvider.tsx`

---

### Task 4: Zustand Stores

**Files:**
- Create: `src/store/app-store.ts`
- Create: `src/store/backtest-store.ts`
- Create: `src/store/settings-store.ts`

---

### Task 5: GitHub API + Report Parser

**Files:**
- Create: `src/data/github-api.ts`
- Create: `src/data/parser.ts`

---

### Task 6: SQLite Cache Layer

**Files:**
- Create: `src/data/sqlite.ts`
- Create: `src/data/cache.ts`

---

### Task 7: Calculation Engine Core

**Files:**
- Create: `src/engine/black-scholes.ts`
- Create: `src/engine/cp-score.ts`
- Create: `src/engine/pop.ts`

---

### Task 8: Shared UI Components

**Files:**
- Create: `src/components/ui/Card.tsx`
- Create: `src/components/ui/Badge.tsx`
- Create: `src/components/ui/StarRating.tsx`
- Create: `src/components/ui/TabButton.tsx`

---

### Task 9: TypeScript Types

**Files:**
- Create: `src/utils/types.ts`
- Create: `src/utils/format.ts`
- Create: `src/utils/constants.ts`
