"""
SMS Service
Mock SMS notification service for MVP
(Later: integrate with Twilio or similar)
"""

import os
from typing import Optional

from app.models import Driver


def send_route_sms(
    driver: Driver,
    route_id: str,
    base_url: str = "http://localhost:8000",
) -> tuple[bool, str]:
    """
    Send SMS notification to driver with their route URL

    Args:
        driver: Driver object
        route_id: Unique route ID
        base_url: Base URL for the application

    Returns:
        (success: bool, message: str)
    """
    route_url = f"{base_url}/driver/route/{route_id}"

    # Build SMS message
    sms_body = f"Your Load Logic route is ready: {route_url}"

    # For MVP: Log to console instead of sending real SMS
    print("\n" + "=" * 80)
    print("SMS NOTIFICATION (MOCK)")
    print("=" * 80)
    print(f"To: {driver.phone}")
    print(f"Driver: {driver.name} ({driver.id})")
    print(f"Route ID: {route_id}")
    print(f"Vehicle: {driver.vehicle}")
    print("-" * 80)
    print(f"Message: {sms_body}")
    print("=" * 80 + "\n")

    # TODO: In production, integrate with Twilio:
    # from twilio.rest import Client
    # account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    # auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    # from_number = os.getenv("TWILIO_FROM_NUMBER")
    # client = Client(account_sid, auth_token)
    # message = client.messages.create(
    #     body=sms_body,
    #     from_=from_number,
    #     to=driver.phone
    # )
    # return (True, f"SMS sent: {message.sid}")

    return (True, f"SMS logged (mock) to {driver.phone}")


def send_route_sms_to_drivers(
    driver_info: list[dict],
    base_url: str = "http://localhost:8000",
) -> list[dict]:
    """
    Send SMS to multiple drivers

    Args:
        driver_info: List of {driver: Driver, route_id: str}
        base_url: Base URL for the application

    Returns:
        List of {driver_id, phone, status, message}
    """
    results = []
    for info in driver_info:
        driver = info["driver"]
        route_id = info["route_id"]
        success, message = send_route_sms(driver, route_id, base_url)
        results.append({
            "driver_id": driver.id,
            "phone": driver.phone,
            "status": "sent" if success else "failed",
            "message": message,
            "route_id": route_id,
        })
    return results
