# 🏃‍♂️ Projet **Avantages Sportifs**

## 🎯 Introduction

**Avantages Sportifs** est une **solution de pipeline de données 100 % conteneurisée**, conçue pour promouvoir l’activité sportive au sein de l’entreprise.  

Elle permet de :  

1️⃣ **Capturer** et historiser les activités sportives des collaborateurs dans une base **PostgreSQL**  
2️⃣ **Diffuser** ces événements en temps réel via **Redpanda (Kafka)**  
3️⃣ **Notifier** automatiquement dans **Slack** les activités des collaborateurs pour les motiver  
4️⃣ **Calculer** et attribuer les **avantages salariés** en fonction de leur pratique sportive  

📌 **Orchestration & Monitoring**  
L’ensemble est orchestré par **Airflow** et supervisé par **Prometheus & Grafana** pour garantir fiabilité et performance de bout en bout.  

---

## 📁 Structure du projet

```text
├── database/
│   ├── init/             # scripts d'initialisation PostgreSQL
│   └── fresh_pgdata/     # volume de données PostgreSQL
│
├── airflow/
│   ├── dags/             # définitions des DAGs Airflow
│   ├── logs/             # logs Airflow
│   └── plugins/          # plugins personnalisés
│
├── kafka_slack_consumer/ # code Python du consumer Kafka → Slack
│   └── consumer.py
│
├── monitoring/
│   └── prometheus.yml    # configuration Prometheus
│
├── docker-compose.yml    # composition de tous les services
├── .env                  # variables d’environnement
└── README.md             # ce document


✅ 1. Prérequis
Docker

Docker Compose

Un fichier .env à la racine du projet, contenant notamment :


SLACK_BOT_TOKEN=
SLACK_CHANNEL=
GOOGLE_MAPS_API_KEY=x
ENTREPRISE_ADRESSE=
PRIME_RATE=
WB_THRESHOLD=
DEP_LIMIT_MARCHE=
DEP_LIMIT_VELO=
DEP_LIMIT_TROTT=
JOURS_BIEN_ETRE=
KAFKA_BOOTSTRAP_SERVERS=
KAFKA_TOPIC=
POSTGRES_USER=
POSTGRES_PASSWORD=
POSTGRES_DB=
POSTGRES_HOST=
POSTGRES_PORT=

🚀 2. Démarrage rapide
1️⃣ Cloner le dépôt

git clone git@github.com:Phoenix9408/Avantages-Sportif.git

cd Avantages-Sportif

2️⃣ Lancer tous les services

docker-compose up -d

3️⃣ Vérifier la santé des services

docker-compose ps


🌐 3. Accès aux interfaces


| Service         | URL d’accès                                    |
| --------------- | ---------------------------------------------- |
| **pgAdmin**     | [http://localhost:5050](http://localhost:5050) |
| **Redpanda UI** | [http://localhost:8080](http://localhost:8080) |
| **Airflow UI**  | [http://localhost:8089](http://localhost:8089) |
| **Grafana**     | [http://localhost:3000](http://localhost:3000) |


🏗 4. Architecture détaillée


<img width="3497" height="1914" alt="Untitled Diagram drawio (2)" src="https://github.com/user-attachments/assets/06d73db8-855e-4174-bd35-46d7fa88c6cf" />


🔮 5. Conclusion & perspectives
✅ Cette plateforme fournit déjà un pipeline bout-en-bout robuste et observable

🚀 Perspectives d’évolution :

Ajout d’une application mobile déclarative en temps réel (Flutter) pour envoyer directement les nouveaux événements sportifs vers public.activites_sportives_event

Intégration d’un système de scoring et de gamification

Dashboard interactif pour visualiser les performances sportives

🤝 Auteurs & Licence
👤 Auteur : Ali BRIK
📊 Data Engineering – Pipeline Kafka/Airflow/Slack

📜 Licence : MIT

✨ N’hésitez pas à ⭐ ce dépôt si vous le trouvez utile !
