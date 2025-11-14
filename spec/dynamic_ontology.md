# 動的オントロジーとしての **level1 → level2 → level3** の演算体系（提案）

いいですね — 「下位レベルのオントロジーに追加・削減ルールを定義すると上位オントロジーが得られ、下位データは上位オントロジーに従ったLPG（Labeled Property Graph）として見える」という発想に沿って、実装可能かつ説明可能な演算体系を整理します。まず概念整理、そのあとに演算（代数的／グラフ変換／実装レシピ）と、あなたの例に沿った具体的変換例（Cypher風の疑似クエリ＋グラフ書き換えルール）を示します。

---

# 概念モデル（形式化）

* **LPGデータ**はノード (N)、エッジ (E)、ラベル (L)、プロパティ (P) で構成されるグラフ (G=(N,E,L,P))。
* **オントロジー** (O) はタイプ集合 (T)（ノードラベル／エッジラベル）、属性スキーマ (S)、制約／推論規則集合 (R) の組 ((T,S,R)) と定義する。
* **動的オントロジー**とは、ある演算群 (\mathcal{F}) を用いてオントロジー (O) を別のオントロジー (O') に変換する仕組み（写像）：
  [
  O' = \mathcal{F}(O)
  ]
  同時にインスタンス（LPG）も対応する変換 (G' = \Phi(G,\mathcal{F})) を受ける。

---

# 基本演算（オペレータ一覧） — 意味と用途

以下は実務で使える演算（とその記号）です。演算は**スキーマ（オントロジー）用**と**インスタンス（データ）用**が対応します。

1. **選択（Filter）** (\sigma_{cond}(G))
   条件でノード/エッジを選ぶ。例：type = electricity の測定のみ。

2. **射影（Projection）** (\pi_{attrs}(G))
   所定属性だけを残す（冗長除去、要約向け）。

3. **集約（Aggregation）** (\mathrm{agg}_{group, f}(G))
   グルーピング（例：工場ごと、製品カテゴリごと）して合計・平均を計算。level1→level2 の代表的操作。

4. **単位変換（Unit Conversion）** (U_{u\to v}(p))
   単位を揃える。例：m³ → kWh（必要なら係数がある場合）。

5. **係数適用（Factor application）** (F_{factor}(G))
   排出係数を乗じてGHG値を計算（level2→level3）。

6. **タイプ変換（Type promotion / demotion）** (T_{promote}(t_{src}\to t_{dst}))
   ノードラベルを上位ラベルに変換（例：measurement → activity）。

7. **マージ／統合（Merge / Collapse）** (M({n_i}))
   類似ノードを合成して1ノードに（ID統合、合計プロパティ付与）。

8. **分割（Split）** (S(n, rule))
   1ノードを複数ノードに分ける（製品→工程別に分割など）。

9. **リネーム（Rename）** (\rho(old\to new))
   プロパティ／ラベル名の変更。例：`type:gass` → `type:gas`。

10. **追加（Enrichment）** (E_{lookup}(G,external_table))
    外部マスタ（排出係数テーブル、燃料エネルギー換算表など）で補強。

11. **差分／変更（Delta）** (\Delta(G_{t1},G_{t2}))
    版管理・時間的変化を扱う。動的オントロジーのコア。

12. **制約チェック（Validation）** (V_{SHACL/SHRINK})
    （例：単位必須、value≥0 など）オントロジーに従った検証。

13. **推論（Inference）** (\mathcal{I}_R(G))
    ルールにより新しいノード/属性を導出（例：スコープ判定、カテゴリ付与）。

これらを組み合わせて「下位オントロジーの追加・削減ルール」を定義し、上位オントロジーを導出します。

---

# オントロジー演算（スキーマ側）の原子操作

オントロジー (O=(T,S,R)) に対して、演算は次のように定義できます。

* `addType(t)`：タイプ (t) を追加（例：activity）。
* `removeType(t)`：タイプ削除。
* `addProp(t,p:Type)`：タイプ (t) にプロパティ (p) を追加。
* `removeProp(t,p)`：削除。
* `mergeTypes(t1,t2 -> t')`：t1,t2 を上位 t' に統合（一般化）。
* `splitType(t -> {t_a,t_b})`：詳細化。
* `mapProp(t1.p -> t2.q, f)`：プロパティ写像（変換関数 f を伴う）。
* `addRule(r)`：推論・変換ルールを追加。

これらを**シリアライズ**して「変換スクリプト（トランスフォーム定義）」にすれば、同じ変換を複数データに再適用できます。動的オントロジーはこの変換スクリプトの集合と見なせます。

---

# グラフ変換（インスタンス側）の典型パターン（擬似アルゴリズム）

1. **level1（生データ） → 正規化**

   * ノード作成：`(:Product {id, factory, type, value, unit})`
   * ノード間の参照（工場ノード等）を結ぶ。
   * 修正：`ρ(type:gass->gas)` 等で正規化。

2. **正規化 → level2（ライン/工場集約）**

   * グルーピングキー例：factory, product_category, time_window
   * 集約演算：`SUM(value)`、`COUNT`、`AVG`
   * 変換：`measurement` ノード群を `activity` ノードへ `merge`、`type` を `activity` に promote。

3. **level2 → level3（GHG算出）**

   * Enrichment：外部 `emission_factor(fuel,type,scope)` を Lookup
   * Unit convert：`U(m3->kWh)` のような必要変換を実施
   * Apply factor：`emission = value * factor`（単位注意）
   * Aggregate totals：scope1, scope2 の合計を `ghgReport` ノードに付与

---

# 具体例（あなたのサンプルに準拠した疑似Cypher／グラフ変換）

## 1) level1 CSV → LPG（Neo4j風 疑似）

```cypher
// CSV読み込み（疑似）
LOAD CSV WITH HEADERS FROM 'file://level1.csv' AS row
MERGE (f:Factory {id: row.factory})
CREATE (p:Product {id: row.product, type: row.type, value: toFloat(row.value), unit: row.unit})
MERGE (f)-[:PRODUCES]->(p);
```

## 2) 型正規化＋集約（level1 -> level2）

（目的：工場ごとの活動ノード activity を作る）

```cypher
// プロパティ名/タイプ正規化（例）
MATCH (p:Product)
WHERE p.type = 'gass'
SET p.type = 'gas';

// 集約して activity を作る（factoryごと、product名ごと）
MATCH (f:Factory)-[:PRODUCES]->(p:Product)
WITH f, p.type AS fuel, p.id AS productId, SUM(p.value) AS totalValue, p.unit AS unit
MERGE (a:Activity {factory: f.id, product: productId})
SET a.type = fuel, a.value = totalValue, a.unit = unit
MERGE (f)-[:HAS_ACTIVITY]->(a);
```

> 結果：`Activity`ノードが level2 の `productA_making` 等に相当する。

## 3) level2 -> level3（係数適用、GHG算出）

想定：`EmissionFactor` ノードがあり `factor` と `scope` を持つ。

```cypher
// 係数参照＆排出量計算
MATCH (a:Activity)
MATCH (ef:EmissionFactor {fuel: a.type})
WITH a, ef, a.value * ef.factor AS emissionValue
MERGE (g:GHGReport {factory: a.factory})
MERGE (g)-[:HAS_EMISSION]->(e:Emission {activity: a.product})
SET e.value = emissionValue, e.unit = ef.emission_unit, e.scope = ef.scope;

// 集計（scope別合計）
MATCH (g:GHGReport)-[:HAS_EMISSION]->(e:Emission)
WITH g, e.scope AS scope, SUM(e.value) AS s
SET g['total_' + scope] = s
WITH g
SET g.total_emission = coalesce(g.total_scope1,0) + coalesce(g.total_scope2,0);
```

> ※単位の一致、係数の単位（kgCO2e／kWh など）に注意。変換ルールを `U` で入れる。

---

# グラフ書き換えルール（Rewrite rules）

動的オントロジーは**グラフ書き換え規則**の集合とみなせます。形式的には
[
\text{rule } r: L \Rightarrow R
]
で、左辺パターン (L) が見つかったら右辺 (R) に置き換える。例：

**r1: measurement → activity (promotion)**

* L: `(:Product {id: pid, factory: fid, type: t, value: v, unit: u})`
* R: 新規 `(:Activity {id: pid + "_making", factory: fid, type: t, value: v, unit: u})` と `(:Factory)-[:HAS_ACTIVITY]->(:Activity)`、元のProductは保持または参照として残す

**r2: apply emission factor**

* L: `(:Activity {type: t, value: v})` + `(:EmissionFactor {fuel:t, factor:f, scope:s})`
* R: `(:Emission {activity:..., value: v * f, scope: s})` を生成

こうした規則を順次適用（あるいは並列で適用）することで、上位オントロジーを導出する。

---

# オントロジー操作の性質（重要な設計注意）

1. **可逆性**：一部の変換は可逆（単純なリネーム），多くは不可逆（集約で元データ消失）。運用で可逆性が必要なら provenance と raw-data を残すこと。
2. **単位と意味の整合**：単位変換と係数のスキーマ（単位・時間窓）を明確化。
3. **透明性と説明可能性**：どのルールでどう集約・係数適用したかを変換メタデータ（`transformation:{rule_id, timestamp, params}`）として保持。
4. **検証**：SHACL相当の制約で出力オントロジーを検証（例：total_emission = sum(emissions)）。LPG環境では独自の検証スクリプト／Cypherで。
5. **バージョン管理**：O1→O2→O3 のオントロジー定義とルールは Git のように管理。データに `ontology_version` を書く。

---

# 高レベルの代数（記号的まとめ）

* スキーマ変換： ( O_2 = \tau(O_1, \alpha) ) （(\alpha) は変換定義の集合）
* インスタンス写像： ( G_2 = \Phi(G_1, \tau) )
* 合計（工場ごと）： ( \mathrm{agg}_{factory, sum}(G_1) \Rightarrow G_2 )
* 排出変換： ( G_3 = F_{ef}(G_2) ), ただし (F_{ef}) は `lookup factor` + `unit conv` + `multiply` の合成

---

# 実装上の技術選択（提案）

* **LPGストア**：Neo4j、JanusGraph、AWS Neptune（LPGサポート状況に注意）
* **ルール実行**：Cypher / Gremlin スクリプト、あるいは外部 ETL（Apache NiFi, Airflow + Python）で graph API 呼ぶ
* **制約検証**：SHACL（RDF）に慣れているなら RDF に射影して検証も可。LPGだとカスタム検証クエリ。
* **外部テーブル**：排出係数、単位換算テーブルは DB／CSV で管理し `E_lookup` で参照。
* **Traceability**：すべての生成ノードに `source_ids`, `transformation` プロパティを付与。

---

# あなたの例に即した「変換スクリプト」スニペット（擬似JSON）

```json
{
  "transformations": [
    {
      "id": "normalize_type",
      "op": "rename_prop_value",
      "target": "Product.type",
      "map": {"gass":"gas", "electricty":"electricity"}
    },
    {
      "id": "aggregate_factory_activity",
      "op": "aggregate",
      "group_by": ["factory","product"],
      "aggregate": {"value":"sum"},
      "output_type": "Activity"
    },
    {
      "id": "apply_emission_factors",
      "op": "enrich_and_multiply",
      "lookup_table": "EmissionFactor",
      "lookup_key": "fuel",
      "output_type": "Emission",
      "emit_scope_field": "scope",
      "store_provenance": true
    },
    {
      "id": "compute_totals",
      "op": "aggregate",
      "group_by": ["GHGReport"],
      "aggregate": {"emission.value":"sum"},
      "output_field_map": {"sum":"total_emission"}
    }
  ]
}
```

---

# まとめ（実務的チェックリスト）

1. **スキーマ（オントロジー）変換規則**を明文化し、ruleset として保存する。
2. **変換は段階的に実行**（level1→level2→level3）、各段階で provenance を残す。
3. **単位／係数管理**を外部テーブルで一元化し、変換時に必ず検証。
4. **集約は不可逆**なので raw level1 を保持（監査用）。
5. **ルールはテスト可能に**（小さな事例データで結果検証→自動化）。

---


