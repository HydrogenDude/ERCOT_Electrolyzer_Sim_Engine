function export_results_hdf5_chunked(results, outFile, chunkSize)
% EXPORT_RESULTS_HDF5_CHUNKED
%
% Writes results to HDF5 using chunked datasets.
% Case-wise chunking enables scalable I/O and future streaming.
%
% Layout is identical to export_results_hdf5.
%

    if nargin < 3
        chunkSize = 20;
    end

    if exist(outFile, 'file')
        delete(outFile);
    end

    nCases = numel(results);
    time   = results(1).sim.time(:);
    nTime  = numel(time);

    % Ensure chunk size is valid
    chunkCases = min(chunkSize, nCases);

    %% --------------------------------------------------
    % Initialize HDF5 file and datasets
    % --------------------------------------------------

    % --- Static time vector (contiguous, no chunking)
    h5create(outFile, '/time', [nTime 1], 'Datatype', 'double');
    h5write(outFile, '/time', datetime_to_posixtime(time));

    % --- Case metadata
    create_dataset(outFile, '/case_id',     [nCases 1],     [chunkCases 1],      'double');

    % --- Simulation time series
    create_dataset(outFile, '/sim/P_grid_kW',[nCases nTime],[chunkCases nTime],   'double');
    create_dataset(outFile, '/sim/h2_kgph',  [nCases nTime],[chunkCases nTime],   'double');
    create_dataset(outFile, '/sim/cost',     [nCases nTime],[chunkCases nTime],   'double');

    % --- Emissions
    create_dataset(outFile, '/emissions/co2_kg_per_timestep', ...
                   [nCases nTime], [chunkCases nTime], 'double');

    % --- Totals
    create_dataset(outFile, '/totals/total_energy_MWh',[nCases 1],[chunkCases 1], 'double');
    create_dataset(outFile, '/totals/total_cost',      [nCases 1],[chunkCases 1], 'double');
    create_dataset(outFile, '/totals/total_h2_kg',     [nCases 1],[chunkCases 1], 'double');
    create_dataset(outFile, '/totals/total_co2_kg',    [nCases 1],[chunkCases 1], 'double');

    % --- State
    create_dataset(outFile, '/state/startups',[nCases 1],[chunkCases 1], 'double');

    %% --------------------------------------------------
    % Write data in case chunks
    % --------------------------------------------------
    for i1 = 1:chunkCases:nCases
        i2 = min(i1 + chunkCases - 1, nCases);
        n  = i2 - i1 + 1;

        % Buffers
        case_id = zeros(n,1);

        P_grid_kW = zeros(n,nTime);
        h2_kgph   = zeros(n,nTime);
        cost      = zeros(n,nTime);
        co2_kg    = zeros(n,nTime);

        total_energy_MWh = zeros(n,1);
        total_cost       = zeros(n,1);
        total_h2_kg      = zeros(n,1);
        total_co2_kg     = zeros(n,1);
        startups         = zeros(n,1);

        % Fill buffers
        for k = 1:n
            r = results(i1 + k - 1);

            case_id(k) = r.ID;

            P_grid_kW(k,:) = r.sim.P_grid_kW(:).';
            h2_kgph(k,:)   = r.sim.h2_kgph(:).';
            cost(k,:)      = r.sim.cost(:).';
            co2_kg(k,:)    = r.emissions.co2_kg_per_timestep(:).';

            total_energy_MWh(k) = r.sim.total_energy_MWh;
            total_cost(k)       = r.sim.total_cost;
            total_h2_kg(k)      = r.sim.total_h2_kg;
            total_co2_kg(k)     = r.emissions.total_co2_kg;
            startups(k)         = r.state.startups;
        end

        % Write chunk
        h5write(outFile, '/case_id', case_id, [i1 1], [n 1]);

        h5write(outFile, '/sim/P_grid_kW', P_grid_kW, [i1 1], [n nTime]);
        h5write(outFile, '/sim/h2_kgph',   h2_kgph,   [i1 1], [n nTime]);
        h5write(outFile, '/sim/cost',      cost,      [i1 1], [n nTime]);

        h5write(outFile, '/emissions/co2_kg_per_timestep', ...
                co2_kg, [i1 1], [n nTime]);

        h5write(outFile, '/totals/total_energy_MWh', total_energy_MWh, [i1 1], [n 1]);
        h5write(outFile, '/totals/total_cost',       total_cost,       [i1 1], [n 1]);
        h5write(outFile, '/totals/total_h2_kg',      total_h2_kg,      [i1 1], [n 1]);
        h5write(outFile, '/totals/total_co2_kg',     total_co2_kg,     [i1 1], [n 1]);

        h5write(outFile, '/state/startups', startups, [i1 1], [n 1]);
    end

    fprintf('Chunked HDF5 results written to:\n  %s\n', outFile);
end

%% ======================================================
% Helper functions
% ======================================================

function create_dataset(file, name, sz, chunkSz, datatype)
    h5create(file, name, sz, ...
        'Datatype', datatype, ...
        'ChunkSize', chunkSz);
end

function t = datetime_to_posixtime(dt)
    t = posixtime(dt);
end