function state = update_electrolyzer_system_state( ...
    state, physics, params, timeline, t)
%UPDATE_ELECTROLYZER_SYSTEM_STATE
% Optimized supervisory state update
% Parameter names aligned exactly with CSV controller cases
%
% All logic is scalar, enum-based, allocation-free.

% =====================================================================
% ENUM DEFINITIONS
% =====================================================================
MODE_OFF = uint8(0);
MODE_ON  = uint8(1);

REG_NORMAL   = uint8(0);
REG_TURNDOWN = uint8(1);

CONSTRAINT_NONE     = uint8(0);
CONSTRAINT_MIN_UP   = uint8(1);  % min_up_steps
CONSTRAINT_MIN_DOWN = uint8(2);  % min_down_steps

% =====================================================================
% Extract signals
% =====================================================================
dt_hr       = timeline.dt_hr;
price       = timeline.price(t);
clean_ratio = timeline.clean_ratio(t);

is_on = (state.mode == MODE_ON);

% =====================================================================
% Safety invariant
% =====================================================================
assert(~(state.on_constraint_active && state.off_constraint_active), ...
    'Invalid state: ON and OFF constraints simultaneously active.');

% =====================================================================
% Countdown active constraints
% =====================================================================
if state.on_constraint_active
    state.on_constraint_steps_remaining = ...
        state.on_constraint_steps_remaining - 1;

    if state.on_constraint_steps_remaining == 0
        state.on_constraint_active = false;
        state.on_constraint_type   = CONSTRAINT_NONE;
    end
end

if state.off_constraint_active
    state.off_constraint_steps_remaining = ...
        state.off_constraint_steps_remaining - 1;

    if state.off_constraint_steps_remaining == 0
        state.off_constraint_active = false;
        state.off_constraint_type   = CONSTRAINT_NONE;
    end
end

% =====================================================================
% Price-stop persistence (price_delay)
% =====================================================================
if price > params.price_stop
    state.price_violation_counter = ...
        state.price_violation_counter + 1;
else
    state.price_violation_counter = uint32(0);
end

price_allowed = ...
    state.price_violation_counter < params.price_delay;

% =====================================================================
% Hard eligibility logic
% =====================================================================
can_start = ...
    clean_ratio >= params.clean_ratio_start && ...
    price       <= params.price_start;

can_continue = ...
    clean_ratio >= params.clean_ratio_stop && ...
    price_allowed;

% =====================================================================
% Soft regime condition evaluation
% =====================================================================
bad_conditions = ...
    clean_ratio < params.clean_ratio_turndown || ...
    price       > params.price_turndown;

good_conditions = ...
    clean_ratio >= params.clean_ratio_start && ...
    price       <= params.price_start;

% =====================================================================
% ========================== ON STATE ===========================
% =====================================================================
if is_on

    state.runtime_steps = state.runtime_steps + 1;
    state.offtime_steps = uint32(0);

    % --- Regime persistence (anti‑chatter) ---
    if bad_conditions
        state.turndown_counter = state.turndown_counter + 1;
        state.recover_counter  = uint32(0);
    else
        state.turndown_counter = uint32(0);
    end

    if good_conditions
        state.recover_counter = state.recover_counter + 1;
    else
        state.recover_counter = uint32(0);
    end

    % --- Regime transitions ---
    if state.operating_regime == REG_NORMAL && ...
       state.turndown_counter >= params.turndown_delay
        state.operating_regime = REG_TURNDOWN;
        state.turndown_counter = uint32(0);
    end

    if state.operating_regime == REG_TURNDOWN && ...
       state.recover_counter >= params.recover_delay
        state.operating_regime = REG_NORMAL;
        state.recover_counter  = uint32(0);
    end

    % --- Accounting ---
    state.h2_produced_kg = ...
        state.h2_produced_kg + physics.mH2_net_kgph * dt_hr;

    state.energy_grid_kWh = ...
        state.energy_grid_kWh + physics.P_grid_total_kW * dt_hr;

    % --- Shutdown logic ---
    if ~state.on_constraint_active && ~can_continue

        state.mode             = MODE_OFF;
        state.is_operating     = false;
        state.operating_regime = REG_NORMAL;
        state.shutdowns        = state.shutdowns + 1;
        state.runtime_steps    = uint32(0);

        % Reset persistence counters
        state.turndown_counter        = uint32(0);
        state.recover_counter         = uint32(0);
        state.price_violation_counter = uint32(0);

        % Enforce minimum downtime
        if params.min_down_steps > 0
            state.off_constraint_active          = true;
            state.off_constraint_type            = CONSTRAINT_MIN_DOWN;
            state.off_constraint_steps_remaining = params.min_down_steps;
        end
    end

% =====================================================================
% ========================== OFF STATE ==========================
% =====================================================================
else

    state.offtime_steps = state.offtime_steps + 1;
    state.runtime_steps = uint32(0);

    state.operating_regime        = REG_NORMAL;
    state.turndown_counter        = uint32(0);
    state.recover_counter         = uint32(0);
    state.price_violation_counter = uint32(0);

    if can_start && ~state.off_constraint_active

        state.mode         = MODE_ON;
        state.is_operating = true;
        state.startups     = state.startups + 1;

        % Enforce minimum runtime
        if params.min_up_steps > 0
            state.on_constraint_active          = true;
            state.on_constraint_type            = CONSTRAINT_MIN_UP;
            state.on_constraint_steps_remaining = params.min_up_steps;
        end
    end
end

end
