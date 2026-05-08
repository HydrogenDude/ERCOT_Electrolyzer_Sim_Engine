LOGIC RULES FOR ELECTROLYZER SUPERVISORY CONTROL DOE

--------------------------------------------------
CLEAN RATIO HYSTERESIS
--------------------------------------------------

clean_ratio_start > clean_ratio_turndown > clean_ratio_stop >= 0

Definitions:
- clean_ratio_start: threshold at which operation is fully enabled
- clean_ratio_turndown: intermediate threshold for reduced operation
- clean_ratio_stop: threshold at which operation stops

Structural requirements:
- clean_ratio_start and clean_ratio_stop are generated first
- clean_ratio_turndown is generated strictly between start and stop
- All clean ratio values must be non-negative
- Ordering must be enforced per ID (row-wise)


--------------------------------------------------
PRICE HYSTERESIS
--------------------------------------------------

price_start < price_turndown < price_stop

Definitions:
- price_start: price threshold to start/resume operation
- price_turndown: intermediate price for reduced operation
- price_stop: price threshold to stop operation

Structural requirements:
- price_start and price_stop are generated first
- price_turndown is generated strictly between start and stop
- price_stop must be sufficiently greater than price_start to allow an interior value
- Ordering must be enforced per ID (row-wise)


--------------------------------------------------
DELAY PARAMETERS
--------------------------------------------------

0 <= turndown_delay <= turndown_delay_max
0 <= recover_delay <= recover_delay_max
0 <= price_delay <= price_delay_max

Definitions:
- Delays are non-negative discrete (integer) values
- Upper bounds are configuration-defined limits
- Equality at both bounds is permitted


--------------------------------------------------
MINIMUM UP / DOWN STEP CONSTRAINTS
--------------------------------------------------

0 <= min_up_steps <= min_up_steps_max
0 <= min_down_steps <= min_down_steps_max

Definitions:
- Minimum up and down steps are non-negative integers
- Zero indicates no minimum enforcement
- Upper bounds are configuration-defined limits


--------------------------------------------------
GLOBAL DESIGN INVARIANTS
--------------------------------------------------

- All ordering relationships apply per ID (row-wise)
- Parameters involved in ordering relationships must be generated together
- (start, turndown, stop) triples must never be split or independently permuted
- Independent parameters may be decorrelated only after valid triples are formed