function state = update_electrolyzer_system_state( ...
    state, current_case, stack, signals, jj, use_discrete_dispatch)
% ================= ENUMS =================
MODE_OFF = uint8(0);
MODE_ON  = uint8(1);
REG_NORMAL   = uint8(0);
REG_TURNDOWN = uint8(1);
% ================= SIGNALS =================
price       = signals.price(jj);
clean_ratio = signals.clean_ratio(jj);
% ================= PRICE DELAY =================
if price > current_case.price_stop
    state.price_violation_counter = state.price_violation_counter + 1;
else
    state.price_violation_counter = uint32(0);
end
% FIX: when price_delay == 0 the threshold is ">=0" which uint32 always
%      satisfies, so price_allowed is permanently false even when the
%      price is fine.  Handle the zero-delay case explicitly.
if current_case.price_delay == 0
    price_allowed = price <= current_case.price_stop;
else
    price_allowed = state.price_violation_counter < current_case.price_delay;
end
% ================= CONDITIONS =================
can_start = ...
    clean_ratio >= current_case.clean_ratio_start && ...
    price       <= current_case.price_start;
stop_conditions = ...
    clean_ratio < current_case.clean_ratio_stop || ...
    ~price_allowed;
bad_conditions = ...
    clean_ratio < current_case.clean_ratio_turndown || ...
    price       > current_case.price_turndown;
good_conditions = ...
    clean_ratio >= current_case.clean_ratio_start && ...
    price       <= current_case.price_start;
% ================= STATE TRANSITIONS =================
if state.mode == MODE_ON
    state.runtime_steps = state.runtime_steps + 1;
    state.offtime_steps = uint32(0);

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

    % FIX: guard with > 0 so that when turndown_delay == 0 the transition
    %      only fires when bad_conditions was actually present (counter
    %      incremented), not on every step where counter >= 0 is vacuous.
    if state.operating_regime == REG_NORMAL && ...
           state.turndown_counter > 0 && ...
           state.turndown_counter >= current_case.turndown_delay
        state.operating_regime = REG_TURNDOWN;
    end

    % FIX: same guard for recover_delay == 0.
    if state.operating_regime == REG_TURNDOWN && ...
           state.recover_counter > 0 && ...
           state.recover_counter >= current_case.recover_delay
        state.operating_regime = REG_NORMAL;
    end

    if state.operating_regime == REG_TURNDOWN && ...
           state.runtime_steps >= current_case.min_up_steps && ...
           stop_conditions
        state.mode             = MODE_OFF;
        state.operating_regime = REG_NORMAL;
        state.is_operating     = false;
        state.shutdowns        = state.shutdowns + 1;
        state.runtime_steps    = uint32(0);
        state.turndown_counter = uint32(0);
        state.recover_counter  = uint32(0);
    end

else
    % ------------ OFF STATE ------------
    state.offtime_steps = state.offtime_steps + 1;
    state.runtime_steps = uint32(0);
    state.operating_regime = REG_NORMAL;
    state.turndown_counter = uint32(0);
    state.recover_counter  = uint32(0);
    state.price_violation_counter = uint32(0);

    % min_down_steps == 0 is safe as-is: offtime_steps is incremented
    % before the check so it is always >= 1, making >= 0 unconditionally
    % true (no minimum hold-off), which is the correct intent.
    if state.offtime_steps >= current_case.min_down_steps && can_start
        state.mode         = MODE_ON;
        state.is_operating = true;
        state.startups     = state.startups + 1;
    end
end
% ================= POWER COMMAND (FINAL & AUTHORITATIVE) =================
state.P_stack_cmd_kW = 0.0;   % ← DEFAULT TO ZERO
if state.mode == MODE_ON
    if state.operating_regime == REG_NORMAL
        state.P_stack_cmd_kW = stack.P_max_kW;
    elseif state.operating_regime == REG_TURNDOWN
        if use_discrete_dispatch
            state.P_stack_cmd_kW = stack.P_min_kW;
        else
            frac = (clean_ratio - current_case.clean_ratio_stop) / ...
                   (current_case.clean_ratio_start - current_case.clean_ratio_stop);
            frac = min(max(frac, 0), 1);
            state.P_stack_cmd_kW = ...
                stack.P_min_kW + frac * ...
                (stack.P_max_kW - stack.P_min_kW);
        end
    end
end
% ================= HARD ASSERT =================
assert(~(state.mode == MODE_OFF && state.P_stack_cmd_kW > 0), ...
    'CRITICAL: OFF mode with non-zero power at timestep %d', jj);
end



%%

% function state = update_electrolyzer_system_state( ...
%     state, current_case, stack, signals, jj, use_discrete_dispatch)
% 
% % ================= ENUMS =================
% MODE_OFF = uint8(0);
% MODE_ON  = uint8(1);
% 
% REG_NORMAL   = uint8(0);
% REG_TURNDOWN = uint8(1);
% 
% % ================= SIGNALS =================
% price       = signals.price(jj);
% clean_ratio = signals.clean_ratio(jj);
% 
% % ================= PRICE DELAY =================
% if price > current_case.price_stop
%     state.price_violation_counter = state.price_violation_counter + 1;
% else
%     state.price_violation_counter = uint32(0);
% end
% 
% price_allowed = ...
%     state.price_violation_counter < current_case.price_delay;
% 
% % ================= CONDITIONS =================
% can_start = ...
%     clean_ratio >= current_case.clean_ratio_start && ...
%     price       <= current_case.price_start;
% 
% stop_conditions = ...
%     clean_ratio < current_case.clean_ratio_stop || ...
%     ~price_allowed;
% 
% bad_conditions = ...
%     clean_ratio < current_case.clean_ratio_turndown || ...
%     price       > current_case.price_turndown;
% 
% good_conditions = ...
%     clean_ratio >= current_case.clean_ratio_start && ...
%     price       <= current_case.price_start;
% 
% % ================= STATE TRANSITIONS =================
% if state.mode == MODE_ON
% 
%     state.runtime_steps = state.runtime_steps + 1;
%     state.offtime_steps = uint32(0);
% 
%     if bad_conditions
%         state.turndown_counter = state.turndown_counter + 1;
%         state.recover_counter  = uint32(0);
%     else
%         state.turndown_counter = uint32(0);
%     end
% 
%     if good_conditions
%         state.recover_counter = state.recover_counter + 1;
%     else
%         state.recover_counter = uint32(0);
%     end
% 
%     if state.operating_regime == REG_NORMAL && ...
%        state.turndown_counter >= current_case.turndown_delay
%         state.operating_regime = REG_TURNDOWN;
%     end
% 
%     if state.operating_regime == REG_TURNDOWN && ...
%        state.recover_counter >= current_case.recover_delay
%         state.operating_regime = REG_NORMAL;
%     end
% 
%     if state.operating_regime == REG_TURNDOWN && ...
%        state.runtime_steps >= current_case.min_up_steps && ...
%        stop_conditions
% 
%         state.mode             = MODE_OFF;
%         state.operating_regime = REG_NORMAL;
%         state.is_operating     = false;
%         state.shutdowns        = state.shutdowns + 1;
% 
%         state.runtime_steps    = uint32(0);
%         state.turndown_counter = uint32(0);
%         state.recover_counter  = uint32(0);
%     end
% 
% else
%     % ------------ OFF STATE ------------
%     state.offtime_steps = state.offtime_steps + 1;
%     state.runtime_steps = uint32(0);
% 
%     state.operating_regime = REG_NORMAL;
%     state.turndown_counter = uint32(0);
%     state.recover_counter  = uint32(0);
%     state.price_violation_counter = uint32(0);
% 
%     if state.offtime_steps >= current_case.min_down_steps && can_start
%         state.mode         = MODE_ON;
%         state.is_operating = true;
%         state.startups     = state.startups + 1;
%     end
% end
% 
% % ================= POWER COMMAND (FINAL & AUTHORITATIVE) =================
% state.P_stack_cmd_kW = 0.0;   % ← DEFAULT TO ZERO
% 
% if state.mode == MODE_ON
%     if state.operating_regime == REG_NORMAL
%         state.P_stack_cmd_kW = stack.P_max_kW;
% 
%     elseif state.operating_regime == REG_TURNDOWN
%         if use_discrete_dispatch
%             state.P_stack_cmd_kW = stack.P_min_kW;
%         else
%             frac = (clean_ratio - current_case.clean_ratio_stop) / ...
%                    (current_case.clean_ratio_start - current_case.clean_ratio_stop);
%             frac = min(max(frac, 0), 1);
%             state.P_stack_cmd_kW = ...
%                 stack.P_min_kW + frac * ...
%                 (stack.P_max_kW - stack.P_min_kW);
%         end
%     end
% end
% 
% % ================= HARD ASSERT =================
% assert(~(state.mode == MODE_OFF && state.P_stack_cmd_kW > 0), ...
%     'CRITICAL: OFF mode with non-zero power at timestep %d', jj);
% 
% end