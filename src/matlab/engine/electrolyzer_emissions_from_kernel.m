function emissions = electrolyzer_emissions_from_kernel( ...
    inputs, emissions_kernel, sim_results, sim_steps)
% ==============================================================
% Electrolyzer CO2 Emissions Attribution (Time‑Window Aware)
%
% PURPOSE:
% Computes CO2 emissions attributable to electrolyzer electricity
% consumption using a precomputed grid emissions kernel, correctly
% aligned to the simulated timestep subset.
%
% REQUIRED INPUTS:
%   inputs.dt_hr
%   sim_results.P_grid_kW            [n_sim_steps x 1]
%   emissions_kernel.alpha_kg_per_MWh [n_total_steps x 1]
%   sim_steps                         [n_sim_steps x 1] indices
%
% OPTIONAL INPUTS:
%   sim_results.h2_kgph              [n_sim_steps x 1]
%
% OUTPUTS:
%   emissions.co2_kg_per_timestep
%   emissions.total_co2_kg
%   emissions.co2_per_MWh_electric
%   emissions.co2_per_kg_h2              (if H2 supplied)
%   emissions.co2_per_kg_h2_timestep     (if H2 supplied)
%
% UNITS:
%   Power        : kW
%   Energy       : MWh
%   Kernel alpha : kg CO2 / MWh
% ==============================================================

dt_hr = inputs.dt_hr;

% --------------------------------------------------
% Validate required fields
% --------------------------------------------------
assert(isfield(sim_results, 'P_grid_kW'), ...
    'sim_results must contain P_grid_kW');

assert(isfield(emissions_kernel, 'alpha_kg_per_MWh'), ...
    'Emissions kernel missing: alpha_kg_per_MWh');

assert(nargin >= 4 && ~isempty(sim_steps), ...
    'sim_steps must be provided for time-windowed attribution');

% --------------------------------------------------
% Slice kernel to simulated timesteps
% --------------------------------------------------
alpha = emissions_kernel.alpha_kg_per_MWh(sim_steps);
P_grid_kW = sim_results.P_grid_kW(:);

assert(length(P_grid_kW) == length(alpha), ...
    'Mismatch: grid power and emissions kernel length after slicing');

% --------------------------------------------------
% Convert power → energy
% --------------------------------------------------
% kW × hr → kWh → MWh
energy_MWh = (P_grid_kW .* dt_hr) / 1000;

% --------------------------------------------------
% CO2 emissions attribution
% --------------------------------------------------
co2_kg_step  = energy_MWh .* alpha;
total_co2_kg = sum(co2_kg_step);

% --------------------------------------------------
% Package outputs
% --------------------------------------------------
emissions.co2_kg_per_timestep  = co2_kg_step;
emissions.total_co2_kg         = total_co2_kg;
emissions.co2_per_MWh_electric = ...
    safe_divide(total_co2_kg, sum(energy_MWh));

% --------------------------------------------------
% Optional hydrogen intensity metrics
% --------------------------------------------------
if isfield(sim_results, 'h2_kgph')
    h2_kg_step = sim_results.h2_kgph(:) .* dt_hr;

    emissions.co2_per_kg_h2 = ...
        safe_divide(total_co2_kg, sum(h2_kg_step));

    emissions.co2_per_kg_h2_timestep = ...
        safe_divide(co2_kg_step, h2_kg_step);
end

% --------------------------------------------------
% Traceability metadata
% --------------------------------------------------
emissions.simulated_timesteps = sim_steps;
if isfield(sim_results, 'time')
    emissions.simulated_time = sim_results.time;
end
emissions.kernel_used = emissions_kernel;

end