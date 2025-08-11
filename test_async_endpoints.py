#!/usr/bin/env python3
"""
Test script for async blockchain endpoints.
Validates that the new async system works correctly.
"""
import asyncio
import aiohttp
import json
from datetime import datetime
import sys

BASE_URL = "http://localhost:8000"

async def test_async_market_creation():
    """Test async market creation endpoint"""
    print("🧪 Testing async market creation...")
    
    payload = {
        "application_id": "test-app-123-456-789"
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            # Submit async task
            async with session.post(f"{BASE_URL}/async/create-market", json=payload) as resp:
                if resp.status == 200:
                    task = await resp.json()
                    print(f"✅ Task submitted: {task['task_id']}")
                    print(f"   Estimated time: {task['estimated_completion_time']}")
                    return task['task_id']
                else:
                    error = await resp.text()
                    print(f"❌ Task submission failed: {resp.status} - {error}")
                    return None
        except Exception as e:
            print(f"❌ Request failed: {e}")
            return None

async def test_task_status(task_id):
    """Test task status endpoint"""
    print(f"🔍 Testing task status for {task_id}...")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{BASE_URL}/task-status/{task_id}") as resp:
                if resp.status == 200:
                    status = await resp.json()
                    print(f"✅ Task status: {status['status']}")
                    print(f"   Created: {status['created_at']}")
                    print(f"   Updated: {status['updated_at']}")
                    print(f"   Retry count: {status['retry_count']}/{status['max_retries']}")
                    if status.get('error_message'):
                        print(f"   Error: {status['error_message']}")
                    if status.get('progress'):
                        print(f"   Progress: {status['progress']}")
                    return status
                else:
                    error = await resp.text()
                    print(f"❌ Status check failed: {resp.status} - {error}")
                    return None
        except Exception as e:
            print(f"❌ Request failed: {e}")
            return None

async def test_queue_status():
    """Test queue status endpoint"""
    print("📊 Testing queue status...")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{BASE_URL}/tasks/queue-status") as resp:
                if resp.status == 200:
                    status = await resp.json()
                    print("✅ Queue status retrieved:")
                    print(f"   Pending tasks: {status['queue_metrics']['pending_tasks']}")
                    print(f"   Processing tasks: {status['queue_metrics']['processing_tasks']}")
                    print(f"   Max concurrent: {status['queue_metrics']['max_concurrent_tasks']}")
                    print(f"   Success rate: {status['recent_performance']['success_rate']}%")
                    return status
                else:
                    error = await resp.text()
                    print(f"❌ Queue status failed: {resp.status} - {error}")
                    return None
        except Exception as e:
            print(f"❌ Request failed: {e}")
            return None

async def test_recent_tasks():
    """Test recent tasks endpoint"""
    print("📋 Testing recent tasks...")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{BASE_URL}/tasks/recent?hours=1") as resp:
                if resp.status == 200:
                    tasks = await resp.json()
                    print(f"✅ Found {len(tasks)} recent tasks")
                    for task in tasks[:3]:  # Show first 3 tasks
                        print(f"   - {task['task_id']}: {task['task_type']} ({task['status']})")
                    return tasks
                else:
                    error = await resp.text()
                    print(f"❌ Recent tasks failed: {resp.status} - {error}")
                    return None
        except Exception as e:
            print(f"❌ Request failed: {e}")
            return None

async def test_health_check():
    """Test that the server is running"""
    print("🏥 Testing health check...")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{BASE_URL}/health") as resp:
                if resp.status == 200:
                    health = await resp.json()
                    print("✅ Server is healthy")
                    print(f"   Service: {health['service']}")
                    print(f"   Platform: {health.get('platform', 'unknown')}")
                    if 'environment' in health and 'railway' in health['environment']:
                        railway = health['environment']['railway']
                        print(f"   Railway: {railway.get('is_railway', False)}")
                    return True
                else:
                    print(f"❌ Health check failed: {resp.status}")
                    return False
        except Exception as e:
            print(f"❌ Health check failed: {e}")
            return False

async def main():
    """Main test function"""
    print("🚀 Starting async blockchain endpoints test")
    print("=" * 50)
    
    # Check if server is running
    if not await test_health_check():
        print("❌ Server not responding. Please start the server first:")
        print("   uvicorn src.main:app --reload")
        sys.exit(1)
    
    print("\n" + "=" * 50)
    
    # Test queue status (should work immediately)
    await test_queue_status()
    
    print("\n" + "=" * 50)
    
    # Test recent tasks (should work immediately)
    await test_recent_tasks()
    
    print("\n" + "=" * 50)
    
    # Test async market creation (will demonstrate the flow)
    task_id = await test_async_market_creation()
    
    if task_id:
        print("\n" + "=" * 50)
        
        # Test task status immediately after creation
        await test_task_status(task_id)
        
        print("\n" + "⏰ Note: The actual market creation will run in the background.")
        print(f"   You can check progress with: GET /task-status/{task_id}")
        print("   Expected status progression: pending → processing → completed/failed")
    
    print("\n" + "=" * 50)
    print("✅ Async endpoints test completed!")
    print("\n📖 Usage Guide:")
    print("   - Use /async/* endpoints for non-blocking operations")
    print("   - Poll /task-status/{task_id} to monitor progress")
    print("   - Check /tasks/queue-status for system health")
    print("   - Review ASYNC_BLOCKCHAIN_GUIDE.md for detailed usage")

if __name__ == "__main__":
    asyncio.run(main())