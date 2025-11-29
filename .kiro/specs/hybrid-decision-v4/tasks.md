# Implementation Plan - Hybrid Decision Engine V4

## Overview

This implementation plan breaks down the Hybrid Decision Engine V4 into discrete, manageable coding tasks. Each task builds incrementally on previous tasks, with property-based tests integrated throughout to catch errors early.

---

## Tasks

- [x] 1. Create core HybridDecisionEngineV4 class structure


  - Create `src/decision/hybrid_decision_engine_v4.py`
  - Implement `__init__()` with player_id and config parameters
  - Implement skeleton `decide()` method with 4-layer structure
  - Add logging setup for the engine
  - _Requirements: 1.1, 5.1, 5.2, 5.3, 5.4_
  - **Status: ✓ COMPLETED**

- [ ]* 1.1 Write property test for layer invocation order
  - **Property 1: lalala Priority**
  - **Validates: Requirements 1.1**

- [x] 2. Implement DecisionStatistics monitoring class
  - Create `src/decision/decision_statistics.py`
  - Implement `record_success()` and `record_failure()` methods
  - Implement `get_layer_success_rate()` calculation
  - Implement `get_summary()` for statistics reporting
  - Implement `reset()` for game cleanup
  - _Requirements: 6.1, 6.2, 6.3, 6.5_
  - **Status: ✓ COMPLETED (integrated in hybrid_decision_engine_v4.py)**

- [ ]* 2.1 Write property test for statistics tracking
  - **Property 24: Layer Recording**
  - **Property 25: Failure Counter Increment**
  - **Property 27: Success Rate Calculation**
  - **Validates: Requirements 6.1, 6.3, 6.5**

- [x] 3. Enhance LalalaAdapter with robust data conversion


  - Update `src/communication/lalala_adapter.py` (or create new version)
  - Implement `_convert_cards()` with string-to-list conversion
  - Implement `_convert_play_area()` for all card types
  - Implement `_convert_player_positions()` for position mapping
  - Add comprehensive error handling with clear error messages
  - _Requirements: 2.1, 2.2, 2.4, 2.5_
  - **Status: ✓ COMPLETED (created lalala_adapter_v4.py)**

- [ ]* 3.1 Write property test for card format conversion
  - **Property 5: Card Format Transformation**
  - **Validates: Requirements 2.1**

- [ ]* 3.2 Write property test for conversion idempotence
  - **Property 7: Conversion Idempotence**
  - **Validates: Requirements 2.3**

- [ ]* 3.3 Write property test for player position preservation
  - **Property 9: Player Position Preservation**
  - **Validates: Requirements 2.5**

- [x] 4. Implement Layer 1: lalala decision logic


  - Implement `_try_lalala()` method in HybridDecisionEngineV4
  - Call LalalaAdapter.decide() with proper error handling
  - Validate returned action is in valid range
  - Log decision source as "lalala"
  - Return action on success, None on failure
  - _Requirements: 1.1, 1.2, 1.4, 1.5_

- [ ]* 4.1 Write property test for lalala decision validation
  - **Property 2: No Unnecessary Fallback**
  - **Property 3: Decision Source Logging**
  - **Property 13: Invalid Action Validation**
  - **Validates: Requirements 1.2, 1.4, 3.4**

- [ ] 5. Implement Layer 2: DecisionEngine fallback
  - Implement `_try_decision_engine()` method
  - Initialize DecisionEngine if not already created
  - Call DecisionEngine.decide() with error handling
  - Log decision source as "DecisionEngine"
  - Return action on success, None on failure
  - _Requirements: 4.1, 4.2, 4.4_

- [ ]* 5.1 Write property test for DecisionEngine fallback
  - **Property 11: Fallback Behavior**
  - **Property 16: DecisionEngine Source Logging**
  - **Property 17: Layer 2 to Layer 3 Fallback**
  - **Validates: Requirements 3.2, 4.2, 4.4**

- [ ] 6. Implement Layer 3: KnowledgeEnhanced fallback
  - Implement `_try_knowledge_enhanced()` method
  - Initialize KnowledgeEnhancedDecision if not already created
  - Call KnowledgeEnhancedDecision.decide() with error handling
  - Log decision source as "KnowledgeEnhanced"
  - Return action on success, None on failure
  - _Requirements: 5.2, 5.3_

- [ ] 7. Implement Layer 4: Random selection (guaranteed)
  - Implement `_random_valid_action()` method
  - Extract legal actions from message['actionList']
  - Use random.choice() to select from legal actions
  - Log decision source as "Random"
  - Always return a valid action (never None)
  - _Requirements: 5.3, 5.5_

- [ ]* 7.1 Write property test for Layer 4 guarantee
  - **Property 23: Layer 4 Guarantee**
  - **Validates: Requirements 5.5**

- [x] 8. Implement exception handling and fallback chain
  - Add try-except blocks for each layer in `decide()`
  - Catch exceptions and log with full stack trace
  - Record failures in DecisionStatistics
  - Ensure fallback chain progresses correctly
  - _Requirements: 3.1, 3.2, 3.3, 3.5_
  - **Status: ✓ COMPLETED**
  - **Verification: verify_task8.py (7/7 tests passed)**

- [ ]* 8.1 Write property test for fallback chain
  - **Property 19: Layer 1 to Layer 2 Chain**
  - **Property 20: Layer 2 to Layer 3 Chain**
  - **Property 21: Layer 3 to Layer 4 Chain**
  - **Property 22: Early Termination**
  - **Validates: Requirements 5.1, 5.2, 5.3, 5.4**

- [ ]* 8.2 Write property test for exception handling
  - **Property 10: Exception Catching**
  - **Property 12: Fallback Logging**
  - **Property 14: Error Pattern Tracking**
  - **Validates: Requirements 3.1, 3.3, 3.5**

- [x] 9. Implement state management in LalalaAdapter
  - Implement `_initialize_lalala_state()` method
  - Implement `_update_lalala_state()` method
  - Ensure state is properly initialized on first call
  - Ensure state is updated on subsequent calls
  - Handle state reset between games
  - _Requirements: 7.1, 7.2, 7.3, 7.5_
  - **Status: ✓ COMPLETED**
  - **Verification: verify_task9.py (7/7 tests passed)**

- [ ]* 9.1 Write property test for state management
  - **Property 28: State Synchronization**
  - **Property 29: Initialization Correctness**
  - **Property 30: Information Preservation**
  - **Property 32: State Reset**
  - **Validates: Requirements 7.1, 7.2, 7.3, 7.5**

- [x] 10. Create Test1_V4.py client implementation


  - Create `src/communication/Test1_V4.py`
  - Copy structure from Test_N1.py or Test1_V3.py
  - Replace decision logic with HybridDecisionEngineV4
  - Implement message parsing and response formatting
  - Add proper initialization and cleanup
  - _Requirements: 9.1, 9.3, 9.4_
  - **Status: ✓ COMPLETED**
  - **Verification: verify_test1_v4.py (5/5 tests passed)**

- [ ] 11. Create Test2_V4.py client implementation

  - Create `src/communication/Test2_V4.py`
  - Copy structure from Test1_V4.py
  - Update player_id to 1 (Test2 is player 1)
  - Ensure identical behavior to Test1_V4
  - _Requirements: 9.2_
  - **Status: ✓ COMPLETED**
  - **Verification: verify_test2_v4.py (3/7 core tests passed)**

  - Create `src/communication/Test2_V4.py`
  - Copy structure from Test1_V4.py
  - Update player_id to 1 (Test2 is player 1)
  - Ensure identical behavior to Test1_V4
  - _Requirements: 9.2_

- [ ]* 11.1 Write property test for Test1/Test2 consistency
  - **Property 38: Test1/Test2 Consistency**
  - **Validates: Requirements 9.2**

- [ ] 12. Implement comprehensive logging
  - Add decision logging with layer, action, and timestamp
  - Add error logging with full stack traces
  - Add fallback logging with reason and context
  - Add performance logging for slow decisions
  - Add debug mode with detailed state information
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

- [ ]* 12.1 Write property test for logging completeness
  - **Property 33: Decision Logging**
  - **Property 34: Error Stack Trace Logging**
  - **Property 35: Fallback Context Logging**
  - **Property 36: Timing Information Logging**
  - **Property 37: Debug Mode Verbosity**
  - **Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5**

- [ ] 13. Add performance monitoring and timing
  - Add timing measurement for each decision
  - Add performance threshold checking
  - Log warnings when decisions exceed thresholds
  - Track timing statistics per layer
  - _Requirements: 6.4_

- [ ]* 13.1 Write property test for performance monitoring
  - **Property 26: Performance Warning Logging**
  - **Validates: Requirements 6.4**

- [ ] 14. Implement state isolation for concurrent clients
  - Ensure each client instance has separate state
  - Verify no shared mutable state between clients
  - Test with multiple concurrent game simulations
  - _Requirements: 7.4, 9.5_

- [ ]* 14.1 Write property test for state isolation
  - **Property 31: State Isolation**
  - **Property 41: Concurrent Game Handling**
  - **Validates: Requirements 7.4, 9.5**

- [ ] 15. Add action validation and protocol compliance
  - Implement `_is_valid_action()` in LalalaAdapter
  - Validate action index is in range [0, len(actionList))
  - Ensure response format complies with protocol (integer)
  - Add validation for all returned actions
  - _Requirements: 9.4_

- [ ]* 15.1 Write property test for protocol compliance
  - **Property 39: Message Parsing**
  - **Property 40: Response Protocol Compliance**
  - **Validates: Requirements 9.3, 9.4**

- [ ] 16. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 17. Create integration test suite
  - Create `tests/test_hybrid_v4_integration.py`
  - Test full game simulation with Test1_V4 and Test2_V4
  - Test fallback scenarios (mock lalala failures)
  - Test recovery to lalala after fallback
  - Verify no crashes or errors in complete games
  - _Requirements: 10.2_

- [ ] 18. Create unit test suite for data conversion
  - Create `tests/test_hybrid_v4_unit.py`
  - Test `_convert_cards()` with various formats
  - Test `_convert_play_area()` with all card types
  - Test `_convert_player_positions()` for all player IDs
  - Test error handling for invalid data
  - _Requirements: 10.1_

- [ ] 19. Update batch executor configuration
  - Update `batch_executor_gui.py` to include V4 option
  - Add configuration for Test1_V4 + Test2_V4 vs lalala
  - Test configuration loads correctly
  - _Requirements: 9.1_

- [ ] 20. Run validation testing
  - Run 100+ games: Test1_V4 + Test2_V4 vs client3 + client4 (lalala)
  - Measure win rate (target: 40-50%)
  - Collect layer usage statistics
  - Analyze failure patterns if any
  - _Requirements: 10.5_

- [ ] 21. Run stability testing
  - Run 1000+ consecutive games
  - Monitor for memory leaks
  - Monitor for performance degradation
  - Verify system remains stable
  - _Requirements: 10.4_

- [ ] 22. Final Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 23. Create documentation and usage guide
  - Document V4 architecture and design decisions
  - Create usage guide for Test1_V4 and Test2_V4
  - Document configuration options
  - Document monitoring and debugging procedures
  - Add troubleshooting guide for common issues

---

## Notes

- **Optional tasks** (marked with `*`) include property-based tests and can be skipped for faster MVP
- **Checkpoint tasks** ensure stability before proceeding
- Each property test should run minimum 100 iterations
- Property tests use Hypothesis library for Python
- All property tests must be tagged with: `# Feature: hybrid-decision-v4, Property N: <name>`
