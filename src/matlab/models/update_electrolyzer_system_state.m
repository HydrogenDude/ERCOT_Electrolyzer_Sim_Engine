function state = update_electrolyzer_system_state( ...
    state, current_case, stack, signals, jj)
%UPDATE_ELECTROLYZER_SYSTEM_STATE
% Supervisory control + stack power command
% NO PHYSICS. NO ACCOUNTING.

% =====================================================================
% ENUMS
% =====================================================================
MODE_OFF = uint8(0);
MODE_ON  = uint8(1);

REG_NORMAL   = uint8(0);
REG_TURNDOWN = uint8(1);

% =====================================================================
% Signals
% =====================================================================
price       = signals.price(jj);
clean_ratio = signals.clean_ratio(jj);

% =====================================================================
% Eligibility logic
% =====================================================================
can_start = ...
    clean_ratio >= current_case.clean_ratio_start && ...
    price       <= current_case.price_start;

can_continue = ...
    clean_ratio >= current_case.clean_ratio_stop && ...
    price       <= current_case.price_stop;

% =====================================================================
% State transitions
% =====================================================================
if state.mode == MODE_ON
    state.runtime_steps = state.runtime_steps + 1;

    if ~can_continue
        state.mode             = MODE_OFF;
        state.operating_regime = REG_NORMAL;
        state.is_operating     = false;
        state.shutdowns        = state.shutdowns + 1;
    end
else
    state.offtime_steps = state.offtime_steps + 1;

    if can_start
        state.mode         = MODE_ON;
        state.is_operating = true;
        state.startups     = state.startups + 1;
    end
end

% =====================================================================
% STACK POWER DECISION (THIS IS THE KEY PART)
% =====================================================================
if state.mode == MODE_OFF
    state.P_stack_cmd_kW = 0.0;
    state.operating_regime = REG_NORMAL;
    return
end

% --- Full power region ---
if clean_ratio >= current_case.clean_ratio_start && ...
   price       <= current_case.price_start

    state.operating_regime = REG_NORMAL;
    state.P_stack_cmd_kW   = stack.P_max_kW;
    return
end

% --- Turndown region ---
if clean_ratio >= current_case.clean_ratio_turndown && ...
   price       <= current_case.price_turndown

    state.operating_regime = REG_TURNDOWN;

    % Linear interpolation between max and min power
    frac = (clean_ratio - current_case.clean_ratio_stop) / ...
           (current_case.clean_ratio_start - current_case.clean_ratio_stop);

    frac = min(max(frac, 0), 1);

    state.P_stack_cmd_kW = ...
        stack.P_min_kW + frac * ...
        (stack.P_max_kW - stack.P_min_kW);

    return
end

% --- Otherwise: shut down ---
state.mode             = MODE_OFF;
state.operating_regime = REG_NORMAL;
state.P_stack_cmd_kW   = 0.0;
state.is_operating     = false;
state.shutdowns        = state.shutdowns + 1;

end