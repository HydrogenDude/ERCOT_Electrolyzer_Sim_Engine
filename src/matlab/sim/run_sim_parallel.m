%% ======================================================
%   INITIALIZE
% ======================================================
clc; clear;

% -----------------------------
% Start parallel pool
% -----------------------------
if isempty(gcp('nocreate'))
    parpool('local', 4);          % Set workers to 4
end

%% ======================================================
%   LOAD INPUTS & CASES
% ======================================================
[inputs, cases] = load_inputs_and_cases();

signals            = compute_clean_energy_ratio(inputs);
emissions_kernel   = compute_grid_emissions_kernel(inputs, signals);
electrolyzer_system = define_electrolyzer_system();

%% ======================================================
%   SIMULATION TIME WINDOW
% ======================================================
run_mode = "year";
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
dt_hr       = hours(inputs.time(2) - inputs.time(1));

fprintf("Simulating %d timesteps (%s mode)\n", n_steps_sim, run_mode);

%% ======================================================
%   PARALLEL CONSTANTS
% ======================================================
inputsC  = parallel.pool.Constant(inputs);
signalsC = parallel.pool.Constant(signals);
kernelC  = parallel.pool.Constant(emissions_kernel);
systemC  = parallel.pool.Constant(electrolyzer_system);

use_discrete_dispatch = false;

%% ======================================================
%   RESULTS PREALLOCATION
% ======================================================
n_cases = height(cases);
results(n_cases) = struct();

%% ======================================================
%   PROGRESS TRACKING
% ======================================================
dq = parallel.pool.DataQueue;
startTime = tic;

afterEach(dq, @(~) report_progress(n_cases, startTime));

%% ======================================================
%   MAIN PARALLEL SIMULATION LOOP
% ======================================================
parfor ii = 1:n_cases

    % --- Pull constants (worker‑local)
    inputs_val  = inputsC.Value;
    signals_val = signalsC.Value;
    kernel_val  = kernelC.Value;
    system_val  = systemC.Value;
    stack       = system_val.stack;

    % --- Case selection
    current_case = table2struct(cases(ii,:), 'ToScalar', true);

    % --- Initialize system state
    state = initialize_electrolyzer_system_state();

    % --- Local arrays (PARFOR‑SAFE)
    time_vec   = inputs_val.time(sim_steps);
    P_stack_kW = zeros(n_steps_sim,1);
    P_grid_kW  = zeros(n_steps_sim,1);
    h2_kgph    = zeros(n_steps_sim,1);
    eta_LHV    = zeros(n_steps_sim,1);
    cost       = zeros(n_steps_sim,1);

    % --- Timestep loop
    for jj = 1:n_steps_sim
        t = sim_steps(jj);

        state = update_electrolyzer_system_state( ...
            state, current_case, stack, signals_val, t, use_discrete_dispatch);

        physics = system_val.physics(state.P_stack_cmd_kW);

        Pgrid = physics.system.P_grid_kW;
        price = signals_val.price(t);

        P_stack_kW(jj) = physics.P_stack_kW;
        P_grid_kW(jj)  = Pgrid;
        h2_kgph(jj)    = physics.psa.mH2_net_kgph;
        eta_LHV(jj)    = physics.system.eta_LHV;
        cost(jj)       = Pgrid * dt_hr * price / 1000;
    end

    % ==================================================
    %  ASSEMBLE SIM STRUCT (✅ ATOMIC CONSTRUCTION)
    % ==================================================
    local_sim = struct( ...
        'time',        time_vec, ...
        'P_stack_kW',  P_stack_kW, ...
        'P_grid_kW',   P_grid_kW, ...
        'h2_kgph',     h2_kgph, ...
        'eta_LHV',     eta_LHV, ...
        'cost',        cost);

    % --- Emissions
    emissions_i = electrolyzer_emissions_from_kernel( ...
        inputs_val, kernel_val, local_sim, sim_steps);

    % --- Totals
    local_sim.total_energy_MWh = sum(P_grid_kW) * dt_hr / 1000;
    local_sim.total_cost      = sum(cost);
    local_sim.total_h2_kg     = sum(h2_kgph) * dt_hr;

    % --- Store results (sliced assignment → OK)
    results(ii).ID        = current_case.ID;
    results(ii).case      = current_case;
    results(ii).sim       = local_sim;
    results(ii).emissions = emissions_i;
    results(ii).state     = state;   % final state only

    % --- Progress ping
    send(dq, 1);
end

fprintf('\nSimulation complete. Elapsed: %s\n', ...
    format_time(toc(startTime)));

%% ======================================================
%   FINAL HDF5 EXPORT (SERIAL)
% ======================================================
project_root = get_project_root();
outDir  = fullfile(project_root,'outputs','results');
outFile = fullfile(outDir,'results_timeseries.h5');

if ~isfolder(outDir)
    mkdir(outDir);
end

fprintf("Writing HDF5 results...\n");
export_results_hdf5(results, outFile);
fprintf("HDF5 export complete.\n");

%% ======================================================
%   LOCAL UTILITIES
% ======================================================
function report_progress(n_total, startTime)
    persistent completed lastPrint lastLen
    if isempty(completed)
        completed = 0;
        lastPrint = tic;
        lastLen   = 0;
    end

    completed = completed + 1;

    if toc(lastPrint) > 0.2 || completed == n_total
        msg = sprintf('Elapsed: %s | Cases remaining: %d', ...
            format_time(toc(startTime)), n_total - completed);

        fprintf('\r%s\r%s', repmat(' ',1,lastLen), msg);
        drawnow limitrate
        lastLen   = numel(msg);
        lastPrint = tic;
    end
end

function s = format_time(seconds)
    h = floor(seconds/3600);
    seconds = seconds - 3600*h;
    m = floor(seconds/60);
    s2 = floor(seconds - 60*m);
    s = sprintf('%02dh:%02dm:%02ds', h, m, s2);
end