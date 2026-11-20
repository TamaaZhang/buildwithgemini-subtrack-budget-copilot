# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import base64
import re
import uuid
from typing import Any, Dict, List, Optional
from a2ui.basic_catalog.provider import BasicCatalog
from a2ui.schema.manager import A2uiSchemaManager
from google import genai
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.code_executors.agent_engine_sandbox_code_executor import AgentEngineSandboxCodeExecutor
from google.adk.models import Gemini
from google.adk.tools import ToolContext
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.genai import types
from google.cloud import firestore
from google.cloud import storage

from .a2ui_utils import a2ui_callback

PROJECT_ID = "qwiklabs-gcp-03-edd919b74a48"
BUCKET_NAME = "subtrack-budget-copilot-qwiklabs-gcp-03-edd919b74a48"
COLLECTION_NAME = "subscriptions"
MODEL = "gemini-3.8-flash"
IMAGE_MODEL = "gemini-3.1-flash-lite-image"
VIDEO_MODEL = "gemini-omni-flash-preview"

# Initialize Firestore client with hardcoded project ID
_db = None


def get_firestore_client() -> firestore.Client:
    global _db
    if _db is None:
        _db = firestore.Client(project=PROJECT_ID)
    return _db


def list_subscriptions(category: Optional[str] = None) -> List[Dict[str, Any]]:
    """Lists all tracked recurring subscriptions from Firestore, optionally filtered by category.

    Args:
        category: Optional category filter (e.g., 'Entertainment', 'Productivity', 'Health & Fitness').

    Returns:
        A list of subscription records with details such as name, cost, billing cycle, renewal day, and category.
    """
    db = get_firestore_client()
    query = db.collection(COLLECTION_NAME)
    if category:
        query = query.where("category", "==", category)

    docs = query.stream()
    subscriptions = []
    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id
        subscriptions.append(data)
    return subscriptions


def get_subscription_details(name_or_id: str) -> Dict[str, Any]:
    """Retrieves detailed information for a specific subscription by its ID or name.

    Args:
        name_or_id: The document ID or service name of the subscription (e.g., 'netflix', 'Spotify Duo').

    Returns:
        The subscription details dictionary, or an error message if not found.
    """
    db = get_firestore_client()
    doc_ref = db.collection(COLLECTION_NAME).document(name_or_id.lower().replace(" ", "_"))
    doc = doc_ref.get()
    if doc.exists:
        data = doc.to_dict()
        data["id"] = doc.id
        return data

    # Fallback to searching by name
    all_docs = db.collection(COLLECTION_NAME).stream()
    for d in all_docs:
        item = d.to_dict()
        if name_or_id.lower() in item.get("name", "").lower():
            item["id"] = d.id
            return item

    return {"error": f"Subscription '{name_or_id}' not found."}


def add_or_update_subscription(
    name: str,
    cost: float,
    category: str = "General",
    billing_cycle: str = "monthly",
    currency: str = "USD",
    renewal_day: int = 1,
    cancellation_difficulty: str = "medium",
    description: str = "",
) -> Dict[str, Any]:
    """Adds a new subscription or updates an existing subscription in Firestore.

    Args:
        name: Name of the subscription service (e.g. 'YouTube Premium', 'iCloud+').
        cost: The recurring fee/amount (e.g., 13.99).
        category: Category such as 'Entertainment', 'Productivity', 'Utilities', 'Health & Fitness'.
        billing_cycle: Billing interval, e.g., 'monthly', 'annual', 'weekly'. Default is 'monthly'.
        currency: Currency code (e.g., 'USD', 'TWD', 'EUR'). Default is 'USD'.
        renewal_day: Day of the month the subscription renews (1-31).
        cancellation_difficulty: Difficulty of canceling ('easy', 'medium', 'hard').
        description: Brief description or notes about the plan.

    Returns:
        A confirmation message with the saved subscription data.
    """
    db = get_firestore_client()
    doc_id = re.sub(r"[^a-z0-9_]", "", name.lower().replace(" ", "_"))
    if not doc_id:
        doc_id = "custom_sub"

    sub_data = {
        "id": doc_id,
        "name": name,
        "cost": float(cost),
        "category": category,
        "billing_cycle": billing_cycle,
        "currency": currency,
        "renewal_day": int(renewal_day),
        "status": "active",
        "cancellation_difficulty": cancellation_difficulty,
        "description": description,
    }

    doc_ref = db.collection(COLLECTION_NAME).document(doc_id)
    doc_ref.set(sub_data, merge=True)

    return {
        "status": "success",
        "message": f"Subscription '{name}' successfully saved.",
        "subscription": sub_data,
    }


def delete_subscription(name_or_id: str) -> Dict[str, str]:
    """Cancels and removes a subscription from the Firestore tracking list.

    Args:
        name_or_id: The ID or name of the subscription to remove.

    Returns:
        A status message indicating success or failure.
    """
    db = get_firestore_client()
    doc_id = re.sub(r"[^a-z0-9_]", "", name_or_id.lower().replace(" ", "_"))
    doc_ref = db.collection(COLLECTION_NAME).document(doc_id)
    if doc_ref.get().exists:
        doc_ref.delete()
        return {"status": "success", "message": f"Subscription '{name_or_id}' removed from tracking."}

    # Search by name match
    all_docs = db.collection(COLLECTION_NAME).stream()
    for d in all_docs:
        item = d.to_dict()
        if name_or_id.lower() in item.get("name", "").lower():
            d.reference.delete()
            return {"status": "success", "message": f"Subscription '{item.get('name')}' removed from tracking."}

    return {"status": "error", "message": f"Subscription '{name_or_id}' was not found."}


def simulate_savings_growth(
    monthly_savings: float,
    annual_return_rate: float = 0.05,
    years: int = 3,
) -> Dict[str, Any]:
    """Calculates compound growth and total money saved if monthly savings are invested over time.

    Args:
        monthly_savings: Amount saved per month (e.g. 150.0).
        annual_return_rate: Expected annual investment return rate in decimal (e.g. 0.05 for 5%). Default is 0.05.
        years: Number of years to project savings for (e.g. 1, 3, 5, 10). Default is 3.

    Returns:
        A dictionary with total deposited, compound interest earned, and final projected portfolio balance.
    """
    total_months = max(1, int(years * 12))
    monthly_rate = float(annual_return_rate) / 12.0
    balance = 0.0

    for _ in range(total_months):
        balance = (balance + float(monthly_savings)) * (1.0 + monthly_rate)

    total_deposited = float(monthly_savings) * total_months
    interest_earned = balance - total_deposited

    return {
        "monthly_savings": float(monthly_savings),
        "years": int(years),
        "annual_return_rate_percent": round(annual_return_rate * 100, 2),
        "total_principal_saved": round(total_deposited, 2),
        "compound_interest_earned": round(interest_earned, 2),
        "projected_total_balance": round(balance, 2),
    }


def convert_currency_rate(
    amount: float,
    from_currency: str = "USD",
    to_currency: str = "TWD",
) -> Dict[str, Any]:
    """Converts a subscription fee from one currency to another using real-time exchange rates.

    Args:
        amount: The monetary amount to convert (e.g. 14.99).
        from_currency: The base 3-letter currency code (e.g. 'USD', 'EUR', 'GBP'). Default is 'USD'.
        to_currency: The target 3-letter currency code (e.g. 'TWD', 'JPY', 'EUR', 'CAD'). Default is 'TWD'.

    Returns:
        A dictionary with original amount, converted amount, exchange rate, and last updated time.
    """
    import json
    import os
    import urllib.request

    base_curr = from_currency.upper().strip()
    target_curr = to_currency.upper().strip()

    # Optional API key support if set in env, otherwise uses open tier endpoint
    api_key = os.getenv("EXCHANGE_RATE_API_KEY")
    if api_key:
        url = f"https://v6.exchangerate-api.com/v6/{api_key}/latest/{base_curr}"
    else:
        url = f"https://open.er-api.com/v6/latest/{base_curr}"

    req = urllib.request.Request(url, headers={"User-Agent": "SubTrackBudgetCopilot/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"error": f"Failed to retrieve live exchange rates: {str(e)}"}

    if data.get("result") != "success":
        return {"error": f"Currency exchange rate API returned non-success result: {data.get('error-type', 'unknown')}"}

    rates = data.get("rates", {})
    rate = rates.get(target_curr)
    if rate is None:
        return {"error": f"Exchange rate for currency '{target_curr}' not found."}

    converted_amount = round(float(amount) * float(rate), 2)

    return {
        "original_amount": float(amount),
        "from_currency": base_curr,
        "to_currency": target_curr,
        "exchange_rate": float(rate),
        "converted_amount": converted_amount,
        "last_updated": data.get("time_last_update_utc", ""),
    }


def geocode_address(address: str) -> Dict[str, Any]:
    """Turns a human-readable street address or landmark into geographic coordinates (latitude and longitude).

    Args:
        address: The address or place to look up (e.g. '1600 Amphitheatre Pkwy, Mountain View, CA' or 'Times Square, New York').

    Returns:
        A dictionary containing formatted address, latitude, and longitude.
    """
    import json
    import os
    import urllib.parse
    import urllib.request

    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return {"error": "GOOGLE_MAPS_API_KEY environment variable is not configured."}

    encoded_address = urllib.parse.quote(address)
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={encoded_address}&key={api_key}"

    req = urllib.request.Request(url, headers={"User-Agent": "SubTrackBudgetCopilot/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"error": f"Failed to call Geocoding API: {str(e)}"}

    if data.get("status") != "OK" or not data.get("results"):
        return {"error": f"Geocoding failed with status: {data.get('status', 'ZERO_RESULTS')}"}

    result = data["results"][0]
    loc = result.get("geometry", {}).get("location", {})

    return {
        "formatted_address": result.get("formatted_address", address),
        "location": {
            "latitude": loc.get("lat"),
            "longitude": loc.get("lng"),
        },
    }


def find_nearby_places(
    latitude: float,
    longitude: float,
    place_type: str = "gym",
    radius_meters: float = 1500.0,
    max_results: int = 5,
) -> Dict[str, Any]:
    """Finds nearby places of a specific type (e.g. gym, cafe, library) using Google Places API (New).

    Args:
        latitude: Latitude coordinate of the center point (e.g. 40.7580).
        longitude: Longitude coordinate of the center point (e.g. -73.9855).
        place_type: Place type to search for (e.g. 'gym', 'fitness_center', 'cafe', 'library', 'bank'). Default is 'gym'.
        radius_meters: Search radius in meters (up to 50000). Default is 1500.0.
        max_results: Maximum number of results to return (1-20). Default is 5.

    Returns:
        A dictionary with a list of matching places containing name, formatted address, and location coordinates.
    """
    import json
    import os
    import urllib.request

    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return {"error": "GOOGLE_MAPS_API_KEY environment variable is not configured."}

    url = "https://places.googleapis.com/v1/places:searchNearby"
    payload = {
        "includedTypes": [place_type.lower().strip()],
        "maxResultCount": min(max(1, int(max_results)), 20),
        "locationRestriction": {
            "circle": {
                "center": {
                    "latitude": float(latitude),
                    "longitude": float(longitude),
                },
                "radius": float(radius_meters),
            }
        },
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location",
            "User-Agent": "SubTrackBudgetCopilot/1.0",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"error": f"Failed to call Places API (New): {str(e)}"}

    raw_places = data.get("places", [])
    places = []
    for p in raw_places:
        places.append({
            "name": p.get("displayName", {}).get("text", "Unknown"),
            "address": p.get("formattedAddress", ""),
            "location": p.get("location", {}),
        })

    return {
        "place_type": place_type,
        "count": len(places),
        "places": places,
    }


def generate_milestone_badge(
    milestone_title: str,
    tool_context: ToolContext,
    description: str = "",
) -> Dict[str, Any]:
    """Generates a personalized financial milestone badge or achievement celebration visual.

    Uses gemini-3.1-flash-lite-image in the global region.
    Saves the image as an ADK artifact and uploads it to public Cloud Storage, returning the public HTTPS URL.

    Args:
        milestone_title: Title of the milestone (e.g. 'Saved $500 Milestone', 'Cancelled 3 Subscriptions', 'Budget Master Badge').
        tool_context: ADK ToolContext used to save the artifact to the session.
        description: Optional details about the achievement to enrich the visual prompt.

    Returns:
        A dictionary with the milestone title, public HTTPS URL of the image, and artifact filename.
    """
    # 1. Initialize GenAI client with global location and Vertex AI
    ai_client = genai.Client(vertexai=True, project=PROJECT_ID, location="global")

    prompt = (
        f"A beautiful, high quality 3D glossy achievement badge medal icon celebrating financial milestone: '{milestone_title}'. "
        f"Context: {description}. Clean modern graphics, vibrant colors, premium finish, isolated on a clean simple background."
    )

    response = ai_client.models.generate_content(
        model=IMAGE_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE"],
        ),
    )

    image_bytes = None
    mime_type = "image/jpeg"
    if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
        for part in response.candidates[0].content.parts:
            if part.inline_data and part.inline_data.data:
                image_bytes = part.inline_data.data
                mime_type = part.inline_data.mime_type or "image/jpeg"
                break

    if not image_bytes:
        return {"error": "Failed to generate image: No image data returned by model."}

    # 2. Save image as an artifact in ToolContext
    filename = f"milestone_{uuid.uuid4().hex[:8]}.jpg"
    tool_context.save_artifact(
        filename=filename,
        artifact=types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
        custom_metadata={"milestone": milestone_title},
    )

    # 3. Upload image bytes to public Cloud Storage bucket
    storage_client = storage.Client(project=PROJECT_ID)
    bucket = storage_client.bucket(BUCKET_NAME)
    blob_name = f"milestones/{filename}"
    blob = bucket.blob(blob_name)
    blob.upload_from_string(image_bytes, content_type=mime_type)

    public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{blob_name}"

    return {
        "milestone_title": milestone_title,
        "filename": filename,
        "image_url": public_url,
        "message": f"Milestone badge '{milestone_title}' successfully created and published.",
    }


def generate_domain_video(
    item_title: str,
    tool_context: ToolContext,
    description: str = "",
) -> Dict[str, Any]:
    """Generates a short animated video for a subscription service, savings goal, or financial milestone using Google's Omni model.

    Uses gemini-omni-flash-preview in the global region.
    (1) Saves the generated video bytes as an ADK artifact with tool_context.save_artifact so it shows up in the Playground's Artifacts panel.
    (2) Uploads the same video bytes to the public Cloud Storage bucket and returns its public HTTPS URL (https://storage.googleapis.com/<bucket>/<object>).

    Args:
        item_title: Name of the subscription item, milestone, or concept (e.g., 'Netflix Subscription Cancelled', 'Savings Growth Celebration', 'Budget Mastery').
        tool_context: ADK ToolContext used to save the artifact to the session.
        description: Optional details describing the visual story, scene, or action.

    Returns:
        A dictionary containing the video public HTTPS URL, artifact filename, and status message.
    """
    ai_client = genai.Client(vertexai=True, project=PROJECT_ID, location="global")

    video_prompt = (
        f"A crisp 3D animated financial celebration video about '{item_title}'. "
        f"Visual details: {description or 'A shiny piggy bank, coins bouncing with joy, budget charts glowing in modern green style, smooth cinematic lighting.'} "
        f"Continuous smooth motion, vibrant fintech aesthetic, 4k quality feel."
    )

    interaction = ai_client.interactions.create(
        model=VIDEO_MODEL,
        input=video_prompt,
    )

    video_bytes = None
    mime_type = "video/mp4"

    if hasattr(interaction, "output_video") and interaction.output_video:
        raw_data = getattr(interaction.output_video, "data", None)
        if raw_data:
            if isinstance(raw_data, str):
                video_bytes = base64.b64decode(raw_data)
            elif isinstance(raw_data, bytes):
                video_bytes = raw_data
        mime_type = getattr(interaction.output_video, "mime_type", None) or "video/mp4"

    if not video_bytes and getattr(interaction, "steps", None):
        for step in reversed(interaction.steps):
            if getattr(step, "type", None) == "model_output":
                content = getattr(step, "content", None) or []
                for item in content:
                    if getattr(item, "type", None) == "video":
                        raw_data = getattr(item, "data", None)
                        if raw_data:
                            if isinstance(raw_data, str):
                                video_bytes = base64.b64decode(raw_data)
                            elif isinstance(raw_data, bytes):
                                video_bytes = raw_data
                        mime_type = getattr(item, "mime_type", None) or "video/mp4"
                        break
            if video_bytes:
                break

    if not video_bytes:
        return {"error": "Failed to generate video: No video data returned by Gemini Omni."}

    # 1. Save artifact in ToolContext for Playground Artifacts panel
    filename = f"video_{uuid.uuid4().hex[:8]}.mp4"
    tool_context.save_artifact(
        filename=filename,
        artifact=types.Part.from_bytes(data=video_bytes, mime_type=mime_type),
        custom_metadata={"item_title": item_title},
    )

    # 2. Upload video bytes to public Cloud Storage bucket
    storage_client = storage.Client(project=PROJECT_ID)
    bucket = storage_client.bucket(BUCKET_NAME)
    blob_name = f"videos/{filename}"
    blob = bucket.blob(blob_name)
    blob.upload_from_string(video_bytes, content_type=mime_type)

    public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{blob_name}"

    return {
        "item_title": item_title,
        "filename": filename,
        "video_url": public_url,
        "message": f"Short video for '{item_title}' successfully generated and published.",
    }


SANDBOX_RESOURCE_NAME = "projects/839496478503/locations/us-east1/reasoningEngines/2536290750790893568/sandboxEnvironments/3545883218135744512"


async def generate_memories_callback(callback_context: CallbackContext):
    """Saves session turn events to Memory Bank for cross-session recall."""
    await callback_context.add_session_to_memory()
    return None


schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

a2ui_instruction = schema_manager.generate_system_prompt(
    role_description="""You are SubTrack & Budget Copilot, a helpful financial copilot specializing in recurring subscriptions and budget management.
You help users keep track of their monthly recurring costs, discover and manage subscriptions, add new expenses, and identify opportunities to save money.
You remember the user's stated preferences, budget goals, financial priorities, personal facts, and critically all user allergies (food, drug, environmental) or dietary restrictions from previous conversations and use them to personalize your responses and recommendations.
When users mention any allergies or dietary restrictions, acknowledge them and keep them in mind for any food or dining-related recommendations.
When users ask about their active subscriptions, always consult the Firestore tools to fetch real-time records.
When users ask about potential savings or investing what they saved, use simulate_savings_growth to show compound projections.
When users ask for costs in different currencies (e.g. TWD, EUR, JPY) or international conversion, use convert_currency_rate to get live rates.
When users look for alternative local services (such as alternative gyms, co-working spaces, cafes) near an address, use geocode_address followed by find_nearby_places to discover local options.
When users reach a savings goal, celebrate a financial milestone, or request an achievement badge, use generate_milestone_badge to generate and share the badge image URL.
When users want a celebration video, promotional clip, or animated visual summary for a subscription, financial milestone, or savings accomplishment, use generate_domain_video to generate a short video and share its public video URL.
You have access to a secure Python sandbox code execution environment. When asked to perform complex financial modeling, simulations, or mathematical verification using Python, write and execute Python code in the sandbox.
Present costs, renewal dates, and categories clearly.""",
    workflow_description="Analyze the request and return structured UI when appropriate.",
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        "{\"Image\": {\"url\": {\"literalString\": \"https://...\"}}}. Never point an "
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
        "headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
    ),
    include_schema=True,
    include_examples=True,
)


root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=a2ui_instruction,
    code_executor=AgentEngineSandboxCodeExecutor(
        sandbox_resource_name=SANDBOX_RESOURCE_NAME,
    ),
    tools=[
        PreloadMemoryTool(),
        list_subscriptions,
        get_subscription_details,
        add_or_update_subscription,
        delete_subscription,
        simulate_savings_growth,
        convert_currency_rate,
        geocode_address,
        find_nearby_places,
        generate_milestone_badge,
        generate_domain_video,
    ],
    after_model_callback=a2ui_callback,
    after_agent_callback=generate_memories_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)
