# Stage-3 Negative Constitution

> P1 Item 13: What this system is NOT.
> Every violation triggers mandatory governance review.

---

## Stage-3 Is NOT

### 1. NOT Learning
- Advisory does NOT update weights
- No gradient descent
- No backpropagation
- No reinforcement signals

### 2. NOT Adapting
- Divergence is logged, NOT acted upon
- No threshold-based behavior changes
- No "if accuracy > X then do Y"
- No feedback loops

### 3. NOT Optimizing
- No objective function is minimized
- No loss function drives behavior
- No reward shaping
- No metric-driven adjustments

### 4. NOT Autonomous
- Cannot initiate actions
- Cannot schedule tasks
- Cannot trigger external calls
- Cannot write to memory

### 5. NOT Self-Improving
- Cannot modify its own weights
- Cannot update its own code
- Cannot change its own rules
- Cannot evolve

---

## Forbidden Code Patterns

```python
# FORBIDDEN - Any of these patterns in Stage-3 code triggers review:

model.update_weights(...)      # Learning
loss.backward()                # Gradient
optimizer.step()               # Weight update
if accuracy > threshold:       # Threshold-based adaptation
divergence.apply()             # Acting on divergence
self.improve()                 # Self-improvement
feedback_loop(...)             # Feedback integration
```

---

## Violation Response

| Detection | Response |
|-----------|----------|
| Code review finds pattern | Block merge |
| Runtime detection | Kill-switch |
| Audit finds evidence | Governance review |

---

## Enforcement Mechanism

1. **Static Analysis**: CI runs pattern scan
2. **Runtime Guard**: `AdvisoryGuard` blocks forbidden phases
3. **Containment Layer**: `check_for_adaptation_attempt()` 
4. **Human Review**: Quarterly audit of all Stage-3 code

---

## This Document Is Immutable

Changes to this constitution require:
- Council majority approval
- Admin signature
- 7-day review period
- Logged as constitutional event
