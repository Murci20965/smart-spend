import asyncio
import logging
import re

import httpx
from openai import AsyncOpenAI

from app.core.config import settings

# Regex to detect 7–16 digit account numbers
PII_REGEX = r"\b(?:\d[ -]*?){7,16}\b"

logger = logging.getLogger("smart_spend.ai_service")


def sanitize_description(description: str) -> str:
    """
    Mask any 7–16 digit sequences to protect privacy.
    Example: 'PAYMENT 12345678' -> 'PAYMENT [REDACTED]'
    """
    if not isinstance(description, str):
        return description
    return re.sub(PII_REGEX, "[REDACTED]", description)


async def predict_category(text: str) -> str:
    """
    HuggingFace zero-shot classification with simple rate limiting.
    If the HF_TOKEN is missing or the request fails, return 'Uncategorized'.
    """
    API_URL = "https://router.huggingface.co/models/" "valhalla/distilbart-mnli-12-1"

    headers = {"Authorization": f"Bearer {settings.HF_TOKEN}"}

    candidate_labels = [
        "Groceries",
        "Rent",
        "Transport",
        "Utilities",
        "Dining",
        "Shopping",
        "Medical",
        "Entertainment",
        "Uncategorized",
    ]

    payload = {
        "inputs": text,
        "parameters": {"candidate_labels": candidate_labels},
    }

    if not settings.HF_TOKEN:
        logger.info(
            "No HF_TOKEN configured, returning 'Uncategorized' from predict_category"
        )
        return "Uncategorized"

    try:
        async with httpx.AsyncClient(timeout=40.0) as client:
            response = await client.post(API_URL, headers=headers, json=payload)
            # Ensure HTTP-level errors are surfaced
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as err:
                logger.warning(
                    "HuggingFace API returned status %s: %s", response.status_code, err
                )
                return "Uncategorized"

            result = response.json()

        # HuggingFace free-tier rate limit (1 request/sec)
        await asyncio.sleep(1.0)

        if (
            isinstance(result, list)
            and len(result) > 0
            and "labels" in result[0]
            and len(result[0]["labels"]) > 0
        ):
            return result[0]["labels"][0]
        else:
            logger.warning("AI CATEGORY ERROR: unexpected response: %s", result)
            return "Uncategorized"
    except Exception as e:
        logger.exception("AI CATEGORY EXCEPTION: %s", e)
        return "Uncategorized"


# =============================================================
# AI COACH — Generate Spending Advice
# =============================================================


def _generate_rule_based_advice(month: str, spent: float, budget: float) -> str:
    """
    Generate financial advice using rule-based logic (fallback when LLM is unavailable).
    Returns 3 actionable bullet points.
    """
    advice_points = []

    # Calculate percentage of budget used
    if budget > 0:
        percentage_used = (spent / budget) * 100
        remaining = budget - spent
    else:
        percentage_used = 0
        remaining = 0

    # Generate advice based on spending patterns
    if spent > budget:
        overspend = spent - budget
        overspend_str = f"${overspend:.2f}"
        advice_points.append(
            "* You've exceeded your budget by "
            + overspend_str
            + ". Review discretionary spending this month."
        )
        advice_points.append(
            "* Consider cutting back on non-essential expenses to get back on "
            "track."
        )
        advice_points.append(
            "* Set up spending alerts to monitor your progress more closely."
        )
    elif percentage_used >= 90:
        perc = f"{percentage_used:.1f}%"
        remaining_str = f"${remaining:.2f}"
        advice_points.append(
            "* You've used " + perc + " of your budget. Be mindful of remaining "
            "expenses."
        )
        advice_points.append(
            "* You have "
            + remaining_str
            + " remaining. Prioritize essential purchases only."
        )
        advice_points.append("* Track daily spending to ensure you stay within budget.")
    elif percentage_used >= 70:
        perc = f"{percentage_used:.1f}%"
        remaining_str = f"${remaining:.2f}"
        advice_points.append(
            "* You've used " + perc + " of your budget. You're on track!"
        )
        advice_points.append(
            "* You have "
            + remaining_str
            + " remaining for the rest of "
            + month
            + "."
        )
        advice_points.append(
            "* Continue monitoring your spending to maintain this healthy pace."
        )
    elif percentage_used >= 50:
        perc = f"{percentage_used:.1f}%"
        remaining_str = f"${remaining:.2f}"
        advice_points.append(
            "* Great job! You've used "
            + perc
            + " of your budget with "
            + remaining_str
            + " remaining."
        )
        advice_points.append(
            "* You're spending at a sustainable rate. Keep up the good habits!"
        )
        advice_points.append(
            "* Consider saving leftover budget for future months or unexpected needs."
        )
    else:
        perc = f"{percentage_used:.1f}%"
        remaining_str = f"${remaining:.2f}"
        advice_points.append(
            "* Excellent! You've only used "
            + perc
            + " of your budget."
        )
        advice_points.append(
            "* You have "
            + remaining_str
            + " remaining. This is a great opportunity to build savings."
        )
        advice_points.append(
            "* Consider allocating some of the remaining budget to an emergency fund."
        )

    return "\n".join(advice_points)


async def generate_spending_advice(month: str, spent: float, budget: float) -> str:
    """
    Generate concise financial insights for the given month.
    Uses HuggingFace OpenAI-compatible API with a Llama model.
    Falls back to rule-based advice if an LLM is not available.

    Returns:
        tuple[str, str]: (advice_text, source) where source is "ai" or "rule_based".
    """

    # Check if HF_TOKEN is configured (not empty string)
    hf_token = settings.HF_TOKEN.strip() if settings.HF_TOKEN else ""

    if not hf_token:
        logger.info("AI ADVICE: No HF_TOKEN configured; using rule-based advice")
        logger.info("Enable AI advice by setting HF_TOKEN in your .env file")
        logger.info("Get token: https://huggingface.co/settings/tokens")
        return _generate_rule_based_advice(month, spent, budget)

    # Use OpenAI-compatible API via HuggingFace router
    model_id = "meta-llama/Llama-3.1-8B-Instruct:novita"

    client = None
    http_client = None
    try:
        logger.info("AI ADVICE: Using model %s via HF router", model_id)

        # Create OpenAI client with HuggingFace router endpoint
        # Use http_client parameter to avoid proxies issue with httpx
        import httpx as httpx_lib

        http_client = httpx_lib.AsyncClient(timeout=30.0)
        client = AsyncOpenAI(
            base_url="https://router.huggingface.co/v1",
            api_key=hf_token,
            http_client=http_client,
        )

        # Calculate spending metrics for more personalized advice
        percentage_used = (spent / budget * 100) if budget > 0 else 0
        remaining = budget - spent

        # Create a detailed prompt for financial advice based on spending data
        prompt_parts = [
            "You are a financial coach analyzing spending data from a bank statement.",
            f"In {month}, the user spent ${spent:.2f}.",
            f"The monthly budget was ${budget:.2f}.",
            f"({percentage_used:.1f}% used, ${remaining:.2f} left).",
            "Provide exactly 3 concise, actionable financial advice bullet points.",
            "Each point should:",
            "- Start with '* ' (asterisk and space)",
            "- Be specific to their spending situation",
            "- Be practical and actionable",
            "- Be 1-2 sentences maximum",
            "Do NOT include introductory text, explanations, or meta-commentary.",
            "Only output the 3 bullet points, one per line.",
        ]
        prompt = "\n\n".join(prompt_parts)

        # Call the chat completion API
        completion = await client.chat.completions.create(
            model=model_id,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.7,
        )

        # Extract the generated text
        generated_text = completion.choices[0].message.content

        logger.info(
            "AI ADVICE: Received response from %s, length: %s",
            model_id,
            len(generated_text) if generated_text else 0,
        )

        if generated_text and len(generated_text.strip()) > 20:
            # Clean and format the response
            text = generated_text.strip()

            # Remove common prefixes the model might add
            prefixes_to_remove = [
                "Based on your situation,",
                "Here are three",
                "Here are 3",
                "As a financial coach,",
                "Here's my advice:",
                "Here is my advice:",
            ]
            for prefix in prefixes_to_remove:
                if text.startswith(prefix):
                    text = text[len(prefix) :].strip()

            # Split into lines and clean
            lines = [line.strip() for line in text.split("\n") if line.strip()]

            # Extract bullet points (look for lines starting with *, -, •, or numbered)
            formatted_lines = []
            for line in lines:
                # Remove bullet markers and clean
                cleaned = line.lstrip("*- •0123456789.").strip()
                # Remove any remaining asterisks in the middle of sentences
                cleaned = cleaned.replace("*", "").strip()

                if len(cleaned) > 10 and not any(
                    word in cleaned.lower()
                    for word in ["here are", "based on", "as a financial"]
                ):
                    formatted_lines.append(f"* {cleaned}")

                if len(formatted_lines) >= 3:
                    break

            if len(formatted_lines) >= 1:
                logger.info(
                    "AI ADVICE: Successfully generated AI advice using %s", model_id
                )
                return "\n".join(formatted_lines)

        # If LLM response is too short or malformed, use fallback
        logger.warning(
            "AI ADVICE: Response insufficient; using rule-based fallback"
        )
        return _generate_rule_based_advice(month, spent, budget)

    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)
        logger.exception(
            "AI ADVICE: %s failed with exception: %s: %s",
            model_id,
            error_type,
            error_msg,
        )

        # Check for specific error types
        if (
            "401" in error_msg
            or "Unauthorized" in error_msg
            or "authentication" in error_msg.lower()
        ):
            logger.error("Authentication failed - check your HF_TOKEN")
            logger.error("Verify your token at: https://huggingface.co/settings/tokens")
        elif "404" in error_msg or "not found" in error_msg.lower():
            logger.error("Model not found - the model may not be available")
        elif "429" in error_msg or "rate limit" in error_msg.lower():
            logger.error("Rate limit exceeded - please wait a moment and try again")
        # Use rule-based fallback on any error
        logger.info("AI ADVICE: Using rule-based fallback")
        return _generate_rule_based_advice(month, spent, budget)

    finally:
        # Ensure clients are properly closed
        if client:
            try:
                await client.close()
            except Exception:
                pass  # Ignore cleanup errors
        if http_client:
            try:
                await http_client.aclose()
            except Exception:
                pass  # Ignore cleanup errors
