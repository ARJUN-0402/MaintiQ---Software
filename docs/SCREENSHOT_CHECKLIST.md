# MaintiQ Screenshot Checklist — University Demonstration

**Application:** MaintiQ v0.2.0  
**Rule:** Only real screenshots captured from the running application are included.
No screenshots are fabricated. Screenshots below were captured from the actual
PySide6 application (`python -m maintiq`, Qt offscreen render of the real
`MainWindow` and page widgets).

## Captured screenshots

| # | Screen | File | Status |
|---|--------|------|--------|
| 1 | Main window — sidebar navigation (12 pages), menu bar, status bar, academic-prototype banner | `docs/screenshots/main_window.png` | Captured |
| 2 | Dashboard — dataset/model status, quick navigation | `docs/screenshots/dashboard.png` | Captured |
| 3 | Predict Failure — six-attribute input form, result cards, explain action | `docs/screenshots/predict_failure.png` | Captured |
| 4 | Model Registry — versions table, details panel, delete actions | `docs/screenshots/model_registry.png` | Captured |
| 5 | Reports and Downloads — report type selector, export button | `docs/screenshots/reports_downloads.png` | Captured |
| 6 | About / Project Limitations — title, version, academic notice | `docs/screenshots/about_limitations.png` | Captured |

## To capture from the built `MaintiQ.exe`

Capture these from the installed/portable build after the Windows Smart App
Control block is resolved (EV code-signed executable or end-user policy bypass;
the unsigned EXE is blocked in this environment):

| # | Screen | Notes |
|---|--------|-------|
| 7 | Dataset Explorer — CSV import dialog, validation messages, dataset profile | Real import flow with the AI4I CSV |
| 8 | Model Training — model selection, progress bar, safe cancellation | Training running on a background worker |
| 9 | Predict Failure — completed prediction (class, score, threshold) with SHAP/LIME explanation panel | SHAP/LIME availability depends on the environment |
| 10 | Model Performance — metrics, confusion matrix, ROC/PR curves, model comparison | After an end-to-end training run |
| 11 | Threshold Analysis — FP/FN trade-off curves, recommended threshold | - |
| 12 | Reports and Downloads — native save dialog, exported files on disk | JSON/CSV/PNG export |
| 13 | Settings — default model and threshold persisted | - |

## How screenshots were captured

`docs/screenshots/main_window.png` and the page screenshots were rendered by the
actual MaintiQ UI code (`src/maintiq/ui/`) with `QT_QPA_PLATFORM=offscreen`
using `QWidget.grab()`, then saved as PNG. They are real renders of the
application, not mockups.

## Demonstration notes

- Show the persistent academic-prototype notice banner in the main window and
  the same disclaimer in generated reports.
- The AI4I 2020 dataset is not bundled; demonstrate import from a local CSV.
- No default trained model is shipped; train a model (Logistic Regression,
  Random Forest, Gradient Boosting, or XGBoost) before demonstrating prediction.
- If SHAP is unavailable in the demo environment, demonstrate LIME and the
  clear "SHAP unavailable" message rather than simulating explanations.
