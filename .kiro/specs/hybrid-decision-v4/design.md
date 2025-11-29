# Design Document - Hybrid Decision Engine V4

## Overview

The Hybrid Decision Engine V4 is a robust, multi-layered decision-making system for the Guandan card game. It prioritizes the proven lalala strategy (40-50% win rate) while providing graceful fallback mechanisms through DecisionEngine, knowledge-enhanced decision, and random selection. The system ensures that a valid action is always returned, even in the face of errors or edge cases.

### Key Design Principles

1. **Reliability First**: Never crash, always return a valid action
2. **Performance Proven**: Leverage lalala's proven 40-50% win rate
3. **Graceful Degradation**: Multiple fallback layers for robustness
4. **Observability**: Comprehensive logging and performance monitoring
5. **Maintainability**: Clean separation of concerns and modular design

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Game Server (External)                    │
└───────────────────────────┬─────────────────────────────────┘
                            │ JSON Messages
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                  Test1_V4 / Test2_V4 Client                  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │         Message Parser & Protocol Handler             │  │
│  └─────────────────────────┬─────────────────────────────┘  │
│                            │                                 │
│  ┌─────────────────────────▼─────────────────────────────┐  │
│  │        Hybrid Decision Engine V4 (Core)               │  │
│  │  ┌─────────────────────────────────────────────────┐  │  │
│  │  │  Layer 1: lalala Strategy (Primary)             │  │  │
│  │  │  - Proven 40-50% win rate                       │  │  │
│  │  │  - Rule-based decision making                   │  │  │
│  │  └──────────────────┬──────────────────────────────┘  │  │
│  │                     │ On Error                         │  │
│  │  ┌──────────────────▼──────────────────────────────┐  │  │
│  │  │  Layer 2: DecisionEngine (Fallback 1)           │  │  │
│  │  │  - Evaluation-based selection                   │  │  │
│  │  │  - Multi-factor scoring                         │  │  │
│  │  └──────────────────┬──────────────────────────────┘  │  │
│  │                     │ On Error                         │  │
│  │  ┌──────────────────▼──────────────────────────────┐  │  │
│  │  │  Layer 3: Knowledge Enhanced (Fallback 2)       │  │  │
│  │  │  - Knowledge base integration                   │  │  │
│  │  │  - Pattern matching                             │  │  │
│  │  └──────────────────┬──────────────────────────────┘  │  │
│  │                     │ On Error                         │  │
│  │  ┌──────────────────▼──────────────────────────────┐  │  │
│  │  │  Layer 4: Random Selection (Guaranteed)         │  │  │
│  │  │  - Always succeeds                              │  │  │
│  │  │  - Selects random valid action                  │  │  │
│  │  └─────────────────────────────────────────────────┘  │  │
│  └─────────────────────────┬─────────────────────────────┘  │
│                            │                                 │
│  ┌─────────────────────────▼─────────────────────────────┐  │
│  │         Performance Monitor & Statistics              │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Component Interaction Flow

```
Game State Input
      │
      ▼
┌──────────────┐
│ Data Convert │ ──────► Convert to lalala format
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Layer 1      │ ──────► Try lalala.decide()
│ (lalala)     │         Success? Return action
└──────┬───────┘         Error? Continue ▼
       │
       ▼
┌──────────────┐
│ Layer 2      │ ──────► Try DecisionEngine.decide()
│ (DecEngine)  │         Success? Return action
└──────┬───────┘         Error? Continue ▼
       │
       ▼
┌──────────────┐
│ Layer 3      │ ──────► Try KnowledgeEnhanced.decide()
│ (Knowledge)  │         Success? Return action
└──────┬───────┘         Error? Continue ▼
       │
       ▼
┌──────────────┐
│ Layer 4      │ ──────► random.choice(legal_actions)
│ (Random)     │         Always succeeds!
└──────┬───────┘
       │
       ▼
  Return Action
```

## Components and Interfaces

### 1. HybridDecisionEngineV4 (Core Component)

**Responsibility**: Orchestrate the 4-layer decision process

```python
class HybridDecisionEngineV4:
    """
    Core decision engine with 4-layer fallback protection.
    """
    
    def __init__(self, player_id: int, config: dict):
        """
        Initialize the hybrid decision engine.
        
        Args:
            player_id: Player position (0-3)
            config: Configuration dictionary
        """
        self.player_id = player_id
        self.config = config
        
        # Initialize decision layers
        self.lalala_adapter = LalalaAdapter(player_id)
        self.decision_engine = DecisionEngine()
        self.knowledge_enhanced = KnowledgeEnhancedDecision()
        
        # Performance monitoring
        self.stats = DecisionStatistics()
        self.logger = logging.getLogger(f"HybridV4-P{player_id}")
    
    def decide(self, message: dict) -> int:
        """
        Make a decision using 4-layer fallback mechanism.
        
        Args:
            message: Game state message from server
            
        Returns:
            Action index (0 for PASS, 1+ for play actions)
        """
        start_time = time.time()
        
        try:
            # Layer 1: lalala (Primary)
            action = self._try_lalala(message)
            if action is not None:
                self.stats.record_success("lalala", time.time() - start_time)
                return action
        except Exception as e:
            self.logger.warning(f"Layer 1 (lalala) failed: {e}")
            self.stats.record_failure("lalala", str(e))
        
        try:
            # Layer 2: DecisionEngine (Fallback 1)
            action = self._try_decision_engine(message)
            if action is not None:
                self.stats.record_success("DecisionEngine", time.time() - start_time)
                return action
        except Exception as e:
            self.logger.warning(f"Layer 2 (DecisionEngine) failed: {e}")
            self.stats.record_failure("DecisionEngine", str(e))
        
        try:
            # Layer 3: Knowledge Enhanced (Fallback 2)
            action = self._try_knowledge_enhanced(message)
            if action is not None:
                self.stats.record_success("KnowledgeEnhanced", time.time() - start_time)
                return action
        except Exception as e:
            self.logger.warning(f"Layer 3 (KnowledgeEnhanced) failed: {e}")
            self.stats.record_failure("KnowledgeEnhanced", str(e))
        
        # Layer 4: Random (Guaranteed)
        action = self._random_valid_action(message)
        self.stats.record_success("Random", time.time() - start_time)
        self.logger.info(f"Using Layer 4 (Random): action={action}")
        return action
    
    def _try_lalala(self, message: dict) -> Optional[int]:
        """Try lalala decision layer."""
        pass
    
    def _try_decision_engine(self, message: dict) -> Optional[int]:
        """Try DecisionEngine layer."""
        pass
    
    def _try_knowledge_enhanced(self, message: dict) -> Optional[int]:
        """Try knowledge-enhanced layer."""
        pass
    
    def _random_valid_action(self, message: dict) -> int:
        """Guaranteed fallback: select random valid action."""
        pass
```

### 2. LalalaAdapter (Data Conversion)

**Responsibility**: Convert between system formats and lalala format

```python
class LalalaAdapter:
    """
    Adapter for lalala strategy with proper data conversion.
    """
    
    def __init__(self, player_id: int):
        self.player_id = player_id
        self.lalala_state = None
        self.logger = logging.getLogger(f"LalalaAdapter-P{player_id}")
    
    def decide(self, message: dict) -> int:
        """
        Make decision using lalala strategy.
        
        Args:
            message: Game state message
            
        Returns:
            Action index
            
        Raises:
            ValueError: If data conversion fails
            RuntimeError: If lalala decision fails
        """
        # Convert message to lalala format
        converted_message = self._convert_message(message)
        
        # Initialize or update lalala state
        if self.lalala_state is None:
            self.lalala_state = self._initialize_lalala_state(converted_message)
        else:
            self.lalala_state = self._update_lalala_state(converted_message)
        
        # Get lalala decision
        action_index = self.lalala_state.decide(converted_message)
        
        # Validate action
        if not self._is_valid_action(action_index, message):
            raise ValueError(f"lalala returned invalid action: {action_index}")
        
        return action_index
    
    def _convert_message(self, message: dict) -> dict:
        """
        Convert message format for lalala.
        
        Critical conversions:
        - Card format: string -> list
        - Player positions: system -> lalala mapping
        - publicInfo.playArea: handle all card types
        """
        converted = message.copy()
        
        # Convert card formats
        if 'myHandCards' in converted:
            converted['myHandCards'] = self._convert_cards(converted['myHandCards'])
        
        if 'publicInfo' in converted and 'playArea' in converted['publicInfo']:
            converted['publicInfo']['playArea'] = self._convert_play_area(
                converted['publicInfo']['playArea']
            )
        
        # Convert player positions
        converted = self._convert_player_positions(converted)
        
        return converted
    
    def _convert_cards(self, cards: Union[str, List]) -> List:
        """Convert card format from string to list."""
        if isinstance(cards, list):
            return cards  # Already converted
        
        if isinstance(cards, str):
            # Parse string format: "3H,4D,5S" -> ["3H", "4D", "5S"]
            if not cards:
                return []
            return [c.strip() for c in cards.split(',') if c.strip()]
        
        raise ValueError(f"Invalid card format: {type(cards)}")
    
    def _convert_play_area(self, play_area: dict) -> dict:
        """Convert playArea card formats."""
        converted = {}
        for player_id, cards in play_area.items():
            converted[player_id] = self._convert_cards(cards)
        return converted
    
    def _convert_player_positions(self, message: dict) -> dict:
        """Convert player position mapping."""
        # Map system positions to lalala positions
        # This depends on player_id and game rules
        pass
    
    def _initialize_lalala_state(self, message: dict):
        """Initialize lalala State object."""
        from lalala.state import State
        return State(self.player_id)
    
    def _update_lalala_state(self, message: dict):
        """Update existing lalala state."""
        # Update state with new message
        pass
    
    def _is_valid_action(self, action: int, message: dict) -> bool:
        """Validate that action is legal."""
        action_list = message.get('actionList', [])
        return 0 <= action < len(action_list)
```

### 3. DecisionStatistics (Monitoring)

**Responsibility**: Track performance metrics and layer usage

```python
class DecisionStatistics:
    """
    Track decision performance and layer usage statistics.
    """
    
    def __init__(self):
        self.layer_usage = {
            "lalala": {"success": 0, "failure": 0, "total_time": 0.0},
            "DecisionEngine": {"success": 0, "failure": 0, "total_time": 0.0},
            "KnowledgeEnhanced": {"success": 0, "failure": 0, "total_time": 0.0},
            "Random": {"success": 0, "failure": 0, "total_time": 0.0}
        }
        self.error_log = []
        self.decision_count = 0
    
    def record_success(self, layer: str, duration: float):
        """Record successful decision."""
        self.layer_usage[layer]["success"] += 1
        self.layer_usage[layer]["total_time"] += duration
        self.decision_count += 1
    
    def record_failure(self, layer: str, error: str):
        """Record failed decision attempt."""
        self.layer_usage[layer]["failure"] += 1
        self.error_log.append({
            "layer": layer,
            "error": error,
            "timestamp": time.time()
        })
    
    def get_layer_success_rate(self, layer: str) -> float:
        """Calculate success rate for a layer."""
        stats = self.layer_usage[layer]
        total = stats["success"] + stats["failure"]
        if total == 0:
            return 0.0
        return stats["success"] / total
    
    def get_summary(self) -> dict:
        """Get statistics summary."""
        return {
            "total_decisions": self.decision_count,
            "layer_usage": self.layer_usage,
            "success_rates": {
                layer: self.get_layer_success_rate(layer)
                for layer in self.layer_usage.keys()
            }
        }
    
    def reset(self):
        """Reset statistics for new game."""
        self.__init__()
```

## Data Models

### Message Format (Input)

```python
{
    "stage": str,  # "tribute", "back", "play"
    "actionList": List[dict],  # Available actions
    "myHandCards": Union[str, List[str]],  # Player's cards
    "publicInfo": {
        "playArea": Dict[int, Union[str, List[str]]],  # Cards on table
        "greaterPos": int,  # Current winning player
        "curRank": int,  # Current rank
        # ... other public info
    },
    "history": List[dict],  # Game history
    # ... other fields
}
```

### Action Format (Output)

```python
# Return value: int
# 0 = PASS
# 1+ = Index into actionList
```

### Statistics Format

```python
{
    "total_decisions": int,
    "layer_usage": {
        "lalala": {
            "success": int,
            "failure": int,
            "total_time": float
        },
        # ... other layers
    },
    "success_rates": {
        "lalala": float,  # 0.0 to 1.0
        # ... other layers
    }
}
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: lalala Priority
*For any* game state, when the System receives a decision request, lalala SHALL be invoked before any other decision layer.
**Validates: Requirements 1.1**

### Property 2: No Unnecessary Fallback
*For any* game state where lalala returns a valid action, the System SHALL NOT invoke DecisionEngine, KnowledgeEnhanced, or Random layers.
**Validates: Requirements 1.2**

### Property 3: Decision Source Logging
*For any* decision made by lalala, the System logs SHALL contain "lalala" as the decision source.
**Validates: Requirements 1.4**

### Property 4: Format Conversion Correctness
*For any* game state, converting to lalala format SHALL produce data structures that match lalala's expected input schema.
**Validates: Requirements 1.5**

### Property 5: Card Format Transformation
*For any* card data in string format, conversion SHALL produce a list format where each element is a valid card string.
**Validates: Requirements 2.1**

### Property 6: Card Type Handling
*For any* card type variation (Single, Pair, Triple, Bomb, etc.) in publicInfo.playArea, conversion SHALL handle it without errors.
**Validates: Requirements 2.2**

### Property 7: Conversion Idempotence
*For any* data, converting twice SHALL produce the same result as converting once: convert(convert(x)) == convert(x).
**Validates: Requirements 2.3**

### Property 8: Invalid Data Error Handling
*For any* invalid input data, the System SHALL raise an exception with a clear error message describing the problem.
**Validates: Requirements 2.4**

### Property 9: Player Position Preservation
*For any* game state, after conversion, teammate and opponent relationships SHALL remain correct (teammates stay teammates, opponents stay opponents).
**Validates: Requirements 2.5**

### Property 10: Exception Catching
*For any* exception raised by lalala, the System SHALL catch it, log the details, and continue to fallback layer.
**Validates: Requirements 3.1**

### Property 11: Fallback Behavior
*For any* game state where lalala fails, the System SHALL invoke DecisionEngine as the next layer.
**Validates: Requirements 3.2**

### Property 12: Fallback Logging
*For any* fallback occurrence, the System logs SHALL contain the error type and reason for fallback.
**Validates: Requirements 3.3**

### Property 13: Invalid Action Validation
*For any* action returned by lalala, if the action index is not in the valid range [0, len(actionList)), the System SHALL fallback to the next layer.
**Validates: Requirements 3.4**

### Property 14: Error Pattern Tracking
*For any* sequence of consecutive errors, the System SHALL maintain a count and log of error occurrences.
**Validates: Requirements 3.5**

### Property 15: Legal Actions Evaluation
*For any* game state processed by DecisionEngine, all legal actions from actionList SHALL be evaluated.
**Validates: Requirements 4.1**

### Property 16: DecisionEngine Source Logging
*For any* decision made by DecisionEngine, the System logs SHALL contain "DecisionEngine" as the decision source.
**Validates: Requirements 4.2**

### Property 17: Layer 2 to Layer 3 Fallback
*For any* game state where DecisionEngine fails, the System SHALL invoke KnowledgeEnhanced as the next layer.
**Validates: Requirements 4.4**

### Property 18: Fallback Reset
*For any* successful fallback decision, the next decision request SHALL attempt lalala first (fallback is temporary, not permanent).
**Validates: Requirements 4.5**

### Property 19: Layer 1 to Layer 2 Chain
*For any* game state where Layer 1 (lalala) fails, the System SHALL attempt Layer 2 (DecisionEngine).
**Validates: Requirements 5.1**

### Property 20: Layer 2 to Layer 3 Chain
*For any* game state where Layer 2 (DecisionEngine) fails, the System SHALL attempt Layer 3 (KnowledgeEnhanced).
**Validates: Requirements 5.2**

### Property 21: Layer 3 to Layer 4 Chain
*For any* game state where Layer 3 (KnowledgeEnhanced) fails, the System SHALL use Layer 4 (Random).
**Validates: Requirements 5.3**

### Property 22: Early Termination
*For any* game state, if Layer N succeeds, Layers N+1 through 4 SHALL NOT be invoked.
**Validates: Requirements 5.4**

### Property 23: Layer 4 Guarantee
*For any* game state with at least one legal action, Layer 4 SHALL always return a valid action index.
**Validates: Requirements 5.5**

### Property 24: Layer Recording
*For any* decision made, the System SHALL record which layer (1-4) was used for that decision.
**Validates: Requirements 6.1**

### Property 25: Failure Counter Increment
*For any* lalala failure, the failure counter SHALL increase by exactly 1.
**Validates: Requirements 6.3**

### Property 26: Performance Warning Logging
*For any* decision that exceeds the time threshold, the System SHALL log a performance warning with timing information.
**Validates: Requirements 6.4**

### Property 27: Success Rate Calculation
*For any* layer with recorded decisions, the success rate SHALL equal successes / (successes + failures).
**Validates: Requirements 6.5**

### Property 28: State Synchronization
*For any* game state update, the internal state representation SHALL reflect all changes from the update.
**Validates: Requirements 7.1**

### Property 29: Initialization Correctness
*For any* new lalala state creation, player positions SHALL match the input player_id and game configuration.
**Validates: Requirements 7.2**

### Property 30: Information Preservation
*For any* state conversion, all critical game information (cards, positions, history) SHALL be preserved in the converted state.
**Validates: Requirements 7.3**

### Property 31: State Isolation
*For any* two concurrent clients, state changes in client A SHALL NOT affect state in client B.
**Validates: Requirements 7.4**

### Property 32: State Reset
*For any* game reset operation, the state SHALL be equivalent to a freshly initialized state.
**Validates: Requirements 7.5**

### Property 33: Decision Logging
*For any* decision made, the System logs SHALL contain decision details including layer used, action selected, and timestamp.
**Validates: Requirements 8.1**

### Property 34: Error Stack Trace Logging
*For any* error occurrence, the System logs SHALL contain the full stack trace.
**Validates: Requirements 8.2**

### Property 35: Fallback Context Logging
*For any* fallback event, the System logs SHALL contain the reason for fallback and relevant context (game state summary).
**Validates: Requirements 8.3**

### Property 36: Timing Information Logging
*For any* decision that triggers a performance issue, the System logs SHALL contain timing information (duration, threshold).
**Validates: Requirements 8.4**

### Property 37: Debug Mode Verbosity
*For any* decision made in debug mode, the System logs SHALL contain detailed state information including hand cards, play area, and action list.
**Validates: Requirements 8.5**

### Property 38: Test1/Test2 Consistency
*For any* game state, Test1_V4 and Test2_V4 SHALL produce the same decision given identical inputs.
**Validates: Requirements 9.2**

### Property 39: Message Parsing
*For any* valid server message, the System SHALL parse it without errors and extract all required fields.
**Validates: Requirements 9.3**

### Property 40: Response Protocol Compliance
*For any* action returned, the response format SHALL comply with the game protocol specification (integer index).
**Validates: Requirements 9.4**

### Property 41: Concurrent Game Handling
*For any* two games running concurrently, decisions in game A SHALL NOT interfere with decisions in game B.
**Validates: Requirements 9.5**

## Error Handling

### Error Categories

1. **Data Conversion Errors**
   - Invalid card format
   - Missing required fields
   - Type mismatches
   - **Handling**: Log error, raise ValueError, trigger fallback

2. **lalala Execution Errors**
   - IndexError in state.py
   - KeyError in publicInfo
   - AttributeError in action logic
   - **Handling**: Catch exception, log details, fallback to Layer 2

3. **DecisionEngine Errors**
   - Evaluation failures
   - No valid actions found
   - Timeout errors
   - **Handling**: Catch exception, log details, fallback to Layer 3

4. **System Errors**
   - Out of memory
   - Unexpected exceptions
   - **Handling**: Log critical error, use Layer 4 (Random)

### Error Recovery Strategy

```python
def decide_with_recovery(self, message: dict) -> int:
    """
    Decision with comprehensive error recovery.
    """
    try:
        return self.decide(message)
    except Exception as e:
        self.logger.critical(f"Unexpected error in decide: {e}", exc_info=True)
        # Emergency fallback: return PASS (0)
        return 0
```

## Testing Strategy

### Unit Testing

We will write unit tests for:

1. **Data Conversion Functions**
   - Test `_convert_cards()` with various input formats
   - Test `_convert_play_area()` with all card types
   - Test `_convert_player_positions()` for all player IDs

2. **Validation Functions**
   - Test `_is_valid_action()` with valid and invalid indices
   - Test error detection logic

3. **Statistics Tracking**
   - Test `record_success()` and `record_failure()`
   - Test `get_layer_success_rate()` calculation
   - Test `get_summary()` aggregation

### Property-Based Testing

We will use **Hypothesis** (Python property-based testing library) to verify correctness properties. Each property test will run a minimum of 100 iterations with randomly generated inputs.

Property-based tests will be tagged with comments referencing the design document:
```python
# Feature: hybrid-decision-v4, Property 1: lalala Priority
@given(game_state=game_state_strategy())
def test_lalala_priority(game_state):
    """Test that lalala is always invoked first."""
    # Test implementation
```

Key property tests:

1. **Conversion Properties**
   - Property 5: Card format transformation correctness
   - Property 7: Conversion idempotence
   - Property 9: Player position preservation

2. **Fallback Chain Properties**
   - Property 19-21: Layer fallback chain
   - Property 22: Early termination
   - Property 23: Layer 4 guarantee

3. **State Management Properties**
   - Property 28: State synchronization
   - Property 31: State isolation
   - Property 32: State reset

4. **Logging Properties**
   - Property 3: Decision source logging
   - Property 33: Decision logging completeness

### Integration Testing

Integration tests will verify:

1. **Full Game Simulation**
   - Run complete games using Test1_V4 and Test2_V4
   - Verify no crashes or errors
   - Verify all decisions are valid

2. **Fallback Scenarios**
   - Simulate lalala failures
   - Verify fallback chain works correctly
   - Verify recovery to lalala after successful fallback

3. **Performance Testing**
   - Measure decision time for each layer
   - Verify timing requirements are met
   - Test under load (100+ consecutive games)

### Validation Testing

Validation tests will verify:

1. **Win Rate Validation**
   - Run 100+ games: Test1_V4 + Test2_V4 vs lalala (client3 + client4)
   - Target: 40-50% win rate
   - Measure: Games won / Total games

2. **Stability Testing**
   - Run 1000+ consecutive games
   - Verify no memory leaks
   - Verify no performance degradation

## Performance Considerations

### Timing Requirements

- **Layer 1 (lalala)**: < 0.8 seconds per decision
- **Layer 2 (DecisionEngine)**: < 1.5 seconds per decision
- **Layer 3 (KnowledgeEnhanced)**: < 2.0 seconds per decision
- **Layer 4 (Random)**: < 0.1 seconds per decision

### Optimization Strategies

1. **Caching**: Cache converted data to avoid redundant conversions
2. **Early Exit**: Return immediately when lalala succeeds (most common case)
3. **Lazy Initialization**: Only initialize fallback layers when needed
4. **Profiling**: Monitor and log slow operations

### Memory Management

- Reset statistics between games to prevent memory growth
- Clear cached data periodically
- Use weak references for large objects when appropriate

## Deployment

### File Structure

```
src/
├── communication/
│   ├── Test1_V4.py          # Client 1 implementation
│   ├── Test2_V4.py          # Client 2 implementation
│   └── lalala_adapter.py    # Data conversion (reuse existing)
├── decision/
│   ├── hybrid_decision_engine_v4.py  # Core engine
│   └── decision_statistics.py        # Monitoring
└── tests/
    ├── test_hybrid_v4_unit.py        # Unit tests
    ├── test_hybrid_v4_properties.py  # Property-based tests
    └── test_hybrid_v4_integration.py # Integration tests
```

### Configuration

```python
# config.yaml
hybrid_v4:
  enable_lalala: true
  enable_fallback: true
  log_level: INFO
  performance_threshold: 1.0  # seconds
  statistics_enabled: true
```

### Monitoring

- Log all decisions with layer information
- Track layer usage statistics
- Alert on high fallback rates (> 10%)
- Monitor decision timing

## Future Enhancements

1. **Adaptive Thresholds**: Adjust timing thresholds based on observed performance
2. **Layer Learning**: Track which layers work best for which game states
3. **Hybrid Strategies**: Combine lalala and DecisionEngine insights
4. **Performance Tuning**: Optimize slow paths identified through profiling
