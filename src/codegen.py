"""
Cypher code generator for the Dynamic Ontology DSL.

This module converts AST nodes into Cypher queries for Neo4j.
"""

from typing import List
from ast_nodes import (
    Program, Statement, Expression,
    LoadStatement, NormalizeStatement, AggregateStatement,
    UnitConvertStatement, EnrichStatement, ComputeStatement, ValidateStatement,
    IdentifierExpr, NumberExpr, StringExpr, BinaryOpExpr, FunctionCallExpr, ConcatenationExpr
)


class CypherGenerator:
    """Generates Cypher queries from AST nodes."""

    def __init__(self):
        self.queries: List[str] = []

    def generate(self, program: Program) -> str:
        """Generate Cypher code from the AST."""
        self.queries = []

        for statement in program.statements:
            query = self.generate_statement(statement)
            if query:
                self.queries.append(query)

        return '\n\n'.join(self.queries)

    def generate_statement(self, stmt: Statement) -> str:
        """Generate Cypher for a single statement."""
        if isinstance(stmt, LoadStatement):
            return self.generate_load(stmt)
        elif isinstance(stmt, NormalizeStatement):
            return self.generate_normalize(stmt)
        elif isinstance(stmt, AggregateStatement):
            return self.generate_aggregate(stmt)
        elif isinstance(stmt, UnitConvertStatement):
            return self.generate_unit_convert(stmt)
        elif isinstance(stmt, EnrichStatement):
            return self.generate_enrich(stmt)
        elif isinstance(stmt, ComputeStatement):
            return self.generate_compute(stmt)
        elif isinstance(stmt, ValidateStatement):
            return self.generate_validate(stmt)
        else:
            return ''

    def _time_window_to_cypher(self, mode: str, field: str) -> str:
        """
        Convert time window mode to appropriate Cypher date function.

        Args:
            mode: Time window mode (monthly, daily, yearly, weekly)
            field: Field name containing the datetime value

        Returns:
            Cypher expression for time window truncation
        """
        mode_lower = mode.lower()

        if mode_lower == 'monthly' or mode_lower == 'month':
            return f"date.truncate('month', datetime({field}))"
        elif mode_lower == 'daily' or mode_lower == 'day':
            return f"date.truncate('day', datetime({field}))"
        elif mode_lower == 'yearly' or mode_lower == 'year':
            return f"date.truncate('year', datetime({field}))"
        elif mode_lower == 'weekly' or mode_lower == 'week':
            return f"date.truncate('week', datetime({field}))"
        elif mode_lower == 'hourly' or mode_lower == 'hour':
            return f"datetime.truncate('hour', datetime({field}))"
        else:
            # Default to monthly if unknown
            return f"date.truncate('month', datetime({field}))"

    def generate_load(self, stmt: LoadStatement) -> str:
        """Generate Cypher for LOAD_CSV statement."""
        lines = [f"// LOAD_CSV: {stmt.path} AS {stmt.node_label}"]
        lines.append(f'LOAD CSV WITH HEADERS FROM "file:///{stmt.path}" AS row')
        lines.append("WITH row")

        # Create factory node
        if 'factory' in stmt.column_map or 'factory_id' in stmt.column_map.values():
            lines.append("MERGE (f:factory { id: row.factory })")

        # Create main node with mapped columns
        fields = []
        for src, dst in stmt.column_map.items():
            fields.append(f"  {dst}: row.{src}")

        lines.append(f"CREATE (m:{stmt.node_label} {{")
        lines.append(",\n".join(fields))
        lines.append("})")

        # Create relationship to factory if applicable
        if 'factory' in stmt.column_map or 'factory_id' in stmt.column_map.values():
            lines.append("MERGE (m)-[:AT_FACTORY]->(f);")
        else:
            lines.append(";")

        return '\n'.join(lines)

    def generate_normalize(self, stmt: NormalizeStatement) -> str:
        """Generate Cypher for NORMALIZE statement."""
        lines = [f"// NORMALIZE: {stmt.node_label}"]

        for prop_name, mappings in stmt.normalizations.items():
            for old_val, new_val in mappings.items():
                lines.append(f"MATCH (n:{stmt.node_label})")
                lines.append(f"WHERE n.{prop_name} = '{old_val}'")
                lines.append(f"SET n.{prop_name} = '{new_val}';")
                lines.append("")

        return '\n'.join(lines).rstrip()

    def generate_aggregate(self, stmt: AggregateStatement) -> str:
        """Generate Cypher for AGGREGATE statement."""
        lines = [f"// AGGREGATE: {stmt.source_label} -> {stmt.target_label}"]
        lines.append(f"MATCH (m:{stmt.source_label})")

        # Build WITH clause for grouping and aggregation
        with_parts = []

        # Group by fields
        for field in stmt.group_by:
            with_parts.append(f"  m.{field} AS {field}")

        # Time window (also a grouping key)
        if stmt.time_window:
            tw = stmt.time_window
            time_expr = self._time_window_to_cypher(tw.mode, f"m.{tw.source_field}")
            with_parts.append(f"  {time_expr} AS {tw.target_field}")

        # Aggregations
        for agg in stmt.aggregations:
            if agg.function == 'sum':
                with_parts.append(f"  SUM(m.{agg.field}) AS {agg.alias}")
            elif agg.function == 'count':
                if agg.field:
                    with_parts.append(f"  COUNT(m.{agg.field}) AS {agg.alias}")
                else:
                    with_parts.append(f"  COUNT(*) AS {agg.alias}")
            elif agg.function == 'first':
                with_parts.append(f"  COLLECT(m.{agg.field})[0] AS {agg.alias}")

        lines.append("WITH")
        lines.append(",\n".join(with_parts))

        # Create aggregated node
        create_fields = []
        for field in stmt.group_by:
            create_fields.append(f"  {field}: {field}")

        for agg in stmt.aggregations:
            create_fields.append(f"  {agg.alias}: {agg.alias}")

        if stmt.time_window:
            create_fields.append(f"  {stmt.time_window.target_field}: {stmt.time_window.target_field}")

        lines.append(f"CREATE (a:{stmt.target_label} {{")
        lines.append(",\n".join(create_fields))
        lines.append("})")

        # Link to factory if applicable
        if 'factory_id' in stmt.group_by:
            lines.append("WITH a")
            lines.append("MATCH (f:factory { id: a.factory_id })")
            lines.append("MERGE (a)-[:AT_FACTORY]->(f);")
        else:
            lines.append(";")

        return '\n'.join(lines)

    def generate_unit_convert(self, stmt: UnitConvertStatement) -> str:
        """Generate Cypher for UNIT_CONVERT statement."""
        lines = [f"// UNIT_CONVERT: {stmt.node_label}.{stmt.field} FROM {stmt.from_unit} TO {stmt.to_unit}"]
        lines.append(f"// Note: Load conversion factors from {stmt.conversion_table}")
        lines.append(f"// This is a placeholder - actual implementation requires loading the conversion table")
        lines.append(f"MATCH (n:{stmt.node_label})")
        lines.append(f"WHERE n.unit = '{stmt.from_unit}'")
        lines.append(f"// MERGE with conversion factor table here")
        lines.append(f"// SET n.{stmt.field} = n.{stmt.field} * conversion_factor")
        lines.append(f"SET n.unit = '{stmt.to_unit}';")

        return '\n'.join(lines)

    def generate_enrich(self, stmt: EnrichStatement) -> str:
        """Generate Cypher for ENRICH statement."""
        lines = [f"// ENRICH: {stmt.source_label} WITH {stmt.factor_table}"]
        lines.append(f"MATCH (a:{stmt.source_label}), (ef:{stmt.factor_table})")
        lines.append(f"WHERE a.{stmt.match_key} = ef.{stmt.match_key}")

        # Build output fields
        create_fields = []
        for field_name, expr in stmt.output_fields.items():
            expr_str = self.generate_expression(expr)
            create_fields.append(f"  {field_name}: {expr_str}")

        lines.append(f"CREATE (e:{stmt.target_label} {{")
        lines.append(",\n".join(create_fields))
        lines.append("})")
        lines.append(f"MERGE (e)-[:FROM_ACTIVITY]->(a);")

        return '\n'.join(lines)

    def generate_compute(self, stmt: ComputeStatement) -> str:
        """Generate Cypher for COMPUTE statement."""
        lines = [f"// COMPUTE: {stmt.field_name} FOR {stmt.source_label}"]
        lines.append(f"MATCH (e:{stmt.source_label})")

        # Group by clause
        group_by_str = ', '.join(f"e.{field}" for field in stmt.group_by)
        lines.append(f"WITH {group_by_str}, {self.generate_expression(stmt.expression, 'e')} AS {stmt.field_name}")

        lines.append(f"MERGE (g:{stmt.target_label} {{ {stmt.group_by[0]}: e.{stmt.group_by[0]} }})")
        lines.append(f"SET g.{stmt.field_name} = {stmt.field_name};")

        return '\n'.join(lines)

    def generate_validate(self, stmt: ValidateStatement) -> str:
        """Generate Cypher for VALIDATE statement."""
        lines = [f"// VALIDATE: {stmt.node_label} WITH {stmt.rule_name}"]
        lines.append(f"// Validation rule: {stmt.rule_name}")
        lines.append(f"MATCH (n:{stmt.node_label})")
        lines.append(f"// Add validation logic based on rule: {stmt.rule_name}")
        lines.append(f"RETURN n;")

        return '\n'.join(lines)

    def generate_expression(self, expr: Expression, context_var: str = None) -> str:
        """Generate Cypher expression from AST expression.

        Args:
            expr: Expression to generate
            context_var: Current context variable (e.g., 'e', 'a') for resolving identifiers
        """
        if isinstance(expr, IdentifierExpr):
            # Handle dotted identifiers (e.g., activity.id)
            parts = expr.name.split('.')
            if len(parts) == 2:
                # Map to appropriate variable
                if parts[0] in ['activity', 'a']:
                    return f"a.{parts[1]}"
                elif parts[0] in ['emission_factor', 'ef', 'factor']:
                    return f"ef.{parts[1]}"
                elif parts[0] in ['emission', 'e']:
                    return f"e.{parts[1]}"
                else:
                    return expr.name
            return expr.name

        elif isinstance(expr, NumberExpr):
            return str(expr.value)

        elif isinstance(expr, StringExpr):
            return f"'{expr.value}'"

        elif isinstance(expr, BinaryOpExpr):
            left = self.generate_expression(expr.left, context_var)
            right = self.generate_expression(expr.right, context_var)
            return f"({left} {expr.operator} {right})"

        elif isinstance(expr, FunctionCallExpr):
            # Add context variable prefix if provided and argument is a simple identifier
            arg = expr.argument
            if context_var and '.' not in arg:
                arg = f"{context_var}.{arg}"
            return f"{expr.function_name.upper()}({arg})"

        elif isinstance(expr, ConcatenationExpr):
            parts = []
            for part in expr.parts:
                if isinstance(part, StringExpr):
                    parts.append(f"'{part.value}'")
                elif isinstance(part, IdentifierExpr):
                    # Handle dotted access
                    if '.' in part.name:
                        field_parts = part.name.split('.')
                        if field_parts[0] in ['activity', 'a']:
                            parts.append(f"a.{field_parts[1]}")
                        elif field_parts[0] in ['emission', 'e']:
                            parts.append(f"e.{field_parts[1]}")
                        else:
                            parts.append(part.name)
                    else:
                        parts.append(part.name)
                else:
                    parts.append(self.generate_expression(part, context_var))
            return " + ".join(parts)

        return ''


def generate_cypher(program: Program) -> str:
    """Generate Cypher code from an AST."""
    generator = CypherGenerator()
    return generator.generate(program)
