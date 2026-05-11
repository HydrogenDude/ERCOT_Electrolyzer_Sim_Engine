function root = get_project_root()
% GET_PROJECT_ROOT Returns absolute path to project root
%
% Project root is identified by presence of .project-root file.
% This makes paths robust to pwd changes and machine differences.

    persistent cached_root

    if ~isempty(cached_root)
        root = cached_root;
        return
    end

    % Start from this file's location (not pwd)
    here = fileparts(mfilename('fullpath'));

    % Walk upward until we find .project-root
    root = here;
    while true
        marker = fullfile(root, '.project-root');
        if isfile(marker)
            cached_root = root;
            return
        end

        parent = fileparts(root);
        if isempty(parent) || strcmp(parent, root)
            error('Project root not found. Missing .project-root file.');
        end

        root = parent;
    end
end