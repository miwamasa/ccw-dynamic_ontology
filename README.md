# Dynamic Ontology DSL

A Domain-Specific Language (DSL) compiler for dynamic ontology transformations in Labeled Property Graphs (LPG). This tool enables declarative specification of data transformations from raw measurements through aggregated activities to calculated emissions, particularly designed for GHG (Greenhouse Gas) reporting workflows.

## Overview

The Dynamic Ontology DSL provides a high-level, declarative language for defining graph transformations that compile to Cypher queries for Neo4j. It supports:

- **Level 1 (Raw Data)**: Loading CSV data into graph nodes
- **Level 2 (Aggregated Data)**: Grouping and aggregating measurements into activities
- **Level 3 (Calculated Data)**: Computing emissions using emission factors

## Features

- **Declarative DSL**: Write what you want to transform, not how to transform it
- **Cypher Code Generation**: Automatically generates optimized Cypher queries
- **Data Pipeline Support**: Handles the complete flow from raw data to reports
- **Type Safety**: Strong type checking at parse time
- **Extensible**: Easy to add new transformation operations

## Project Structure

```
ccw-dynamic_ontology/
├── src/
│   ├── ast_nodes.py      # AST node definitions
│   ├── parser.py         # DSL lexer and parser
│   ├── codegen.py        # Cypher code generator
│   └── main.py           # CLI entry point
├── examples/
│   ├── sample.dsl        # Sample DSL script
│   ├── level1.csv        # Sample raw data
│   ├── emission_factors.csv  # Emission factor table
│   ├── conv_table.csv    # Unit conversion table
│   └── output.cypher     # Generated Cypher code
├── spec/
│   ├── dynamic_ontology.md   # Ontology concept specification
│   ├── DSL_grammer.md        # ANTLR4 grammar (reference)
│   ├── DSL_spcification.md   # DSL specification
│   └── DSL_to_Cypher.md      # Cypher generation templates
└── tests/                # Test files
```

## Installation

### Requirements

- Python 3.7 or higher
- Neo4j (for executing generated Cypher queries)

### Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/ccw-dynamic_ontology.git
cd ccw-dynamic_ontology

# No external dependencies required for the compiler
# The implementation uses only Python standard library
```

## Usage

### Basic Usage

Compile a DSL file to Cypher:

```bash
python3 src/main.py examples/sample.dsl
```

Save output to a file:

```bash
python3 src/main.py examples/sample.dsl -o output.cypher
```

### DSL Syntax

#### 1. LOAD_CSV - Load data from CSV files

```
LOAD_CSV "level1.csv" AS measurement
  MAP_COLUMNS {
    factory -> factory_id,
    product -> product_id,
    type -> fuel,
    value -> value,
    unit -> unit,
    time -> time
  }
```

#### 2. NORMALIZE - Normalize data values

```
NORMALIZE measurement {
  fuel: {"gass": "gas", "electricty": "electricity"}
}
```

#### 3. AGGREGATE - Group and aggregate data

```
AGGREGATE measurement
  BY [factory_id, product_id]
  INTO activity
  AGG_SUM(value) AS value
  TAKE_FIRST(unit) AS unit
  TIME_WINDOW monthly FROM time INTO time_window
```

#### 4. UNIT_CONVERT - Convert units

```
UNIT_CONVERT activity.value FROM m3 TO "kwh" USING "conv_table.csv"
```

#### 5. ENRICH - Join with external data

```
ENRICH activity WITH emission_factor_table
  MATCH ON fuel
  OUTPUT emission AS {
    id: "em_" + activity.id,
    activity_id: activity.id,
    scope: emission_factor.scope,
    value: activity.value * emission_factor.factor,
    unit: emission_factor.factor_unit
  }
```

#### 6. COMPUTE - Calculate aggregated values

```
COMPUTE total_emission
  FOR emission
  GROUP BY scope
  INTO ghg_report
  AS sum(value)
```

#### 7. VALIDATE - Validate data constraints

```
VALIDATE ghg_report WITH "total_equals_sum"
```

## Example Workflow

See `examples/sample.dsl` for a complete example that demonstrates:

1. Loading raw measurement data (level1)
2. Normalizing fuel type names (fixing typos)
3. Aggregating measurements into activities (level2)
4. Enriching with emission factors
5. Computing total emissions by scope (level3)
6. Validating the results

### Sample Data

**level1.csv** (Raw measurements):
```csv
product,factory,type,value,unit,time
productA,FA1,electricity,100,kwh,2025-11-01
productB,FA1,gass,200,m3,2025-11-01
productC,FA1,electricty,200,kwh,2025-11-01
```

**emission_factors.csv**:
```csv
fuel,factor,factor_unit,scope
electricity,0.5,kgco2e_per_kwh,scope2
gas,2.0,kgco2e_per_m3,scope1
```

### Generated Output

The DSL compiler generates Cypher queries that can be executed in Neo4j:

```cypher
// LOAD_CSV: level1.csv AS measurement
LOAD CSV WITH HEADERS FROM "file:///level1.csv" AS row
WITH row
MERGE (f:factory { id: row.factory })
CREATE (m:measurement {
  factory_id: row.factory,
  product_id: row.product,
  fuel: row.type,
  value: row.value,
  unit: row.unit,
  time: row.time
})
MERGE (m)-[:AT_FACTORY]->(f);

// NORMALIZE: measurement
MATCH (n:measurement)
WHERE n.fuel = 'gass'
SET n.fuel = 'gas';
...
```

## Architecture

### Components

1. **Lexer** (`parser.py`): Tokenizes DSL source code
2. **Parser** (`parser.py`): Builds Abstract Syntax Tree (AST)
3. **AST Nodes** (`ast_nodes.py`): Data structures representing parsed DSL
4. **Code Generator** (`codegen.py`): Converts AST to Cypher queries
5. **CLI** (`main.py`): Command-line interface

### Data Flow

```
DSL Source → Lexer → Tokens → Parser → AST → Code Generator → Cypher
```

## Design Principles

1. **Declarative**: Focus on what to transform, not how
2. **Type-Safe**: Catch errors at compile time
3. **Composable**: Operations can be chained naturally
4. **Traceable**: Generated code includes comments for debugging
5. **Extensible**: Easy to add new operations

## Ontology Levels

The DSL supports three levels of data abstraction:

- **Level 1 (Raw)**: Direct measurements from sources (CSV, sensors, etc.)
- **Level 2 (Aggregated)**: Grouped and summarized activities
- **Level 3 (Calculated)**: Derived metrics (emissions, totals, reports)

Each level transformation preserves lineage and enables traceability.

## Use Cases

- GHG emissions reporting (Scope 1, 2, 3)
- Energy consumption analysis
- Supply chain carbon footprint tracking
- Factory-level activity aggregation
- Multi-level data transformations

## Testing

Run the example to test the compiler:

```bash
python3 src/main.py examples/sample.dsl -o test_output.cypher
```

Verify the generated Cypher code compiles correctly and produces expected queries.

## Contributing

Contributions are welcome! Please ensure:

1. Code follows Python PEP 8 style guidelines
2. New features include examples
3. DSL syntax changes are documented in spec files
4. Generated Cypher is valid and optimized

## License

[Specify your license here]

## References

- Neo4j Cypher: https://neo4j.com/docs/cypher-manual/
- Labeled Property Graph: https://neo4j.com/developer/graph-database/
- GHG Protocol: https://ghgprotocol.org/

## Authors

[Your name/organization]

## Version

1.0.0

---

For detailed specifications, see the `spec/` directory.
