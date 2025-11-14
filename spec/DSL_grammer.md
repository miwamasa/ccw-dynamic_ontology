// ANTLR4 grammar for the LPG DSL described earlier
// - Supports macros: LOAD_CSV, NORMALIZE, AGGREGATE, UNIT_CONVERT, ENRICH, COMPUTE, VALIDATE
// - Intended as a starting point for a transpiler to Cypher (or other backends)
// - This file is written for ANTLR4 (parser + lexer in one file)

grammar LPGDSL;

program
    : statement* EOF
    ;

statement
    : loadStmt
    | normalizeStmt
    | aggregateStmt
    | unitConvertStmt
    | enrichStmt
    | computeStmt
    | validateStmt
    | commentStmt
    ;

// -----------------------------
// Statements
// -----------------------------

loadStmt
    : LOAD_CSV STRING 'AS' ID mapColumns?
    ;

mapColumns
    : MAP_COLUMNS '{' mapEntry (',' mapEntry)* '}'
    ;

mapEntry
    : ID '->' ID
    ;

normalizeStmt
    : NORMALIZE ID '{' normEntry (',' normEntry)* '}'
    ;

normEntry
    : ID ':' '{' normPair (',' normPair)* '}'
    ;

normPair
    : valueLiteral ':' valueLiteral
    ;

aggregateStmt
    : AGGREGATE ID BY '[' idList ']' INTO ID aggClause+ timeWindow?
    ;

aggClause
    : AGG_SUM '(' ID ')' 'AS' ID
    | TAKE_FIRST '(' ID ')' 'AS' ID
    | AGG_COUNT '(' ID? ')' 'AS' ID
    ;

timeWindow
    : TIME_WINDOW ID FROM ID INTO ID
    ;

unitConvertStmt
    : UNIT_CONVERT ID '.' ID FROM valueLiteral TO valueLiteral USING STRING
    ;

enrichStmt
    : ENRICH ID WITH valueLiteral MATCH ON ID OUTPUT ID AS '{' outputField (',' outputField)* '}'
    ;

outputField
    : ID ':' expr
    ;

computeStmt
    : COMPUTE ID FOR ID GROUP BY idList INTO ID AS expr
    ;

validateStmt
    : VALIDATE ID WITH STRING
    ;

commentStmt
    : LINE_COMMENT
    ;

// -----------------------------
// Helpers / expressions
// -----------------------------

idList
    : ID (',' ID)*
    ;

expr
    : expr op=(MUL | DIV) expr            # MulDivExpr
    | expr op=(ADD | SUB) expr            # AddSubExpr
    | FUNC_NAME '(' ID ')'                # FuncCallExpr
    | ID                                  # IdExpr
    | NUMBER                              # NumberExpr
    | STRING                              # StringExpr
    | concatenation                        # ConcatExpr
    ;

concatenation
    : STRING '+' STRING
    | STRING '+' ID
    | ID '+' STRING
    | ID '+' ID
    ;

// -----------------------------
// Lexer tokens (keywords and literals)
// Keywords are uppercase tokens
// -----------------------------

LOAD_CSV: 'LOAD_CSV';
MAP_COLUMNS: 'MAP_COLUMNS';
NORMALIZE: 'NORMALIZE';
AGGREGATE: 'AGGREGATE';
BY: 'BY';
INTO: 'INTO';
AGG_SUM: 'AGG_SUM';
TAKE_FIRST: 'TAKE_FIRST';
AGG_COUNT: 'AGG_COUNT';
TIME_WINDOW: 'TIME_WINDOW';
FROM: 'FROM';
INTO_KW: 'INTO';
UNIT_CONVERT: 'UNIT_CONVERT';
FROM: 'FROM';
TO: 'TO';
USING: 'USING';
ENRICH: 'ENRICH';
WITH: 'WITH';
MATCH: 'MATCH';
ON: 'ON';
OUTPUT: 'OUTPUT';
AS: 'AS';
COMPUTE: 'COMPUTE';
FOR: 'FOR';
GROUP: 'GROUP';
BY_KW: 'BY';
GROUP_BY: 'GROUP BY';
INTO_KW2: 'INTO';
VALIDATE: 'VALIDATE';
WITH_KW: 'WITH';

// Function names allowed in expressions (SUM, SUM etc.)
FUNC_NAME: ('sum' | 'SUM' | 'sum' | 'SUM' | 'avg' | 'AVG' | 'count' | 'COUNT') ;

// Generic tokens
ID  : [a-zA-Z_][a-zA-Z0-9_\-]* ;
NUMBER : [0-9]+ ('.' [0-9]+)? ;
STRING : '"' (~["\\] | '\\' .)* '"' ;

// valueLiteral accepts either ID or STRING (for map keys and values)
fragment valueLiteralFragment: ID | STRING ;

// Comments and whitespace
LINE_COMMENT: '#' ~[\r\n]* -> skip ;
WS  : [ \t\r\n]+ -> skip ;

// Operators and punctuation
ADD : '+' ;
SUB : '-' ;
MUL : '*' ;
DIV : '/' ;

// Note: Some repeated keyword tokens above are intentionally duplicated for clarity in parser rules.
// When implementing the transpiler, align these tokens consistently and consider case-insensitive handling.
