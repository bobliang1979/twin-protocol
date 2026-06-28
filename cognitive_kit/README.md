# cognitive-kit

Production-grade cognitive architecture toolkit for AI agents.

## Components

- **mcts/engine.py** - UCB1 MCTS with Wilson score, bounded memory, static token invariance
- **cognitive/circuit_breaker.py** - DHG entropy monitoring for system degradation detection
- **cognitive/health_field.py** - Multi-dimensional runtime health monitoring
- **cognitive/reflection.py** - 6 failure mode classifier with auto-recovery
- **skills/integrator.py** - Pluggable skill loading framework

## Quick Start

```python
from cognitive_kit.mcts import ReasoningEngine

engine = ReasoningEngine()
result = await engine.run(query="Solve problem X")
```
