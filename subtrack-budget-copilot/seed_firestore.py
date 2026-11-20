"""Seed initial subscription data into Cloud Firestore."""

from google.cloud import firestore

PROJECT_ID = "qwiklabs-gcp-03-edd919b74a48"
COLLECTION_NAME = "subscriptions"

SEED_SUBSCRIPTIONS = [
    {
        "id": "netflix",
        "name": "Netflix Premium",
        "category": "Entertainment",
        "cost": 22.99,
        "currency": "USD",
        "billing_cycle": "monthly",
        "renewal_day": 15,
        "status": "active",
        "cancellation_difficulty": "easy",
        "description": "4K streaming service for family.",
    },
    {
        "id": "spotify",
        "name": "Spotify Duo",
        "category": "Entertainment",
        "cost": 14.99,
        "currency": "USD",
        "billing_cycle": "monthly",
        "renewal_day": 1,
        "status": "active",
        "cancellation_difficulty": "easy",
        "description": "Music and podcast streaming.",
    },
    {
        "id": "chatgpt_plus",
        "name": "ChatGPT Plus",
        "category": "Productivity",
        "cost": 20.00,
        "currency": "USD",
        "billing_cycle": "monthly",
        "renewal_day": 10,
        "status": "active",
        "cancellation_difficulty": "easy",
        "description": "AI assistance and advanced reasoning tools.",
    },
    {
        "id": "github_copilot",
        "name": "GitHub Copilot Individual",
        "category": "Productivity",
        "cost": 10.00,
        "currency": "USD",
        "billing_cycle": "monthly",
        "renewal_day": 20,
        "status": "active",
        "cancellation_difficulty": "easy",
        "description": "Code completion and developer productivity.",
    },
    {
        "id": "gym_membership",
        "name": "Equinox Fitness",
        "category": "Health & Fitness",
        "cost": 150.00,
        "currency": "USD",
        "billing_cycle": "monthly",
        "renewal_day": 5,
        "status": "active",
        "cancellation_difficulty": "hard",
        "description": "Local gym and wellness club membership.",
    },
]


def seed_database():
    print(f"Connecting to Firestore for project: {PROJECT_ID}...")
    db = firestore.Client(project=PROJECT_ID)
    collection = db.collection(COLLECTION_NAME)

    for item in SEED_SUBSCRIPTIONS:
        doc_id = item["id"]
        doc_ref = collection.document(doc_id)
        doc_ref.set(item)
        print(f"  ✓ Seeded: {item['name']} ({item['cost']} {item['currency']}/{item['billing_cycle']})")

    print(f"Successfully seeded {len(SEED_SUBSCRIPTIONS)} subscriptions into '{COLLECTION_NAME}'.")


if __name__ == "__main__":
    seed_database()
