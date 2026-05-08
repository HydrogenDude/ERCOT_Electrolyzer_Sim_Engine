function cases = load_supervisory_control_cases()
%LOAD_SUPERVISORY_CONTROL_CASES
% Loads supervisory_control_cases.csv from configs/paper_cases
% Independent of current working directory

    % ------------------------------------------------------------
    % Start from this file's location
    % ------------------------------------------------------------
    this_file = mfilename('fullpath');
    this_dir  = fileparts(this_file);

    % ------------------------------------------------------------
    % Walk upward until project root is found
    % ------------------------------------------------------------
    project_root = '';
    search_dir = this_dir;

    while ~isempty(search_dir)
        candidate = fullfile( ...
            search_dir, ...
            'configs', ...
            'paper_cases', ...
            'supervisory_control_cases.csv' );

        if isfile(candidate)
            project_root = search_dir;
            break
        end

        % Move up one directory
        parent_dir = fileparts(search_dir);

        if strcmp(parent_dir, search_dir)
            break   % hit filesystem root
        end

        search_dir = parent_dir;
    end

    % ------------------------------------------------------------
    % Error if not found
    % ------------------------------------------------------------
    if isempty(project_root)
        error('Could not locate project root containing configs/paper_cases.');
    end

    % ------------------------------------------------------------
    % Load CSV
    % ------------------------------------------------------------
    csv_path = fullfile( ...
        project_root, ...
        'configs', ...
        'paper_cases', ...
        'supervisory_control_cases.csv' );

    opts = detectImportOptions(csv_path);
    opts.VariableNamingRule = 'preserve';

    cases = readtable(csv_path, opts);

end