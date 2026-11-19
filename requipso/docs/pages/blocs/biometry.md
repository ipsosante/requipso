# `Biometry` : mesures biométriques

{{ bloc_resume("Biometry") }}

## Ce que fait le bloc

Renvoie une mesure biométrique du patient (poids, taille, tension, IMC…). Par défaut, il renvoie la
**dernière** mesure connue, telle quelle.

## Données utilisées

| Table | Colonnes |
| --- | --- |
| `biometry` | `patient_id`, `biometry_label`, `biometry_value`, `biometry_date` |
| `patient` | `patient_id`, `patient_birth_date` (pour l'IMC) |

## Détail du calcul

- `value` = le libellé de la mesure (obligatoire), parmi le tableau ci-dessous.
- Une ligne par mesure ; `x` = la valeur mesurée ; `start_date` = `end_date` = date de la consultation.
- Les valeurs **hors des bornes de plausibilité** sont écartées (erreurs de saisie).
- `agg_func = LAST(x)` garde la mesure **la plus récente** (après `date_sql`).

| `value` | Mesure | Bornes gardées |
| --- | --- | --- |
| `weight` | Poids (kg) | 1 – 250 |
| `height` | Taille (cm) | 30 – 230 |
| `bmi` | IMC (kg/m²), **calculé** | 10 – 60 |
| `blood_pressure_systolic` | Pression artérielle systolique (mmHg) | 30 – 250 |
| `blood_pressure_diastolic` | Pression artérielle diastolique (mmHg) | 10 – 150 |
| `heart_rate` | Fréquence cardiaque (/min) | 25 – 220 |
| `temperature` | Température (°C) | 35 – 41 |
| `spo2` | Saturation en oxygène (%) | 60 – 100 |
| `respiratory_rate` | Fréquence respiratoire (/min) | 5 – 50 |
| `glycemia` | Glycémie capillaire (g/L) | 0,1 – 10 |
| `head_circumference` | Périmètre crânien (cm) | 20 – 65 |
| `waist_size` | Tour de taille (cm) | 20 – 120 |
| `peak_expiratory_flow` | Débit expiratoire de pointe (L/min) | 50 – 1000 |
| `uterine_height` | Hauteur utérine (cm) | 0 – 40 |
| `cardio_fetal_rhythm` | Rythme cardiaque fœtal (/min) | 25 – 220 |
| `digital_visual_scale` | Échelle visuelle numérique de la douleur | 0 – 10 |

### Le cas de l'IMC

L'IMC n'est pas saisi : il est **calculé** à partir du poids et de la taille.

1. Pour chaque mesure de poids, on cherche la mesure de taille du même patient **la plus proche dans
   le temps**.
2. Le couple n'est gardé que si l'écart entre les deux mesures est acceptable, selon l'âge au moment
   de la mesure de taille :

    | Âge à la mesure de taille | Écart maximal poids / taille |
    | --- | --- |
    | moins de 1 an | aucun couple gardé (voir ci-dessous) |
    | 1 à 18 ans | moins d'un an |
    | plus de 18 ans | moins de 5 ans |

3. IMC = poids (kg) / taille (m)², daté à la date du poids.

## Paramètres

{{ bloc_parametres("Biometry") }}

## Exemples

=== "Inclusion : IMC ≥ 30 (dernier connu)"

    | block_name | block_type | value | post_func | date_sql |
    | --- | --- | --- | --- | --- |
    | `obeses` | `Biometry` | `bmi` | `x >= 30` | `start_date <= reference_date` |

=== "Inclusion : au moins une tension mesurée dans l'année"

    | block_name | block_type | value | agg_func | post_func | date_sql |
    | --- | --- | --- | --- | --- | --- |
    | `pas_12m` | `Biometry` | `blood_pressure_systolic` | `COUNT(x)` | `x >= 1` | `start_date >= reference_date - INTERVAL '1 year' AND start_date <= reference_date` |

=== "Tableau : IMC en classes"

    | block_name | block_type | variable_type | value | subsets |
    | --- | --- | --- | --- | --- |
    | `imc` | `Biometry` | `numerical` | `bmi` | `[0, 18.5, 25, 30, 35]` |

=== "Tableau : poids maximal"

    | block_name | block_type | variable_type | value | agg_func |
    | --- | --- | --- | --- | --- |
    | `poids_max` | `Biometry` | `numerical` | `weight` | `MAX(x)` |

## Points d'attention

- Sans `date_sql`, « la dernière mesure » peut être **postérieure** à la date de référence. Ajoutez
  `start_date <= reference_date` pour la dernière mesure connue à cette date.
- Ici `post_func = x` par défaut : pour l'inclusion, il faut écrire une condition (ex. `x >= 30`),
  sinon l'étape ne renvoie pas un vrai/faux.
- L'IMC n'est actuellement **jamais calculé pour les nourrissons de moins d'un an** (la règle exige
  un écart strictement inférieur à 0 jour).
- La glycémie est exprimée en **g/L** (bornes 0,1 – 10).
