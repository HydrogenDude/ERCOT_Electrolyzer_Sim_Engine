function init_results_hdf5_chunked(outFile, nCases, time, chunkSize)

if exist(outFile,'file')
    delete(outFile);
end

time = time(:);
nTime = numel(time);
chunkCases = min(chunkSize, nCases);

% --- Time (static, contiguous)
h5create(outFile,'/time',[nTime 1],'Datatype','double');
h5write(outFile,'/time',posixtime(time));

% --- Metadata
create('/case_id',[nCases 1],[chunkCases 1]);

% --- Time series
create('/sim/P_grid_kW',[nCases nTime],[chunkCases nTime]);
create('/sim/h2_kgph',  [nCases nTime],[chunkCases nTime]);
create('/sim/cost',     [nCases nTime],[chunkCases nTime]);

% --- Emissions
create('/emissions/co2_kg_per_timestep',[nCases nTime],[chunkCases nTime]);

% --- Totals
create('/totals/total_energy_MWh',[nCases 1],[chunkCases 1]);
create('/totals/total_cost',      [nCases 1],[chunkCases 1]);
create('/totals/total_h2_kg',     [nCases 1],[chunkCases 1]);
create('/totals/total_co2_kg',    [nCases 1],[chunkCases 1]);

% --- State
create('/state/startups',[nCases 1],[chunkCases 1]);

    function create(name,sz,chunk)
        h5create(outFile,name,sz, ...
            'ChunkSize',chunk,'Datatype','double');
    end
end
