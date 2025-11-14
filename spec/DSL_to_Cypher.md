了解です。「**DSL → Cypher 変換テンプレート（Jinja2 スタイル）**」を 3 種類
**LOAD / AGGREGATE / ENRICH** について提示します。
実装しやすいように、「DSL パーサで得た AST → テンプレに流し込む形」を想定しています。

---

# ✅ 1. LOAD_CSV → Cypher 変換テンプレート（Jinja2）

### ● DSL

```
LOAD_CSV "level1.csv" AS measurement
  MAP_COLUMNS { factory -> factory_id, product -> product_id, type -> fuel }
```

### ● AST 例

```json
{
  "type": "load",
  "path": "level1.csv",
  "node_label": "measurement",
  "column_map": {
    "factory": "factory_id",
    "product": "product_id",
    "type": "fuel"
  }
}
```

### ● Jinja2 テンプレート

```jinja2
LOAD CSV WITH HEADERS FROM "{{ path }}" AS row
WITH row
MERGE (f:factory { id: row.factory })
CREATE (m:{{ node_label }} {
    {% for src, dst in column_map.items() %}
    {{ dst }}: row.{{ src }}{{ "," if not loop.last }}
    {% endfor %}
})
MERGE (m)-[:AT_FACTORY]->(f);
```

---

# ✅ 2. AGGREGATE → Cypher 変換テンプレート

### ● DSL

```
AGGREGATE measurement
  BY [factory_id, product_id]
  INTO activity
  AGG_SUM(value) AS value
  TAKE_FIRST(unit) AS unit
  TIME_WINDOW monthly FROM time INTO time_window
```

### ● AST 例

```json
{
  "type": "aggregate",
  "source": "measurement",
  "group_by": ["factory_id", "product_id"],
  "target": "activity",
  "aggregations": [
    { "func": "sum",  "field": "value", "alias": "value" },
    { "func": "first","field": "unit",  "alias": "unit" }
  ],
  "time_window": {
    "mode": "monthly",
    "from": "time",
    "alias": "time_window"
  }
}
```

### ● Jinja2 テンプレート

```jinja2
MATCH (m:{{ source }})
WITH
    {% for g in group_by %}
    m.{{ g }} AS {{ g }}{{ "," }}
    {% endfor %}
    {% for agg in aggregations %}
    {{ agg.func|upper }}(m.{{ agg.field }}) AS {{ agg.alias }}{{ "," }}
    {% endfor %}
    {% if time_window %}
    {{ time_window.mode }}(m.{{ time_window.from }}) AS {{ time_window.alias }}
    {% endif %}
CREATE (a:{{ target }} {
    {% for g in group_by %}
    {{ g }}: {{ g }}, 
    {% endfor %}
    {% for agg in aggregations %}
    {{ agg.alias }}: {{ agg.alias }}{{ "," if not loop.last }}
    {% endfor %}
    {% if time_window %},
    {{ time_window.alias }}: {{ time_window.alias }}
    {% endif %}
})
WITH a
MATCH (f:factory { id: a.factory_id })
MERGE (a)-[:AT_FACTORY]->(f);
```

---

# ✅ 3. ENRICH（activity → emission）→ Cypher 変換テンプレート

### ● DSL

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

### ● AST 例

```json
{
  "type": "enrich",
  "source": "activity",
  "factor_table": "emission_factor_table",
  "match_key": "fuel",
  "target": "emission",
  "output": {
    "id": "concat('em_', a.id)",
    "activity_id": "a.id",
    "scope": "ef.scope",
    "value": "a.value * ef.factor",
    "unit": "ef.factor_unit"
  }
}
```

### ● Jinja2 テンプレート

```jinja2
MATCH (a:{{ source }}), (ef:{{ factor_table }})
WHERE a.{{ match_key }} = ef.{{ match_key }}
CREATE (e:{{ target }} {
    {% for key, expr in output.items() %}
    {{ key }}: {{ expr }}{{ "," if not loop.last }}
    {% endfor %}
})
MERGE (e)-[:FROM_ACTIVITY]->(a);
```

---

# 🎯 これでできること

上記3つのテンプレートを土台に：

* **DSL を構文解析 → AST（JSON） → Cypher** が可能になる
* Jinja2 でテンプレを持つだけで **DSL の拡張にも柔軟対応**
* LLM に自然言語から DSL を生成させる場合も、
  AST の構造がシンプルなのでミスが少ない

---

