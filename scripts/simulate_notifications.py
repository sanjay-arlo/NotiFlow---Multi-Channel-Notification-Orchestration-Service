#!/usr/bin/env python3
"""
Script to simulate notification sending for testing and load testing.
"""

import asyncio
import argparse
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List

import httpx


class NotificationSimulator:
    """Simulate notification sending for testing."""
    
    def __init__(self, api_url: str, api_key: str):
        self.api_url = api_url.rstrip('/')
        self.api_key = api_key
        self.client = httpx.AsyncClient(
            headers={"X-API-Key": api_key},
            timeout=30.0
        )
    
    async def send_single_notification(
        self,
        user_id: str,
        title: str,
        body: str,
        channels: List[str] = None,
        priority: str = "normal"
    ) -> Dict:
        """Send a single notification."""
        payload = {
            "user_id": user_id,
            "title": title,
            "body": body,
            "channels": channels,
            "priority": priority
        }
        
        try:
            response = await self.client.post(
                f"{self.api_url}/api/v1/notifications/send",
                json=payload
            )
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "notification_id": response.json()["id"],
                    "status": response.json()["status"]
                }
            else:
                return {
                    "success": False,
                    "error": response.text,
                    "status_code": response.status_code
                }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def send_batch_notifications(
        self,
        user_ids: List[str],
        title: str,
        body: str,
        channels: List[str] = None,
        priority: str = "normal"
    ) -> Dict:
        """Send batch notifications."""
        payload = {
            "user_ids": user_ids,
            "title": title,
            "body": body,
            "channels": channels,
            "priority": priority
        }
        
        try:
            response = await self.client.post(
                f"{self.api_url}/api/v1/notifications/batch",
                json=payload
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    "success": False,
                    "error": response.text,
                    "status_code": response.status_code
                }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_notification_status(self, notification_id: str) -> Dict:
        """Get notification status."""
        try:
            response = await self.client.get(
                f"{self.api_url}/api/v1/notifications/{notification_id}"
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    "success": False,
                    "error": response.text,
                    "status_code": response.status_code
                }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def run_load_test(
        self,
        duration_seconds: int = 60,
        rate_per_second: int = 10,
        user_ids: List[str] = None
    ) -> Dict:
        """Run a load test."""
        if not user_ids:
            user_ids = ["test_user_1", "test_user_2", "test_user_3"]
        
        start_time = time.time()
        end_time = start_time + duration_seconds
        sent_count = 0
        success_count = 0
        error_count = 0
        
        print(f"🚀 Starting load test: {rate_per_second} notifications/second for {duration_seconds} seconds")
        print(f"   Target: {rate_per_second * duration_seconds} notifications")
        print(f"   Users: {len(user_ids)}")
        
        while time.time() < end_time:
            batch_start = time.time()
            
            # Send notifications in batches
            tasks = []
            for i in range(rate_per_second):
                user_id = user_ids[i % len(user_ids)]
                task = self.send_single_notification(
                    user_id=user_id,
                    title=f"Load Test Notification #{sent_count + i + 1}",
                    body=f"This is a load test notification sent at {datetime.now().isoformat()}",
                    priority="normal"
                )
                tasks.append(task)
            
            # Wait for all tasks in this batch
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for result in results:
                sent_count += 1
                if isinstance(result, dict):
                    if result.get("success"):
                        success_count += 1
                    else:
                        error_count += 1
                        print(f"❌ Error: {result.get('error', 'Unknown error')}")
                else:
                    error_count += 1
                    print(f"❌ Exception: {result}")
            
            # Calculate time to wait for next batch
            batch_time = time.time() - batch_start
            wait_time = max(0, 1.0 - batch_time)
            
            if wait_time > 0:
                await asyncio.sleep(wait_time)
        
        total_time = time.time() - start_time
        actual_rate = sent_count / total_time
        
        print(f"\n📊 Load Test Results:")
        print(f"   Duration: {total_time:.2f} seconds")
        print(f"   Sent: {sent_count}")
        print(f"   Success: {success_count}")
        print(f"   Errors: {error_count}")
        print(f"   Success Rate: {(success_count/sent_count)*100:.2f}%")
        print(f"   Actual Rate: {actual_rate:.2f} notifications/second")
        
        return {
            "duration_seconds": total_time,
            "sent_count": sent_count,
            "success_count": success_count,
            "error_count": error_count,
            "success_rate": (success_count/sent_count)*100,
            "actual_rate": actual_rate
        }
    
    async def test_priority_routing(
        self,
        user_id: str
    ) -> Dict:
        """Test priority-based routing."""
        priorities = ["critical", "high", "normal", "low"]
        results = {}
        
        for priority in priorities:
            result = await self.send_single_notification(
                user_id=user_id,
                title=f"Priority Test - {priority.upper()}",
                body=f"This is a {priority} priority test notification sent at {datetime.now().isoformat()}",
                priority=priority
            )
            results[priority] = result
            print(f"📤 Sent {priority} priority notification: {result.get('success', False)}")
        
        return results
    
    async def test_channels(
        self,
        user_id: str
    ) -> Dict:
        """Test different channels."""
        channels = ["email", "sms", "webhook"]
        results = {}
        
        for channel in channels:
            result = await self.send_single_notification(
                user_id=user_id,
                title=f"Channel Test - {channel.upper()}",
                body=f"This is a {channel} test notification sent at {datetime.now().isoformat()}",
                channels=[channel]
            )
            results[channel] = result
            print(f"📤 Sent {channel} notification: {result.get('success', False)}")
        
        return results
    
    async def test_template_rendering(
        self,
        user_id: str,
        template_slug: str
    ) -> Dict:
        """Test template rendering."""
        variables = {
            "name": "Test User",
            "email": "test@example.com",
            "company": "Test Company",
            "reset_link": "https://example.com/reset"
        }
        
        payload = {
            "user_id": user_id,
            "template_slug": template_slug,
            "template_variables": variables
        }
        
        try:
            response = await self.client.post(
                f"{self.api_url}/api/v1/notifications/send",
                json=payload
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"📤 Sent template notification: {result.get('id')}")
                return {
                    "success": True,
                    "notification_id": result.get("id"),
                    "template_used": template_slug,
                    "variables": variables
                }
            else:
                return {
                    "success": False,
                    "error": response.text,
                    "status_code": response.status_code
                }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()


async def main():
    """Main simulation function."""
    parser = argparse.ArgumentParser(description="NotiFlow Notification Simulator")
    parser.add_argument("--url", default="http://localhost:8000", help="API URL")
    parser.add_argument("--key", required=True, help="API Key")
    parser.add_argument("--mode", choices=["single", "batch", "load", "priority", "channels", "template"], required=True, help="Test mode")
    parser.add_argument("--user", default="test_user_1", help="User ID for testing")
    parser.add_argument("--users", nargs="+", help="User IDs for batch testing")
    parser.add_argument("--duration", type=int, default=60, help="Load test duration in seconds")
    parser.add_argument("--rate", type=int, default=10, help="Notifications per second for load test")
    parser.add_argument("--template", default="welcome-email", help="Template slug for template testing")
    
    args = parser.parse_args()
    
    simulator = NotificationSimulator(args.url, args.key)
    
    try:
        if args.mode == "single":
            print("📤 Sending single notification...")
            result = await simulator.send_single_notification(
                user_id=args.user,
                title="Test Notification",
                body="This is a test notification from the simulator."
            )
            print(f"Result: {json.dumps(result, indent=2)}")
        
        elif args.mode == "batch":
            print("📤 Sending batch notifications...")
            result = await simulator.send_batch_notifications(
                user_ids=args.users or ["test_user_1", "test_user_2", "test_user_3"],
                title="Batch Test Notification",
                body="This is a batch test notification."
            )
            print(f"Result: {json.dumps(result, indent=2)}")
        
        elif args.mode == "load":
            print("🚀 Running load test...")
            result = await simulator.run_load_test(
                duration_seconds=args.duration,
                rate_per_second=args.rate,
                user_ids=args.users
            )
            print(f"Result: {json.dumps(result, indent=2)}")
        
        elif args.mode == "priority":
            print("🎯 Testing priority routing...")
            result = await simulator.test_priority_routing(args.user)
            print(f"Result: {json.dumps(result, indent=2)}")
        
        elif args.mode == "channels":
            print("📡 Testing different channels...")
            result = await simulator.test_channels(args.user)
            print(f"Result: {json.dumps(result, indent=2)}")
        
        elif args.mode == "template":
            print("📋 Testing template rendering...")
            result = await simulator.test_template_rendering(
                user_id=args.user,
                template_slug=args.template
            )
            print(f"Result: {json.dumps(result, indent=2)}")
    
    finally:
        await simulator.close()


if __name__ == "__main__":
    asyncio.run(main())
