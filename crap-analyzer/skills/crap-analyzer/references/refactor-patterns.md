# Refactor patterns for high-CRAP code

Lowering CRAP means lowering complexity **or** raising coverage. These patterns target complexity. Pair each with tests (see [test-stub-templates.md](test-stub-templates.md)) for compounding effect.

Examples below use TypeScript and Python because the patterns are clearest there, but the shapes apply to every language: **a decision point is a decision point, and extracting a helper is extracting a helper.**

## Table of contents

- [Extract method (the default move)](#extract-method-the-default-move)
- [Guard clauses and early returns](#guard-clauses-and-early-returns)
- [Replace conditional chain with lookup](#replace-conditional-chain-with-lookup)
- [Decompose logical expressions](#decompose-logical-expressions)
- [Strategy / polymorphism for dispatch](#strategy--polymorphism-for-dispatch)
- [Pipeline extraction (streams, pipes, iterators)](#pipeline-extraction-streams-pipes-iterators)
- [Split the function along its responsibilities](#split-the-function-along-its-responsibilities)
- [What counts as a "safe" refactor for auto-apply](#what-counts-as-a-safe-refactor-for-auto-apply)

## Extract method (the default move)

Pull a coherent block into a named helper that describes intent. Works when a function has multiple "stages" (parse → validate → transform → emit).

**Before (TypeScript):**
```ts
processOrder(order: Order) {
  if (!order.id || order.items.length === 0) {
    throw new Error('invalid');
  }
  let total = 0;
  for (const item of order.items) {
    if (item.discount) {
      total += item.price * (1 - item.discount);
    } else {
      total += item.price;
    }
  }
  if (order.coupon) {
    if (order.coupon.kind === 'pct') total *= 1 - order.coupon.value;
    else total -= order.coupon.value;
  }
  this.repo.save({ ...order, total });
}
```

**After:**
```ts
processOrder(order: Order) {
  this.assertValid(order);
  const subtotal = this.subtotal(order.items);
  const total = this.applyCoupon(subtotal, order.coupon);
  this.repo.save({ ...order, total });
}

private assertValid(order: Order) {
  if (!order.id || order.items.length === 0) throw new Error('invalid');
}

private subtotal(items: Item[]) {
  return items.reduce((sum, i) => sum + i.price * (1 - (i.discount ?? 0)), 0);
}

private applyCoupon(subtotal: number, coupon: Coupon | undefined) {
  if (!coupon) return subtotal;
  return coupon.kind === 'pct' ? subtotal * (1 - coupon.value) : subtotal - coupon.value;
}
```

Each helper is independently testable and has CRAP low enough to ignore.

## Guard clauses and early returns

Replace nested conditionals with early returns. Cuts both cyclomatic complexity and cognitive load.

**Before (Python):**
```python
def process(user):
    if user is not None:
        if user.active:
            if 'write' in user.permissions:
                return do_work(user)
    return None
```

**After:**
```python
def process(user):
    if user is None:
        return None
    if not user.active:
        return None
    if 'write' not in user.permissions:
        return None
    return do_work(user)
```

## Replace conditional chain with lookup

When a long `if/elif` or `switch` maps a key to a value (no side effects), use a table.

**Before:**
```ts
getLabel(kind: Kind): string {
  if (kind === 'a') return 'Alpha';
  else if (kind === 'b') return 'Beta';
  else if (kind === 'c') return 'Gamma';
  else if (kind === 'd') return 'Delta';
  return 'Unknown';
}
```

**After:**
```ts
private static readonly LABELS: Record<Kind, string> = {
  a: 'Alpha', b: 'Beta', c: 'Gamma', d: 'Delta',
};

getLabel(kind: Kind): string {
  return MyClass.LABELS[kind] ?? 'Unknown';
}
```

Python version:
```python
LABELS = {'a': 'Alpha', 'b': 'Beta', 'c': 'Gamma', 'd': 'Delta'}

def get_label(kind: str) -> str:
    return LABELS.get(kind, 'Unknown')
```

In both cases complexity collapses. If the language has exhaustive-match types (TypeScript `Record<Kind, ...>`, Rust `match`, Kotlin `when`), lean on them — the compiler now enforces coverage of all arms.

## Decompose logical expressions

Each `&&` / `||` / `??` / `and` / `or` adds a decision point. When an expression reads as "name these conditions," extract named booleans.

**Before:**
```ts
if (user && user.active && (user.role === 'admin' || user.role === 'owner') && !user.banned) {
  // ...
}
```

**After:**
```ts
const isPrivileged = user?.role === 'admin' || user?.role === 'owner';
const canAct = user?.active && !user?.banned;
if (isPrivileged && canAct) {
  // ...
}
```

Containing function's complexity drops; intent is self-documenting.

## Strategy / polymorphism for dispatch

When each branch runs **different logic** (not just mapping to a value), extract each arm into a dedicated function or inject a strategy.

```ts
const handlers: Record<EventKind, (e: Event) => void> = {
  click: this.onClick.bind(this),
  hover: this.onHover.bind(this),
  submit: this.onSubmit.bind(this),
};

handle(event: Event) {
  handlers[event.kind]?.(event);
}
```

Python dict-of-callables or classes implementing a shared interface work the same way. In Go, a `map[EventKind]func(Event)` is idiomatic. In Rust, a `match` that each calls into a small `fn` keeps complexity in the dispatch table rather than the body.

## Pipeline extraction (streams, pipes, iterators)

When complexity lives inside a chained pipeline — RxJS operator chains, Java streams, Rust iterator chains, Python comprehensions with `if`s — extract each stage into a named helper. The pipeline becomes a narrative of function calls; each helper is trivially testable.

**Before:**
```ts
return this.http.get<Raw>(url).pipe(
  map((raw) => {
    if (raw == null) return null;
    if (raw.kind === 'a' && raw.value > 0) return { ok: true, kind: 'a' };
    if (raw.kind === 'b' || raw.fallback) return { ok: true, kind: 'b' };
    return null;
  }),
);
```

**After:**
```ts
return this.http.get<Raw>(url).pipe(map(this.toResult));

private toResult(raw: Raw | null): Result | null {
  if (raw == null) return null;
  if (raw.kind === 'a' && raw.value > 0) return { ok: true, kind: 'a' };
  if (raw.kind === 'b' || raw.fallback) return { ok: true, kind: 'b' };
  return null;
}
```

`toResult` is now a pure function — trivial to unit-test without touching the framework.

## Split the function along its responsibilities

If the flagged function does both I/O (HTTP, DB, FS) **and** business decisions, pull the decision logic into a pure function. I/O stays thin; logic is tested without mocks.

Rule of thumb: if a function references three or more injected dependencies, it's wearing too many hats. Move the decisions.

## What counts as a "safe" refactor for auto-apply

A refactor is safe if, for every possible input:

1. The observable return value is identical (same type, same fields, same order of emissions for streams).
2. The side effects are identical (same calls to collaborators, same order, same arguments).
3. Throws / panics / errors propagate identically.

**Usually safe:**
- Extract method with no closure over mutable state
- Guard-clause rewrite of nested conditionals
- Replacing a pure-mapping `switch`/`if/elif` with a lookup table

**Never safe to auto-apply:**
- Any refactor that reorders async / stream operators (Promise chains, `await` order, RxJS operators, Go channel ops, coroutines)
- Anything touching constructors, initializers, or lifecycle hooks
- Splitting a function that calls something that might throw — error-propagation order matters
- Changes that move code across async boundaries (`await`, `.then`, `subscribe`, `go func`, `spawn`)

When in doubt, show the diff and ask.
