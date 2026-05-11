function write_results_hdf5_chunk(outFile, buffer, iStart)

n = numel(buffer);
nTime = numel(buffer(1).sim.P_grid_kW);

case_id = zeros(n,1);
P_grid_kW = zeros(n,nTime);
h2_kgph   = zeros(n,nTime);
cost      = zeros(n,nTime);
co2_kg    = zeros(n,nTime);

E = zeros(n,1);
C = zeros(n,1);
H = zeros(n,1);
CO2 = zeros(n,1);
S = zeros(n,1);

for k = 1:n
    r = buffer(k);
    case_id(k) = r.ID;
    P_grid_kW(k,:) = r.sim.P_grid_kW.';
    h2_kgph(k,:)   = r.sim.h2_kgph.';
    cost(k,:)      = r.sim.cost.';
    co2_kg(k,:)    = r.emissions.co2_kg_per_timestep.';
    E(k) = r.sim.total_energy_MWh;
    C(k) = r.sim.total_cost;
    H(k) = r.sim.total_h2_kg;
    CO2(k) = r.emissions.total_co2_kg;
    S(k) = r.state.startups;
end

iEnd = iStart + n - 1;

h5write(outFile,'/case_id',case_id,[iStart 1],[n 1]);
h5write(outFile,'/sim/P_grid_kW',P_grid_kW,[iStart 1],[n nTime]);
h5write(outFile,'/sim/h2_kgph',  h2_kgph,  [iStart 1],[n nTime]);
h5write(outFile,'/sim/cost',     cost,     [iStart 1],[n nTime]);
h5write(outFile,'/emissions/co2_kg_per_timestep',co2_kg,[iStart 1],[n nTime]);

h5write(outFile,'/totals/total_energy_MWh',E,[iStart 1],[n 1]);
h5write(outFile,'/totals/total_cost',      C,[iStart 1],[n 1]);
h5write(outFile,'/totals/total_h2_kg',     H,[iStart 1],[n 1]);
h5write(outFile,'/totals/total_co2_kg',    CO2,[iStart 1],[n 1]);
h5write(outFile,'/state/startups',S,[iStart 1],[n 1]);
end