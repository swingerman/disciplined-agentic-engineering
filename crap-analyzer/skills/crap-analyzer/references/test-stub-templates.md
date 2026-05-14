# Test stub templates for raising coverage on high-CRAP functions

Goal: every uncovered branch reported in the CRAP finding gets at least one failing-then-passing test. Ship stubs — not full implementations — so the user can fill in the assertions after seeing the skeleton.

**Detect the repo's test framework before picking a template** — read the project manifest first:

| Signal | Framework | Template |
|---|---|---|
| `jest.config.*`, `"jest"` in `package.json` | Jest | [Jest / Vitest](#jest--vitest) |
| `vitest.config.*`, `vitest` in `devDependencies` | Vitest | [Jest / Vitest](#jest--vitest) |
| `karma.conf.*` | Karma + Jasmine | [Jasmine](#jasmine--karma) |
| `mocha`, `.mocharc*` | Mocha | [Mocha](#mocha) |
| `pyproject.toml` with `[tool.pytest.*]`, `pytest.ini` | pytest | [pytest](#pytest) |
| `unittest` imports, test files with `TestCase` | unittest | [unittest](#unittest) |
| `pom.xml` or `build.gradle` with `junit-jupiter` | JUnit 5 | [JUnit 5](#junit-5) |
| `go.mod` | Go `testing` | [Go testing](#go-testing) |
| `Gemfile` with `rspec` | RSpec | [RSpec](#rspec) |
| `*.csproj` with `xunit` / `nunit` / `mstest` | xUnit / NUnit / MSTest | [xUnit / NUnit](#xunit--nunit-c) |
| `Cargo.toml` | Rust built-in tests | [Rust tests](#rust-tests) |
| `composer.json` with `phpunit` | PHPUnit | [PHPUnit](#phpunit) |

If several frameworks are configured (monorepo), match the one used in the tree closest to the changed file.

## Table of contents

- [Picking what to test](#picking-what-to-test)
- [Jest / Vitest](#jest--vitest)
- [Jasmine / Karma](#jasmine--karma)
- [Mocha](#mocha)
- [pytest](#pytest)
- [unittest](#unittest)
- [JUnit 5](#junit-5)
- [Go testing](#go-testing)
- [RSpec](#rspec)
- [xUnit / NUnit (C#)](#xunit--nunit-c)
- [Rust tests](#rust-tests)
- [PHPUnit](#phpunit)
- [Stub file placement](#stub-file-placement)

## Picking what to test

Read the function body and list each decision point:

- `if (cond)` / `if cond:` → one test where `cond` is true, one where it's false
- `switch` / `match` / lookup → one test per branch, plus the default/else
- `&&` / `||` / `??` / `and` / `or` → one test that hits the short-circuit and one that doesn't
- `for` / `while` / iteration → empty collection, single item, multiple items
- `try/catch` / `except` / `rescue` / `Result<Err>` → happy path and the throw/error path

Don't aim for 100%. Aim for every **decision point** to have both outcomes exercised — that's what the CRAP formula rewards.

## Jest / Vitest

Identical API for these templates; change `import from 'vitest'` for Vitest or omit imports for Jest's globals.

```ts
import { applyCoupon } from './order';

describe('applyCoupon', () => {
  it('returns subtotal unchanged when no coupon', () => {
    expect(applyCoupon(100, undefined)).toBe(100);
  });

  it('applies percentage coupons', () => {
    expect(applyCoupon(100, { kind: 'pct', value: 0.1 })).toBe(90);
  });

  it('applies flat coupons', () => {
    expect(applyCoupon(100, { kind: 'flat', value: 15 })).toBe(85);
  });
});
```

**Class with injected dependencies:**
```ts
import { WidgetService } from './widget.service';

describe('WidgetService', () => {
  let service: WidgetService;
  let repo: { save: jest.Mock };

  beforeEach(() => {
    repo = { save: jest.fn() };
    service = new WidgetService(repo as any);
  });

  it('rejects invalid orders', () => {
    expect(() => service.processOrder({ id: '', items: [] } as any)).toThrow('invalid');
    expect(repo.save).not.toHaveBeenCalled();
  });

  it('saves the computed total', () => {
    service.processOrder({ id: '1', items: [{ price: 10 }, { price: 5 }] } as any);
    expect(repo.save).toHaveBeenCalledWith(expect.objectContaining({ total: 15 }));
  });
});
```

For frameworks with DI containers (Angular `TestBed`, NestJS `Test.createTestingModule`), follow the project's existing spec style rather than hand-rolling a new pattern.

## Jasmine / Karma

Jasmine spies replace `jest.fn()`:

```ts
describe('WidgetService', () => {
  let service: WidgetService;
  let repo: jasmine.SpyObj<Repo>;

  beforeEach(() => {
    repo = jasmine.createSpyObj<Repo>('Repo', ['save']);
    service = new WidgetService(repo);
  });

  it('rejects invalid orders', () => {
    expect(() => service.processOrder({ id: '', items: [] } as any)).toThrowError('invalid');
    expect(repo.save).not.toHaveBeenCalled();
  });
});
```

## Mocha

Mocha has no assertion library — pair with `chai` or `node:assert`:

```ts
import { expect } from 'chai';
import { applyCoupon } from './order';

describe('applyCoupon', () => {
  it('returns subtotal unchanged when no coupon', () => {
    expect(applyCoupon(100, undefined)).to.equal(100);
  });
});
```

## pytest

Use fixtures for shared setup. Parametrize to cover multiple branches tersely.

```python
import pytest
from order import apply_coupon


def test_returns_subtotal_when_no_coupon():
    assert apply_coupon(100, None) == 100


@pytest.mark.parametrize("coupon,expected", [
    ({"kind": "pct", "value": 0.1}, 90),
    ({"kind": "flat", "value": 15}, 85),
])
def test_applies_coupons(coupon, expected):
    assert apply_coupon(100, coupon) == expected
```

**Class with injected dependencies:**
```python
import pytest
from unittest.mock import MagicMock
from widget import WidgetService


@pytest.fixture
def repo():
    return MagicMock()


@pytest.fixture
def service(repo):
    return WidgetService(repo)


def test_rejects_invalid_orders(service, repo):
    with pytest.raises(ValueError, match="invalid"):
        service.process_order({"id": "", "items": []})
    repo.save.assert_not_called()


def test_saves_computed_total(service, repo):
    service.process_order({"id": "1", "items": [{"price": 10}, {"price": 5}]})
    repo.save.assert_called_once()
    assert repo.save.call_args.args[0]["total"] == 15
```

## unittest

Use when the project doesn't depend on pytest.

```python
import unittest
from unittest.mock import MagicMock
from widget import WidgetService


class WidgetServiceTest(unittest.TestCase):
    def setUp(self):
        self.repo = MagicMock()
        self.service = WidgetService(self.repo)

    def test_rejects_invalid_orders(self):
        with self.assertRaises(ValueError):
            self.service.process_order({"id": "", "items": []})
        self.repo.save.assert_not_called()
```

## JUnit 5

```java
import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.*;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class WidgetServiceTest {
    private Repo repo;
    private WidgetService service;

    @BeforeEach
    void setUp() {
        repo = mock(Repo.class);
        service = new WidgetService(repo);
    }

    @Test
    void rejectsInvalidOrders() {
        assertThatThrownBy(() -> service.processOrder(Order.empty()))
            .isInstanceOf(IllegalArgumentException.class)
            .hasMessageContaining("invalid");
        verify(repo, never()).save(any());
    }

    @Test
    void savesComputedTotal() {
        service.processOrder(Order.of(10, 5));
        var captor = ArgumentCaptor.forClass(Order.class);
        verify(repo).save(captor.capture());
        assertThat(captor.getValue().total()).isEqualTo(15);
    }
}
```

For Kotlin, prefer `kotlin.test` or `kotest`:

```kotlin
class WidgetServiceTest {
    private val repo = mockk<Repo>(relaxed = true)
    private val service = WidgetService(repo)

    @Test
    fun `rejects invalid orders`() {
        assertThrows<IllegalArgumentException> { service.processOrder(Order.empty()) }
        verify(exactly = 0) { repo.save(any()) }
    }
}
```

## Go testing

Table-driven tests are idiomatic:

```go
package order

import "testing"

func TestApplyCoupon(t *testing.T) {
    tests := []struct {
        name     string
        subtotal float64
        coupon   *Coupon
        want     float64
    }{
        {"no coupon", 100, nil, 100},
        {"percentage", 100, &Coupon{Kind: "pct", Value: 0.1}, 90},
        {"flat", 100, &Coupon{Kind: "flat", Value: 15}, 85},
    }
    for _, tc := range tests {
        t.Run(tc.name, func(t *testing.T) {
            got := ApplyCoupon(tc.subtotal, tc.coupon)
            if got != tc.want {
                t.Errorf("got %v want %v", got, tc.want)
            }
        })
    }
}
```

## RSpec

```ruby
RSpec.describe WidgetService do
  let(:repo)    { instance_double(Repo, save: nil) }
  let(:service) { described_class.new(repo) }

  describe "#process_order" do
    it "rejects invalid orders" do
      expect { service.process_order(id: "", items: []) }.to raise_error(/invalid/)
      expect(repo).not_to have_received(:save)
    end

    it "saves the computed total" do
      service.process_order(id: "1", items: [{ price: 10 }, { price: 5 }])
      expect(repo).to have_received(:save).with(hash_including(total: 15))
    end
  end
end
```

## xUnit / NUnit (C#)

```csharp
using Moq;
using Xunit;

public class WidgetServiceTests
{
    private readonly Mock<IRepo> _repo = new();
    private readonly WidgetService _service;

    public WidgetServiceTests() => _service = new WidgetService(_repo.Object);

    [Fact]
    public void RejectsInvalidOrders()
    {
        var ex = Assert.Throws<ArgumentException>(() =>
            _service.ProcessOrder(new Order { Id = "", Items = Array.Empty<Item>() }));
        Assert.Contains("invalid", ex.Message);
        _repo.Verify(r => r.Save(It.IsAny<Order>()), Times.Never);
    }
}
```

## Rust tests

Tests live in the same file under `#[cfg(test)] mod tests`:

```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn returns_subtotal_when_no_coupon() {
        assert_eq!(apply_coupon(100.0, None), 100.0);
    }

    #[test]
    fn applies_percentage_coupon() {
        let coupon = Coupon::Pct(0.1);
        assert_eq!(apply_coupon(100.0, Some(coupon)), 90.0);
    }
}
```

## PHPUnit

```php
use PHPUnit\Framework\TestCase;

class WidgetServiceTest extends TestCase
{
    private Repo $repo;
    private WidgetService $service;

    protected function setUp(): void
    {
        $this->repo = $this->createMock(Repo::class);
        $this->service = new WidgetService($this->repo);
    }

    public function testRejectsInvalidOrders(): void
    {
        $this->expectException(InvalidArgumentException::class);
        $this->service->processOrder(new Order('', []));
        $this->repo->expects($this->never())->method('save');
    }
}
```

## Stub file placement

Follow the existing convention in the repo. Typical defaults:

| Language | Convention |
|---|---|
| JS/TS (Jest/Vitest/Karma) | `<name>.spec.ts` alongside source |
| JS/TS (Mocha) | `test/<name>.test.ts` or alongside source |
| Python (pytest) | `tests/test_<name>.py` or `test_<name>.py` alongside source |
| Java | `src/test/java/<same-package>/<Name>Test.java` |
| Kotlin | `src/test/kotlin/<same-package>/<Name>Test.kt` |
| Go | `<name>_test.go` in the same package |
| Ruby | `spec/<name>_spec.rb` mirroring `lib/<name>.rb` |
| C# | `<Name>Tests.cs` in a sibling test project |
| Rust | Inline `#[cfg(test)] mod tests` or `tests/<name>.rs` |
| PHP | `tests/<Name>Test.php` |

**Never create a test stub without at least one assertion** — empty tests pass silently and actually *lower* effective coverage because they add executable lines without exercising logic.
