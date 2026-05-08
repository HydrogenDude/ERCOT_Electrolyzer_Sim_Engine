function print_struct_structure(s, indent)
% PRINTSTRUCTSTRUCTURE Pretty-prints the STRUCTURE of a struct (not values)
%
%   printStructStructure(s)
%   printStructStructure(s, indent)
%
% Shows:
%   - field names
%   - data types
%   - sizes
%   - nesting
%   - struct and cell hierarchy
%
% Intended for config inspection and debugging.

    if nargin < 2
        indent = 0;
    end

    spacer = repmat(' ', 1, indent);

    if ~isstruct(s)
        error('Input must be a struct.');
    end

    % Handle struct arrays
    if numel(s) > 1
        sz = size(s);
        fprintf('%sstruct array %s\n', spacer, mat2str(sz));
        fprintf('%sFields:\n', spacer);
        s = s(1); % structure identical across elements
        indent = indent + 4;
        spacer = repmat(' ', 1, indent);
    end

    fields = fieldnames(s);

    for i = 1:numel(fields)
        field = fields{i};
        value = s.(field);

        typeStr = class(value);
        sizeStr = mat2str(size(value));

        fprintf('%s├─ %s  (%s, %s)\n', spacer, field, typeStr, sizeStr);

        if isstruct(value)
            printStructStructure(value, indent + 4);

        elseif iscell(value)
            printCellStructure(value, indent + 4);

        end
    end
end

function printCellStructure(c, indent)
% Prints structural info for cell arrays (not contents)

    spacer = repmat(' ', 1, indent);
    sz = size(c);

    fprintf('%scell array %s\n', spacer, mat2str(sz));

    % Inspect first element only (structure representative)
    if ~isempty(c)
        first = c{1};
        fprintf('%s├─ {1} → %s (%s)\n', ...
            spacer, class(first), mat2str(size(first)));

        if isstruct(first)
            printStructStructure(first, indent + 4);
        end
    end
end