// LOAD_CSV: level1.csv AS measurement
LOAD CSV WITH HEADERS FROM "file:///level1.csv" AS row
WITH row
MERGE (f:factory { id: row.factory })
CREATE (m:measurement {
  factory_id: row.factory,
  product_id: row.product,
  fuel: row.type,
  value: toFloat(row.value),
  unit: row.unit,
  time: row.time
})
MERGE (m)-[:AT_FACTORY]->(f);

// LOAD_CSV: emission_factors.csv AS emission_factor_table
LOAD CSV WITH HEADERS FROM "file:///emission_factors.csv" AS row
WITH row
CREATE (m:emission_factor_table {
  fuel: row.fuel,
  factor: toFloat(row.factor),
  factor_unit: row.factor_unit,
  scope: row.scope
})
;

// NORMALIZE: measurement
MATCH (n:measurement)
WHERE n.fuel = 'gass'
SET n.fuel = 'gas';

MATCH (n:measurement)
WHERE n.fuel = 'electricty'
SET n.fuel = 'electricity';

// AGGREGATE: measurement -> activity
MATCH (m:measurement)
WITH
  m.factory_id AS factory_id,
  m.product_id AS product_id,
  date.truncate('month', datetime(m.time)) AS time_window,
  SUM(toFloat(m.value)) AS value,
  COLLECT(m.unit)[0] AS unit,
  COLLECT(m.fuel)[0] AS fuel
CREATE (a:activity {
  factory_id: factory_id,
  product_id: product_id,
  value: value,
  unit: unit,
  fuel: fuel,
  time_window: time_window
})
WITH a
MATCH (f:factory { id: a.factory_id })
MERGE (a)-[:AT_FACTORY]->(f);

// ENRICH: activity WITH emission_factor_table
MATCH (a:activity), (ef:emission_factor_table)
WHERE a.fuel = ef.fuel
CREATE (e:emission {
  id: 'em_' + a.id,
  activity_id: a.id,
  scope: ef.scope,
  value: (a.value * ef.factor),
  unit: ef.factor_unit
})
MERGE (e)-[:FROM_ACTIVITY]->(a);

// COMPUTE: total_emission FOR emission
MATCH (e:emission)
WITH e.scope AS scope, SUM(e.value) AS total_emission
MERGE (g:ghg_report { scope: scope })
SET g.total_emission = total_emission;

// VALIDATE: ghg_report WITH total_equals_sum
// Validation rule: total_equals_sum
MATCH (n:ghg_report)
// Add validation logic based on rule: total_equals_sum
RETURN n;