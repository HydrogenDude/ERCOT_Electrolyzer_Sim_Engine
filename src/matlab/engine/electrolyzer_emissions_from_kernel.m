function emissions = electrolyzer_emissions_from_kernel(inputs, emissions_kernel, sim_results)
% ==============================================================
% Electrolyzer CO2 Emissions Attribution (Post-Simulation)
%
% PURPOSE:
% Computes CO2 emissions attributable to electrolyzer electricity
% consumption using a precomputed grid emissions kernel.
%
% REQUIRED INPUTS:
%   inputs.dt_hr
%   sim_results.P_grid_kW        [n_steps x 1]  (grid-side power)
%   emissions_kernel.alpha_kg_per_MWh [n_steps x 1]
%
% OPTIONAL INPUTS:
%   sim_results.h2_kgph          [n_steps x 1]
%
% OUTPUTS (returned as struct):
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
% Required signals
% --------------------------------------------------
assert(isfield(sim_results, 'P_grid_kW'), ...
    'sim_results must contain P_grid_kW');

P_grid_kW = sim_results.P_grid_kW(:);

assert(isfield(emissions_kernel, 'alpha_kg_per_MWh'), ...
    'Emissions kernel missing: alpha_kg_per_MWh');

alpha = emissions_kernel.alpha_kg_per_MWh(:);

assert(length(P_grid_kW) == length(alpha), ...
    'Mismatch: grid power and emissions kernel length');

% --------------------------------------------------
% Convert power to energy
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
emissions.co2_kg_per_timestep = co2_kg_step;
emissions.total_co2_kg        = total_co2_kg;

emissions.co2_per_MWh_electric = ...
    safe_divide(total_co2_kg, sum(energy_MWh));

% --------------------------------------------------
% Optional hydrogen intensity metrics
% --------------------------------------------------
if isfield(sim_results, 'h2_kgph')

    h2_kgph = sim_results.h2_kgph(:);

    assert(length(h2_kgph) == length(co2_kg_step), ...
        'Mismatch: hydrogen production and emissions vectors');

    h2_kg_step = h2_kgph .* dt_hr;

    emissions.co2_per_kg_h2 = ...
        safe_divide(total_co2_kg, sum(h2_kg_step));

    emissions.co2_per_kg_h2_timestep = ...
        safe_divide(co2_kg_step, h2_kg_step);
end

% --------------------------------------------------
% Traceability
% --------------------------------------------------
emissions.kernel_used = emissions_kernel;

end