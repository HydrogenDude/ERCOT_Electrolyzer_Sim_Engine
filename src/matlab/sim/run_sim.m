%% ======================================================
%   INITIALIZE
%  ======================================================
clc; clear;

% -----------------------------
% Load inputs and cases
% -----------------------------
[inputs, cases] = load_inputs_and_cases();

% -----------------------------
% Exogenous signals
% -----------------------------
signals = compute_clean_energy_ratio(inputs);

% -----------------------------
% Grid-only emissions kernel
% -----------------------------
emissions_kernel = compute_grid_emissions_kernel(inputs, signals);

% -----------------------------
% Electrolyzer system definition
% -----------------------------
electrolyzer_system = define_electrolyzer_system();
stack = electrolyzer_system.stack;


%% ======================================================
%   MAIN SIMULATION LOOP
%  ======================================================

use_discrete_dispatch = false;

n_cases = height(cases);
n_steps = inputs.n_steps;

results(n_cases) = struct();   % preallocate

for ii = 1:n_cases

    % --------------------------------------------------
    % Select current case (row → scalar struct)
    % --------------------------------------------------
    current_case = table2struct(cases(ii,:), 'ToScalar', true);

    fprintf('Running case %d / %d (ID = %d)\n', ...
        ii, n_cases, current_case.ID);

    % --------------------------------------------------
    % Reset supervisory state
    % --------------------------------------------------
    state = initialize_electrolyzer_system_state();

    % --------------------------------------------------
    % Preallocate time-series outputs
    % --------------------------------------------------
    sim_results.P_stack_kW   = zeros(n_steps,1);
    sim_results.P_grid_kW    = zeros(n_steps,1);
    sim_results.h2_kgph      = zeros(n_steps,1);
    sim_results.eta_LHV      = zeros(n_steps,1);

    % --------------------------------------------------
    % TIMESTEP LOOP
    % --------------------------------------------------
    for jj = 1:n_steps

        % ----------------------------------------------
        % Supervisory update → stack power command
        % ----------------------------------------------
        state = update_electrolyzer_system_state( ...
            state, current_case, stack, signals, jj, use_discrete_dispatch)

        % ----------------------------------------------
        % Physics evaluation (authoritative)
        % ----------------------------------------------
        physics = electrolyzer_system.physics(state.P_stack_cmd_kW);

        % ----------------------------------------------
        % Store timestep outputs
        % ----------------------------------------------
        sim_results.P_stack_kW(jj) = physics.P_stack_kW;
        sim_results.P_grid_kW(jj)  = physics.system.P_grid_kW;
        sim_results.h2_kgph(jj)    = physics.psa.mH2_net_kgph;
        sim_results.eta_LHV(jj)    = physics.system.eta_LHV;

    end

    % --------------------------------------------------
    % Emissions attribution (post-run)
    % --------------------------------------------------
    emissions_i = electrolyzer_emissions_from_kernel( ...
        inputs, emissions_kernel, sim_results);

    % --------------------------------------------------
    % Store case-level results
    % --------------------------------------------------
    results(ii).ID        = current_case.ID;
    results(ii).case      = current_case;
    results(ii).sim       = sim_results;
    results(ii).emissions = emissions_i;
    results(ii).state     = state;   % final state snapshot

end



%% ======================================================
%   POST-PROCESSING
%  ======================================================


%% ======================================================
%   VISUALIZATION
%  ======================================================

figure;

h = stackedplot( ...
    inputs.time, ...
    [ ...
        results.sim.P_grid_kW(:), ...
        signals.clean_ratio(:), ...
        signals.price(:) ...
    ] ...
);

h.DisplayLabels = { ...
    'Grid Power (kW)', ...
    'Clean Energy Ratio', ...
    'Price ($/MWh)' ...
};