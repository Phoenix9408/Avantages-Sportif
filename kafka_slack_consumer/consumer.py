import os
import json
import time
import base64
import random
import decimal
import logging
from datetime import datetime, timedelta

import psycopg2
from kafka import KafkaConsumer
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# ──────────── Config ────────────────────────────────────────────────────────
TOPIC = os.getenv("KAFKA_TOPIC", "activites.public.activites_sportives_event")
BROKERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "redpanda:9092")

SLACK_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_CHANNEL = os.environ["SLACK_CHANNEL"]

PG = {
    "host": os.getenv("POSTGRES_HOST", "postgres"),
    "port": int(os.getenv("POSTGRES_PORT", 5432)),
    "user": os.getenv("POSTGRES_USER", "USRBTCH"),
    "password": os.getenv("POSTGRES_PASSWORD", "USRBTCH"),
    "dbname": os.getenv("POSTGRES_DB", "sport_avantages"),
}

MIN_INTERVAL_S = 1.0  
HARD_LIMIT_PM = 50   

TEMPLATES = [
    "Bravo {prenom} {nom} ! Tu viens de faire {distance} km en {duree} min ! Quelle énergie ! 🔥🏅",
    "Super sortie {prenom} ! {type_activite} de {distance} km terminée avec succès 💪",
    "Magnifique effort {prenom} {nom} ! Tu as conquis {distance} km aujourd'hui 🚴‍♂️",
    "Respect {prenom} ! {type_activite} intense de {duree} minutes – tu inspires toute l’équipe ⭐",
]
# ─────────────────────────────────────────────────────────────────────────────

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)7s %(message)s")
slack = WebClient(token=SLACK_TOKEN)

# ──────────── Helpers ───────────────────────────────────────────────────────

def decode_decimal(field: dict | None) -> decimal.Decimal | None:
    """Décode un champ DECIMAL Debezium en mètres (Decimal)"""
    if not field or not isinstance(field, dict):
        return None
    raw = int.from_bytes(base64.b64decode(field["value"]), "big", signed=True)
    return decimal.Decimal(raw).scaleb(-field["scale"])  # mètres


def fetch_identite(cur, id_salarie: int):
    cur.execute("SELECT nom, prenom FROM priv.identites WHERE id_salarie=%s;", (id_salarie,))
    return cur.fetchone() or ("Inconnu", "Inconnu")


def build_message(act: dict, cur) -> str:
    nom, prenom = fetch_identite(cur, act["id_salarie"])
    dist_m = decode_decimal(act["distance_m"])
    dist_km = round(dist_m / 1000, 1) if dist_m is not None else "?"
    type_act = act.get("type") or "Activité"

    debut = datetime.fromtimestamp(act["date_debut"] // 1_000_000)
    fin = datetime.fromtimestamp(act["date_fin"] // 1_000_000)
    duree = int((fin - debut).total_seconds() / 60)

    if type_act.lower() == "escalade":
        return f"🧗‍♂️ {prenom} {nom} a gravi de nouveaux sommets durant {duree} minutes ! 💪"

    return random.choice(TEMPLATES).format(
        nom=nom,
        prenom=prenom,
        distance=dist_km,
        duree=duree,
        type_activite=type_act,
    )

# ──────────── Boucle principale ─────────────────────────────────────────────

def main() -> None:
    consumer = KafkaConsumer(
        TOPIC,
        bootstrap_servers=BROKERS,
        group_id="slack-group",
        enable_auto_commit=False,
        auto_offset_reset="latest",
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
    )

    with psycopg2.connect(**PG) as conn, conn.cursor() as cur:
        logging.info(" En attente de messages Kafka sur %s …", TOPIC)

        sent_this_min = 0
        minute_window = datetime.utcnow().replace(second=0, microsecond=0)
        last_send_ts = 0.0  # timestamp du dernier post Slack

        for msg in consumer:
            payload = msg.value.get("payload", {})
            after = payload.get("after")
            if not after:
                consumer.commit()
                continue

            # ─── quota minute ────────────────────────────────────────────
            now = datetime.utcnow()
            if now >= minute_window + timedelta(minutes=1):
                minute_window = now.replace(second=0, microsecond=0)
                sent_this_min = 0
            if sent_this_min >= HARD_LIMIT_PM:
                sleep = (minute_window + timedelta(minutes=1) - now).total_seconds()
                logging.warning("Rate-limit Slack : pause %.0fs (quota/minute dépassé)", sleep)
                time.sleep(sleep)
                minute_window = datetime.utcnow().replace(second=0, microsecond=0)
                sent_this_min = 0

            # ─── intervalle 1 msg/s ──────────────────────────────────────
            delta = MIN_INTERVAL_S - (time.time() - last_send_ts)
            if delta > 0:
                time.sleep(delta)

            text = build_message(after, cur)

            try:
                slack.chat_postMessage(channel=SLACK_CHANNEL, text=text)
                logging.info("Slack : publié.")
                sent_this_min += 1
                last_send_ts = time.time()
                consumer.commit()  #  offset confirmé

            except SlackApiError as e:
                err = e.response["error"]
                if e.response.status_code == 429 or err in {
                    "rate_limited",
                    "message_limit_exceeded",
                    "channel_rate_limited",
                }:
                    retry = int(e.response.headers.get("Retry-After", 5))
                    logging.warning("Rate-limit Slack (%s) : pause %ss", err, retry)
                    time.sleep(retry)
                    # l’offset n'est PAS commité → on retentera ce message
                else:
                    logging.error("Erreur Slack : %s", err)
                    consumer.commit()  # on ignore et on passe


if __name__ == "__main__":
    main()
