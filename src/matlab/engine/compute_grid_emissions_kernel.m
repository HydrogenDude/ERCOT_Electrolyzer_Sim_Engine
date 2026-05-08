function emissions = compute_grid_emissions_kernel(inputs, signals)

% ==============================================================
% Grid CO2 Emissions Kernel (Average Attribution)
%
% PURPOSE:
% Precomputes a time-indexed grid emissions intensity that maps
% electricity consumption to CO2 emissions:
%
%   CO2(t) = Energy_consumed(t) [MWh] × alpha(t) [kg CO2/MWh]
%
% This kernel depends ONLY on grid operation (inputs), not on
% electrolyzer behavior.
%
% OUTPUT:
%   emissions.alpha_kg_per_MWh   [n_steps x 1]
%
% NOTES:s
% - Kernel is defined per unit ENERGY (MWh), NOT power
% - Electrolyzer power may be supplied later in kW or MW
% ==============================================================

dt_hr = inputs.dt_hr;
N     = inputs.n_steps;

% -------------------------------
% Emission factors (kg CO2 / MWh)
% -------------------------------
EF.coal       = 1000;
EF.ng_cc      = 450;
EF.ng_simple  = 500;
EF.ng_steam   = 600;

% -------------------------------
% Extract fossil generation (MW)
% -------------------------------
P_coal   = max(inputs.coal, 0);
P_ng_cc  = max(inputs.gas_cc, 0);
P_ng_all = max(inputs.gas_other, 0);

% -------------------------------
% Ramp-based NG decomposition
% -------------------------------
% Uses slow (steam) vs fast (simple-cycle) operational behavior
% to infer plausible contributions when unit-level data are absent
steam_window_steps = round(5 / dt_hr);

P_ng_baseline = movmean(P_ng_all, steam_window_steps);
P_ng_steam    = min(P_ng_baseline, P_ng_all);
P_ng_simple   = max(P_ng_all - P_ng_steam, 0);

% -------------------------------
% Fossil mix weights
% -------------------------------
P_fossil = P_coal + P_ng_cc + P_ng_simple + P_ng_steam;

w.coal      = safe_divide(P_coal,      P_fossil);
w.cc        = safe_divide(P_ng_cc,      P_fossil);
w.ng_simple = safe_divide(P_ng_simple,  P_fossil);
w.ng_steam  = safe_divide(P_ng_steam,   P_fossil);

% -------------------------------
% Effective fossil CO2 intensity
% -------------------------------
% Result: kg CO2 / MWh of fossil electricity
EF_effective = ...
    w.coal      * EF.coal + ...
    w.cc        * EF.ng_cc + ...
    w.ng_simple * EF.ng_simple + ...
    w.ng_steam  * EF.ng_steam;

% -------------------------------
% Clean energy ratio (power-based)
% -------------------------------
clean_ratio = signals.clean_ratio;

% -------------------------------
% Final grid emissions kernel
% -------------------------------
% alpha(t): kg CO2 per MWh of electricity consumed
emissions.alpha_kg_per_MWh = (1 - clean_ratio) .* EF_effective;

% -------------------------------
% Diagnostics & traceability
% -------------------------------
emissions.EF_effective   = EF_effective;

emissions.decomposition.P_ng_simple = P_ng_simple;
emissions.decomposition.P_ng_steam  = P_ng_steam;

emissions.assumptions.EF = EF;
emissions.assumptions.method = ...
    ['Average attribution with ramp-based NG decomposition ' ...
     '(steam = slow energy, peaker = fast residual).'];

end

