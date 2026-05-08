function inputs = load_inputs(input_dir)
%LOAD_INPUTS Load all ERCOT input time series from data/inputs
%
% inputs fields:
%   .time      -> datetime column (Nx1)
%   .load
%   .wind
%   .solar
%   .gas_cc
%   .coal
%   .nuclear
%   .hydro
%   .biomass
%   .bess
%   .wsl
%   .price
%   .dt_minutes
%   .n_steps

    %----------------------------------------------------------------------
    % Resolve input directory robustly (repo-root relative)
    %----------------------------------------------------------------------
    if nargin == 0 || isempty(input_dir)
        repoRoot = getenv('ERCOT_SIM_ROOT');
        if isempty(repoRoot)
            error(['ERCOT_SIM_ROOT not set. ', ...
                   'Did you open the MATLAB project or run startup.m?']);
        end
        input_dir = fullfile(repoRoot, 'data', 'inputs');
    end

    if ~isfolder(input_dir)
        error('Input directory does not exist: %s', input_dir);
    end

    %----------------------------------------------------------------------
    % Define expected files
    %----------------------------------------------------------------------
    series_files = struct( ...
        'load',     'load.txt', ...
        'wind',     'wind.txt', ...
        'solar',    'solar.txt', ...
        'gas_cc',   'gas_cc.txt', ...
        'coal',     'coal.txt', ...
        'nuclear',  'nuclear.txt', ...
        'hydro',    'hydro.txt', ...
        'biomass',  'biomass.txt', ...
        'bess',     'bess.txt', ...
        'wsl',      'wsl.txt', ...
        'price',    'price.txt' ...
    );

    fields = fieldnames(series_files);

    %----------------------------------------------------------------------
    % Load first file to establish master time vector
    %----------------------------------------------------------------------
    first_file = fullfile(input_dir, series_files.(fields{1}));

    if ~isfile(first_file)
        error('Missing input file: %s', first_file);
    end

    T = readtable(first_file, 'PreserveVariableNames', true);

    time = datetime(T{:,1}, 'InputFormat', 'yyyy-MM-dd HH:mm');
    inputs.time = time;

    %----------------------------------------------------------------------
    % Load remaining series and enforce time alignment
    %----------------------------------------------------------------------
    for k = 1:numel(fields)
        name = fields{k};
        file = fullfile(input_dir, series_files.(name));

        if ~isfile(file)
            error('Missing input file: %s', file);
        end

        T = readtable(file, 'PreserveVariableNames', true);

        t = datetime(T{:,1}, 'InputFormat', 'yyyy-MM-dd HH:mm');
        v = T{:,2};

        if ~isequal(t, time)
            error('Timestamp mismatch in file: %s', file);
        end

        inputs.(name) = v(:);
    end

    %----------------------------------------------------------------------
    % Metadata
    %----------------------------------------------------------------------
    if numel(time) < 2
        error('Not enough time points to compute timestep.');
    end

    dt = time(2) - time(1);   % duration
    inputs.dt_hr   = hours(dt);
    inputs.n_steps = numel(time);

end
