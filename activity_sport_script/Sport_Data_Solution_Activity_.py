import os
from pathlib import Path
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
import requests


# ────────────────────────────────────────────────────────────────
# Chemins des fichiers
# ────────────────────────────────────────────────────────────────
ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
RH_FILE = DATA_DIR / "Donnees_RH.xlsx"
ACTIVITIES_FILE = DATA_DIR / "activites_sportives.csv"
SPORT_FILE = DATA_DIR / "Donnees_Sportive.xlsx"

# ────────────────────────────────────────────────────────────────
# Paramètres de connexion PostgreSQL
# ────────────────────────────────────────────────────────────────
DB_PARAMS = {
    "user": os.getenv("POSTGRES_USER", "USRBTCH"),
    "password": os.getenv("POSTGRES_PASSWORD", "USRBTCH"),
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": os.getenv("POSTGRES_PORT", "5432"),
    "dbname": os.getenv("POSTGRES_DB", "sport_avantages"),
}

# ────────────────────────────────────────────────────────────────
# Paramètres métier
# ────────────────────────────────────────────────────────────────
PRIME_RATE = float(os.getenv("PRIME_RATE", "0.05"))
JOURS_BIEN_ETRE = int(os.getenv("JOURS_BIEN_ETRE", "5")) 
WB_THRESHOLD = int(os.getenv("WB_THRESHOLD", "5")) 

# Limites km par mode de déplacement
DEP_LIMIT_MARCHE = float(os.getenv("DEP_LIMIT_MARCHE", "15"))
DEP_LIMIT_VELO = float(os.getenv("DEP_LIMIT_VELO", "25"))
LIMITES_KM = {
    "Marche/running": DEP_LIMIT_MARCHE,
    "Vélo/Trottinette/Autres": DEP_LIMIT_VELO,
}

# ────────────────────────────────────────────────────────────────
# Google Maps API
# ────────────────────────────────────────────────────────────────
ENTREPRISE_ADRESSE = os.getenv("ENTREPRISE_ADRESSE")
GOOGLE_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
DISTANCE_URL = "https://maps.googleapis.com/maps/api/distancematrix/json"


# ────────────────────────────────────────────────────────────────
# Tests de cohérence via Great Expectations
# ────────────────────────────────────────────────────────────────
def run_data_tests(df_rh: pd.DataFrame, df_act: pd.DataFrame, df_ctrl: pd.DataFrame) -> None:
    """
    Exécute des tests basiques sur les DataFrames :
      - df_rh  : id_salarie non null, dates valides
      - df_act : distance_m non négative
      - df_ctrl: distance_km non négative
    """
    # Vérifications RH
    rh_ge = ge.from_pandas(df_rh)
    rh_ge.expect_column_values_to_not_be_null("id_salarie")
    rh_ge.expect_column_values_to_be_valid_datetime("date_naissance")
    rh_ge.expect_column_values_to_be_valid_datetime("date_embauche")
    # Vérifications activités
    act_ge = ge.from_pandas(df_act)
    act_ge.expect_column_values_to_not_be_null("id_salarie")
    act_ge.expect_column_values_to_be_between("distance_m", min_value=0)
    # Vérifications contrôle déplacements
    ctrl_ge = ge.from_pandas(df_ctrl)
    ctrl_ge.expect_column_values_to_not_be_null("distance_km")
    ctrl_ge.expect_column_values_to_be_between("distance_km", min_value=0)
    # Validation
    results = {
        "RH": rh_ge.validate(),
        "ACT": act_ge.validate(),
        "CTRL": ctrl_ge.validate(),
    }
    for name, res in results.items():
        if not res.success:
            raise RuntimeError(f"Tests de cohérence échoués pour {name}: {res}")

def calculer_distance(adresse_domicile: str, mode: str) -> float | None:
    """Appelle Google Maps Distance Matrix et renvoie la distance en km"""
    if not GOOGLE_API_KEY:
        raise RuntimeError("Il faut définir GOOGLE_MAPS_API_KEY")
    # Mapping des modes RH vers API
    mode_api = {
        "Marche/running": "walking",
        "Vélo/Trottinette/Autres": "bicycling",
    }.get(mode, "walking")
    params = {
        "origins": adresse_domicile,
        "destinations": ENTREPRISE_ADRESSE,
        "mode": mode_api,
        "key": GOOGLE_API_KEY,
    }
    r = requests.get(DISTANCE_URL, params=params, timeout=5)
    r.raise_for_status()
    elt = r.json()["rows"][0]["elements"][0]
    if elt.get("status") != "OK":
        return None
    return elt["distance"]["value"] / 1000  # m→km


def verifier_deplacements(df_rh: pd.DataFrame) -> None:
    """
    Exporte un CSV avec pour chaque salarié la distance calculée,
    le seuil et un flag 'anomalie' = True si dépassement
    """
    lignes = []
    for _, row in df_rh.iterrows():
        mode = row["moyen_deplacement"]
        if mode not in LIMITES_KM:
            continue
        adresse = row["adresse"]
        dist = calculer_distance(adresse, mode)
        seuil = LIMITES_KM[mode]
        lignes.append({
            "id_salarie": row["id_salarie"],
            "adresse": adresse,
            "mode": mode,
            "distance_km": dist,
            "seuil_km": seuil,
            "anomalie": (dist is None or dist > seuil)
        })
    df_ctrl = pd.DataFrame(lignes)
    ctr_file = DATA_DIR / "controle_deplacements.csv"
    df_ctrl.to_csv(ctr_file, index=False, encoding="utf-8-sig")
    print(f"[Stats-DEP] distances et flags exportés → {ctr_file}")


def load_all_data() -> None:
    # 1) RH: chargement & nettoyage
    df_rh = pd.read_excel(RH_FILE, dtype={"ID salarié": str})
    df_rh = df_rh.rename(columns={
        "ID salarié": "id_salarie",
        "Nom": "nom",
        "Prénom": "prenom",
        "Date de naissance": "date_naissance",
        "BU": "bu",
        "Date d'embauche": "date_embauche",
        "Salaire brut": "salaire_brut",
        "Type de contrat": "type_contrat",
        "Nombre de jours de CP": "jours_cp",
        "Adresse du domicile": "adresse",
        "Moyen de déplacement": "moyen_deplacement",
    }).dropna(subset=["id_salarie"])
    dup = df_rh.duplicated(subset=["id_salarie"], keep="first");
    print(f"[Stats-RH] doublons RH supprimés: {dup.sum()}")
    df_rh = df_rh[~dup]
    for c in ["date_naissance", "date_embauche"]:
        df_rh[c] = pd.to_datetime(df_rh[c], errors="coerce").dt.date

    # 2) Activités: ingestion & agrégation
    df_act = pd.read_csv(ACTIVITIES_FILE, dtype={"ID salarié": str})
    df_act = df_act.rename(columns={
        "ID salarié": "id_salarie",
        "Date de début": "date_debut",
        "Type": "type",
        "Distance (m)": "distance_m",
        "Date de fin": "date_fin",
        "Commentaire": "commentaire",
    }).query("id_salarie in @df_rh.id_salarie")
    dup2 = df_act.duplicated(subset=["id_salarie", "date_debut"], keep="first");
    print(f"[Stats-ACT] doublons source suppr : {dup2.sum()}")
    df_act = (df_act[~dup2]
              .groupby(["id_salarie", "date_debut"], as_index=False)
              .agg(date_debut=("date_debut", "min"),
                   type=("type", "first"),
                   distance_m=("distance_m", "sum"),
                   date_fin=("date_fin", "max"),
                   commentaire=("commentaire", "first")))

    # 3) Avantages: prime & nb activités
    df_adv = (df_act.groupby("id_salarie", as_index=False)
              .agg(nb_activites=("date_debut", "size"),
                   total_distance=("distance_m", "sum"))
              .merge(df_rh[["id_salarie", "salaire_brut", "moyen_deplacement"]], on="id_salarie"))
    df_adv["prime_5"] = df_adv.apply(
        lambda r: round(r["salaire_brut"] * PRIME_RATE, 2)
        if r["moyen_deplacement"] in LIMITES_KM else 0.0,
        axis=1
    )

    # 4) Jours bien-être : compter les sessions hors-travail
    df_sport = pd.read_excel(SPORT_FILE, dtype={"ID salarié": str})
    df_sport = df_sport.rename(columns={
        "ID salarié": "id_salarie",
        "Pratique d'un sport": "pratique_exterieure"
    })
    df_act_ext = df_act[df_act["id_salarie"].isin(df_sport["id_salarie"])].copy()
    df_sessions = (
        df_act_ext.groupby("id_salarie", as_index=False)
        .agg(nb_sessions=("date_debut", "size"))
    )
    df_adv = df_adv.merge(df_sessions, on="id_salarie", how="left").fillna({"nb_sessions": 0})
    df_adv["jours_bien_etre"] = df_adv["nb_sessions"].apply(lambda n: JOURS_BIEN_ETRE if n >= WB_THRESHOLD else 0)

    # 5) Chargement en base
    with psycopg2.connect(**DB_PARAMS) as conn, conn.cursor() as cur:
        # identites
        cols_i = ["id_salarie", "nom", "prenom", "adresse",
                  "date_naissance", "salaire_brut", "bu",
                  "date_embauche", "type_contrat"]
        vals_i = df_rh[cols_i].values.tolist()
        if vals_i:
            execute_values(cur,
                           "INSERT INTO priv.identites (id_salarie, nom, prenom, adresse, date_naissance, salaire_brut, bu, date_embauche, type_contrat) VALUES %s;",
                           vals_i)
        # employes_tech
        cols_t = ["id_salarie", "jours_cp", "moyen_deplacement"]
        vals_t = df_rh[cols_t].values.tolist()
        if vals_t:
            execute_values(cur, "INSERT INTO public.employes_tech (id_salarie, jours_cp, moyen_deplacement) VALUES %s;",
                           vals_t)
        # activites_sportives
        vals_a = df_act[["id_salarie", "date_debut", "type",
                         "distance_m", "date_fin", "commentaire"]].values.tolist()
        if vals_a:
            execute_values(cur,
                           "INSERT INTO public.activites_sportives (id_salarie, date_debut, type, distance_m, date_fin, commentaire) VALUES %s;",
                           vals_a)
        # avantages
        vals_adv = df_adv[["id_salarie", "nb_activites", "prime_5", "jours_bien_etre"]].values.tolist()
        if vals_adv:
            execute_values(cur,
                           "INSERT INTO public.avantages (id_salarie, nb_activites, prime_5, jours_bien_etre) VALUES %s;",
                           vals_adv)

    print("✓ Données chargées et insérées sans conflit.")

    # 6) Export CSV pour PowerBI
    df_export = df_rh[["id_salarie", "nom", "prenom", "salaire_brut"]].merge(
        df_adv[["id_salarie", "nb_activites", "prime_5", "jours_bien_etre"]], on="id_salarie", how="left"
    )
    export_file = DATA_DIR / "export_avantages.csv"
    df_export.to_csv(export_file, index=False, encoding="utf-8-sig")
    print(f"[Export] Table avantages exportée → {export_file}")

    # 7) Contrôle distances
    verifier_deplacements(df_rh)



if __name__ == "__main__":
    load_all_data()
