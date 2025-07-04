import sys
from pathlib import Path

import pandas as pd
import great_expectations as ge


def run_data_tests(df_rh: pd.DataFrame) -> None:
    """Vérifie que les colonnes critiques ne sont pas nulles."""
    validator = ge.dataset.PandasDataset(df_rh)

    for col in ["id_salarie", "date_naissance", "date_embauche"]:
        validator.expect_column_values_to_not_be_null(col)

    results = validator.validate()
    if not results.success:
        failed = {
            r.expectation_config.kwargs["column"]
            for r in results.results
            if not r.success
        }
        raise RuntimeError(
            f"❌ Colonnes avec valeurs nulles : {', '.join(failed)}"
        )

    print("✅ Toutes les colonnes critiques contiennent des valeurs non nulles.")


if __name__ == "__main__":
    # 1) Chargement
    root = Path(__file__).resolve().parents[1]
    rh_file = root / "data" / "Donnees_RH.xlsx"
    df_rh = pd.read_excel(rh_file, dtype={"ID salarié": str})

    # 2) Renommage + sélection
    df_rh = (
        df_rh.rename(columns={
            "ID salarié":        "id_salarie",
            "Date de naissance": "date_naissance",
            "Date d'embauche":   "date_embauche",
        })
        [["id_salarie", "date_naissance", "date_embauche"]]
    )

    # 3) Test & sortie
    try:
        run_data_tests(df_rh)
        sys.exit(0)
    except Exception as e:
        print(f"❌ Erreur lors de la validation : {e}")
        sys.exit(1)
