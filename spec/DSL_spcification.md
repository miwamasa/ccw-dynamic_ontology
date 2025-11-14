いいですね — 方向性明確。自然言語→DSL→（マクロ変換で）Cypher、というパイプラインを想定して、LPGの書き方を制限しつつ直感的で生成しやすいDSL設計案を一気に提示します。最後に「LLMに投げるためのプロンプトテンプレート」と「自然言語→DSLの具体例（あなたのサンプル）」も付けます。長いですが、実装に落とせる具体性を重視しました。

# 要件整理（短く）

* LPGの表現を制約してDSLで扱いやすくする（ラベル名・プロパティ名を限定）。
* DSLは宣言的かつマクロ化して、ユーザーは「何をしたいか」を書くだけで良い。
* DSLから自動でCypher（またはほかのグラフクエリ）を生成するマッピングを明確化。
* 最終的にNL→DSLはLLMに任せる（ステップはプロンプト設計とテンプレの準備）。

---

# 1. 制限したLPGミニ・スキーマ（必須ルール）

DSLの簡潔さを担保するため、LPGノード・エッジの許容を制限します。これによりDSLの文法が非常に単純になります。

許容ノードラベル（1語、小文字）

* `factory`（必須プロパティ: `id`）
* `measurement`（生データ、level1）: 必須プロパティ `id, factory_id, product_id, fuel, value, unit, time`
* `activity`（集約後、level2）: 必須プロパティ `id, factory_id, product_id, fuel, value, unit, time_window`
* `emission`（level3 要素）: 必須プロパティ `id, activity_id, scope, value, unit`
* `emission_factor`（外部参照マスタ）: `fuel, factor, factor_unit, scope`

許容エッジ（固定型、1方向）

* `:AT_FACTORY` factory ← node (measurement/activity)
* `:FROM_ACTIVITY` activity ← emission
* （内部でMERGEするためエッジはほぼ固定化）

ネーミングルール

* 属性名はスネークケース（`factory_id` 等）
* 単位は短縮統一（`kwh`, `m3`, `kgco2e`）

これでDSLは対象語彙に集中できます。

---

# 2. DSL設計（概観）

DSLは行指向の宣言言語（YAML風でも良いが、ここでは読みやすいインデント付きDSL）：

* セクション: `schema`, `load`, `transform`, `enrich`, `compute`, `report`
* 各命令は高レベルなマクロ（aggregate, promote, map, convert, apply_factor, validate）

簡単な構文（EBNF風 簡易）

```
program := statement*
statement := load_stmt | transform_stmt | enrich_stmt | compute_stmt | report_stmt | validate_stmt

load_stmt := "LOAD" source "AS" node_label
transform_stmt := "AGGREGATE" group_by "INTO" node_label "AS" id_expr { "," agg_expr }
enrich_stmt := "ENRICH" node_label "USING" factor_table "MATCH" match_expr
compute_stmt := "COMPUTE" target_field "AS" expression "FOR" node_label
report_stmt := "REPORT" node_label "AS" report_name
validate_stmt := "VALIDATE" node_label "WITH" rule_name
```

でも実際にはもっと親しみやすいキーワードで書きます — 以下に「マクロ」と「DSLサンプル」を示します。

---

# 3. マクロ一覧（DSL → 意味 → Cypher生成方針）

主要マクロと生成されるCypher（概要）を表にまとめます。

1. `LOAD_CSV path AS measurement`

   * 意味: CSVを `:measurement` ノードとしてロードし、`factory` と接続
   * 生成: `LOAD CSV` → `MERGE (f:factory {id:row.factory}) CREATE (m:measurement { ... }) MERGE (m)-[:AT_FACTORY]->(f)`

2. `NORMALIZE prop_map`

   * 意味: 指定マップでプロパティ値を正規化（typo fix）
   * 生成: `MATCH (n) WHERE n.prop IN [old1,old2] SET n.prop = new`

3. `AGGREGATE measurements BY [factory_id, product_id] INTO activity SUM(value) AS value UNIT unit TIME_WINDOW month(time) AS time_window`

   * 意味: measurementをグループ化して `:activity` を作る
   * 生成: `MATCH (f:factory)-[:AT_FACTORY]-(m:measurement) WITH f.id AS factory_id, m.product_id AS product_id, SUM(m.value) AS value ... CREATE (a:activity {...}) MERGE (a)-[:AT_FACTORY]->(f)`

4. `PROMOTE measurement TO activity USING mapping`

   * 意味: 個別 measurement を activity 構造に変換（1対1）
   * 生成: `CREATE (a:activity {..})` + link

5. `ENRICH activity WITH emission_factor ON fuel INTO emission USING factor_table`

   * 意味: emission_factor を lookup して `:emission` ノードを生成
   * 生成: `MATCH (a:activity) MATCH (ef:emission_factor {fuel:a.fuel}) CREATE (e:emission {...}) MERGE (e)-[:FROM_ACTIVITY]->(a)`

6. `UNIT_CONVERT node.field FROM unitA TO unitB USING table`

   * 意味: 単位変換（外部tableで係数を参照）
   * 生成: lookup + set value = value * conv_factor

7. `COMPUTE total_emission FOR GHGReport BY sum(emission.value) GROUP BY scope`

   * 意味: レポート集計フィールド算出
   * 生成: 集約Cypher

8. `VALIDATE node WITH rule_name`

   * 意味: 簡易検証（non-null, positive 等）を走らせる。失敗はログ出力。
   * 生成: `MATCH (n) WHERE NOT (n.prop IS NOT NULL) RETURN n` 等

---

# 4. DSLサンプル（あなたのケース）

下は実際のDSL例 — level1 CSVからlevel3 ghg reportまでを記述する短いスクリプト。

```
# --- load raw measurements (level1)
LOAD_CSV "level1.csv" AS measurement
  MAP_COLUMNS {
    factory -> factory_id,
    product -> product_id,
    type -> fuel,
    value -> value,
    unit -> unit,
    time -> time
  }

# --- normalize typos
NORMALIZE measurement {
  fuel: {"gass": "gas", "electricty": "electricity"}
}

# --- create factories (auto-merge happens in LOAD if missing)
# --- aggregate to activities (level2)
AGGREGATE measurement
  BY [factory_id, product_id]
  INTO activity
  AGG_SUM(value) AS value
  TAKE_FIRST(unit) AS unit
  TIME_WINDOW monthly FROM time INTO time_window

# --- unit conversion if needed (assume m3->kwh requires conv_table)
UNIT_CONVERT activity.value FROM unit TO "kwh" USING "conv_table.csv"

# --- enrich with emission factors and generate emissions (level3)
ENRICH activity WITH emission_factor_table
  MATCH ON fuel
  OUTPUT emission AS {
    id: "em_" + activity.id,
    activity_id: activity.id,
    scope: emission_factor.scope,
    value: activity.value * emission_factor.factor,
    unit: emission_factor.factor_unit
  }

# --- compute totals for report
COMPUTE total_emission
  FOR emission
  GROUP BY scope
  INTO ghg_report
  AS sum(value)

# --- validate results
VALIDATE ghg_report WITH "total_equals_sum"
```

（上記DSLは行末コメントやインデントを自由に使える設計。`MAP_COLUMNS`はCSV列名とNodeプロパティの対応を定義）

---

# 5. DSL → Cypher の変換ルール（例：AGGREGATE の展開）

AGGREGATE 文を例に擬似的な変換テンプレを示します。

DSL:

```
AGGREGATE measurement BY [factory_id, product_id] INTO activity AGG_SUM(value) AS value TAKE_FIRST(unit) AS unit
```

生成される（疑似）Cypher:

```cypher
MATCH (m:measurement)
WITH m.factory_id AS factory_id, m.product_id AS product_id,
     SUM(m.value) AS value, COLLECT(m.unit)[0] AS unit
MERGE (f:factory {id: factory_id})
MERGE (a:activity {factory_id: factory_id, product_id: product_id})
SET a.value = value, a.unit = unit
MERGE (a)-[:AT_FACTORY]->(f);
```

このテンプレ化をDSLトランスパイラに実装します。

---

# 6. 自然言語→DSL を想定したプロンプト設計（LLM向けテンプレ）

LLMに「自然言語の指示」をDSLに変換させるときのテンプレを示します。LLMはここで `system` としてこのテンプレを学習・固定してから使います。

プロンプト（system-level）

```
You are a DSL generator. Convert user instructions (in natural language) into the minimal DSL described below.
Rules:
- Use only these node types: factory, measurement, activity, emission, emission_factor.
- Use macros: LOAD_CSV, NORMALIZE, AGGREGATE, UNIT_CONVERT, ENRICH, COMPUTE, VALIDATE.
- Output only DSL script, no explanation.
- When ambiguous about grouping, prefer grouping by factory and product.
Example:
Input: "Take the CSV and aggregate energy per product per factory monthly. Then apply emission factors to compute CO2."
Output:
<DSL script here>
```

ユーザプロンプト（例）

```
Convert to DSL: "Aggregate level1.csv by factory and product to monthly activities; convert m3 to kwh using conversion table conv.csv; lookup emission factors in factors.csv and compute emissions per activity; produce totals per scope."
```

期待される出力は上のDSLサンプル。

---

# 7. サンプル：あなたの最初のデータをDSL化（完全例）

元データ（level1）

```
productA,FA1,electricity,100,kwh,2025-11-01
productB,FA1,gas,200,m3,2025-11-01
productC,FA1,electricity,200,kwh,2025-11-01
```

対応DSL（即生成例）

```
LOAD_CSV "level1.csv" AS measurement
  MAP_COLUMNS { product -> product_id, factory -> factory_id, type -> fuel, value -> value, unit -> unit, time -> time }

NORMALIZE measurement { fuel: {"gass":"gas", "electricty":"electricity"} }

AGGREGATE measurement BY [factory_id, product_id] INTO activity AGG_SUM(value) AS value TAKE_FIRST(unit) AS unit TIME_WINDOW daily FROM time INTO time_window

UNIT_CONVERT activity.value FROM unit TO "kwh" USING "conv_table.csv"

ENRICH activity WITH "factors.csv" MATCH ON fuel OUTPUT emission AS {
  id: "em_" + activity.id,
  activity_id: activity.id,
  scope: factor.scope,
  value: activity.value * factor.factor,
  unit: factor.factor_unit
}

COMPUTE totals FOR emission GROUP BY scope INTO ghg_report AS sum(value)

VALIDATE ghg_report WITH "total_equals_sum"
```

（このDSLをトランスパイラに流すと、先ほどのサンプルの `total_scope1=400` 等が算出されます。ただし unit/conv/factor の整合は外部表に依存）

---

# 8. 実装メモ（システム構成）

1. **DSLパーサ**：ANTLR（文法定義）か、軽ければ手書きパーサ（Pythonのlark等）
2. **中間IR**：DSLを中間表現（JSON AST）にして、検証と最適化（例えば複数AGGREGATEの合併）を行う
3. **コードジェネレータ**：IR→Cypher テンプレートエンジン（Jinja2など）で生成
4. **ランタイム**：生成CypherをNeo4jに投げる。トランザクションと provenance の付与を忘れずに。
5. **NL→DSL**：LLMをフロントに置き、system promptでルールを固定、出力をDSLに限定。出力検証（ASTをパース）して不正を弾く。
6. **テスト**：DSLユニットテスト（入力CSV小サンプル → 期待Cypher → 実行結果チェック）

---

# 9. LLMプロンプト例（ユーザが直接使うテンプレ）

```
System: You are a DSL generator. Only output the DSL using macros: LOAD_CSV, NORMALIZE, AGGREGATE, UNIT_CONVERT, ENRICH, COMPUTE, VALIDATE. Allowed node types: factory, measurement, activity, emission, emission_factor.

User: "From 'level1.csv', aggregate energy for each product per factory monthly into activities. Convert m3 gas to kwh using conv_table.csv. Use factors.csv to compute emissions per activity (factor units are kgCO2e/kWh or kgCO2e/m3 as appropriate). Produce totals by scope."
```

LLM出力 should be the DSL script only.

---

# 10. 追加の改善案（将来機能）

* DSLに`explain`命令を入れて、生成されたCypherに対する人間向け簡単説明を生成（デバッグ用）。
* DSLに `PROVENANCE ON` を付けると、各生成ノードに `source_rows` と `transform_step` を付与。
* 逆変換（Cypher → DSL の簡易復元）を作ると、既存パイプラインの取り込みが楽。
* GUI（フォーム）→DSL自動生成（非技術者向け）。

---


