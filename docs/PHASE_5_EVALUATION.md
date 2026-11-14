# Phase 5 Evaluation — MaintiQ

Documentation for the evaluation, threshold analysis, model comparison,
charting, and reporting subsystems implemented in Phase 5.

## Metric definitions

For binary classification, `EvaluationService` computes and exposes:

| Metric | Definition | Undefined case |
|---|---|---|
| accuracy | (tp + tn) / n_samples | None (n_samples > 0 always) |
| precision | tp / (tp + fp) | 0.0 when tp + fp == 0 |
| recall | tp / (tp + fn) | 0.0 when tp + fn == 0 |
| f1 | 2·tp / (2·tp + fp + fn) | 0.0 when denominator == 0 |
| roc_auc | Mann-Whitney U: P(positive scores above negative) | None when single target class |
| specificity | tn / (tn + fp) | 0.0 when tn + fp == 0 |
| balanced_accuracy | (recall + specificity) / 2 | 0.0 when either component is 0.0 |
| fpr (false positive rate) | fp / (fp + tn) | 0.0 when fp + tn == 0 |
| fnr (false negative rate) | fn / (fn + tp) | 0.0 when fn + tp == 0 |
| average_precision | Area under precision-recall curve (step interpolation) | None when single target class |

Confusion matrix counts: `tn`, `fp`, `fn`, `tp`.

Zero-division policy: rates with a zero denominator are reported as `0.0`
(never NaN or Infinity). ROC-AUC and average precision are `None` when a
single target class is present. All values are JSON-safe primitives.

## Positive-class mapping

The positive-class probability column is identified by inspecting
`estimator.classes_` for class `1`. If `1` is present, its column index is
used. Otherwise the last column is used. Column index 1 is never assumed to
be positive without inspection.

## Split strategy and leakage prevention

### Mandatory leakage rule

Threshold selection **must not** use the final held-out test set. The test
set remains untouched until final evaluation of the chosen model/threshold.

### Recommended flow

1. Split data into train / validation / test (e.g. 64/16/20 or 60/20/20).
2. Train the model on the training partition only.
3. Score the validation partition to obtain validation probabilities.
4. Run `ThresholdAnalysisService.analyze()` on validation scores/targets.
5. Select the recommended threshold (maximizes validation F1 by default).
6. Evaluate on the held-out test set using the selected threshold.

### Recorded metadata

Random seed, split sizes/ratios, and the source of threshold selection
(``validation_source``) are recorded in metadata. The UI/report makes
explicit which data partition produced each metric.

## Threshold analysis

`ThresholdAnalysisService` computes per-threshold results for each candidate
threshold:

- threshold, precision, recall, f1, false positives, false negatives,
  true positives, true negatives, specificity.

### Default grid

`np.linspace(0.0, 1.0, 21)` → [0.00, 0.05, ..., 1.00]. The configured
default threshold (0.50) is included even if not on the grid.

### Recommendation

Default objective: maximize validation F1. Tie-breaking is deterministic:
closest to the default threshold (0.50), then the lowest threshold. An
optimized threshold is **not** presented as universally optimal or as a
clinical/industrial safety threshold; human review remains responsible.

## Model comparison

`ComparisonService` compares Logistic Regression, Random Forest, Gradient
Boosting, and XGBoost when each is available:

- Identical data partitions (same trainer instance, same random seed, same
  test size) and identical metric definitions across candidates.
- Records model display name, configuration, training outcome,
  artifact/version reference, and evaluation metrics.
- Unavailable models are reported with an explicit `status`/`reason`
  ("unavailable" or "failed") rather than fabricating results.
- Best model is selected only by the explicitly configured metric
  (default: F1). Models are **not** promoted solely by accuracy.
- Warning included: benchmark results do not establish production industrial
  reliability.

## Charts and visualisations

Charts use matplotlib (the project's adopted plotting library) and are
generated from actual calculated arrays/metrics only:

- Model metric comparison (bar chart)
- Confusion matrix (heatmap)
- ROC curve (when both target classes present)
- Precision-recall curve (when both target classes present)
- Threshold vs metric analysis (line chart)
- False positive / false negative trade-off (line chart)

Every chart has a title, axis labels, and legend where useful. Figures are
saved under the configured `reports/figures` directory. Figure handles are
closed after saving. One-class input is handled gracefully (ROC/PR charts
raise `ValueError` rather than producing fabricated curves).

## Reporting and exports

`ReportService` supports:

- **JSON** metrics/model comparison export — includes MaintiQ version, model
  family and registered version, dataset fingerprint, target definition,
  input feature names/order, random seed and split details, threshold and
  threshold-selection method, metrics and confusion matrix, creation
  timestamp, warnings/limitations.
- **CSV** threshold-analysis export — per-threshold metrics.
- **PNG** evaluation charts — delegates to the charts module.

Exports are written atomically where practical. Filenames are sanitized
and path traversal is prevented. No PDF generation in this phase.

## Limitations

- SHAP explanations are unavailable in environments where sklearn cluster
  extensions are blocked (e.g. Windows Application Control).
- Cross-process registry locking is not implemented (same-process threading
  lock only).
- AI4I 2020 dataset is not present in the repository; no benchmark metrics
  or training results are claimed without it.
- Threshold optimization is dataset-specific and not a substitute for human
  review.
