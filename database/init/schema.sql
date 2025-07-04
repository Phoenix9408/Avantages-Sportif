CREATE SCHEMA IF NOT EXISTS priv;
CREATE SCHEMA IF NOT EXISTS airflow;
CREATE ROLE airflow LOGIN PASSWORD 'airflow';
GRANT USAGE  ON SCHEMA airflow TO airflow;
GRANT CREATE ON SCHEMA airflow TO airflow;

GRANT ALL PRIVILEGES ON DATABASE sport_avantages TO airflow;

ALTER ROLE airflow SET search_path = airflow,public;

-- 2.1) identités (clé composite)
CREATE TABLE IF NOT EXISTS priv.identites (
  id_salarie  INTEGER,
  d_jour      DATE NOT NULL DEFAULT CURRENT_DATE,
  nom         TEXT NOT NULL,
  prenom      TEXT NOT NULL,
  adresse     TEXT,
  date_naissance DATE,
  salaire_brut  NUMERIC,
  bu          TEXT,
  date_embauche DATE,
  type_contrat  TEXT,
  PRIMARY KEY (id_salarie, d_jour)
);

-- 2.2) employés_tech
CREATE TABLE IF NOT EXISTS public.employes_tech (
  id_salarie  INTEGER,
  d_jour      DATE NOT NULL DEFAULT CURRENT_DATE,
  jours_cp      INTEGER,
  moyen_deplacement TEXT,
  PRIMARY KEY (id_salarie, d_jour),
  FOREIGN KEY (id_salarie, d_jour)
    REFERENCES priv.identites(id_salarie, d_jour)
    ON DELETE CASCADE
);

-- 2.3) activités sportives
CREATE TABLE IF NOT EXISTS public.activites_sportives (
  id_salarie  INTEGER,
  d_jour      DATE NOT NULL DEFAULT CURRENT_DATE,
  date_debut  TIMESTAMP,
  type        TEXT,
  distance_m  NUMERIC,
  date_fin    TIMESTAMP,
  commentaire TEXT,
  PRIMARY KEY (id_salarie, d_jour, date_debut),
  FOREIGN KEY (id_salarie, d_jour)
    REFERENCES priv.identites(id_salarie, d_jour)
    ON DELETE CASCADE
);

-- 2.4) évènements d’activités
CREATE TABLE IF NOT EXISTS public.activites_sportives_event (
  id_salarie  INTEGER,
  d_jour      DATE NOT NULL DEFAULT CURRENT_DATE,
  date_debut  TIMESTAMP,
  type        TEXT,
  distance_m  NUMERIC,
  date_fin    TIMESTAMP,
  commentaire TEXT,
  PRIMARY KEY (id_salarie, d_jour, date_debut),
  FOREIGN KEY (id_salarie, d_jour)
    REFERENCES priv.identites(id_salarie, d_jour)
    ON DELETE CASCADE
);

-- 2.5) avantages
CREATE TABLE IF NOT EXISTS public.avantages (
  id_salarie      INTEGER,
  d_jour          DATE NOT NULL DEFAULT CURRENT_DATE,
  nb_activites    INTEGER,
  prime_5         NUMERIC,
  jours_bien_etre INTEGER,
  PRIMARY KEY (id_salarie, d_jour),
  FOREIGN KEY (id_salarie, d_jour)
    REFERENCES public.employes_tech(id_salarie, d_jour)
    ON DELETE CASCADE
);

