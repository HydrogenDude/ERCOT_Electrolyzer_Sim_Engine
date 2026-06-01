%% Calculate Moving Averages
% Inputs
P_grid_kW = results.sim.P_grid_kW;
h2_kgph = results.sim.h2_kgph;
electricity_price = signals.price;
clean_ratio = signals.clean_ratio;
co2_kg = results.emissions.co2_kg_per_timestep;
co2_kg_per_h2_kg = results.emissions.co2_per_kg_h2_timestep;
cost = results.sim.cost;
e_MWh = P_grid_kW * 0.25 / 1000;
h2_kg = h2_kgph * 0.25;

%% Calculate Moving Averages (D-day window)

D = 14; % <-- change this to any number of days you want

samples_per_day = 24 * 4;     % 15-min timesteps → 96 per day
window = D * samples_per_day; % total samples in window

% Trailing moving averages (causal)
P_grid_kW_avg      = movmean(P_grid_kW,      [window-1 0]);
h2_kgph_avg        = movmean(h2_kgph,        [window-1 0]);
electricity_price_avg = movmean(electricity_price, [window-1 0]);
clean_ratio_avg    = movmean(clean_ratio,    [window-1 0]);
co2_kg_avg    = movmean(co2_kg,    [window-1 0]);
co2_kg_per_h2_kg_avg   = movmean(co2_kg_per_h2_kg,    [window-1 0]);
cost_avg = movmean(cost, [window-1 0]);
e_MWh_avg = movmean(e_MWh, [window-1 0]);
h2_kg_avg = movmean(h2_kg, [window-1 0]);
