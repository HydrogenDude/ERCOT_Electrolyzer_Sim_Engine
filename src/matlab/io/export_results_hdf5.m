function export_results_hdf5(results, outFile)
% EXPORT_RESULTS_HDF5
%
% Save simulation results to an HDF5 file with structure:
%
% /time                               [T]
% /case_id                            [N]
%
% /sim/P_grid_kW                      [N x T]
% /sim/h2_kgph                        [N x T]
% /sim/cost                           [N x T]
%
% /emissions/co2_kg_per_timestep      [N x T]
%
% /totals/total_energy_MWh            [N]
% /totals/total_cost                  [N]
% /totals/total_h2_kg                 [N]
% /totals/total_co2_kg                [N]
%
% This format maps cleanly to Python (h5py / xarray).

    if exist(outFile, 'file')
        delete(outFile);
    end

    nCases = numel(results);
    time   = results(1).sim.time(:);
    nTime  = numel(time);

    % -----------------------------
    % Preallocate arrays
    % -----------------------------
    case_id = zeros(nCases,1);

    P_grid_kW = zeros(nCases, nTime);
    h2_kgph   = zeros(nCases, nTime);
    cost      = zeros(nCases, nTime);
    co2_kg    = zeros(nCases, nTime);

    total_energy_MWh = zeros(nCases,1);
    total_cost       = zeros(nCases,1);
    total_h2_kg      = zeros(nCases,1);
    total_co2_kg     = zeros(nCases,1);

    startups = zeros(nCases,1);

    % -----------------------------
    % Fill arrays
    % -----------------------------
    for ii = 1:nCases
        r = results(ii);

        case_id(ii) = r.ID;

        P_grid_kW(ii,:) = r.sim.P_grid_kW(:).';
        h2_kgph(ii,:)   = r.sim.h2_kgph(:).';
        cost(ii,:)      = r.sim.cost(:).';

        co2_kg(ii,:) = r.emissions.co2_kg_per_timestep(:).';

        total_energy_MWh(ii) = r.sim.total_energy_MWh;
        total_cost(ii)       = r.sim.total_cost;
        total_h2_kg(ii)      = r.sim.total_h2_kg;
        total_co2_kg(ii)     = r.emissions.total_co2_kg;

        startups(ii)         = r.state.startups;
    end

    % -----------------------------
    % Write datasets
    % -----------------------------
    write_dataset(outFile, '/time', datetime_to_posixtime(time));
    write_dataset(outFile, '/case_id', case_id);

    write_dataset(outFile, '/sim/P_grid_kW', P_grid_kW);
    write_dataset(outFile, '/sim/h2_kgph',   h2_kgph);
    write_dataset(outFile, '/sim/cost',      cost);

    write_dataset(outFile, '/emissions/co2_kg_per_timestep', co2_kg);

    write_dataset(outFile, '/totals/total_energy_MWh', total_energy_MWh);
    write_dataset(outFile, '/totals/total_cost',       total_cost);
    write_dataset(outFile, '/totals/total_h2_kg',      total_h2_kg);
    write_dataset(outFile, '/totals/total_co2_kg',     total_co2_kg);

    write_dataset(outFile, '/state/startups', startups);

    fprintf('HDF5 results written to:\n  %s\n', outFile);
end

% ======================================================
% Helper functions
% ======================================================

function write_dataset(file, name, data)
    sz = size(data);
    h5create(file, name, sz, 'Datatype', class(data));
    h5write(file, name, data);
end

function t = datetime_to_posixtime(dt)
% Convert datetime → seconds since Unix epoch (Python‑friendly)
    t = posixtime(dt);
end
