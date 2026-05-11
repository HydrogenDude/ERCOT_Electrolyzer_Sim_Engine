%% ======================================================
%   INITIALIZE
%  ======================================================
clc; clear;

%% ======================================================
%   LOAD INPUTS AND CASES
%  ======================================================
[inputs, cases] = load_inputs_and_cases();

signals = compute_clean_energy_ratio(inputs);
emissions_kernel = compute_grid_emissions_kernel(inputs, signals);
electrolyzer_system = define_electrolyzer_system();
stack = electrolyzer_system.stack;

%% ======================================================
%   SIMULATION WINDOW
%  ======================================================
run_mode = "year";
years_to_simulate = 2025;

switch run_mode
    case "all"
        sim_idx = true(size(inputs.time));
    case "year"
        sim_idx = ismember(year(inputs.time), years_to_simulate);
end

sim_steps   = find(sim_idx);
n_steps_sim = numel(sim_steps);
dt_hr       = hours(inputs.time(2) - inputs.time(1));

fprintf("Simulating %d timesteps (%s mode)\n", n_steps_sim, run_mode);

%% ======================================================
%   HDF5 STREAMING SETUP
%  ======================================================
n_cases   = height(cases);
chunkSize = 20;

project_root = get_project_root();
outDir  = fullfile(project_root,'outputs','results');
outFile = fullfile(outDir,'results_timeseries.h5');

if ~isfolder(outDir)
    mkdir(outDir);
end

init_results_hdf5_chunked( ...
    outFile, ...
    n_cases, ...
    inputs.time(sim_steps), ...
    chunkSize);

%% ======================================================
%   MAIN SERIAL LOOP (STREAMING)
%  ======================================================
buffer     = struct([]);
chunkStart = 1;
startTime  = tic;
lastPrint  = tic;

for ii = 1:n_cases

    % --- Progress update (single line)
    if toc(lastPrint) > 0.1 || ii == n_cases
        fprintf('\rElapsed: %s | Cases remaining: %d', ...
            format_time(toc(startTime)), n_cases - ii + 1);
        drawnow limitrate
        lastPrint = tic;
    end

    % --- Case setup
    current_case = table2struct(cases(ii,:), 'ToScalar', true);
    state = initialize_electrolyzer_system_state();

    P_grid_kW = zeros(n_steps_sim,1);
    h2_kgph   = zeros(n_steps_sim,1);
    cost      = zeros(n_steps_sim,1);

    % --- Timestep loop
    for jj = 1:n_steps_sim
        t = sim_steps(jj);

        state = update_electrolyzer_system_state( ...
            state, current_case, stack, signals, t, false);

        phys = electrolyzer_system.physics(state.P_stack_cmd_kW);

        P_grid_kW(jj) = phys.system.P_grid_kW;
        h2_kgph(jj)   = phys.psa.mH2_net_kgph;
        cost(jj)      = phys.system.P_grid_kW * dt_hr * signals.price(t)/1000;
    end

    % --- Assemble sim struct
    local_sim = struct();
    local_sim.time       = inputs.time(sim_steps);
    local_sim.P_grid_kW  = P_grid_kW;
    local_sim.h2_kgph    = h2_kgph;
    local_sim.cost       = cost;

    % --- Emissions
    emissions_i = electrolyzer_emissions_from_kernel( ...
        inputs, emissions_kernel, local_sim, sim_steps);

    % --- Totals
    local_sim.total_energy_MWh = sum(P_grid_kW) * dt_hr / 1000;
    local_sim.total_cost      = sum(cost);
    local_sim.total_h2_kg     = sum(h2_kgph) * dt_hr;

    % --- Collect buffer
    buffer(end+1).ID        = current_case.ID;
    buffer(end).sim         = local_sim;
    buffer(end).emissions   = emissions_i;
    buffer(end).state       = state;

    % --- Flush chunk
    if numel(buffer) == chunkSize || ii == n_cases
        write_results_hdf5_chunk(outFile, buffer, chunkStart);
        chunkStart = chunkStart + numel(buffer);
        buffer = struct([]);
    end
end

fprintf('\nCompleted all cases. Elapsed: %s\n', ...
    format_time(toc(startTime)));

%% ======================================================
%   UTIL
%  ======================================================
function s = format_time(sec)
    h = floor(sec/3600);
    sec = sec - 3600*h;
    m = floor(sec/60);
    s2 = floor(sec - 60*m);
    s = sprintf('%02dh:%02dm:%02ds', h, m, s2);
end