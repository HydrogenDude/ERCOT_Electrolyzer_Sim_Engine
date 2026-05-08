function state = initialize_electrolyzer_system_state()
%INITIALIZE_ELECTROLYZER_SYSTEM_STATE
% Optimized supervisory state initializer for electrolyzer system
%
% Design principles:
%   - Numeric enums instead of strings (performance)
%   - No dynamic field creation after initialization
%   - Scalar-only persistent state
%   - Parameter names aligned with CSV controller cases
%
% Enum encodings:
%
%   mode:
%       0 = OFF
%       1 = ON
%
%   operating_regime:
%       0 = NORMAL
%       1 = TURNDOWN
%
%   constraint_type:
%       0 = none
%       1 = MIN_UP      (min_up_steps)
%       2 = MIN_DOWN    (min_down_steps)

% -------------------------------------------------------------------------
% Availability & operating regime (ENUMS)
% -------------------------------------------------------------------------
state.mode             = uint8(0);   % OFF
state.operating_regime = uint8(0);   % NORMAL
state.is_operating     = false;      % cached boolean for convenience

% -------------------------------------------------------------------------
% Runtime tracking (timesteps)
% -------------------------------------------------------------------------
state.runtime_steps = uint32(0);
state.offtime_steps = uint32(0);

state.startups  = uint32(0);
state.shutdowns = uint32(0);

% -------------------------------------------------------------------------
% Regime persistence counters
% (associated with turndown_delay and recover_delay)
% -------------------------------------------------------------------------
state.turndown_counter = uint32(0);
state.recover_counter  = uint32(0);

% -------------------------------------------------------------------------
% Price-stop persistence counter
% (associated with price_delay)
% -------------------------------------------------------------------------
state.price_violation_counter = uint32(0);

% -------------------------------------------------------------------------
% ON constraint (minimum runtime enforcement)
% Corresponds to: min_up_steps
% -------------------------------------------------------------------------
state.on_constraint_active          = false;
state.on_constraint_type            = uint8(0);   % none | MIN_UP
state.on_constraint_steps_remaining = uint32(0);

% -------------------------------------------------------------------------
% OFF constraint (minimum downtime enforcement)
% Corresponds to: min_down_steps
% -------------------------------------------------------------------------
state.off_constraint_active          = false;
state.off_constraint_type            = uint8(0); % none | MIN_DOWN
state.off_constraint_steps_remaining = uint32(0);

% -------------------------------------------------------------------------
% Cumulative accounting (non-decision, diagnostic only)
% -------------------------------------------------------------------------
state.h2_produced_kg  = 0.0;
state.energy_grid_kWh = 0.0;

end