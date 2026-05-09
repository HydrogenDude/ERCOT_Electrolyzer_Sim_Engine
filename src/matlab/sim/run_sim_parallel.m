%% ======================================================
%   INITIALIZE
%  ======================================================
clc; clear;
tic

% -----------------------------
% Start parallel pool (once)
% -----------------------------
if isempty(gcp('nocreate'))
    parpool;   % default number of workers
end

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
%   SIMULATION TIME WINDOW SELECTION
%  ======================================================

run_mode = "year";        % "all" | "year"
years_to_simulate = 2025;

switch run_mode
    case "all"
        sim_idx = true(size(inputs.time));
    case "year"
        sim_idx = ismember(year(inputs.time), years_to_simulate);
    otherwise
        error("Unknown run_mode");
end

sim_steps   = find(sim_idx);
n_steps_sim = numel(sim_steps);

fprintf("Simulating %d timesteps (%s mode)\n", ...
    n_steps_sim, run_mode);

%% ======================================================
%   PREPARE READ-ONLY DATA FOR PARALLEL USE
%  ======================================================
% Prevents large struct duplication on every worker

inputsC   = parallel.pool.Constant(inputs);
signalsC  = parallel.pool.Constant(signals);
kernelC   = parallel.pool.Constant(emissions_kernel);
systemC   = parallel.pool.Constant(electrolyzer_system);

use_discrete_dispatch = false;

%% ======================================================
%   MAIN SIMULATION LOOP (PARALLELIZED)
%  ======================================================

n_cases = height(cases);
results(n_cases) = struct();   % sliced output (REQUIRED)

parfor ii = 1:n_cases

    % --------------------------------------------------
    % Pull read-only data locally (worker scope)
    % --------------------------------------------------
    inputs            = inputsC.Value;
    signals           = signalsC.Value;
    emissions_kernel  = kernelC.Value;
    electrolyzer_sys  = systemC.Value;
    stack             = electrolyzer_sys.stack;

    % --------------------------------------------------
    % Select current case
    % --------------------------------------------------
    current_case = table2struct(cases(ii,:), 'ToScalar', true);

    % --------------------------------------------------
    % Reset supervisory state (LOCAL)
    % --------------------------------------------------
    state = initialize_electrolyzer_system_state();

    % --------------------------------------------------
    % Local results struct (CRITICAL for parfor)
    % --------------------------------------------------
    local_sim = struct();
    local_sim.time        = inputs.time(sim_steps);
    local_sim.P_stack_kW  = zeros(n_steps_sim,1);
    local_sim.P_grid_kW   = zeros(n_steps_sim,1);
    local_sim.h2_kgph     = zeros(n_steps_sim,1);
    local_sim.eta_LHV     = zeros(n_steps_sim,1);

    % --------------------------------------------------
    % TIMESTEP LOOP (SERIAL — CORRECT)
    % --------------------------------------------------
    for jj = 1:n_steps_sim

        t = sim_steps(jj);

        state = update_electrolyzer_system_state( ...
            state, current_case, stack, signals, t, use_discrete_dispatch);

        physics = electrolyzer_sys.physics(state.P_stack_cmd_kW);

        local_sim.P_stack_kW(jj) = physics.P_stack_kW;
        local_sim.P_grid_kW(jj)  = physics.system.P_grid_kW;
        local_sim.h2_kgph(jj)    = physics.psa.mH2_net_kgph;
        local_sim.eta_LHV(jj)    = physics.system.eta_LHV;
    end

    % --------------------------------------------------
    % Emissions attribution
    % --------------------------------------------------
    emissions_i = electrolyzer_emissions_from_kernel( ...
        inputs, emissions_kernel, local_sim, sim_steps);

    % --------------------------------------------------
    % Store sliced results (ONLY ONCE)
    % --------------------------------------------------
    results(ii).ID        = current_case.ID;
    results(ii).case      = current_case;
    results(ii).sim       = local_sim;
    results(ii).emissions = emissions_i;
    results(ii).state     = state;

end

toc

%% ======================================================
%   VISUALIZATION (example: first case)
%  ======================================================

figure;

h = stackedplot( ...
    results(1).sim.time, ...
    [ ...
        results(1).sim.P_grid_kW(:), ...
        signals.clean_ratio(sim_steps), ...
        signals.price(sim_steps) ...
    ] ...
);

h.DisplayLabels = { ...
    'Grid Power (kW)', ...
    'Clean Energy Ratio', ...
    'Price ($/MWh)' ...
};