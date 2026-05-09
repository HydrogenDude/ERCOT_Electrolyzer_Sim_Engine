function signals = compute_clean_energy_ratio(inputs)

% ==============================================================
% Clean Energy Ratio Calculator
%
% PURPOSE:
% Computes the time-resolved fraction of clean electricity supplied
% to the grid. Clean energy is defined as:
%
%   Clean = Renewable + Nuclear
%
% Non-renewable sources include fossil generation and BESS discharge.
% BESS charging (negative MW) is explicitly excluded.
%
% This signal is intended for emissions attribution and average
% grid-intensity modeling.
%
% DEFINITIONS:
%   - Renewable: wind, solar, hydro, biomass, WSL
%   - Clean (non-renewable): nuclear
%   - Non-renewable: gas, coal, BESS discharge
%
% NOTE:
%   BESS is treated as non-renewable when discharging and ignored
%   when charging. Storage is not credited as clean energy.
%
% UNITS:
%   All power signals are assumed to be in MW.
% ==============================================================


% -------------------------------
% Define generator groupings
% -------------------------------
renewable_types = {
    'wind'
    'solar'
    'hydro'
    'biomass'
    'wsl'
};

clean_types = {
    'nuclear'
};

nonrenewable_types = {
    'gas_cc'
    'gas_other'
    'coal'
%    'bess'
};


% -------------------------------
% Initialize accumulators
% -------------------------------
N = inputs.n_steps;

total_MW        = zeros(N,1);
renewable_MW    = zeros(N,1);
clean_MW        = zeros(N,1);
nonrenewable_MW = zeros(N,1);


% -------------------------------
% Accumulate renewable generation
% -------------------------------
for ii = 1:numel(renewable_types)
    type = renewable_types{ii};

    if isfield(inputs, type)
        P = inputs.(type)(:);
        P = max(P, 0);

        renewable_MW = renewable_MW + P;
        total_MW = total_MW + P;
    end
end


% -------------------------------
% Accumulate clean (non-renewable) generation
% -------------------------------
for ii = 1:numel(clean_types)
    type = clean_types{ii};

    if isfield(inputs, type)
        P = inputs.(type)(:);
        P = max(P, 0);

        clean_MW = clean_MW + P;
        total_MW = total_MW + P;
    end
end



% -------------------------------
% Accumulate non-renewable generation
% (BESS discharge only)
% -------------------------------
for ii = 1:numel(nonrenewable_types)
    type = nonrenewable_types{ii};

    if isfield(inputs, type)
        P = inputs.(type)(:);

        % Only count discharge for BESS
        if strcmp(type, 'bess')
            P = max(P, 0);
        end

        nonrenewable_MW = nonrenewable_MW + P;
        total_MW        = total_MW        + P;
    end
end


% -------------------------------
% Compute clean energy ratios
% -------------------------------
clean_ratio = safe_divide(renewable_MW + clean_MW, total_MW);
renewable_ratio = safe_divide(renewable_MW, total_MW);


% -------------------------------
% Package outputs
% -------------------------------
signals.clean_ratio       = clean_ratio;
signals.renewable_ratio   = renewable_ratio;
signals.price             = inputs.price;


signals.total_MW           = total_MW;
signals.renewable_MW       = renewable_MW;
signals.clean_MW           = renewable_MW + clean_MW;
signals.nonrenewable_MW    = nonrenewable_MW;

end


