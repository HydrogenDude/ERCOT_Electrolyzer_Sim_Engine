%% ======================================================
%   INITIALIZE
%  ======================================================
clc; clear;

[inputs, cases] = load_inputs_and_cases();

signals = compute_clean_energy_ratio(inputs);

emissions_kernel = compute_grid_emissions_kernel(inputs, signals);

base_state = initialize_electrolyzer_system_state();

%% ======================================================
%   MAIN SIMULATION LOOP
%  ======================================================

n_cases = height(cases);
results(n_cases) = struct();

n_steps = inputs.n_steps;

for ii = 1:n_cases

    
fprintf('Running case %d / %d (ID = %d)\n', ii, n_cases, cases.ID(ii));


    for jj = 1:n_steps

    end

end



%% ======================================================
%   POST-PROCESSING
%  ======================================================

emissions = electrolyzer_emissions_from_kernel(inputs, kernel_emissions, sim_results);