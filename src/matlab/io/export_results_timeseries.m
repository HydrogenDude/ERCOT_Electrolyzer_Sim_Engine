function export_results_timeseries(results, varList, outFile)
% EXPORT_RESULTS_TIMESERIES
%
% Export selected time-series variables from results struct to a flat table
% suitable for Python (pandas) plotting.
%
% Inputs:
%   results  - struct array (results(ii))
%   varList  - string array or cellstr of dot-paths
%              e.g. ["sim.P_grid_kW", "sim.h2_kgph", "emissions.co2_kg_per_timestep"]
%   outFile  - output CSV filename
%
% Output:
%   Writes CSV to disk

    if ischar(varList)
        varList = {varList};
    end

    rows = []; %#ok<NASGU>
    allTables = cell(numel(results),1);

    for ii = 1:numel(results)

        r = results(ii);
        t = r.sim.time;
        n = numel(t);

        T = table();
        T.case_id = repmat(r.ID, n, 1);
        T.time    = t;

        for v = 1:numel(varList)
            path = varList{v};

            data = get_nested_field(r, path);

            if numel(data) ~= n
                error('Variable "%s" is not a time-series of length %d.', ...
                      path, n);
            end

            varName = matlab.lang.makeValidName(strrep(path,'.','_'));
            T.(varName) = data;
        end

        allTables{ii} = T;
    end

    outTable = vertcat(allTables{:});
    writetable(outTable, outFile);

    fprintf('Exported %d rows to %s\n', height(outTable), outFile);
end
function value = get_nested_field(s, path)
% GET_NESTED_FIELD Access struct fields using dot notation
%
% Example:
%   get_nested_field(results(1), 'sim.P_grid_kW')

    parts = strsplit(path, '.');
    value = s;

    for i = 1:numel(parts)
        field = parts{i};
        if ~isfield(value, field)
            error('Field "%s" not found in path "%s".', field, path);
        end
        value = value.(field);
    end
end