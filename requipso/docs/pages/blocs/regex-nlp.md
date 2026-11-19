# Recherche dans le texte libre

Les blocs [`RegexConsultation`](regex-consultation.md) et
[`RegexPatientObservation`](regex-patient-observation.md) recherchent des mots ou expressions dans
le **texte libre** du dossier médical (notes de consultation, antécédents…). Ils reposent sur la
bibliothèque de traitement du langage [edsnlp](https://aphp.github.io/edsnlp/), développée par l'AP-HP
pour les textes médicaux en français.

Ils sont utiles quand l'information n'est pas codée : un symptôme, une habitude de vie, une
pathologie mal reconnue…

## Deux façons de chercher

### 1. Des motifs (expressions régulières)

Écrivez dans `value` un ou plusieurs motifs séparés par `|` :

| `value` | Trouve |
| --- | --- |
| `diabete` | « diabète », « Diabète », « DIABETE »… |
| `diabete|dt2|dnid` | l'un des trois termes |
| `insuffisan\w* renal\w*` | « insuffisance rénale », « insuffisant rénal »… |
| `\bhta\b` | « HTA » comme mot entier (pas « ahta ») |

!!! danger "Écrivez sans accents"
    Le texte est **normalisé avant la recherche** : passage en minuscules et suppression des accents.
    Un motif contenant un accent (`diabète`) ne trouve **jamais rien**. Écrivez `diabete`, `renal`,
    `pre-eclampsie`… La casse n'a pas d'importance.

Quelques éléments d'écriture des motifs :

| Symbole | Signification | Exemple |
| --- | --- | --- |
| `|` | ou | `asthme|bpco` |
| `.` | n'importe quel caractère | `diab.te` |
| `\w*` | une suite de lettres (éventuellement vide) | `diabet\w*` → diabète, diabétique |
| `\b` | limite de mot | `\bavc\b` |
| `\s+` | un ou plusieurs espaces | `type\s+2` |
| `?` | le caractère précédent est facultatif | `diabetiques?` |

### 2. Un pipeline edsnlp prêt à l'emploi

edsnlp fournit des détecteurs déjà construits pour certaines pathologies (avec leurs nombreuses
façons d'être écrites). Écrivez `edsnlp.` suivi du nom, **seul** dans `value` :

| `value` | Détecte |
| --- | --- |
| `edsnlp.diabetes` | Diabète |
| `edsnlp.tobacco` | Tabagisme |
| `edsnlp.alcohol` | Consommation d'alcool |
| `edsnlp.ckd` | Insuffisance rénale chronique |
| `edsnlp.copd` | BPCO |
| `edsnlp.congestive_heart_failure` | Insuffisance cardiaque |
| `edsnlp.myocardial_infarction` | Infarctus du myocarde |
| `edsnlp.cerebrovascular_accident` | AVC |
| `edsnlp.peripheral_vascular_disease` | Artériopathie périphérique |
| `edsnlp.dementia` | Démence |
| `edsnlp.liver_disease` | Maladie hépatique |
| `edsnlp.solid_tumor` | Tumeur solide |
| `edsnlp.covid` | COVID-19 |

La liste complète est dans la [documentation edsnlp](https://aphp.github.io/edsnlp/latest/pipes/).

!!! note "Un seul pipeline à la fois"
    `edsnlp.xxx` doit être la **seule** valeur de la cellule. Pour combiner plusieurs pipelines, ou un
    pipeline et des motifs, utilisez un [groupe](../guide/combiner-blocs.md) `OR`.

## Les qualificatifs : négation, hypothèse…

Trouver le mot « diabète » ne suffit pas : « pas de diabète » ou « suspicion de diabète » ne doivent
pas compter. Après la recherche, chaque mention est **qualifiée** ; les mentions qui portent l'un des
qualificatifs listés dans le paramètre `qualifiers` sont **écartées**.

| Qualificatif | Écarte les mentions du type | Actif par défaut |
| --- | --- | --- |
| `negation` | « pas de diabète », « absence d'HTA » | Oui |
| `hypothesis` | « suspicion de diabète », « diabète ? » | Oui |
| `family` | « père diabétique » | Non |
| `history` | « antécédent de… » (mention ancienne) | Non |
| `reported_speech` | « le patient dit avoir… » | Non |

Pour modifier la liste, utilisez `supplementary_params` :

```text
{"qualifiers": ["negation", "hypothesis", "family"]}
```

`{"qualifiers": []}` garde toutes les mentions, sans qualification.

Les qualificatifs s'appliquent à la **phrase** de la mention. Les retours à la ligne suivis d'un
tiret (`- diabète`) sont considérés comme des fins de phrase : dans une liste à puces, la négation
d'une ligne ne déborde pas sur la suivante.

## Ce que renvoient ces blocs

- Une ligne par **mention trouvée** ; `x` = le texte trouvé, tel qu'il est écrit dans la note
  (ex. `Diabète`).
- Par défaut, `agg_func = COUNT(x)` compte les mentions et `post_func = x>=1` garde les patients avec
  au moins une mention.
- Pour voir les formulations trouvées dans le tableau descriptif, utilisez par exemple
  `variable_type = categorical`, `agg_func = FIRST(x)`, `post_func = x`.

## Performances

L'analyse de texte est **beaucoup plus lente** que les autres blocs (plusieurs minutes sur toute la
base). Elle ne traite que les patients retenus par l'étape parente : placez ces blocs **le plus bas
possible** dans le flowchart.
