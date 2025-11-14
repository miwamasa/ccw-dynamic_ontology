"""
Parser for the Dynamic Ontology DSL.

This module provides a lexer and parser to convert DSL text into an AST.
The parser is implemented as a hand-written recursive descent parser.
"""

import re
from typing import List, Optional, Dict, Any
from enum import Enum, auto
from dataclasses import dataclass

from ast_nodes import (
    Program, Statement, Expression,
    LoadStatement, NormalizeStatement, AggregateStatement,
    UnitConvertStatement, EnrichStatement, ComputeStatement, ValidateStatement,
    AggregationClause, TimeWindow,
    IdentifierExpr, NumberExpr, StringExpr, BinaryOpExpr, FunctionCallExpr, ConcatenationExpr
)


class TokenType(Enum):
    """Token types for the lexer."""
    # Keywords
    LOAD_CSV = auto()
    MAP_COLUMNS = auto()
    NORMALIZE = auto()
    AGGREGATE = auto()
    BY = auto()
    INTO = auto()
    AGG_SUM = auto()
    AGG_COUNT = auto()
    TAKE_FIRST = auto()
    TIME_WINDOW = auto()
    FROM = auto()
    TO = auto()
    UNIT_CONVERT = auto()
    USING = auto()
    ENRICH = auto()
    WITH = auto()
    MATCH = auto()
    ON = auto()
    OUTPUT = auto()
    AS = auto()
    COMPUTE = auto()
    FOR = auto()
    GROUP = auto()
    VALIDATE = auto()

    # Literals and identifiers
    IDENTIFIER = auto()
    NUMBER = auto()
    STRING = auto()

    # Operators and punctuation
    LBRACE = auto()    # {
    RBRACE = auto()    # }
    LBRACKET = auto()  # [
    RBRACKET = auto()  # ]
    LPAREN = auto()    # (
    RPAREN = auto()    # )
    COMMA = auto()     # ,
    COLON = auto()     # :
    ARROW = auto()     # ->
    DOT = auto()       # .
    PLUS = auto()      # +
    MINUS = auto()     # -
    MULTIPLY = auto()  # *
    DIVIDE = auto()    # /

    # Special
    COMMENT = auto()
    NEWLINE = auto()
    EOF = auto()


@dataclass
class Token:
    """Represents a token in the DSL."""
    type: TokenType
    value: Any
    line: int
    column: int


class Lexer:
    """Tokenizer for the DSL."""

    KEYWORDS = {
        'LOAD_CSV': TokenType.LOAD_CSV,
        'MAP_COLUMNS': TokenType.MAP_COLUMNS,
        'NORMALIZE': TokenType.NORMALIZE,
        'AGGREGATE': TokenType.AGGREGATE,
        'BY': TokenType.BY,
        'INTO': TokenType.INTO,
        'AGG_SUM': TokenType.AGG_SUM,
        'AGG_COUNT': TokenType.AGG_COUNT,
        'TAKE_FIRST': TokenType.TAKE_FIRST,
        'TIME_WINDOW': TokenType.TIME_WINDOW,
        'FROM': TokenType.FROM,
        'TO': TokenType.TO,
        'UNIT_CONVERT': TokenType.UNIT_CONVERT,
        'USING': TokenType.USING,
        'ENRICH': TokenType.ENRICH,
        'WITH': TokenType.WITH,
        'MATCH': TokenType.MATCH,
        'ON': TokenType.ON,
        'OUTPUT': TokenType.OUTPUT,
        'AS': TokenType.AS,
        'COMPUTE': TokenType.COMPUTE,
        'FOR': TokenType.FOR,
        'GROUP': TokenType.GROUP,
        'VALIDATE': TokenType.VALIDATE,
    }

    def __init__(self, text: str):
        self.text = text
        self.pos = 0
        self.line = 1
        self.column = 1
        self.tokens: List[Token] = []

    def current_char(self) -> Optional[str]:
        """Get the current character."""
        if self.pos < len(self.text):
            return self.text[self.pos]
        return None

    def peek_char(self, offset: int = 1) -> Optional[str]:
        """Peek at a character ahead."""
        pos = self.pos + offset
        if pos < len(self.text):
            return self.text[pos]
        return None

    def advance(self):
        """Move to the next character."""
        if self.pos < len(self.text):
            if self.text[self.pos] == '\n':
                self.line += 1
                self.column = 1
            else:
                self.column += 1
            self.pos += 1

    def skip_whitespace(self):
        """Skip whitespace except newlines."""
        while self.current_char() and self.current_char() in ' \t\r':
            self.advance()

    def skip_comment(self):
        """Skip comment lines starting with #."""
        if self.current_char() == '#':
            while self.current_char() and self.current_char() != '\n':
                self.advance()

    def read_string(self) -> str:
        """Read a string literal."""
        result = ''
        self.advance()  # Skip opening quote

        while self.current_char() and self.current_char() != '"':
            if self.current_char() == '\\':
                self.advance()
                if self.current_char():
                    result += self.current_char()
                    self.advance()
            else:
                result += self.current_char()
                self.advance()

        if self.current_char() == '"':
            self.advance()  # Skip closing quote

        return result

    def read_number(self) -> float:
        """Read a numeric literal."""
        result = ''

        while self.current_char() and (self.current_char().isdigit() or self.current_char() == '.'):
            result += self.current_char()
            self.advance()

        return float(result) if '.' in result else int(result)

    def read_identifier(self) -> str:
        """Read an identifier or keyword."""
        result = ''

        while self.current_char() and (self.current_char().isalnum() or self.current_char() in '_-'):
            result += self.current_char()
            self.advance()

        return result

    def tokenize(self) -> List[Token]:
        """Tokenize the input text."""
        while self.current_char():
            self.skip_whitespace()

            if not self.current_char():
                break

            line, column = self.line, self.column

            # Comments
            if self.current_char() == '#':
                self.skip_comment()
                continue

            # Newlines
            if self.current_char() == '\n':
                self.advance()
                continue

            # Strings
            if self.current_char() == '"':
                value = self.read_string()
                self.tokens.append(Token(TokenType.STRING, value, line, column))
                continue

            # Numbers
            if self.current_char().isdigit():
                value = self.read_number()
                self.tokens.append(Token(TokenType.NUMBER, value, line, column))
                continue

            # Operators and punctuation
            if self.current_char() == '{':
                self.tokens.append(Token(TokenType.LBRACE, '{', line, column))
                self.advance()
                continue

            if self.current_char() == '}':
                self.tokens.append(Token(TokenType.RBRACE, '}', line, column))
                self.advance()
                continue

            if self.current_char() == '[':
                self.tokens.append(Token(TokenType.LBRACKET, '[', line, column))
                self.advance()
                continue

            if self.current_char() == ']':
                self.tokens.append(Token(TokenType.RBRACKET, ']', line, column))
                self.advance()
                continue

            if self.current_char() == '(':
                self.tokens.append(Token(TokenType.LPAREN, '(', line, column))
                self.advance()
                continue

            if self.current_char() == ')':
                self.tokens.append(Token(TokenType.RPAREN, ')', line, column))
                self.advance()
                continue

            if self.current_char() == ',':
                self.tokens.append(Token(TokenType.COMMA, ',', line, column))
                self.advance()
                continue

            if self.current_char() == ':':
                self.tokens.append(Token(TokenType.COLON, ':', line, column))
                self.advance()
                continue

            if self.current_char() == '.':
                self.tokens.append(Token(TokenType.DOT, '.', line, column))
                self.advance()
                continue

            if self.current_char() == '+':
                self.tokens.append(Token(TokenType.PLUS, '+', line, column))
                self.advance()
                continue

            if self.current_char() == '*':
                self.tokens.append(Token(TokenType.MULTIPLY, '*', line, column))
                self.advance()
                continue

            if self.current_char() == '/':
                self.tokens.append(Token(TokenType.DIVIDE, '/', line, column))
                self.advance()
                continue

            if self.current_char() == '-':
                if self.peek_char() == '>':
                    self.tokens.append(Token(TokenType.ARROW, '->', line, column))
                    self.advance()
                    self.advance()
                else:
                    self.tokens.append(Token(TokenType.MINUS, '-', line, column))
                    self.advance()
                continue

            # Identifiers and keywords
            if self.current_char().isalpha() or self.current_char() == '_':
                value = self.read_identifier()
                token_type = self.KEYWORDS.get(value, TokenType.IDENTIFIER)
                self.tokens.append(Token(token_type, value, line, column))
                continue

            # Unknown character
            raise SyntaxError(f"Unexpected character '{self.current_char()}' at line {line}, column {column}")

        # Add EOF token
        self.tokens.append(Token(TokenType.EOF, None, self.line, self.column))
        return self.tokens


class Parser:
    """Parser for the DSL."""

    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0

    def current_token(self) -> Token:
        """Get the current token."""
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return self.tokens[-1]  # Return EOF

    def peek_token(self, offset: int = 1) -> Token:
        """Peek at a token ahead."""
        pos = self.pos + offset
        if pos < len(self.tokens):
            return self.tokens[pos]
        return self.tokens[-1]  # Return EOF

    def advance(self):
        """Move to the next token."""
        if self.pos < len(self.tokens) - 1:
            self.pos += 1

    def expect(self, token_type: TokenType) -> Token:
        """Expect a specific token type and advance."""
        token = self.current_token()
        if token.type != token_type:
            raise SyntaxError(
                f"Expected {token_type.name} but got {token.type.name} "
                f"at line {token.line}, column {token.column}"
            )
        self.advance()
        return token

    def parse(self) -> Program:
        """Parse the token stream into an AST."""
        statements = []

        while self.current_token().type != TokenType.EOF:
            stmt = self.parse_statement()
            if stmt:
                statements.append(stmt)

        return Program(statements)

    def parse_statement(self) -> Optional[Statement]:
        """Parse a single statement."""
        token = self.current_token()

        if token.type == TokenType.LOAD_CSV:
            return self.parse_load_statement()
        elif token.type == TokenType.NORMALIZE:
            return self.parse_normalize_statement()
        elif token.type == TokenType.AGGREGATE:
            return self.parse_aggregate_statement()
        elif token.type == TokenType.UNIT_CONVERT:
            return self.parse_unit_convert_statement()
        elif token.type == TokenType.ENRICH:
            return self.parse_enrich_statement()
        elif token.type == TokenType.COMPUTE:
            return self.parse_compute_statement()
        elif token.type == TokenType.VALIDATE:
            return self.parse_validate_statement()
        else:
            raise SyntaxError(
                f"Unexpected token {token.type.name} at line {token.line}, column {token.column}"
            )

    def parse_load_statement(self) -> LoadStatement:
        """Parse LOAD_CSV statement."""
        self.expect(TokenType.LOAD_CSV)
        path = self.expect(TokenType.STRING).value
        self.expect(TokenType.AS)
        node_label = self.expect(TokenType.IDENTIFIER).value

        column_map = {}
        if self.current_token().type == TokenType.MAP_COLUMNS:
            self.advance()
            self.expect(TokenType.LBRACE)

            while self.current_token().type != TokenType.RBRACE:
                src = self.expect(TokenType.IDENTIFIER).value
                self.expect(TokenType.ARROW)
                dst = self.expect(TokenType.IDENTIFIER).value
                column_map[src] = dst

                if self.current_token().type == TokenType.COMMA:
                    self.advance()

            self.expect(TokenType.RBRACE)

        return LoadStatement(path, node_label, column_map)

    def parse_normalize_statement(self) -> NormalizeStatement:
        """Parse NORMALIZE statement."""
        self.expect(TokenType.NORMALIZE)
        node_label = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.LBRACE)

        normalizations = {}

        while self.current_token().type != TokenType.RBRACE:
            prop_name = self.expect(TokenType.IDENTIFIER).value
            self.expect(TokenType.COLON)
            self.expect(TokenType.LBRACE)

            mappings = {}
            while self.current_token().type != TokenType.RBRACE:
                old_val = self.parse_value_literal()
                self.expect(TokenType.COLON)
                new_val = self.parse_value_literal()
                mappings[old_val] = new_val

                if self.current_token().type == TokenType.COMMA:
                    self.advance()

            self.expect(TokenType.RBRACE)
            normalizations[prop_name] = mappings

            if self.current_token().type == TokenType.COMMA:
                self.advance()

        self.expect(TokenType.RBRACE)
        return NormalizeStatement(node_label, normalizations)

    def parse_aggregate_statement(self) -> AggregateStatement:
        """Parse AGGREGATE statement."""
        self.expect(TokenType.AGGREGATE)
        source_label = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.BY)

        # Parse group by list
        self.expect(TokenType.LBRACKET)
        group_by = []
        while self.current_token().type != TokenType.RBRACKET:
            group_by.append(self.expect(TokenType.IDENTIFIER).value)
            if self.current_token().type == TokenType.COMMA:
                self.advance()
        self.expect(TokenType.RBRACKET)

        self.expect(TokenType.INTO)
        target_label = self.expect(TokenType.IDENTIFIER).value

        # Parse aggregation clauses
        aggregations = []
        while self.current_token().type in [TokenType.AGG_SUM, TokenType.AGG_COUNT, TokenType.TAKE_FIRST]:
            agg_type = self.current_token().type
            self.advance()
            self.expect(TokenType.LPAREN)

            field = None
            if self.current_token().type == TokenType.IDENTIFIER:
                field = self.expect(TokenType.IDENTIFIER).value

            self.expect(TokenType.RPAREN)
            self.expect(TokenType.AS)
            alias = self.expect(TokenType.IDENTIFIER).value

            if agg_type == TokenType.AGG_SUM:
                func = 'sum'
            elif agg_type == TokenType.AGG_COUNT:
                func = 'count'
            elif agg_type == TokenType.TAKE_FIRST:
                func = 'first'

            aggregations.append(AggregationClause(func, field, alias))

        # Parse optional time window
        time_window = None
        if self.current_token().type == TokenType.TIME_WINDOW:
            self.advance()
            mode = self.expect(TokenType.IDENTIFIER).value
            self.expect(TokenType.FROM)
            source_field = self.expect(TokenType.IDENTIFIER).value
            self.expect(TokenType.INTO)
            target_field = self.expect(TokenType.IDENTIFIER).value
            time_window = TimeWindow(mode, source_field, target_field)

        return AggregateStatement(source_label, group_by, target_label, aggregations, time_window)

    def parse_unit_convert_statement(self) -> UnitConvertStatement:
        """Parse UNIT_CONVERT statement."""
        self.expect(TokenType.UNIT_CONVERT)
        node_label = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.DOT)
        field = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.FROM)
        from_unit = self.parse_value_literal()
        self.expect(TokenType.TO)
        to_unit = self.parse_value_literal()
        self.expect(TokenType.USING)
        conversion_table = self.expect(TokenType.STRING).value

        return UnitConvertStatement(node_label, field, from_unit, to_unit, conversion_table)

    def parse_enrich_statement(self) -> EnrichStatement:
        """Parse ENRICH statement."""
        self.expect(TokenType.ENRICH)
        source_label = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.WITH)
        factor_table = self.parse_value_literal()
        self.expect(TokenType.MATCH)
        self.expect(TokenType.ON)
        match_key = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.OUTPUT)
        target_label = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.AS)
        self.expect(TokenType.LBRACE)

        output_fields = {}
        while self.current_token().type != TokenType.RBRACE:
            field_name = self.expect(TokenType.IDENTIFIER).value
            self.expect(TokenType.COLON)
            expr = self.parse_expression()
            output_fields[field_name] = expr

            if self.current_token().type == TokenType.COMMA:
                self.advance()

        self.expect(TokenType.RBRACE)
        return EnrichStatement(source_label, factor_table, match_key, target_label, output_fields)

    def parse_compute_statement(self) -> ComputeStatement:
        """Parse COMPUTE statement."""
        self.expect(TokenType.COMPUTE)
        field_name = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.FOR)
        source_label = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.GROUP)
        self.expect(TokenType.BY)

        group_by = []
        if self.current_token().type == TokenType.LBRACKET:
            self.advance()
            while self.current_token().type != TokenType.RBRACKET:
                group_by.append(self.expect(TokenType.IDENTIFIER).value)
                if self.current_token().type == TokenType.COMMA:
                    self.advance()
            self.expect(TokenType.RBRACKET)
        else:
            group_by.append(self.expect(TokenType.IDENTIFIER).value)

        self.expect(TokenType.INTO)
        target_label = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.AS)
        expression = self.parse_expression()

        return ComputeStatement(field_name, source_label, group_by, target_label, expression)

    def parse_validate_statement(self) -> ValidateStatement:
        """Parse VALIDATE statement."""
        self.expect(TokenType.VALIDATE)
        node_label = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.WITH)
        rule_name = self.expect(TokenType.STRING).value

        return ValidateStatement(node_label, rule_name)

    def parse_value_literal(self) -> str:
        """Parse a value literal (identifier or string)."""
        token = self.current_token()
        if token.type == TokenType.IDENTIFIER:
            self.advance()
            return token.value
        elif token.type == TokenType.STRING:
            self.advance()
            return token.value
        else:
            raise SyntaxError(
                f"Expected identifier or string but got {token.type.name} "
                f"at line {token.line}, column {token.column}"
            )

    def parse_expression(self) -> Expression:
        """Parse an expression."""
        return self.parse_additive_expression()

    def parse_additive_expression(self) -> Expression:
        """Parse addition/subtraction expression."""
        left = self.parse_multiplicative_expression()

        while self.current_token().type in [TokenType.PLUS, TokenType.MINUS]:
            op = self.current_token().value
            self.advance()
            right = self.parse_multiplicative_expression()
            left = BinaryOpExpr(left, op, right)

        return left

    def parse_multiplicative_expression(self) -> Expression:
        """Parse multiplication/division expression."""
        left = self.parse_primary_expression()

        while self.current_token().type in [TokenType.MULTIPLY, TokenType.DIVIDE]:
            op = self.current_token().value
            self.advance()
            right = self.parse_primary_expression()
            left = BinaryOpExpr(left, op, right)

        return left

    def parse_primary_expression(self) -> Expression:
        """Parse primary expression."""
        token = self.current_token()

        # Function call
        if token.type == TokenType.IDENTIFIER and self.peek_token().type == TokenType.LPAREN:
            func_name = token.value
            self.advance()
            self.expect(TokenType.LPAREN)
            arg = self.expect(TokenType.IDENTIFIER).value
            self.expect(TokenType.RPAREN)
            return FunctionCallExpr(func_name, arg)

        # Identifier with possible concatenation
        if token.type == TokenType.IDENTIFIER:
            # Check for dotted access first (e.g., activity.id)
            id_val = token.value
            self.advance()
            if self.current_token().type == TokenType.DOT:
                self.advance()
                field = self.expect(TokenType.IDENTIFIER).value
                id_val = f"{id_val}.{field}"

            parts = [IdentifierExpr(id_val)]

            # Check for concatenation
            while self.current_token().type == TokenType.PLUS:
                self.advance()
                next_token = self.current_token()
                if next_token.type == TokenType.IDENTIFIER:
                    # Check for dotted access (e.g., activity.id)
                    id_val = next_token.value
                    self.advance()
                    if self.current_token().type == TokenType.DOT:
                        self.advance()
                        field = self.expect(TokenType.IDENTIFIER).value
                        parts.append(IdentifierExpr(f"{id_val}.{field}"))
                    else:
                        parts.append(IdentifierExpr(id_val))
                elif next_token.type == TokenType.STRING:
                    parts.append(StringExpr(next_token.value))
                    self.advance()

            if len(parts) == 1:
                return parts[0]
            return ConcatenationExpr(parts)

        # String literal with possible concatenation
        if token.type == TokenType.STRING:
            parts = [StringExpr(token.value)]
            self.advance()

            while self.current_token().type == TokenType.PLUS:
                self.advance()
                next_token = self.current_token()
                if next_token.type == TokenType.IDENTIFIER:
                    id_val = next_token.value
                    self.advance()
                    if self.current_token().type == TokenType.DOT:
                        self.advance()
                        field = self.expect(TokenType.IDENTIFIER).value
                        parts.append(IdentifierExpr(f"{id_val}.{field}"))
                    else:
                        parts.append(IdentifierExpr(id_val))
                elif next_token.type == TokenType.STRING:
                    parts.append(StringExpr(next_token.value))
                    self.advance()

            if len(parts) == 1:
                return parts[0]
            return ConcatenationExpr(parts)

        # Number
        if token.type == TokenType.NUMBER:
            self.advance()
            return NumberExpr(token.value)

        raise SyntaxError(
            f"Unexpected token {token.type.name} in expression "
            f"at line {token.line}, column {token.column}"
        )


def parse_dsl(text: str) -> Program:
    """Parse DSL text into an AST."""
    lexer = Lexer(text)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    return parser.parse()
