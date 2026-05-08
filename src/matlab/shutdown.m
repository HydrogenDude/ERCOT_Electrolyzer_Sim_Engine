function shutdown()
%SHUTDOWN Cleanup for ERCOT Electrolyzer Sim Engine
%
% Restores MATLAB environment to a clean state.
% Intended to leave no side effects after project use.

    fprintf('[shutdown] Shutting down ERCOT Electrolyzer Sim Engine...\n');

    %------------------------------------------------------------------
    % Clear persistent variables & classes
    %------------------------------------------------------------------
    clear functions
    clear classes

    %------------------------------------------------------------------
    % Restore MATLAB default path
    %------------------------------------------------------------------
    restoredefaultpath;

    %------------------------------------------------------------------
    % Close figures created during engine use (if any)
    %------------------------------------------------------------------
    close all force

    fprintf('[shutdown] Environment restored to MATLAB defaults.\n');

end