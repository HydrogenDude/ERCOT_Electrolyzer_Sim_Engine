function electrolyzer_system = define_electrolyzer_system()

electrolyzer_system.stack = define_stack_model();
electrolyzer_system.smps  = define_smps_model();
electrolyzer_system.psa   = define_psa_model();
electrolyzer_system.aux   = define_aux_model();

electrolyzer_system.physics = @(P_stack_kW) ...
    evaluate_system_physics( ...
        P_stack_kW, ...
        electrolyzer_system.stack, ...
        electrolyzer_system.smps, ...
        electrolyzer_system.psa, ...
        electrolyzer_system.aux );

end


% ========================================================================
%  SYSTEM PHYSICS (VECTORIZED, FAST)
% =========================================================================

function physics = evaluate_system_physics(P_stack_kW, stack, smps, psa, aux)

% Ensure column vector
P = P_stack_kW(:);
N = numel(P);

% -------------------------------------------------------------------------
% Physical guardrails (no policy)
% -------------------------------------------------------------------------
P = max(P, 0);
P = min(P, stack.P_max_kW);

% -------------------------------------------------------------------------
% OFF mask (AUTHORITATIVE)
% -------------------------------------------------------------------------
is_on = P > 0;

% -------------------------------------------------------------------------
% Preallocate outputs (struct-of-arrays)
% -------------------------------------------------------------------------
physics.P_stack_kW        = P;
physics.mH2_gross_kgph    = zeros(N,1);
physics.mH2_net_kgph      = zeros(N,1);
physics.mH2_loss_kgph     = zeros(N,1);
physics.P_grid_smps_kW    = zeros(N,1);
physics.P_aux_kW          = zeros(N,1);
physics.P_grid_total_kW   = zeros(N,1);
physics.eta_system_LHV    = zeros(N,1);

% -------------------------------------------------------------------------
% Stack electrochemistry (ONLY WHEN ON)
% -------------------------------------------------------------------------
physics.mH2_gross_kgph(is_on) = ...
    stack.mH2_gross_kgph(P(is_on));

% -------------------------------------------------------------------------
% PSA purification (ONLY WHEN ON)
% -------------------------------------------------------------------------
physics.mH2_net_kgph(is_on)  = ...
    psa.mH2_net_kgph(physics.mH2_gross_kgph(is_on));

physics.mH2_loss_kgph(is_on) = ...
    psa.mH2_loss_actual_kgph(physics.mH2_gross_kgph(is_on));

% -------------------------------------------------------------------------
% SMPS AC→DC electrical behavior (ONLY WHEN ON)
% -------------------------------------------------------------------------
physics.P_grid_smps_kW(is_on) = ...
    smps.P_grid_kW(P(is_on));

P_smps_loss = physics.P_grid_smps_kW - P;

% -------------------------------------------------------------------------
% Auxiliary loads (ONLY WHEN ON)
% -------------------------------------------------------------------------
physics.P_aux_kW(is_on) = aux.P_total_kW();

% -------------------------------------------------------------------------
% Total grid-side power (ONLY WHEN ON)
% -------------------------------------------------------------------------
physics.P_grid_total_kW(is_on) = ...
      physics.P_grid_smps_kW(is_on) ...
    + physics.P_aux_kW(is_on) ...
    + psa.P_parasitic_kW(physics.mH2_gross_kgph(is_on));

% -------------------------------------------------------------------------
% Chemical power (LHV)
% -------------------------------------------------------------------------
P_H2_net_LHV_kW = zeros(N,1);
P_H2_net_LHV_kW(is_on) = ...
    physics.mH2_net_kgph(is_on) .* stack.LHV_H2_MJ_per_kg / 3.6;

% -------------------------------------------------------------------------
% System efficiency (authoritative)
% -------------------------------------------------------------------------
valid = physics.P_grid_total_kW > 0;
physics.eta_system_LHV(valid) = ...
    P_H2_net_LHV_kW(valid) ./ physics.P_grid_total_kW(valid);

% -------------------------------------------------------------------------
% Hierarchical grouping (diagnostics-friendly)
% -------------------------------------------------------------------------
physics.stack.P_dc_kW        = physics.P_stack_kW;
physics.stack.mH2_gross_kgph = physics.mH2_gross_kgph;

physics.device.P_grid_kW     = physics.P_grid_smps_kW;
physics.device.P_loss_kW     = P_smps_loss;

physics.psa.mH2_net_kgph     = physics.mH2_net_kgph;
physics.psa.mH2_loss_kgph    = physics.mH2_loss_kgph;

physics.system.P_grid_kW     = physics.P_grid_total_kW;
physics.system.eta_LHV       = physics.eta_system_LHV;

% -------------------------------------------------------------------------
% HARD PHYSICAL ASSERT
% -------------------------------------------------------------------------
idx = physics.P_stack_kW == 0;

assert( ...
    all(physics.P_grid_total_kW(idx) == 0), ...
    'Physics violation: non-zero system power when stack is OFF' ...
);

end


% ========================================================================
%  SYSTEM COMPONENTS
% =========================================================================
function stack = define_stack_model()

stack.name = "PEM_60kW_stack";

stack.P_rated_kW     = 60;
stack.P_max_kW       = 52;
stack.turndown_ratio = 0.30;
stack.P_min_kW       = stack.P_max_kW * stack.turndown_ratio;

stack.P_axis_kW = stack.P_max_kW * [1.0 0.9 0.8 0.7 0.6 0.5 0.4 0.3]';
stack.mH2_axis  = [0.89 0.82 0.73 0.66 0.58 0.49 0.40 0.32]';

assert(all(diff(stack.P_axis_kW) < 0));
assert(all(diff(stack.mH2_axis)  < 0));

stack.mH2_gross_kgph = @(P) ...
    interp1(stack.P_axis_kW, stack.mH2_axis, P, 'pchip', 0);

stack.HHV_H2_MJ_per_kg = 141.88;
stack.LHV_H2_MJ_per_kg = 119.96;

end

function smps = define_smps_model()

smps.name = "SMPS_ACDC_interface";

smps.P_axis_kW = [5 10 20 30 40 50 60]';
smps.eta_axis  = [0.80 0.86 0.91 0.92 0.925 0.93 0.935]';

assert(all(diff(smps.P_axis_kW) > 0));

smps.efficiency = @(P) ...
    interp1(smps.P_axis_kW, smps.eta_axis, P, 'pchip', smps.eta_axis(1));

smps.P_grid_kW = @(P_stack_kW) P_stack_kW ./ smps.efficiency(P_stack_kW);

end

function psa = define_psa_model()

psa.name = "PSA_purification_system";

psa.mH2_loss_kgph_nominal = 0.12;

psa.mH2_net_kgph = @(m) max(m - psa.mH2_loss_kgph_nominal, 0);
psa.mH2_loss_actual_kgph = @(m) min(psa.mH2_loss_kgph_nominal, m);

psa.P_parasitic_kW = @(~) 0;

end

function aux = define_aux_model()


aux.name = "Auxiliary_systems";

aux.P_aux_kW     = 2.0;
aux.P_chiller_kW = 17.0;

aux.P_total_kW   = @() aux.P_aux_kW + aux.P_chiller_kW;


end