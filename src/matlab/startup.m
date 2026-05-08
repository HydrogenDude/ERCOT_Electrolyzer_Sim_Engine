function startup()
%STARTUP Project startup for ERCOT Electrolyzer Sim Engine
%
% This MATLAB project is a pure simulation engine.
% - No data is owned here
% - No plots are created here
% - No configs are defined here
% - Only numeric simulation code lives on the path

    fprintf('[startup] Initializing ERCOT Electrolyzer Sim Engine...\n');

    %------------------------------------------------------------------
    % Resolve paths
    %------------------------------------------------------------------
    % This file: "<repo>/src/matlab/startup.m"
    thisFile      = mfilename('fullpath');
    matlabRoot    = fileparts(thisFile);                 % <repo>/src/matlab
    repoRoot      = fileparts(fileparts(matlabRoot));    % <repo>

    %------------------------------------------------------------------
    % Export repo root for IO and batch jobs
    %------------------------------------------------------------------
    setenv('ERCOT_SIM_ROOT', repoRoot);
    fprintf('[startup] ERCOT_SIM_ROOT set to:\n  %s\n', repoRoot);

    %------------------------------------------------------------------
    % Safety check: ensure expected MATLAB structure exists
    %------------------------------------------------------------------
    requiredDirs = {
        'engine'
        'models'
        'sim'
        'utils'
        'io'
    };

    for i = 1:numel(requiredDirs)
        dirPath = fullfile(matlabRoot, requiredDirs{i});
        if ~isfolder(dirPath)
            error('[startup] Required directory missing: %s', dirPath);
        end
    end

    %------------------------------------------------------------------
    % Reset MATLAB path (project hygiene)
    %------------------------------------------------------------------
    restoredefaultpath;

    %------------------------------------------------------------------
    % Add ONLY execution-relevant directories
    %------------------------------------------------------------------
    addpath( ...
        matlabRoot, ...
        fullfile(matlabRoot, 'engine'), ...
        fullfile(matlabRoot, 'models'), ...
        fullfile(matlabRoot, 'sim'), ...
        fullfile(matlabRoot, 'utils'), ...
        fullfile(matlabRoot, 'io')  ...
    );

    %------------------------------------------------------------------
    % Explicitly DO NOT add (documentation-by-code)
    %------------------------------------------------------------------
    % tools/        -> developer-only helpers
    % configs/      -> declarative inputs (CSV, TOML, etc.)
    % data/         -> immutable inputs (accessed only by io/)
    % scripts/      -> orchestration only
    % outputs/      -> artifacts only
    % docs/         -> no executable code

    %------------------------------------------------------------------
    % Optional: numeric & display defaults (safe)
    %------------------------------------------------------------------
    format long g
    warning('off','MATLAB:dispatcher:nameConflict');

    fprintf('[startup] MATLAB path configured successfully.\n');

end