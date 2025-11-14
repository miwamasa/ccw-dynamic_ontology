"""
AST (Abstract Syntax Tree) node definitions for the Dynamic Ontology DSL.

This module defines the data structures representing the parsed DSL statements.
Each class corresponds to a specific DSL statement type.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


@dataclass
class Expression:
    """Base class for expressions in the DSL."""
    pass


@dataclass
class IdentifierExpr(Expression):
    """Identifier expression (e.g., variable name)."""
    name: str


@dataclass
class NumberExpr(Expression):
    """Numeric literal expression."""
    value: float


@dataclass
class StringExpr(Expression):
    """String literal expression."""
    value: str


@dataclass
class BinaryOpExpr(Expression):
    """Binary operation (e.g., a + b, a * b)."""
    left: Expression
    operator: str  # '+', '-', '*', '/'
    right: Expression


@dataclass
class FunctionCallExpr(Expression):
    """Function call expression (e.g., sum(value))."""
    function_name: str
    argument: str


@dataclass
class ConcatenationExpr(Expression):
    """String concatenation expression."""
    parts: List[Expression]


@dataclass
class Statement:
    """Base class for all DSL statements."""
    pass


@dataclass
class LoadStatement(Statement):
    """
    LOAD_CSV statement for loading CSV data into graph nodes.

    Example:
        LOAD_CSV "level1.csv" AS measurement
          MAP_COLUMNS { factory -> factory_id, product -> product_id }
    """
    path: str
    node_label: str
    column_map: Dict[str, str] = field(default_factory=dict)


@dataclass
class NormalizeStatement(Statement):
    """
    NORMALIZE statement for data normalization (e.g., fixing typos).

    Example:
        NORMALIZE measurement {
          fuel: {"gass": "gas", "electricty": "electricity"}
        }
    """
    node_label: str
    normalizations: Dict[str, Dict[str, str]]  # property -> {old_value: new_value}


@dataclass
class AggregationClause:
    """Aggregation function specification."""
    function: str  # 'sum', 'count', 'first', 'avg'
    field: Optional[str]  # field to aggregate (None for COUNT)
    alias: str  # output field name


@dataclass
class TimeWindow:
    """Time window specification for aggregation."""
    mode: str  # 'daily', 'monthly', 'yearly'
    source_field: str
    target_field: str


@dataclass
class AggregateStatement(Statement):
    """
    AGGREGATE statement for grouping and aggregating data.

    Example:
        AGGREGATE measurement
          BY [factory_id, product_id]
          INTO activity
          AGG_SUM(value) AS value
          TAKE_FIRST(unit) AS unit
          TIME_WINDOW monthly FROM time INTO time_window
    """
    source_label: str
    group_by: List[str]
    target_label: str
    aggregations: List[AggregationClause]
    time_window: Optional[TimeWindow] = None


@dataclass
class UnitConvertStatement(Statement):
    """
    UNIT_CONVERT statement for unit conversion.

    Example:
        UNIT_CONVERT activity.value FROM unit TO "kwh" USING "conv_table.csv"
    """
    node_label: str
    field: str
    from_unit: str
    to_unit: str
    conversion_table: str


@dataclass
class EnrichStatement(Statement):
    """
    ENRICH statement for enriching nodes with external data.

    Example:
        ENRICH activity WITH emission_factor_table
          MATCH ON fuel
          OUTPUT emission AS {
            id: "em_" + activity.id,
            scope: emission_factor.scope
          }
    """
    source_label: str
    factor_table: str
    match_key: str
    target_label: str
    output_fields: Dict[str, Expression]


@dataclass
class ComputeStatement(Statement):
    """
    COMPUTE statement for calculating aggregate values.

    Example:
        COMPUTE total_emission
          FOR emission
          GROUP BY scope
          INTO ghg_report
          AS sum(value)
    """
    field_name: str
    source_label: str
    group_by: List[str]
    target_label: str
    expression: Expression


@dataclass
class ValidateStatement(Statement):
    """
    VALIDATE statement for data validation.

    Example:
        VALIDATE ghg_report WITH "total_equals_sum"
    """
    node_label: str
    rule_name: str


@dataclass
class Program:
    """Root node representing the entire DSL program."""
    statements: List[Statement]
