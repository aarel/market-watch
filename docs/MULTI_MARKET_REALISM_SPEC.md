# Market-Watch Multi-Market Trading Realism & Regulatory Modeling
## Full Production Design Specification

<a id="top"></a>

**Navigation**  
[TOC](#table-of-contents) | [Architecture](#i-core-architecture-overview) | [Execution](#ii-executionmodel-design) | [High-ROI Upgrades](#iii-high-roi-realism-upgrades) | [Domain Model](#iv-domain-model-additions) | [Costs](#v-cost-model-design) | [Tax](#vi-tax-model-design) | [Margin](#vii-margin-model) | [PDT](#viii-pdt-compliance-model-us) | [International](#ix-international-support) | [Permissions](#x-permission-engine) | [Performance](#xi-performance-engine) | [Accuracy Tiers](#xii-accuracy-tier-framework) | [Simulation vs Reality](#xiii-simulation-vs-reality-disclaimer) | [Config](#xiv-configuration-structure) | [Data](#xv-data-migration) | [Testing](#xvi-testing-strategy) | [Phases](#xvii-phased-implementation) | [Risks](#xviii-risk--limitations) | [Non-Goals](#xix-explicit-non-goals) | [API Contract](#xx-output--reporting-contract) | [Acceptance](#xxi-acceptance-criteria) | [ROI Table](#xxii-roi-classification-table) | [Diff Summary](#xxiii-diff-summary)

## Table of Contents
1. [I. Core Architecture Overview](#i-core-architecture-overview)
2. [II. ExecutionModel Design](#ii-executionmodel-design)
3. [III. High-ROI Realism Upgrades](#iii-high-roi-realism-upgrades)
4. [IV. Domain Model Additions](#iv-domain-model-additions)
5. [V. Cost Model Design](#v-cost-model-design)
6. [VI. Tax Model Design](#vi-tax-model-design)
7. [VII. Margin Model](#vii-margin-model)
8. [VIII. PDT Compliance Model (US)](#viii-pdt-compliance-model-us)
9. [IX. International Support](#ix-international-support)
10. [X. Permission Engine](#x-permission-engine)
11. [XI. Performance Engine](#xi-performance-engine)
12. [XII. Accuracy Tier Framework](#xii-accuracy-tier-framework)
13. [XIII. Simulation vs Reality Disclaimer](#xiii-simulation-vs-reality-disclaimer)
14. [XIV. Configuration Structure](#xiv-configuration-structure)
15. [XV. Data Migration](#xv-data-migration)
16. [XVI. Testing Strategy](#xvi-testing-strategy)
17. [XVII. Phased Implementation](#xvii-phased-implementation)
18. [XVIII. Risk & Limitations](#xviii-risk--limitations)
19. [XIX. Explicit Non-Goals](#xix-explicit-non-goals)
20. [XX. Output & Reporting Contract](#xx-output--reporting-contract)
21. [XXI. Acceptance Criteria](#xxi-acceptance-criteria)
22. [XXII. ROI Classification Table](#xxii-roi-classification-table)
23. [XXIII. Diff Summary](#xxiii-diff-summary)

## I. Core Architecture Overview
Bounded contexts:
1. MarketModel
2. SessionModel
3. AccountModel
4. ExecutionModel
5. CostModel
6. CostBasisEngine
7. CorporateActionModel
8. SettlementEngine
9. TaxModel
10. MarginModel
11. ComplianceModel
12. CurrencyModel
13. PerformanceEngine
14. LedgerModel

Execution flow:
```text
TradeRequest
  -> TradePermissionEngine.validate()
  -> PreTradeCompliance.validate()
  -> ExecutionModel.prepare()
  -> Broker.execute() or FillSimulator.execute()
  -> CostModel.apply()
  -> SettlementEngine.apply_trade_settlement_effects()
  -> CostBasisEngine.update_lots()
  -> CorporateActionModel.apply_pending_adjustments()
  -> CurrencyModel.apply_fx()
  -> PerformanceEngine.update()
  -> TaxModel.evaluate_estimate()
  -> MarginModel.update()
  -> PostTradeCompliance.update()
  -> AccountState.persist()
  -> LedgerModel.record()
```

Dependency boundaries:
- TaxModel consumes realized gains from CostBasisEngine.
- ComplianceModel consumes settlement availability from SettlementEngine.
- PerformanceEngine consumes corporate action adjustment outputs.
- Broker integration remains isolated from modeling engines.

[Back to Top](#top)

## II. ExecutionModel Design
ExecutionModel responsibilities:
- order type handling: market, limit, stop, stop-limit
- fill model abstraction
- liquidity buckets
- partial fill simulation
- queue-position assumption handling
- volatility regime adjustments
- session-dependent fill behavior

Core interfaces:
- `ExecutionModel.route(order, context)`
- `FillSimulator.simulate(order, market_state, execution_policy)`

Execution modes:
- deterministic mode: fixed rules and reproducible outcomes
- stochastic mode: seeded randomness for scenario testing

Operation profiles:
- backtest mode: synthetic fills with explicit assumptions
- live-reporting mode: broker fill ingestion and reconciliation

Scope boundary:
- no venue-level depth simulation
- no hidden-liquidity inference

[Back to Top](#top)

## III. High-ROI Realism Upgrades
### Tier A (Implement Now)
1. CorporateActionModel
2. CostBasisEngine
3. SettlementEngine

### Tier B (Implement After Core)
1. Enhanced MarginModel (risk-based)
2. FX timing refinement

### Tier C (Exclude)
1. L2 order book simulation
2. Auction microstructure simulation
3. Maker/taker rebate optimization
4. Hidden liquidity modeling
5. Capital control regime modeling
6. Full international tax treaty engine

Selection criteria:
- impact on long-horizon backtest drift
- impact on regulatory realism
- impact on user-facing performance accuracy
- architectural cost and maintainability

[Back to Top](#top)

## IV. Domain Model Additions
### 1. AccountProfile
- account_id
- jurisdiction
- account_type (`cash|margin`)
- equity
- margin_enabled
- pdt_flag
- international_enabled
- base_currency
- tax_profile_id

### 2. MarketProfile
- market_code
- timezone
- trading_hours
- extended_hours
- settlement_cycle
- transaction_tax_rate
- stamp_duty_rate
- supports_margin
- currency

### 3. SessionType
- PRE_MARKET
- REGULAR
- AFTER_HOURS
- INTERNATIONAL_REGULAR
- AUCTION_OPEN
- AUCTION_CLOSE

### 4. CorporateActionEvent
- action_id
- symbol
- action_type (`split|reverse_split|special_dividend|spin_off|symbol_change|merger`)
- effective_date
- adjustment_factor
- cash_component
- metadata

### 5. Extended TradeRecord
- gross_pnl
- transaction_cost
- net_pnl
- fx_pnl
- tax_estimate
- after_tax_pnl
- session_type
- market_code
- holding_period_days
- cost_breakdown (JSON)
- compliance_flags
- fill_mode (`simulated|broker_reported`)
- settlement_status

[Back to Top](#top)

## V. Cost Model Design
Cost components:
- CommissionCost
- SpreadCost
- SlippageCost
- RegulatoryFeeCost
- StampDutyCost
- FXSpreadCost
- MarginInterestCost

Schedules:
- BrokerFeeSchedule
- ProductFeeSchedule

Interface:
`CostModel.total(trade, account, market, session, execution_details)`

Realism rules:
- separate theoretical slippage multipliers from execution-derived slippage
- apply order-type slippage behavior
- apply open/close and extended-hours liquidity modifiers
- deterministic rounding and configuration-driven defaults

[Back to Top](#top)

## VI. Tax Model Design
Scope: US-centric estimated tax modeling with extensible jurisdiction adapters.

Inputs:
- realized lot gains from CostBasisEngine
- holding periods
- jurisdiction and tax profile
- dividend qualification flags
- ADR flags

Lot-accounting strategies:
- FIFO
- LIFO
- Specific ID

Planned extensions:
- wash-sale modeling (future)
- foreign tax credit placeholder

Interface:
`TaxModel.calculate(realized_lot_events, jurisdiction, tax_profile, lot_strategy)`

Required disclaimer:
- estimated tax only
- not tax advice
- no replacement for broker/tax statements

[Back to Top](#top)

## VII. Margin Model
### Tier B Upgrade Scope
- intraday vs overnight margin recalculation
- volatility-adjusted maintenance margin
- broker-specific margin tiers
- dynamic margin requirement changes
- margin stress threshold logic

Excluded in this plan:
- portfolio margin VAR modeling

Simulation-only escalation workflow:
1. warning threshold
2. opening-trade restrictions
3. forced liquidation simulation

[Back to Top](#top)

## VIII. PDT Compliance Model (US)
Tracked dimensions:
- rolling 5-business-day window
- day trade classification assumptions
- equity threshold and timing snapshot
- margin-account applicability

Rule baseline:
- day trades >= 4 in rolling 5-business-day window and equity < 25,000 triggers restriction

ComplianceModel dependencies:
- SettlementEngine for unsettled-funds aware restrictions in cash accounts
- MarketCalendar for business-day window calculations

Limitation note:
- broker-specific PDT classification can differ; model remains configurable

[Back to Top](#top)

## IX. International Support
International realism scope:
- market transaction taxes
- stamp duties
- settlement cycle differences
- FX conversion and FX PnL
- ADR vs local listing distinctions
- local custody fee placeholder

MarketCalendar abstraction:
- holidays
- half days
- auction sessions
- settlement business-day calendars

FX timing modes (Tier B):
- trade-date conversion
- settlement-date conversion
- deterministic fallback rate source

[Back to Top](#top)

## X. Permission Engine
Pre-execution check:
`TradePermissionEngine.validate(trade, account, market, session)`

Checks:
- market/session enabled
- PDT restrictions
- margin eligibility
- unsettled-funds restrictions (cash accounts via SettlementEngine)
- international entitlement
- product/order-type permissioning

Hard rule:
- no execution when validation fails

[Back to Top](#top)

## XI. Performance Engine
PerformanceEngine aggregates:
- gross return
- net return pre-tax
- after-tax estimated return
- cost drag
- tax drag
- FX impact
- margin interest impact
- execution-quality impact
- corporate action adjustment impact

Required integration:
- consume split/symbol/dividend adjustments from CorporateActionModel
- consume realized gain events from CostBasisEngine
- account for settlement timing effects in availability-driven trade opportunities

[Back to Top](#top)

## XII. Accuracy Tier Framework
### Tier 1 - Retail Simulation
- multiplier-based slippage
- static margin
- estimated taxes
- basic session effects

### Tier 2 - Advanced Simulation
- FillSimulator with partial fills
- dynamic margin
- lot accounting (CostBasisEngine)
- settlement-aware availability
- FX timing modes

### Tier 3 - Broker-Grade Replay
- broker fill ingestion
- broker fee ingestion
- no synthetic slippage in replay
- external authoritative tax reporting

[Back to Top](#top)

## XIII. Simulation vs Reality Disclaimer
Accuracy domains:
- simulation realism: model-based approximations
- broker execution realism: observed broker fills and fees
- tax estimation realism: non-authoritative estimates

Output labels:
- `simulated`
- `broker_reported`
- `estimated_tax`

This system is not a substitute for broker confirmations, clearing records, or tax filings.

[Back to Top](#top)

## XIV. Configuration Structure
`config/performance.yaml` sections:
- cost_defaults
- broker_fee_schedules
- product_fee_schedules
- tax_profiles
- tax_lot_defaults
- market_profiles
- market_calendars
- margin_defaults
- settlement_defaults
- corporate_action_defaults
- compliance_rules
- execution_defaults
- accuracy_tier
- rounding_policy
- feature_flags

[Back to Top](#top)

## XV. Data Migration
Spec-level schema impact:
- extend TradeRecord
- add AccountProfile
- add MarketProfile
- add TaxProfile
- add ComplianceEvent
- add LedgerEntry
- add CorporateActionEvent
- add LotLedger / CostBasis lots
- add SettlementLedger

Compatibility:
- preserve legacy gross-only reporting
- default missing legacy friction fields to zero/null

[Back to Top](#top)

## XVI. Testing Strategy
Unit tests:
- CorporateActionModel split/dividend/symbol-change adjustments
- CostBasisEngine lot selection and realized gains
- SettlementEngine cycle handling and cash-availability gating
- FillSimulator deterministic and seeded stochastic behavior
- PDT business-day window + unsettled-funds interactions

Integration tests:
- long-horizon backtest with corporate actions
- cash-account trade blocking on unsettled proceeds
- tax estimate pipeline using lot-level realized gains
- international settlement + FX timing scenarios

Performance tests:
- deterministic replay consistency under Tier 2
- drift reduction benchmark vs baseline

[Back to Top](#top)

## XVII. Phased Implementation
Phase 1 - Structural Accuracy Layer:
1. CorporateActionModel
2. CostBasisEngine
3. SettlementEngine

Phase 2 - Enhanced Financial Realism:
4. Enhanced MarginModel (risk-based, no VAR)
5. FX timing refinement

Phase 3 - Advanced Tax Extensions:
6. wash-sale modeling (extension)
7. dividend qualification tracking
8. foreign tax credit placeholder

Phase 4 - Broker-Grade Replay Hardening:
9. broker fill ingestion hardening
10. broker fee ingestion hardening
11. reconciliation-only realism mode

[Back to Top](#top)

## XVIII. Risk & Limitations
Primary risks:
- incorrect corporate action ingestion can distort long-horizon PnL
- lot-selection bugs can distort tax estimates
- settlement mis-modeling can cause unrealistic trade permissions
- broker interpretation differences can affect PDT parity
- FX timing policy mismatch can distort cross-market comparisons

Limitations:
- no L2 depth realism
- no hidden liquidity realism
- no institutional capital-control modeling
- no full treaty-grade international tax engine

Mitigations:
- deterministic defaults
- explicit source tagging and audit logs
- tiered rollout and replay checks

[Back to Top](#top)

## XIX. Explicit Non-Goals
Excluded from current scope:
- maker/taker rebate optimization
- L2 order book simulation
- hidden liquidity modeling
- auction microstructure overbuild
- capital controls modeling
- full international tax treaty compliance engine
- portfolio margin VAR engine

[Back to Top](#top)

## XX. Output & Reporting Contract
Expose metrics:
- gross_pnl
- net_pnl
- after_tax_pnl_estimated
- cost_drag_pct
- tax_drag_pct_estimated
- fx_impact_pct
- margin_interest_total
- settlement_block_count
- corporate_action_adjustment_impact
- fill_mode
- execution_realism_tier

Contract requirements:
- preserve existing gross fields
- version all added realism fields
- no silent endpoint breakage

[Back to Top](#top)

## XXI. Acceptance Criteria
Revision complete when:
- CorporateActionModel is defined
- CostBasisEngine is defined
- SettlementEngine is defined
- TaxModel depends on CostBasisEngine outputs
- ComplianceModel references SettlementEngine for funds availability
- PerformanceEngine references corporate action adjustments
- phased roadmap updated with logical progression
- Tier C exclusions explicitly listed
- Accuracy Tier framework preserved
- no prior bounded context removed

[Back to Top](#top)

## XXII. ROI Classification Table
| Upgrade | Tier | Realism Impact | Architectural Cost | Decision |
|---|---|---|---|---|
| CorporateActionModel | A | High (major long-horizon drift reduction) | Medium | Implement now |
| CostBasisEngine (lot accounting) | A | High (tax and realized PnL accuracy) | Medium | Implement now |
| SettlementEngine | A | High (cash-account regulatory realism) | Medium | Implement now |
| Enhanced MarginModel (risk-based) | B | Medium-High (risk realism) | Medium-High | Implement after core |
| FX timing refinement | B | Medium (cross-market comparability) | Medium | Implement after core |
| L2 order book simulation | C | Low-Medium (for target use case) | High | Exclude |
| Auction microstructure simulation | C | Low-Medium | High | Exclude |
| Maker/taker rebate optimization | C | Low | Medium | Exclude |
| Hidden liquidity modeling | C | Low-Medium | High | Exclude |
| Capital control regimes | C | Low (current scope) | High | Exclude |
| Full international tax treaty engine | C | Medium | Very High | Exclude |

[Back to Top](#top)

## XXIII. Diff Summary
### Sections Added
- III. High-ROI Realism Upgrades
- XIX. Explicit Non-Goals
- XXII. ROI Classification Table

### Sections Modified
- I. Core Architecture Overview
- IV. Domain Model Additions
- VI. Tax Model Design
- VIII. PDT Compliance Model (US)
- IX. International Support
- X. Permission Engine
- XI. Performance Engine
- XVII. Phased Implementation
- XVIII. Risk & Limitations

### Roadmap Changes
- Phase order revised to prioritize structural accuracy first:
  - Phase 1: CorporateActionModel, CostBasisEngine, SettlementEngine
  - Phase 2: Enhanced MarginModel, FX timing refinement
  - Phase 3: Advanced tax extensions
  - Phase 4: Broker-grade replay hardening

[Back to Top](#top)
