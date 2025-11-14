# Dynamic Ontology DSL Sample
# This script demonstrates the transformation from level1 (raw data)
# through level2 (aggregated activities) to level3 (GHG emissions)

# --- Load raw measurements (level1) ---
LOAD_CSV "level1.csv" AS measurement
  MAP_COLUMNS {
    factory -> factory_id,
    product -> product_id,
    type -> fuel,
    value -> value,
    unit -> unit,
    time -> time
  }

# --- Normalize typos in fuel types ---
NORMALIZE measurement {
  fuel: {"gass": "gas", "electricty": "electricity"}
}

# --- Aggregate measurements to activities (level2) ---
AGGREGATE measurement
  BY [factory_id, product_id]
  INTO activity
  AGG_SUM(value) AS value
  TAKE_FIRST(unit) AS unit
  TIME_WINDOW monthly FROM time INTO time_window

# --- Unit conversion (optional) ---
# UNIT_CONVERT activity.value FROM m3 TO "kwh" USING "conv_table.csv"

# --- Enrich with emission factors and generate emissions (level3) ---
ENRICH activity WITH emission_factor_table
  MATCH ON fuel
  OUTPUT emission AS {
    id: "em_" + activity.id,
    activity_id: activity.id,
    scope: emission_factor.scope,
    value: activity.value * emission_factor.factor,
    unit: emission_factor.factor_unit
  }

# --- Compute totals for GHG report ---
COMPUTE total_emission
  FOR emission
  GROUP BY scope
  INTO ghg_report
  AS sum(value)

# --- Validate results ---
VALIDATE ghg_report WITH "total_equals_sum"
